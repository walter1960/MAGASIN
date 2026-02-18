import sys
import torch_init  # Configure PyTorch avant tout
import multiprocessing
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from config.settings import settings
from services.logger_service import setup_logging

def main():
    # Needed for multiprocessing on Windows/frozen apps
    multiprocessing.freeze_support()
    
    setup_logging()
    
    app = QApplication(sys.argv)
    app.setApplicationName(settings.APP_NAME)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
