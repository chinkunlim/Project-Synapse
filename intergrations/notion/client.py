# import libraries
import requests
import logging
import json

# import modules
from ..config import config

logger = logging.getLogger(__name__)

class NotionApiClient:
    def __init__(self, api_key):
        base_url = config.get_config("base_url", section="Notion", default="https://api.notion.com/v1")
        content_type = config.get_config("content_type", section="Notion", default="application/json")
        api_version = config.get_config("api_version", section="Notion", default="2022-06-28")
        
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": content_type,
            "Notion-Version": api_version
        }

    def _send_request(self, method, endpoint, payload=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to request: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
    
    def test_connection(self):
        response = self._send_request("GET", "users/me")
        # logger.debug(f"Type of response: {type(response)}")
        # logger.debug(json.dumps(response.json(),indent=4))
        return response.json() if response and response.status_code == 200 else None
    
    def append_block_children(self, parent_page_id, layout_payload):
        payload = {"children": layout_payload}
        # logger.debug(json.dumps(payload,indent=4))
        return self._send_request("PATCH", f"blocks/{parent_page_id}/children", payload)

    def get_block_children(self, parent_page_id):
        return self._send_request("GET", f"blocks/{parent_page_id}/children", )
    
    def delete_block(self, block_id):
        return self._send_request("DELETE", f"blocks/{block_id}")
    
    def create_database(self, payload):
        response = self._send_request("POST", "databases", payload)
        return response.json() if response and response.status_code == 200 else None
    
    def update_database(self, database_id, properties):
        payload = {"properties": properties}
        response = self._send_request("PATCH", f"databases/{database_id}", payload)
        return response.json() if response and response.status_code == 200 else None