# import libraries
import os
import logging
import configparser
from dotenv import load_dotenv, set_key, find_dotenv

# import modules

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, ini_path="config.ini"):
        self.config=configparser.ConfigParser()
        if os.path.exists(ini_path):
            self.config.read(ini_path, encoding="utf-8")

    def get_config(self, key, section, default):
        if section and self.config.has_option(section, key):
            return self.config.get(section, key)
        return default
    
    def load_env(self):
        dotenv_path = find_dotenv()
        if not dotenv_path:
            logger.warning(f"Couldn't find .env file...")
            return
        
        load_dotenv(dotenv_path)
        logger.info(f"Read .env file successfully")
    
    def get_env(self):
        config_keys = [
            "NOTION_API_KEY",
            "PARENT_PAGE_ID",
            "COURSE_HUB_ID",
            "CLASS_SESSION_ID",
            "TAKS_DB_ID",
            "NOTE_DB_ID",
            "PROJECT_DB_ID",
            "RESOURCE_DB_ID",
        ]
        return {key: os.getenv(key) for key in config_keys if os.getenv(key) is not None}

    def set_env(self, key, value):
        dotenv_path = find_dotenv()
        if not dotenv_path:
            logger.warning(f".env file not found...")
        
        write_env_key = set_key(dotenv_path, key, value)
        if write_env_key:
            logger.info(f"write value to {key} successfully...")
        else:
            logger.error(f"failed to write value to {key}...")

config = Config()