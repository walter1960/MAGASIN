from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor
import multiprocessing
import queue
import cv2
import numpy as np
from workers.video_worker import VideoWorker
from services.logger_service import logger

class CameraWidget(QWidget):
    """
    Widget to display video feed from a specific camera source using VideoWorker.
    """
    alert_signal = pyqtSignal(list) # Signal to emit alerts to main window

    def __init__(self, source=0, parent=None):
        super().__init__(parent)
        self.source = source
        self.worker = None
        self.result_queue = multiprocessing.Queue(maxsize=3)
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_frame)
        self.running = False
        
        # UI Setup
        self.image_label = QLabel("Waiting for camera...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; color: white; font-size: 16px;")
        
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def start_camera(self):
        if self.running:
            return
            
        logger.info(f"Starting camera widget for source {self.source}")
        self.worker = VideoWorker(self.source, self.result_queue)
        self.worker.start()
        self.display_timer.start(30) # Check for frames every 30ms
        self.running = True

    def stop_camera(self):
        if not self.running:
            return
            
        if self.worker:
            self.worker.terminate() # Using terminate for speed in this context, use stop() properly in prod
            self.worker.join()
        
        self.display_timer.stop()
        self.running = False
        self.image_label.setText("Camera Stopped")
        
    @pyqtSlot()
    def update_frame(self):
        try:
            # Get latest frame (non-blocking)
            frame_data = self.result_queue.get_nowait()
            frame, detections, alerts = frame_data
            
            if frame is not None:
                self.display_image(frame)
            
            if alerts:
                self.alert_signal.emit(alerts)
                
        except queue.Empty:
            pass

    def display_image(self, frame):
        """
        Convert CV2 frame to QPixmap and display.
        """
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Scale to fit label (keeping aspect ratio)
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()
