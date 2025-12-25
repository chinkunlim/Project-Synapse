import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

# Ensure logs directory exists
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'app.log'

def setup_logger(name='synapse'):
    """
    Configure strict structured logging for the application.
    Writes to both console and a rotating file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(module)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File Handler (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Singleton logger instance
logger = setup_logger()
