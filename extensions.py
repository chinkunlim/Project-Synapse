import os
from notion_client import Client
from intergrations.notion import NotionProcessor, setup_logging
from utils.google_classroom_integration import GoogleClassroomIntegration
from utils.google_ndhu_integration import GoogleNDHUIntegration
from utils.logger import logger

# Global Instances
notion = None
notion_processor = None
classroom_integration = None
ndhu_integration = None
database_id = None

def init_extensions():
    """
    Initialize all third-party integrations (Notion, Google Classroom, NDHU).
    
    This function instantiates global objects for each service.
    It catches initialization errors individually to ensure the app still boots
    even if one service (e.g., Notion) is misconfigured or down.
    """
    global notion, notion_processor, classroom_integration, ndhu_integration, database_id
    
    logger.info("Initializing Synapse extensions...")
    
    # Initialize Logging (Deprecated old setup, now using utils.logger)
    # setup_logging() 
    
    # Initialize Notion
    try:
        notion = Client(auth=os.getenv("NOTION_API_KEY"))
        database_id = os.getenv("NOTION_DATABASE_ID")
        notion_processor = NotionProcessor()
        logger.info("Notion integration initialized successfully.")
    except Exception as e:
        logger.warning(f"Notion Initialization Warning: {e}")
        notion = None
        database_id = None
        notion_processor = None

    # Initialize Google Classroom
    try:
        classroom_integration = GoogleClassroomIntegration()
        logger.info("Google Classroom integration initialized successfully.")
    except Exception as e:
        logger.warning(f"Google Classroom Initialization Warning: {e}")
        classroom_integration = None

    # Initialize Google NDHU
    try:
        ndhu_integration = GoogleNDHUIntegration()
        logger.info("Google NDHU integration initialized successfully.")
    except Exception as e:
        logger.warning(f"Google NDHU Initialization Warning: {e}")
        ndhu_integration = None
