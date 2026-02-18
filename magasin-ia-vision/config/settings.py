import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    # Base Paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    MODELS_DIR = BASE_DIR / "models"
    LOGS_DIR = BASE_DIR / "logs"

    # Database
    DB_NAME = os.getenv("DB_NAME", "magasin_ia.sqlite")
    DB_URL = f"sqlite:///{DATA_DIR}/{DB_NAME}"  # Default to SQLite for ease of dev

    # Camera / Video
    RTSP_URLS = os.getenv("RTSP_URLS", "").split(",")
    SAVE_VIDEO_CLIPS = os.getenv("SAVE_VIDEO_CLIPS", "True").lower() == "true"

    # AI Configuration
    YOLO_MODEL_PATH = MODELS_DIR / "yolov8n.pt"  # Placeholder
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.25))
    
    # App Settings
    APP_NAME = "Magasin IA Vision"
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

settings = Settings()
