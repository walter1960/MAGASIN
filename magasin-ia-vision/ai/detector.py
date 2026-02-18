from ultralytics import YOLO, SAM
import torch
from config.settings import settings
from services.logger_service import logger

class ObjectDetector:
    """
    Wrapper around Ultralytics YOLO and SAM2 models.
    """
    def __init__(self, model_path=None):
        self.model_path = model_path or settings.YOLO_MODEL_PATH
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = None
        self.sam_model = None
        self.sam_path = None
        self._load_model()

    def _load_model(self):
        try:
            logger.info(f"Loading YOLO model from {self.model_path} on {self.device}...")
            self.model = YOLO(self.model_path)
            self.model.to(self.device)
            logger.success("Model loaded successfully.")
        except Exception as e:
            logger.critical(f"Failed to load YOLO model: {e}")
            raise e

    def set_model(self, model_id):
        """Update detection model dynamically"""
        model_map = {
            "yolov8n": "yolov8n.pt",
            "yolov8s": "yolov8s.pt",
            "yolov8m": "yolov8m.pt",
            "yolov8l": "yolov8l.pt",
            "yolov11n": "yolo11n.pt",
        }
        
        if model_id in model_map:
            self.model_path = model_map[model_id]
            self._load_model()
            return True
        return False

    def set_segmenter(self, model_id):
        """Load or update SAM2 model for segmentation"""
        sam_map = {
            "sam2-tiny": "sam2_t.pt",
            "sam2-small": "sam2_s.pt",
            "sam2-base": "sam2_b.pt",
            "sam2-large": "sam2_l.pt",
        }
        
        if model_id in sam_map:
            self.sam_path = sam_map[model_id]
            try:
                logger.info(f"Loading SAM2 model from {self.sam_path}...")
                self.sam_model = SAM(self.sam_path)
                self.sam_model.to(self.device)
                logger.success(f"SAM2 model {model_id} loaded.")
                return True
            except Exception as e:
                logger.error(f"Failed to load SAM2: {e}")
        elif model_id is None or model_id == "none" or model_id == "":
            self.sam_model = None
            self.sam_path = None
            return True
        return False

    def predict(self, frame, conf=0.5, classes=None, tracker=None, segment=False):
        """
        Run inference. Supports detection, tracking and segmentation.
        """
        if self.model is None:
            return []
        
        # 1. Detection/Tracking
        if tracker:
            results = self.model.track(
                source=frame,
                persist=True,
                tracker=tracker,
                conf=conf,
                classes=classes,
                device=self.device,
                verbose=False
            )
        else:
            results = self.model.predict(
                source=frame,
                conf=conf,
                classes=classes,
                device=self.device,
                verbose=False
            )
            
        # 2. Segmentation (SAM2) - if requested and model loaded
        if segment and self.sam_model and results and len(results) > 0:
            boxes = results[0].boxes.xyxy
            if len(boxes) > 0:
                # Use YOLO boxes as prompts for SAM2
                sam_results = self.sam_model(frame, bboxes=boxes, device=self.device, verbose=False)
                # Merge masks into original results for overlay
                if sam_results and len(sam_results) > 0:
                    results[0].update(masks=sam_results[0].masks)
                    
        return results
