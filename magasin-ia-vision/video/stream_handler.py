import cv2
import time
import threading
from services.logger_service import logger

class StreamHandler:
    """
    Handles video stream capture from a single source (RTSP or Webcam).
    Uses a separate thread to read frames to prevent I/O blocking.
    """
    def __init__(self, source, source_id=0):
        self.source = source
        self.source_id = source_id
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.latest_frame = None
        self.last_read_time = 0
        self.fps = 0
        self.frame_count = 0
        self.start_time = 0

    def start(self):
        if self.running:
            return
        
        logger.info(f"Starting stream handler for source: {self.source}")
        self._connect()
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _connect(self):
        if self.cap:
            self.cap.release()
        
        # Determine if source is int (webcam index) or string (RTSP url/file path)
        src = self.source
        if str(src).isdigit():
            src = int(src)
            
        self.cap = cv2.VideoCapture(src)
        
        if not self.cap.isOpened():
            logger.error(f"Failed to open video source: {self.source}")
            return False
            
        # Optimization for RTSP
        if isinstance(src, str) and (src.startswith("rtsp") or src.startswith("http")):
             self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
             
        logger.success(f"Successfully connected to source: {self.source}")
        return True

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
        logger.info(f"Stopped stream handler for source: {self.source}")

    def _update(self):
        self.start_time = time.time()
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                time.sleep(1)
                self._connect()
                continue

            ret, frame = self.cap.read()
            if not ret:
                logger.warning(f"Failed to read frame from {self.source}. Reconnecting...")
                self._connect()
                time.sleep(0.5)
                continue

            with self.lock:
                self.latest_frame = frame
                self.last_read_time = time.time()
                self.frame_count += 1
            
            # Simple FPS calculation
            elapsed = time.time() - self.start_time
            if elapsed > 1.0:
                self.fps = self.frame_count / elapsed
                self.frame_count = 0
                self.start_time = time.time()
            
            # Limit loop speed to avoid CPU burn if camera is very fast (unlikely but safe)
            time.sleep(0.005)

    def get_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def is_active(self):
        return self.running and self.cap is not None and self.cap.isOpened()
