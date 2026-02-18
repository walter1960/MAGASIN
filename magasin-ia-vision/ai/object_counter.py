"""
Object Counter Engine for ASECNA Stock Management System

Counts objects in specific zones using YOLO detection and ROI filtering.
Supports automatic quantity tracking for inventory management.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import logging

from ai.detector import ObjectDetector

logger = logging.getLogger(__name__)


@dataclass
class CountResult:
    """Result of an object counting operation"""
    class_name: str
    count: int
    confidence: float
    timestamp: datetime
    detections: List[Tuple[float, float, float, float]]  # [(x1, y1, x2, y2), ...]


class ObjectCounter:
    """
    Counts objects in video frames using YOLO detection.
    
    Features:
    - ROI-based counting (only count objects in specific regions)
    - Multiple class support
    - Confidence filtering
    - Entry/exit detection across lines
    """
    
    def __init__(self, model_path: str = "yolov8n.pt"):
        """
        Initialize object counter.
        
        Args:
            model_path: Path to YOLO model
        """
        self.detector = ObjectDetector(model_path)
        self.class_history: Dict[str, List[int]] = {}  # Track counts over time
        logger.info(f"ObjectCounter initialized with model: {model_path}")
    
    def count_in_roi(
        self,
        frame: np.ndarray,
        roi_coords: List[List[int]],
        target_classes: Optional[List[str]] = None,
        conf_threshold: float = 0.5
    ) -> CountResult:
        """
        Count objects within a Region of Interest (ROI).
        
        Args:
            frame: Input image frame
            roi_coords: ROI polygon coordinates [[x1,y1], [x2,y2], ...]
            target_classes: List of class names to count (None = all)
            conf_threshold: Minimum confidence threshold
            
        Returns:
            CountResult with detected objects and count
        """
        # Run YOLO detection
        results = self.detector.predict(frame, conf=conf_threshold)
        
        if not results or len(results) == 0:
            return CountResult(
                class_name="all" if not target_classes else target_classes[0],
                count=0,
                confidence=0.0,
                timestamp=datetime.now(),
                detections=[]
            )
        
        # Create ROI mask
        roi_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        roi_points = np.array(roi_coords, dtype=np.int32)
        cv2.fillPoly(roi_mask, [roi_points], 255)
        
        # Filter detections by ROI
        detections_in_roi = []
        total_confidence = 0.0
        
        boxes = results[0].boxes
        for box in boxes:
            # Get box center point
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            
            # Check if center is in ROI
            if roi_mask[center_y, center_x] > 0:
                cls_id = int(box.cls[0])
                cls_name = results[0].names[cls_id]
                
                # Filter by target classes if specified
                if target_classes is None or cls_name in target_classes:
                    confidence = float(box.conf[0])
                    detections_in_roi.append((x1, y1, x2, y2))
                    total_confidence += confidence
        
        count = len(detections_in_roi)
        avg_confidence = total_confidence / count if count > 0 else 0.0
        
        return CountResult(
            class_name="all" if not target_classes else target_classes[0],
            count=count,
            confidence=avg_confidence,
            timestamp=datetime.now(),
            detections=detections_in_roi
        )
    
    def count_objects(
        self,
        frame: np.ndarray,
        target_class: str,
        conf_threshold: float = 0.5
    ) -> int:
        """
        Count specific objects in the entire frame.
        
        Args:
            frame: Input image
            target_class: Class name to count (e.g., 'person', 'car')
            conf_threshold: Minimum confidence
            
        Returns:
            Number of detected objects
        """
        results = self.detector.predict(frame, conf=conf_threshold)
        
        if not results or len(results) == 0:
            return 0
        
        count = 0
        boxes = results[0].boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            cls_name = results[0].names[cls_id]
            if cls_name == target_class:
                count += 1
        
        return count
    
    def detect_quantity_change(
        self,
        current_count: int,
        previous_count: int,
        threshold: int = 5
    ) -> Tuple[bool, int, str]:
        """
        Detect significant quantity changes.
        
        Args:
            current_count: Current object count
            previous_count: Previous object count
            threshold: Minimum change to trigger detection
            
        Returns:
            Tuple of (changed, delta, change_type)
            change_type: 'addition', 'removal', or 'none'
        """
        delta = current_count - previous_count
        
        if abs(delta) < threshold:
            return False, delta, 'none'
        
        if delta > 0:
            return True, delta, 'addition'
        else:
            return True, delta, 'removal'
    
    def track_entry_exit(
        self,
        frame: np.ndarray,
        line_coords: Tuple[Tuple[int, int], Tuple[int, int]],
        target_class: str = "person"
    ) -> Dict[str, int]:
        """
        Track objects crossing a line (entry/exit detection).
        
        Args:
            frame: Input frame
            line_coords: ((x1, y1), (x2, y2)) line coordinates
            target_class: Object class to track
            
        Returns:
            Dictionary with 'entries' and 'exits' counts
        """
        # This is a simplified version - full implementation would require
        # tracking object IDs across frames using ByteTrack
        
        results = self.detector.predict(
            frame,
            conf=0.5,
            tracker="bytetrack.yaml"  # Use tracking for persistent IDs
        )
        
        # For now, return placeholder
        # Full implementation needs multi-frame tracking
        return {"entries": 0, "exits": 0}
    
    def update_class_history(self, class_name: str, count: int, max_history: int = 100):
        """
        Update counting history for a class.
        
        Args:
            class_name: Object class name
            count: Current count
            max_history: Maximum history length
        """
        if class_name not in self.class_history:
            self.class_history[class_name] = []
        
        self.class_history[class_name].append(count)
        
        # Keep only recent history
        if len(self.class_history[class_name]) > max_history:
            self.class_history[class_name] = self.class_history[class_name][-max_history:]
    
    def get_average_count(self, class_name: str, window: int = 10) -> float:
        """
        Get average count for a class over recent history.
        
        Args:
            class_name: Object class name
            window: Number of recent counts to average
            
        Returns:
            Average count
        """
        if class_name not in self.class_history:
            return 0.0
        
        recent = self.class_history[class_name][-window:]
        return sum(recent) / len(recent) if recent else 0.0
    
    def draw_roi(
        self,
        frame: np.ndarray,
        roi_coords: List[List[int]],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw ROI polygon on frame for visualization.
        
        Args:
            frame: Input frame
            roi_coords: ROI coordinates
            color: Line color (BGR)
            thickness: Line thickness
            
        Returns:
            Frame with ROI drawn
        """
        frame_copy = frame.copy()
        roi_points = np.array(roi_coords, dtype=np.int32)
        cv2.polylines(frame_copy, [roi_points], isClosed=True, color=color, thickness=thickness)
        return frame_copy
    
    def annotate_count(
        self,
        frame: np.ndarray,
        count_result: CountResult,
        position: Tuple[int, int] = (50, 50)
    ) -> np.ndarray:
        """
        Annotate frame with count information.
        
        Args:
            frame: Input frame
            count_result: Result from count_in_roi
            position: Text position (x, y)
            
        Returns:
            Annotated frame
        """
        frame_copy = frame.copy()
        
        text = f"{count_result.class_name}: {count_result.count} (conf: {count_result.confidence:.2f})"
        cv2.putText(
            frame_copy,
            text,
            position,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2
        )
        
        # Draw bounding boxes for detections
        for (x1, y1, x2, y2) in count_result.detections:
            cv2.rectangle(
                frame_copy,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),
                2
            )
        
        return frame_copy


# Singleton instance
_object_counter = None


def get_object_counter(model_path: str = "yolov8n.pt") -> ObjectCounter:
    """Get or create the global object counter instance"""
    global _object_counter
    if _object_counter is None:
        _object_counter = ObjectCounter(model_path)
    return _object_counter
