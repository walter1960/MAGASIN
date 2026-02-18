import sys
import logging
from loguru import logger
from config.settings import settings

class InterceptHandler(logging.Handler):
    """
    Redirects standard logging messages to Loguru.
    """
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logging():
    # Remove default logger
    logger.remove()

    # Add console sink
    logger.add(
        sys.stderr,
        level="DEBUG" if settings.DEBUG else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # Add file sink with rotation
    log_file = settings.LOGS_DIR / "app.log"
    logger.add(
        log_file,
        rotation="10 MB",
        retention="1 week",
        level="INFO",
        compression="zip"
    )

    # Intercept standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # Silence noisy libraries if needed
    logging.getLogger("PyQt6").setLevel(logging.WARNING)

    logger.info(f"Logging configured. Debug mode: {settings.DEBUG}")

