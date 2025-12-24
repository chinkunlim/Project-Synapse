# import libraries
import logging
from pathlib import Path
from rich.logging import RichHandler

# import modules
from .config import config

def setup_logging():
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    # print(PROJECT_ROOT)

    log_folder = config.get_config("log_folder", section="Logging", default="logs")
    log_filename = config.get_config("log_filename", section="Logging", default="app.log")
    log_level = config.get_config("log_level", section="Logging", default="INFO").upper()
    log_format = config.get_config("log_format", section="Logging", default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_encoding = config.get_config("log_encoding", section="Logging", default="utf-8")

    log_dir = PROJECT_ROOT / log_folder
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / log_filename

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, mode="a", encoding=log_encoding),
            RichHandler(rich_tracebacks=True)
        ]
    )
    # logger = logging.getLogger(__name__)
    # logger.info(f"Logging configured...")
    # logger.info(f"log_folder   : {log_folder}")
    # logger.info(f"log_filename : {log_filename}")
    # logger.info(f"log_level    : {log_level}")
    # logger.info(f"log_format   : {log_format}")
    # logger.info(f"log_encoding : {log_encoding}")