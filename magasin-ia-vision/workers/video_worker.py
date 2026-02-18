import multiprocessing
import time
import cv2
import queue
from video.stream_handler import StreamHandler
from ai.detector import ObjectDetector
from services.logger_service import logger

class VideoWorker(multiprocessing.Process):
    """
    Background process for Video Acquisition + AI Inference.
    Sends processed frames (and metadata) back to the main process via a Queue.
    """
    def __init__(self, source, result_queue, model_path=None):
        super().__init__()
        self.source = source
        self.result_queue = result_queue
        self.model_path = model_path
        self.running = multiprocessing.Event()
        self.command_queue = multiprocessing.Queue()

    def run(self):
        """
        Main loop of the worker process.
        """
        self.running.set()
        logger.info(f"VideoWorker started for source: {self.source}")
        
        # Initialize components INSIDE the process
        stream = StreamHandler(self.source)
        stream.start()
        
        detector = None
        try:
            detector = ObjectDetector(self.model_path)
            logger.info("AI Model loaded in worker process.")
        except Exception as e:
            logger.error(f"Failed to load AI model in worker: {e}")
            # Continue without AI? Or stop?
            # For now, let's continue but skip inference

        fps_limit = 30
        frame_time = 1.0 / fps_limit

        while self.running.is_set():
            start_time = time.time()
            
            # Check for commands
            try:
                cmd = self.command_queue.get_nowait()
                if cmd == "STOP":
                    break
            except queue.Empty:
                pass

            frame = stream.get_frame()
            if frame is not None:
                # Inference
                detections = []
                if detector:
                    # Run tracking directly
                    try:
                        results = detector.track(frame, persist=True)
                        if results:
                            # Extract plotting or raw data
                            # For UI display, an annotated frame + raw data list is useful
                            annotated_frame = results[0].plot()
                            detections = results[0].boxes.data.tolist()  # [data]
                            
                            # Alert Logic (Simple Demo: Detect Person)
                            alerts = []
                            for box in results[0].boxes:
                                cls_id = int(box.cls[0])
                                if cls_id == 0: # Person
                                    conf = float(box.conf[0])
                                    if conf > 0.6:
                                        alerts.append({"type": "INTRUSION", "message": "Personne détectée dans la zone !"})
                            
                            # Send to UI
                            try:
                                if self.result_queue.full():
                                    try:
                                        self.result_queue.get_nowait() # Drop old frame
                                    except queue.Empty:
                                        pass
                                self.result_queue.put((annotated_frame, detections, alerts), timeout=0.01)
                            except queue.Full:
                                pass
                    except Exception as e:
                        logger.error(f"Inference error: {e}")
            
            # FPS Control
            elapsed = time.time() - start_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)

        stream.stop()
        logger.info("VideoWorker stopped.")

    def stop(self):
        self.running.clear()
        self.command_queue.put("STOP")
        self.join(timeout=2.0)
        # Force kill if needed?
        if self.is_alive():
            self.terminate()
