"""
Notion 整合模組 - API 客戶端
=============================
此模組負責處理與 Notion API 的所有通訊，包括：
- HTTP 請求的建立與發送
- API 連線測試
- 區塊操作（新增、更新、刪除）
- 頁面操作（建立、查詢）
- 資料庫操作（建立、查詢、更新記錄）

作者：Project Synapse Team
版本：2.1 (修正資料庫封存邏輯)
最後更新：2026-03
"""

import requests
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from .config import notion_config

logger = logging.getLogger(__name__)

class NotionApiClient:
    """Notion API 客戶端類別"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or notion_config.api_key
        
        if not self.api_key:
            error_msg = "Notion API 金鑰未設定！請在 .env 檔案中設定 NOTION_API_KEY"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.base_url = notion_config.base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": notion_config.content_type,
            "Notion-Version": notion_config.api_version
        }
        
        logger.info(f"✅ Notion API 客戶端初始化完成")

    def _send_request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None, retry_count: int = 3) -> Optional[requests.Response]:
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retry_count):
            try:
                logger.debug(f"🔄 發送請求 [{attempt + 1}/{retry_count}] | 方法: {method} | URL: {url}")
                response = requests.request(method=method, url=url, headers=self.headers, json=payload, timeout=30)
                response.raise_for_status()
                logger.debug(f"✅ 請求成功: {response.status_code}")
                return response
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 'N/A'
                logger.error(f"❌ HTTP 錯誤: {status_code}")
                if 400 <= status_code < 500:
                    return None
                if attempt < retry_count - 1:
                    import time
                    time.sleep(2)
                    continue
                return None
            except Exception as e:
                logger.error(f"❌ 請求發生異常: {str(e)}")
                if attempt < retry_count - 1:
                    import time
                    time.sleep(2)
                    continue
                return None
        return None
    
    def test_connection(self) -> Optional[Dict[str, Any]]:
        logger.info("🔍 測試 Notion API 連線...")
        response = self._send_request("GET", "users/me")
        if response and response.status_code == 200:
            user_info = response.json()
            logger.info(f"✅ 連線成功！使用者: {user_info.get('name', '未知使用者')}")
            return user_info
        logger.error("❌ 連線失敗，請檢查 API 金鑰")
        return None
    
    def retrieve_database(self, database_id: str) -> Optional[Dict[str, Any]]:
        """獲取資料庫最新結構資訊"""
        logger.info(f"🔍 讀取資料庫結構: {database_id}")
        response = self._send_request("GET", f"databases/{database_id}")
        return response.json() if response and response.status_code == 200 else None

    def get_block_children(self, block_id: str) -> Optional[List[Dict[str, Any]]]:
        """獲取頁面或區塊的所有子內容"""
        logger.info(f"📖 讀取區塊內容: {block_id}")
        response = self._send_request("GET", f"blocks/{block_id}/children?page_size=100")
        return response.json().get('results', []) if response and response.status_code == 200 else None
    
    def append_block_children(self, parent_page_id: str, layout_payload: List[Dict[str, Any]]) -> Optional[requests.Response]:
        logger.info(f"📝 新增區塊內容到頁面: {parent_page_id}")
        payload = {"children": layout_payload}
        response = self._send_request("PATCH", f"blocks/{parent_page_id}/children", payload)
        if response: logger.info(f"✅ 成功新增 {len(layout_payload)} 個區塊")
        return response
    
    def create_page(self, parent_id: str, page_title: str, properties: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        logger.info(f"📄 建立新頁面: {page_title}")
        if properties is None:
            properties = {"title": {"title": [{"type": "text", "text": {"content": page_title}}]}}
        payload = {"parent": {"page_id": parent_id}, "properties": properties}
        response = self._send_request("POST", "pages", payload)
        if response:
            logger.info(f"✅ 頁面建立成功")
            return response.json()
        return None
    
    def create_database(self, parent_id: str, db_title: str, properties_schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        logger.info(f"🗄️  建立新資料庫: {db_title}")
        payload = {
            "parent": {"type": "page_id", "page_id": parent_id},
            "title": [{"type": "text", "text": {"content": db_title}}],
            "properties": properties_schema
        }
        response = self._send_request("POST", "databases", payload)
        if response:
            db_data = response.json()
            logger.info(f"✅ 資料庫建立成功 | ID: {db_data.get('id')}")
            return db_data
        return None
    
    def query_database(self, database_id: str, filter_conditions: Optional[Dict[str, Any]] = None, sorts: Optional[List[Dict[str, Any]]] = None, page_size: int = 100) -> Optional[List[Dict[str, Any]]]:
        payload = {"page_size": min(page_size, 100)}
        if filter_conditions: payload["filter"] = filter_conditions
        if sorts: payload["sorts"] = sorts
        response = self._send_request("POST", f"databases/{database_id}/query", payload)
        if response: return response.json().get('results', [])
        return None
    
    def create_page_in_database(self, database_id: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        logger.debug(f"➕ 在資料庫中建立新記錄")
        payload = {"parent": {"database_id": database_id}, "properties": properties}
        response = self._send_request("POST", "pages", payload)
        if response: return response.json()
        return None
    
    def delete_blocks(self, page_id: str) -> bool:
        """
        刪除指定頁面的所有子區塊
        【修正】判斷區塊類型，若是資料庫則改用 PATCH endpoint 封存。
        """
        logger.info(f"🗑️  刪除頁面區塊與封存資料庫: {page_id}")
        response = self._send_request("GET", f"blocks/{page_id}/children?page_size=100")
        
        if not response:
            logger.error("❌ 無法取得區塊列表")
            return False
        
        blocks = response.json().get('results', [])
        logger.info(f"   找到 {len(blocks)} 個區塊準備刪除/封存")
        
        deleted_count = 0
        for block in blocks:
            block_id = block.get('id')
            block_type = block.get('type')
            if not block_id: continue
            
            # 根據不同類型決定刪除/封存方式
            if block_type == 'child_database':
                logger.debug(f"   封存資料庫: {block_id}")
                del_response = self._send_request("PATCH", f"databases/{block_id}", {"archived": True})
            elif block_type == 'child_page':
                logger.debug(f"   封存子頁面: {block_id}")
                del_response = self._send_request("PATCH", f"pages/{block_id}", {"archived": True})
            else:
                logger.debug(f"   刪除區塊: {block_id}")
                del_response = self._send_request("DELETE", f"blocks/{block_id}")
            
            if del_response:
                deleted_count += 1
        
        logger.info(f"✅ 成功清理 {deleted_count}/{len(blocks)} 個區塊或資料庫")
        return deleted_count == len(blocks)