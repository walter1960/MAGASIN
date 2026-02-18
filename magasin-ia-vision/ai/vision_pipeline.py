"""
MediaPipe-Orchestrated Vision Pipeline for ASECNA Stock Management.
Architecture: MediaPipe (Hands/Flow) -> YOLO (Detection) -> SAM2 (Segmentation) -> Interaction Logic
"""

import cv2
import numpy as np
import time
from typing import List, Dict, Optional, Tuple
from services.logger_service import logger

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MP_AVAILABLE = True
except ImportError:
    logger.warning("MediaPipe not found. VisionPipeline will run in compatibility/mock mode.")
    MP_AVAILABLE = False

from config.settings import settings
from ai.detector import ObjectDetector
from ai.temporal_detection import get_temporal_engine

class VisionPipeline:
    """
    Orchestrator for the intelligent vision pipeline.
    Handles the sequence: Capture -> MediaPipe Hands -> YOLO -> Interaction Logic.
    """
    def __init__(self, camera_id: str, model_id: str = "yolov8n", segment: bool = False):
        self.camera_id = camera_id
        self.detector = ObjectDetector(model_path=f"{model_id}.pt")
        self.segment = segment
        self.temporal_engine = get_temporal_engine()
        
        # MediaPipe initialization
        self.mp_enabled = MP_AVAILABLE
        self.hand_landmarker = None
        self.mp_hands = None
        self.mp_draw = None
        
        if self.mp_enabled:
            try:
                # Attempt to use the Task API first
                base_options = python.BaseOptions(model_asset_path='ai/hand_landmarker.task')
                options = vision.HandLandmarkerOptions(base_options=base_options,
                                                       num_hands=2)
                self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
                logger.success(f"MediaPipe HandLandmarker (Task API) initialized for camera {self.camera_id}")
            except Exception as e:
                logger.warning(f"Could not init MediaPipe HandLandmarker (Task API): {e}. Attempting legacy solution API.")
                # Fallback to legacy solution API if Task API fails
                try:
                    if not hasattr(mp, 'solutions'):
                        raise ImportError("MediaPipe solutions not found")
                    
                    self.mp_hands = mp.solutions.hands.Hands(
                        static_image_mode=False,
                        max_num_hands=2,
                        min_detection_confidence=0.5
                    )
                    self.mp_draw = mp.solutions.drawing_utils
                    self.hand_landmarker = "legacy" # Indicate using legacy API
                    logger.success(f"MediaPipe Hands (Solution API) initialized for camera {self.camera_id}")
                except Exception as e_legacy:
                    logger.warning(f"Could not init MediaPipe Hands (Solution API): {e_legacy}. MediaPipe disabled for this pipeline.")
                    self.mp_enabled = False
            
        self.tracked_objects = {}  # {track_id: object_data}
        self.last_process_time = 0
        self.current_tracker = None
        
    def process_frame(self, frame: np.ndarray, tracker_id: Optional[str] = None, segment: Optional[bool] = None) -> Tuple[np.ndarray, List[Dict], List[Dict]]:
        start_time = time.time()
        
        # Update flags if provided
        if segment is not None:
            self.segment = segment
            
        detections = []
        alerts = []
        hands_data = []
        annotated_frame = frame.copy()
        
        # Sync segmenter/segment flag
        self.current_tracker = tracker_id
        
        # 1. MediaPipe Hands Detection
        if self.mp_enabled:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            if self.hand_landmarker == "legacy":
                results_hands = self.mp_hands.process(rgb_frame)
                if results_hands.multi_hand_landmarks:
                    for hand_landmarks in results_hands.multi_hand_landmarks:
                        # Draw landmarks
                        mp.solutions.drawing_utils.draw_landmarks(
                            annotated_frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                        
                        # Store simple centroid for interaction logic
                        h, w, c = frame.shape
                        cx = int(hand_landmarks.landmark[9].x * w) # Middle finger MCP
                        cy = int(hand_landmarks.landmark[9].y * h)
                        hands_data.append({"id": "hand", "pos": (cx, cy)})

        # 2. YOLO Detection & 3. SAM2 Segmentation
        results = self.detector.predict(
            frame, 
            conf=settings.CONFIDENCE_THRESHOLD, 
            tracker=self.current_tracker,
            segment=self.segment
        )
        
        current_frame_ids = set()
        
        if results and len(results) > 0:
            result = results[0]
            # Overlay YOLO results on top of MediaPipe drawings
            annotated_frame = result.plot(img=annotated_frame)
            
            if result.boxes:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = self.detector.model.names[cls_id]
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].tolist()
                    
                    # Unified ID
                    track_id = str(int(box.id[0])) if box.is_track else f"temp_{int(time.time()*1000)}"
                    current_frame_ids.add(track_id)
                    
                    # Logic: Interaction/Handling Detection
                    status = "stable"
                    for hand in hands_data:
                        hx, hy = hand["pos"]
                        # Check if hand is inside bbox
                        if xyxy[0] < hx < xyxy[2] and xyxy[1] < hy < xyxy[3]:
                            status = "handling"
                            # Draw interaction line
                            cv2.line(annotated_frame, (hx, hy), (int((xyxy[0]+xyxy[2])/2), int((xyxy[1]+xyxy[3])/2)), (0, 0, 255), 2)
                            cv2.putText(annotated_frame, "HANDLING", (int(xyxy[0]), int(xyxy[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                            logger.info(f"Interaction détectée: Main sur {cls_name} ({track_id})")

                    # Update Temporal Engine
                    temporal_status = self.temporal_engine.process_detection(
                        object_type=cls_name,
                        camera_id=self.camera_id,
                        confidence=conf,
                        bbox_coords=tuple(xyxy),
                        tracking_id=track_id
                    )
                    
                    if temporal_status == "stable":
                        self.temporal_engine.create_validation_request(cls_name, self.camera_id)
                    
                    detections.append({
                        "id": track_id,
                        "class": cls_name,
                        "confidence": conf,
                        "bbox": xyxy,
                        "status": status if status == "handling" else temporal_status,
                        "interaction": status == "handling"
                    })

        # Measure performance
        process_duration = time.time() - start_time
        self.last_process_time = process_duration
        
        return annotated_frame, detections, alerts

# Factory for pipelines
_pipelines = {}

def get_vision_pipeline(camera_id: str, model_id: str = "yolov8n", segment: bool = False) -> VisionPipeline:
    if camera_id not in _pipelines:
        _pipelines[camera_id] = VisionPipeline(camera_id, model_id, segment)
    return _pipelines[camera_id]
