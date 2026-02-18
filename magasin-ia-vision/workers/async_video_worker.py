"""
Async Video Worker for FastAPI
Captures video frames and runs YOLO detection in a background thread
"""
import torch_init  # Fix PyTorch weights_only issue
import asyncio
import cv2
import threading
import queue
from ai.detector import ObjectDetector
from ai.temporal_detection import get_temporal_engine
from services.logger_service import logger

class AsyncVideoWorker:
    def __init__(self, source=0, camera_id=None, model_id="yolov8n", tracker_id=None, segmentation_id=None):
        self.source = source
        self.camera_id = camera_id or str(source)
        self.frame_queue = queue.Queue(maxsize=2)
        self.running = False
        self.thread = None
        self.detector = None
        
        # New model/tracking settings
        self.model_id = model_id
        self.tracker_id = tracker_id # None, "bytetrack.yaml", "botsort.yaml"
        self.segmentation_id = segmentation_id
        
    def start(self):
        """Start the video capture thread"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"AsyncVideoWorker started for source: {self.source}")
        
    def stop(self):
        """Stop the video capture thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("AsyncVideoWorker stopped")

    def switch_model(self, model_id):
        """Switch detection model at runtime"""
        if self.detector:
            success = self.detector.set_model(model_id)
            if success:
                self.model_id = model_id
                logger.info(f"Worker switched to model: {model_id}")
                return True
        return False

    def switch_tracker(self, tracker_id):
        """Switch or disable tracker"""
        # tracker_id can be "bytetrack", "botsort", or None
        if tracker_id == "none" or tracker_id == "" or tracker_id is None:
            self.tracker_id = None
        else:
            self.tracker_id = f"{tracker_id}.yaml"
        logger.info(f"Worker switched tracker to: {self.tracker_id}")
        return True

    def switch_segmenter(self, model_id):
        """Switch or disable segmentation model"""
        if self.detector:
            success = self.detector.set_segmenter(model_id)
            if success:
                self.segmentation_id = model_id
                logger.info(f"Worker switched segmenter to: {model_id}")
                return True
        return False

    def _capture_loop(self):
        """Main capture loop running in background thread"""
        cap = cv2.VideoCapture(self.source)
        
        if not cap.isOpened():
            logger.error(f"Failed to open video source: {self.source}")
            # Fallback for webcam if index 0 or 2 fails
            if isinstance(self.source, int):
                for fallback_idx in [2, 0, 1]:
                    if fallback_idx == self.source: continue
                    logger.info(f"Trying fallback camera index: {fallback_idx}")
                    cap = cv2.VideoCapture(fallback_idx)
                    if cap.isOpened():
                        logger.success(f"Found working camera at index: {fallback_idx}")
                        self.source = fallback_idx
                        break
            
            if not cap.isOpened():
                self.running = False
                return
            
        # Initialize detector
        try:
            self.detector = ObjectDetector(model_path=self.model_id + ".pt")
        except Exception as e:
            logger.error(f"Failed to initialize detector: {e}")
            return
            
        logger.success(f"Video source opened: {self.source}")
        
        import time
        last_frame_time = 0
        target_fps = 20  # Limit capture to 20 FPS to reduce CPU
        frame_interval = 1.0 / target_fps

        while self.running:
            current_time = time.time()
            if current_time - last_frame_time < frame_interval:
                cap.grab() # Just grab, don't decode for skipping
                continue
                
            ret, frame = cap.read()
            last_frame_time = current_time
            
            if not ret:
                logger.warning("Failed to read frame")
                continue
            
            # Optimization: Resize frame if it's too large
            # Increased from 640 to 800 for better sensitivity to distant/side objects
            height, width = frame.shape[:2]
            if height > 800:
                scale = 800 / height
                frame = cv2.resize(frame, (int(width * scale), 800))
                
            # NEW: Orchestrated Vision Pipeline (YOLO + SAM2 + MediaPipe)
            try:
                from ai.vision_pipeline import get_vision_pipeline
                pipeline = get_vision_pipeline(
                    camera_id=self.camera_id, 
                    model_id=self.model_id, 
                    segment=(self.segmentation_id is not None)
                )
                
                annotated_frame, detections, alerts = pipeline.process_frame(
                    frame, 
                    tracker_id=self.tracker_id, 
                    segment=(self.segmentation_id is not None)
                )
                
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                annotated_frame = frame
                detections = []
                alerts = []
                
            # Put frame in queue (non-blocking)
            try:
                # Clear queue if it's lagging to ensure latest frame is always available
                if self.frame_queue.full():
                    try: self.frame_queue.get_nowait()
                    except: pass
                self.frame_queue.put_nowait((annotated_frame, detections, alerts))
            except Exception:
                pass
                
        cap.release()
        logger.info("Video capture released")
        
    def get_frame(self):
        """Get the latest frame (non-blocking)"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
