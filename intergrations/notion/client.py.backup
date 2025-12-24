"""
Notion 整合模組 - API 客戶端
處理與 Notion API 的所有通訊
"""
import requests
import logging
import json
from typing import Optional, Dict, Any, List

from .config import notion_config

logger = logging.getLogger(__name__)


class NotionApiClient:
    """Notion API 客戶端類別"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Notion API 客戶端
        
        Args:
            api_key: Notion API Key，若未提供則從配置中獲取
        """
        self.api_key = api_key or notion_config.api_key
        if not self.api_key:
            raise ValueError("Notion API Key 未設置，請檢查環境變數 NOTION_API_KEY")
        
        self.base_url = notion_config.base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": notion_config.content_type,
            "Notion-Version": notion_config.api_version
        }
        
        logger.debug(f"Notion API 客戶端已初始化: {self.base_url}")

    def _send_request(
        self, 
        method: str, 
        endpoint: str, 
        payload: Optional[Dict[str, Any]] = None
    ) -> Optional[requests.Response]:
        """
        發送 HTTP 請求到 Notion API
        
        Args:
            method: HTTP 方法 (GET, POST, PATCH, DELETE)
            endpoint: API 端點
            payload: 請求數據
            
        Returns:
            Response 對象或 None（失敗時）
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.debug(f"發送請求: {method} {url}")
            if payload:
                logger.debug(f"請求數據: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            response = requests.request(method, url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            logger.debug(f"請求成功: {response.status_code}")
            return response
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP 錯誤: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"回應內容: {e.response.text}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"請求失敗: {e}")
            return None
    
    def test_connection(self) -> Optional[Dict[str, Any]]:
        """
        測試 Notion API 連接
        
        Returns:
            用戶信息字典或 None（失敗時）
        """
        logger.info("測試 Notion API 連接...")
        response = self._send_request("GET", "users/me")
        
        if response and response.status_code == 200:
            user_info = response.json()
            logger.info(f"連接成功，用戶: {user_info.get('name', 'Unknown')}")
            return user_info
        
        logger.error("連接失敗")
        return None
    
    def append_block_children(
        self, 
        parent_page_id: str, 
        layout_payload: List[Dict[str, Any]]
    ) -> Optional[requests.Response]:
        """
        向頁面添加子區塊
        
        Args:
            parent_page_id: 父頁面 ID
            layout_payload: 區塊佈局數據
            
        Returns:
            Response 對象或 None（失敗時）
        """
        payload = {"children": layout_payload}
        logger.info(f"向頁面 {parent_page_id[:8]}... 添加 {len(layout_payload)} 個區塊")
        return self._send_request("PATCH", f"blocks/{parent_page_id}/children", payload)

    def get_block_children(self, parent_page_id: str) -> Optional[requests.Response]:
        """
        獲取頁面的子區塊
        
        Args:
            parent_page_id: 父頁面 ID
            
        Returns:
            Response 對象或 None（失敗時）
        """
        logger.info(f"獲取頁面 {parent_page_id[:8]}... 的子區塊")
        return self._send_request("GET", f"blocks/{parent_page_id}/children")
    
    def delete_block(self, block_id: str) -> Optional[requests.Response]:
        """
        刪除指定區塊
        
        Args:
            block_id: 區塊 ID
            
        Returns:
            Response 對象或 None（失敗時）
        """
        logger.debug(f"刪除區塊: {block_id[:8]}...")
        return self._send_request("DELETE", f"blocks/{block_id}")
    
    def create_database(
        self, 
        payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        創建新的數據庫
        
        Args:
            payload: 數據庫配置數據
            
        Returns:
            數據庫信息字典或 None（失敗時）
        """
        logger.info(f"創建數據庫...")
        response = self._send_request("POST", "databases", payload)
        
        if response and response.status_code == 200:
            db_info = response.json()
            logger.info(f"數據庫創建成功: {db_info.get('id', 'Unknown')[:8]}...")
            return db_info
        
        logger.error("數據庫創建失敗")
        return None
    
    def update_database(
        self, 
        database_id: str, 
        properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        更新數據庫屬性
        
        Args:
            database_id: 數據庫 ID
            properties: 要更新的屬性
            
        Returns:
            更新後的數據庫信息或 None（失敗時）
        """
        payload = {"properties": properties}
        logger.info(f"更新數據庫 {database_id[:8]}...")
        response = self._send_request("PATCH", f"databases/{database_id}", payload)
        
        if response and response.status_code == 200:
            logger.info("數據庫更新成功")
            return response.json()
        
        logger.error("數據庫更新失敗")
        return None