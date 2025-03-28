import logging
from logging.handlers import RotatingFileHandler
from core import cfg
__all__ = ["setup_logging"]

def setup_logging():
    # Configure logging before app initialization
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Use RotatingFileHandler for log rotation (optional)
    log_handler = RotatingFileHandler(filename=cfg.log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    log_handler.setFormatter(log_formatter)
    log_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    # Configure Uvicorn/Starlette loggers explicitly
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "starlette"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)  # Set logger level to INFO
        logger.addHandler(log_handler)  # Add file handler
        if cfg.mode == "dev": logger.addHandler(console_handler)
    logging.getLogger("uvicorn").info("Logging setup complete")