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
版本：2.0
最後更新：2025-12-25
"""

import requests
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from .config import notion_config

# 設定日誌記錄器
logger = logging.getLogger(__name__)


class NotionApiClient:
    """
    Notion API 客戶端類別
    
    此類別封裝了所有與 Notion API 的互動邏輯，提供：
    - 統一的 HTTP 請求介面
    - 自動化的錯誤處理
    - 完整的日誌記錄
    - API 版本管理
    
    屬性：
        api_key (str): Notion API 金鑰
        base_url (str): Notion API 基礎 URL
        headers (dict): HTTP 請求標頭
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Notion API 客戶端
        
        此方法會：
        1. 載入 API 金鑰（從參數或環境變數）
        2. 設定 HTTP 請求標頭
        3. 初始化日誌記錄
        
        參數：
            api_key (str, optional): Notion API 金鑰
                                     若未提供，則從環境變數 NOTION_API_KEY 讀取
        
        拋出異常：
            ValueError: 當 API 金鑰未設定時
        
        範例：
            >>> client = NotionApiClient()
            >>> # 或指定金鑰
            >>> client = NotionApiClient(api_key="secret_xxx...")
        """
        # 取得 API 金鑰（優先使用參數，否則從設定檔取得）
        self.api_key = api_key or notion_config.api_key
        
        # 驗證 API 金鑰是否存在
        if not self.api_key:
            error_msg = (
                "Notion API 金鑰未設定！\n"
                "請在 .env 檔案中設定 NOTION_API_KEY=your_api_key\n"
                "或在初始化時提供 api_key 參數"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 設定 API 基礎 URL
        self.base_url = notion_config.base_url
        
        # 建立 HTTP 請求標頭
        # 包含：授權資訊、內容類型、API 版本
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": notion_config.content_type,
            "Notion-Version": notion_config.api_version
        }
        
        logger.info(f"✅ Notion API 客戶端初始化完成")
        logger.debug(f"   基礎 URL: {self.base_url}")
        logger.debug(f"   API 版本: {notion_config.api_version}")

    def _send_request(
        self, 
        method: str, 
        endpoint: str, 
        payload: Optional[Dict[str, Any]] = None,
        retry_count: int = 3
    ) -> Optional[requests.Response]:
        """
        發送 HTTP 請求到 Notion API（內部方法）
        
        此方法提供：
        - 自動重試機制
        - 完整的錯誤處理
        - 請求/回應日誌記錄
        - HTTP 狀態碼驗證
        
        參數：
            method (str): HTTP 方法（GET, POST, PATCH, DELETE）
            endpoint (str): API 端點（例如：'pages', 'databases/query'）
            payload (dict, optional): 請求主體資料（JSON 格式）
            retry_count (int): 失敗時的重試次數（預設：3）
            
        回傳：
            Response: HTTP 回應物件（成功時）
            None: 請求失敗時
        
        範例：
            >>> response = client._send_request('GET', 'users/me')
            >>> if response:
            ...     data = response.json()
        """
        # 組合完整的 API URL
        url = f"{self.base_url}/{endpoint}"
        
        # 執行重試邏輯
        for attempt in range(retry_count):
            try:
                # 記錄請求資訊（除錯模式）
                logger.debug(f"🔄 發送請求 [{attempt + 1}/{retry_count}]")
                logger.debug(f"   方法: {method}")
                logger.debug(f"   URL: {url}")
                
                if payload:
                    logger.debug(f"   請求資料: {json.dumps(payload, indent=2, ensure_ascii=False)}")
                
                # 發送 HTTP 請求
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=payload,
                    timeout=30  # 30 秒逾時
                )
                
                # 驗證 HTTP 狀態碼（若失敗會拋出 HTTPError）
                response.raise_for_status()
                
                # 記錄成功資訊
                logger.debug(f"✅ 請求成功: {response.status_code}")
                return response
                
            except requests.exceptions.HTTPError as e:
                # HTTP 錯誤（4xx, 5xx）
                status_code = e.response.status_code if e.response else 'N/A'
                logger.error(f"❌ HTTP 錯誤: {status_code}")
                
                if e.response is not None:
                    try:
                        error_data = e.response.json()
                        logger.error(f"   錯誤詳情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                    except:
                        logger.error(f"   回應內容: {e.response.text[:500]}")
                
                # 若是客戶端錯誤（4xx），不重試
                if 400 <= status_code < 500:
                    logger.error("   客戶端錯誤，停止重試")
                    return None
                
                # 伺服器錯誤（5xx），繼續重試
                if attempt < retry_count - 1:
                    logger.warning(f"   將在 2 秒後重試...")
                    import time
                    time.sleep(2)
                    continue
                else:
                    logger.error("   已達最大重試次數，放棄請求")
                    return None
                
            except requests.exceptions.Timeout:
                # 請求逾時
                logger.error(f"❌ 請求逾時（超過 30 秒）")
                if attempt < retry_count - 1:
                    logger.warning(f"   將在 2 秒後重試...")
                    import time
                    time.sleep(2)
                    continue
                return None
                
            except requests.exceptions.ConnectionError as e:
                # 連線錯誤
                logger.error(f"❌ 連線失敗: {str(e)}")
                if attempt < retry_count - 1:
                    logger.warning(f"   將在 2 秒後重試...")
                    import time
                    time.sleep(2)
                    continue
                return None
                
            except requests.exceptions.RequestException as e:
                # 其他請求異常
                logger.error(f"❌ 請求發生異常: {str(e)}")
                return None
        
        # 所有重試都失敗
        return None
    
    def test_connection(self) -> Optional[Dict[str, Any]]:
        """
        測試 Notion API 連線狀態
        
        此方法會：
        1. 呼叫 Notion API 的 /users/me 端點
        2. 驗證 API 金鑰是否有效
        3. 回傳目前使用者資訊
        
        回傳：
            dict: 使用者資訊字典，包含：
                - id: 使用者 ID
                - name: 使用者名稱
                - type: 使用者類型（person/bot）
                - avatar_url: 大頭照 URL
            None: 連線失敗時
        
        範例：
            >>> client = NotionApiClient()
            >>> user_info = client.test_connection()
            >>> if user_info:
            ...     print(f"已登入為：{user_info['name']}")
        """
        logger.info("🔍 測試 Notion API 連線...")
        
        # 發送 GET 請求到 /users/me
        response = self._send_request("GET", "users/me")
        
        if response and response.status_code == 200:
            # 解析回應資料
            user_info = response.json()
            user_name = user_info.get('name', '未知使用者')
            user_type = user_info.get('type', 'unknown')
            
            logger.info(f"✅ 連線成功！")
            logger.info(f"   使用者: {user_name}")
            logger.info(f"   類型: {user_type}")
            
            return user_info
        
        logger.error("❌ 連線失敗，請檢查 API 金鑰是否正確")
        return None
    
    def append_block_children(
        self, 
        parent_page_id: str, 
        layout_payload: List[Dict[str, Any]]
    ) -> Optional[requests.Response]:
        """
        在指定頁面中新增區塊內容
        
        此方法用於在 Notion 頁面中新增各種類型的區塊，包括：
        - 標題區塊（heading_1, heading_2, heading_3）
        - 段落區塊（paragraph）
        - 分隔線區塊（divider）
        - 列表區塊（bulleted_list_item, numbered_list_item）
        - 其他區塊類型
        
        參數：
            parent_page_id (str): 父頁面的 ID（格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）
            layout_payload (list): 區塊內容列表，每個元素為一個區塊定義
        
        回傳：
            Response: HTTP 回應物件（成功時）
            None: 操作失敗時
        
        範例：
            >>> blocks = [
            ...     {
            ...         "object": "block",
            ...         "type": "heading_1",
            ...         "heading_1": {
            ...             "rich_text": [{"type": "text", "text": {"content": "標題"}}]
            ...         }
            ...     }
            ... ]
            >>> response = client.append_block_children(page_id, blocks)
        """
        logger.info(f"📝 新增區塊內容到頁面: {parent_page_id}")
        logger.debug(f"   區塊數量: {len(layout_payload)}")
        
        # 準備請求資料
        payload = {"children": layout_payload}
        
        # 發送 PATCH 請求到區塊子項目端點
        response = self._send_request(
            "PATCH",
            f"blocks/{parent_page_id}/children",
            payload
        )
        
        if response:
            logger.info(f"✅ 成功新增 {len(layout_payload)} 個區塊")
        else:
            logger.error(f"❌ 新增區塊失敗")
        
        return response
    
    def create_page(
        self, 
        parent_id: str, 
        page_title: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        在指定父頁面下建立新頁面
        
        此方法會建立一個新的 Notion 頁面，可以：
        - 設定頁面標題
        - 設定自訂屬性
        - 指定父頁面
        
        參數：
            parent_id (str): 父頁面或資料庫的 ID
            page_title (str): 新頁面的標題
            properties (dict, optional): 頁面屬性字典（用於資料庫記錄）
        
        回傳：
            dict: 新建立的頁面資訊，包含：
                - id: 頁面 ID
                - url: 頁面 URL
                - created_time: 建立時間
            None: 建立失敗時
        
        範例：
            >>> page_data = client.create_page(
            ...     parent_id=parent_page_id,
            ...     page_title="我的新頁面"
            ... )
            >>> print(f"頁面已建立：{page_data['url']}")
        """
        logger.info(f"📄 建立新頁面: {page_title}")
        
        # 建立頁面標題屬性
        if properties is None:
            properties = {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": page_title}
                        }
                    ]
                }
            }
        
        # 準備請求資料
        payload = {
            "parent": {"page_id": parent_id},
            "properties": properties
        }
        
        # 發送 POST 請求到頁面端點
        response = self._send_request("POST", "pages", payload)
        
        if response:
            page_data = response.json()
            page_url = page_data.get('url', 'N/A')
            logger.info(f"✅ 頁面建立成功")
            logger.info(f"   URL: {page_url}")
            return page_data
        
        logger.error(f"❌ 頁面建立失敗")
        return None
    
    def create_database(
        self, 
        parent_id: str, 
        db_title: str, 
        properties_schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        在指定父頁面下建立新資料庫
        
        此方法會建立一個新的 Notion 資料庫，可以：
        - 設定資料庫標題
        - 定義欄位架構（屬性類型）
        - 指定父頁面
        
        參數：
            parent_id (str): 父頁面的 ID
            db_title (str): 資料庫標題
            properties_schema (dict): 欄位架構定義，格式：
                {
                    "欄位名稱": {"type": "類型"},
                    ...
                }
                支援的類型：title, rich_text, number, select, multi_select,
                          date, checkbox, url, email, phone_number, etc.
        
        回傳：
            dict: 新建立的資料庫資訊，包含：
                - id: 資料庫 ID
                - url: 資料庫 URL
                - title: 資料庫標題
            None: 建立失敗時
        
        範例：
            >>> schema = {
            ...     "Name": {"title": {}},
            ...     "Status": {"select": {"options": [{"name": "To Do"}]}}
            ... }
            >>> db_data = client.create_database(
            ...     parent_id=parent_page_id,
            ...     db_title="任務清單",
            ...     properties_schema=schema
            ... )
        """
        logger.info(f"🗄️  建立新資料庫: {db_title}")
        logger.debug(f"   欄位數量: {len(properties_schema)}")
        
        # 準備請求資料
        payload = {
            "parent": {"type": "page_id", "page_id": parent_id},
            "title": [
                {
                    "type": "text",
                    "text": {"content": db_title}
                }
            ],
            "properties": properties_schema
        }
        
        # 發送 POST 請求到資料庫端點
        response = self._send_request("POST", "databases", payload)
        
        if response:
            db_data = response.json()
            db_url = db_data.get('url', 'N/A')
            db_id = db_data.get('id', 'N/A')
            
            logger.info(f"✅ 資料庫建立成功")
            logger.info(f"   ID: {db_id}")
            logger.info(f"   URL: {db_url}")
            
            return db_data
        
        logger.error(f"❌ 資料庫建立失敗")
        return None
    
    def query_database(
        self, 
        database_id: str, 
        filter_conditions: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        查詢資料庫記錄
        
        此方法用於從 Notion 資料庫中查詢記錄，支援：
        - 篩選條件（filter）
        - 排序（sort）
        - 分頁查詢
        
        參數：
            database_id (str): 資料庫 ID
            filter_conditions (dict, optional): 篩選條件
            sorts (list, optional): 排序規則列表
            page_size (int): 每頁記錄數（預設：100，最大：100）
        
        回傳：
            list: 記錄列表，每個元素為一筆記錄的完整資料
            None: 查詢失敗時
        
        範例：
            >>> # 查詢所有記錄
            >>> records = client.query_database(db_id)
            >>> 
            >>> # 帶篩選條件的查詢
            >>> filter = {
            ...     "property": "Status",
            ...     "select": {"equals": "In Progress"}
            ... }
            >>> records = client.query_database(db_id, filter_conditions=filter)
        """
        logger.info(f"🔍 查詢資料庫: {database_id}")
        
        # 準備查詢參數
        payload = {"page_size": min(page_size, 100)}
        
        if filter_conditions:
            payload["filter"] = filter_conditions
            logger.debug(f"   使用篩選條件")
        
        if sorts:
            payload["sorts"] = sorts
            logger.debug(f"   使用排序規則")
        
        # 發送 POST 請求到資料庫查詢端點
        response = self._send_request(
            "POST",
            f"databases/{database_id}/query",
            payload
        )
        
        if response:
            data = response.json()
            results = data.get('results', [])
            logger.info(f"✅ 查詢成功，找到 {len(results)} 筆記錄")
            return results
        
        logger.error(f"❌ 查詢失敗")
        return None
    
    def create_page_in_database(
        self, 
        database_id: str, 
        properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        在資料庫中建立新記錄
        
        此方法用於在 Notion 資料庫中新增一筆記錄。
        
        參數：
            database_id (str): 資料庫 ID
            properties (dict): 記錄屬性，格式依資料庫架構而定
        
        回傳：
            dict: 新建立的記錄資訊
            None: 建立失敗時
        
        範例：
            >>> properties = {
            ...     "Name": {
            ...         "title": [{"text": {"content": "新任務"}}]
            ...     },
            ...     "Status": {
            ...         "select": {"name": "To Do"}
            ...     }
            ... }
            >>> record = client.create_page_in_database(db_id, properties)
        """
        logger.debug(f"➕ 在資料庫中建立新記錄")
        
        # 準備請求資料
        payload = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        # 發送 POST 請求到頁面端點（資料庫記錄也是頁面）
        response = self._send_request("POST", "pages", payload)
        
        if response:
            page_data = response.json()
            logger.debug(f"✅ 記錄建立成功")
            return page_data
        
        logger.error(f"❌ 記錄建立失敗")
        return None
    
    def delete_blocks(self, page_id: str) -> bool:
        """
        刪除指定頁面的所有子區塊
        
        此方法會：
        1. 取得頁面的所有子區塊
        2. 逐一刪除每個區塊
        
        參數：
            page_id (str): 頁面 ID
        
        回傳：
            bool: True 表示成功，False 表示失敗
        
        範例：
            >>> success = client.delete_blocks(page_id)
            >>> if success:
            ...     print("頁面已清空")
        """
        logger.info(f"🗑️  刪除頁面區塊: {page_id}")
        
        # 1. 取得所有子區塊
        response = self._send_request(
            "GET",
            f"blocks/{page_id}/children?page_size=100"
        )
        
        if not response:
            logger.error("❌ 無法取得區塊列表")
            return False
        
        blocks = response.json().get('results', [])
        logger.info(f"   找到 {len(blocks)} 個區塊")
        
        # 2. 逐一刪除區塊
        deleted_count = 0
        for block in blocks:
            block_id = block.get('id')
            if not block_id:
                continue
            
            # 發送 DELETE 請求
            del_response = self._send_request(
                "DELETE",
                f"blocks/{block_id}"
            )
            
            if del_response:
                deleted_count += 1
        
        logger.info(f"✅ 成功刪除 {deleted_count}/{len(blocks)} 個區塊")
        return deleted_count == len(blocks)
