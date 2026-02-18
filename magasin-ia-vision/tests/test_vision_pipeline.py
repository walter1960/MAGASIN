"""
Test script for the new VisionPipeline (YOLO+SAM2+MediaPipe)
"""
import cv2
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from ai.vision_pipeline import get_vision_pipeline
from services.logger_service import logger

def test_pipeline():
    logger.info("Starting VisionPipeline Test...")
    
    # Create a dummy frame (black image)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, "ASECNA TEST", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Initialize pipeline
    pipeline = get_vision_pipeline(camera_id="test_cam_01", model_id="yolov8n", segment=False)
    
    logger.info("Processing frame 1...")
    annotated_frame, detections, alerts = pipeline.process_frame(frame)
    
    logger.info(f"Frame 1: {len(detections)} detections, {len(alerts)} alerts.")
    print(f"Detections: {detections}")
    
    logger.success("VisionPipeline test completed successfully (Technical verification).")

if __name__ == "__main__":
    test_pipeline()
