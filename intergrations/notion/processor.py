# import libraries
import logging
import json
from pathlib import Path
from rich.console import Console
from tqdm import tqdm

# import modules
from .config import config
from .notion.notion_api_client import NotionApiClient

logger = logging.getLogger(__name__)
console = Console()

def execute_test_connection(api_key):
    logger.info(f"Test connection...")
    client = NotionApiClient(api_key)
    notion_info = client.test_connection()
    if notion_info:
        notion_bot = notion_info.get("name")
        logger.info(f"Notion's bot: {notion_bot}")
        logger.info(f"Connection test passed...")
        return True
    else:
        logger.critical(f"Connection test failed...")
        return False

def execute_build_dashboard_layout(api_key, parent_page_id):
    try:
        PORJECT_ROOT = Path(__file__).resolve().parent.parent
        schema_path = PORJECT_ROOT / "schema.json"
        logger.info(schema_path)
        with open(schema_path, "r", encoding="utf-8") as f:
            logger.info(f"File loaded...")
            layout_schema = json.load(f)
        layout_payload = layout_schema.get("layout", [])
        logger.info(f"Layout payload loaded...")
        client = NotionApiClient(api_key)
        response = client.append_block_children(parent_page_id, layout_payload)
        if not response or response.status_code != 200:
            logger.error(f"Build dashboard layout failed...")
    except FileNotFoundError as e:
        logger.error(f"Failed to read schema.json...{e}")

def execute_delete_blocks(api_key, parent_page_id):
    logger.info(f"Detecting blocks to delete...")
    client = NotionApiClient(api_key)
    response = client.get_block_children(parent_page_id)
    logger.debug(f"response: {response}")
    logger.debug(f"response's type: {type(response)}")
    if not response or response.status_code != 200:
        logger.info(f"Failed to get contents")
        return False
    
    blocks = response.json().get("results",[])
    logger.info(f"Blocks: \n {json.dumps(blocks, indent=4)}")
    logger.info(f"len of blocks: {len(blocks)}")
    
    if len(blocks) == 0:
        logger.info(f"No blocks detected...")
        return False

    logger.info(f"Get {len(blocks)} items...")
    logger.warning(f"Detected {len(blocks)} to delete...")
    if console.input(f"Delete all blocks? (y/n)").lower() == "y":
        if console.input(f"Delete all blocks? (y/n)").lower() == "y":
            logger.info(f"Deleting all blocks...")
            for block in tqdm(blocks, desc="Deleting...", unit="block"):
                client.delete_block(block["id"])
                logger.info(f"Block {block["id"]} deleted")
            logger.info(f"All blocks deleted...")
        else:
            logger.info(f"Cancelled...")
    else:
        logger.info(f"Cancelled")
    logger.info("Done...")

def execute_create_database(api_key, parent_page_id):
    client = NotionApiClient(api_key)
    logger.info("Creating databases...")
    logger.info("Getting databases structure from schema.json")
    try:
        PORJECT_ROOT = Path(__file__).resolve().parent.parent
        schema_path = PORJECT_ROOT / "schema.json"
        logger.info(schema_path)
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        db_schemas = schema.get("databases", [])
        logger.info(f"{json.dumps(db_schemas, indent=4)}")
    except FileNotFoundError as e:
        logger.error(f"Failed to read schema.json...{e}")
        return
    
    created_databases = {}

    logger.info("Creating databases...")
    for db_schema in tqdm(db_schemas, desc="Creating Databases..."):
        db_name = db_schema["db_name"]
        properties = {}
        
        logger.debug(f"Processing schema for '{db_name}': {db_schema}")

        for prop_name, prop_details in db_schema["properties"].items():
            if "relation_placeholder" not in prop_details:
                properties[prop_name] = prop_details

        payload = {
            "parent": { "type": "page_id", "page_id": parent_page_id },
            "title": [{ "type": "text", "text": { "content": db_schema["title"] } }],
            "properties": properties
        }

        logger.info(f"Creating database: '{db_name}'...")
        response = client.create_database(payload)

        if response:
            new_db_id = response.get("id")
            created_databases[db_name] = new_db_id
            logger.info(f"Successfully created '{db_name}' with ID: {new_db_id}")
            config.set_env(db_schema["env_key"], new_db_id)
        else:
            logger.error(f"Failed to create database: '{db_name}'. Stopping process.")
            return
        
    logger.info("Updating databases...")
    for db_schema in tqdm(db_schemas, desc="Updating Relations"):
        db_name = db_schema["db_name"]
        current_db_id = created_databases.get(db_name)
        
        if not current_db_id:
            continue

        properties = {}
        for prop_name, prop_details in db_schema["properties"].items():
            if "relation_placeholder" in prop_details:
                target_db_name = prop_details["relation_placeholder"]["db_name"]
                target_db_id = created_databases.get(target_db_name)
                
                if target_db_id:
                    properties[prop_name] = {
                        "relation": {
                            "database_id": target_db_id,
                            "type": "dual_property",
                            "dual_property": {}
                        }
                    }
        
        if properties:
            logger.info(f"Updating relations for database: '{db_name}'...")
            update_response = client.update_database(current_db_id, properties)
            if update_response:
                logger.info(f"Successfully updated relations for '{db_name}'.")
            else:
                logger.error(f"Failed to update relations for '{db_name}'.")
    
    logger.info("Database created...")