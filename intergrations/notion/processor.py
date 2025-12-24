"""
Notion 整合模組 - 商業邏輯處理器
=====================================
此模組負責處理 Notion 相關的高階商業邏輯，包括：
- 連線測試與驗證
- 儀表板佈局建立
- 資料庫建立與管理
- CSV 資料匯入
- 課程會話自動生成
- 區塊內容管理

作者：Project Synapse Team
版本：2.0
最後更新：2025-12-25
"""

import logging
import json
import csv
import io
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from tqdm import tqdm

from .client import NotionApiClient
from .config import notion_config

# 設定日誌記錄器
logger = logging.getLogger(__name__)
console = Console()


class NotionProcessor:
    """
    Notion 商業邏輯處理器
    
    此類別封裝了所有 Notion 相關的高階操作，提供：
    - 完整的連線測試功能
    - 自動化的資料庫建立流程
    - CSV 資料匯入與轉換
    - 台灣課程系統整合
    - 豐富的使用者介面回饋
    
    屬性：
        api_key (str): Notion API 金鑰
        client (NotionApiClient): Notion API 客戶端實例
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Notion 處理器
        
        此方法會：
        1. 載入 API 金鑰（從參數或設定檔）
        2. 建立 API 客戶端實例
        3. 初始化日誌記錄
        
        參數：
            api_key (str, optional): Notion API 金鑰
                                     若未提供，則從環境變數讀取
        
        範例：
            >>> processor = NotionProcessor()
            >>> # 或指定金鑰
            >>> processor = NotionProcessor(api_key="secret_xxx...")
        """
        # 取得 API 金鑰（優先使用參數，否則從設定檔取得）
        self.api_key = api_key or notion_config.api_key
        
        # 建立 API 客戶端實例
        self.client = NotionApiClient(self.api_key)
        
        logger.debug("✅ Notion 處理器已初始化完成")
    
    def test_connection(self) -> bool:
        """
        測試 Notion API 連線狀態
        
        此方法會：
        1. 呼叫 API 客戶端的連線測試
        2. 取得目前登入的機器人資訊
        3. 在主控台顯示連線結果
        4. 記錄連線狀態日誌
        
        回傳：
            bool: True 表示連線成功，False 表示連線失敗
        
        範例：
            >>> processor = NotionProcessor()
            >>> if processor.test_connection():
            ...     print("已成功連線到 Notion API")
        """
        logger.info("🔍 開始測試 Notion API 連線...")
        
        # 呼叫客戶端的連線測試方法
        notion_info = self.client.test_connection()
        
        if notion_info:
            # 取得機器人資訊
            notion_bot = notion_info.get("name", "未知機器人")
            bot_type = notion_info.get("type", "未知類型")
            
            # 記錄成功資訊
            logger.info(f"✅ 連線測試通過")
            logger.info(f"   機器人名稱: {notion_bot}")
            logger.info(f"   機器人類型: {bot_type}")
            
            # 在主控台顯示成功訊息
            console.print(f"[green]✅ Notion 連線測試通過[/green]")
            console.print(f"[cyan]🤖 機器人: {notion_bot} ({bot_type})[/cyan]")
            
            return True
        else:
            # 連線失敗
            logger.critical("❌ Notion 連線測試失敗")
            logger.error("   請檢查：")
            logger.error("   1. API 金鑰是否正確")
            logger.error("   2. 網路連線是否正常")
            logger.error("   3. Notion 服務是否可用")
            
            console.print("[red]❌ Notion 連線測試失敗[/red]")
            console.print("[yellow]請檢查 API 金鑰與網路連線[/yellow]")
            
            return False

    def build_dashboard_layout(self, parent_page_id: Optional[str] = None) -> bool:
        """
        建立儀表板佈局
        
        此方法會：
        1. 載入儀表板佈局設定檔
        2. 解析佈局區塊定義
        3. 將區塊新增到指定頁面
        4. 驗證建立結果
        
        參數：
            parent_page_id (str, optional): 父頁面 ID
                                           若未提供，則從設定檔讀取
        
        回傳：
            bool: True 表示建立成功，False 表示建立失敗
        
        拋出異常：
            FileNotFoundError: 找不到佈局設定檔
            json.JSONDecodeError: JSON 格式錯誤
        
        範例：
            >>> processor = NotionProcessor()
            >>> success = processor.build_dashboard_layout(page_id)
            >>> if success:
            ...     print("儀表板已建立完成")
        """
        # 取得父頁面 ID
        parent_page_id = parent_page_id or notion_config.parent_page_id
        
        if not parent_page_id:
            error_msg = "父頁面 ID 未設定！請在環境變數中設定 NOTION_PARENT_PAGE_ID"
            logger.error(error_msg)
            console.print(f"[red]❌ {error_msg}[/red]")
            return False
        
        try:
            # 載入佈局設定檔
            logger.info("📂 載入儀表板佈局設定檔...")
            schema_path = notion_config.schema_path
            
            if not schema_path.exists():
                error_msg = f"找不到設定檔: {schema_path}"
                logger.error(error_msg)
                console.print(f"[red]❌ {error_msg}[/red]")
                return False
            
            # 讀取並解析 JSON 設定檔
            with open(schema_path, "r", encoding="utf-8") as f:
                layout_schema = json.load(f)
            
            # 取得佈局區塊列表
            layout_payload = layout_schema.get("layout", [])
            block_count = len(layout_payload)
            
            logger.info(f"✅ 已載入 {block_count} 個佈局區塊定義")
            
            # 在主控台顯示建立進度
            console.print(f"[cyan]📐 開始建立儀表板佈局（共 {block_count} 個區塊）...[/cyan]")
            
            # 呼叫 API 客戶端新增區塊
            response = self.client.append_block_children(parent_page_id, layout_payload)
            
            # 驗證建立結果
            if response and response.status_code == 200:
                logger.info(f"✅ 儀表板佈局建立成功")
                console.print(f"[green]✅ 儀表板佈局建立成功（{block_count} 個區塊）[/green]")
                return True
            else:
                logger.error("❌ 儀表板佈局建立失敗")
                console.print("[red]❌ 儀表板佈局建立失敗[/red]")
                return False
                
        except FileNotFoundError as e:
            # 檔案不存在錯誤
            error_msg = f"檔案讀取錯誤: {e}"
            logger.error(error_msg)
            console.print(f"[red]❌ {error_msg}[/red]")
            return False
            
        except json.JSONDecodeError as e:
            # JSON 解析錯誤
            error_msg = f"JSON 格式錯誤: {e}"
            logger.error(error_msg)
            console.print(f"[red]❌ {error_msg}[/red]")
            console.print("[yellow]請檢查設定檔的 JSON 格式是否正確[/yellow]")
            return False
            
        except Exception as e:
            # 其他未預期的錯誤
            error_msg = f"發生未預期的錯誤: {e}"
            logger.error(error_msg, exc_info=True)
            console.print(f"[red]❌ {error_msg}[/red]")
            return False

    def delete_blocks(self, parent_page_id: Optional[str] = None) -> bool:
        """
        刪除頁面中的所有區塊
        
        此方法會：
        1. 取得頁面的所有子區塊
        2. 顯示刪除確認資訊
        3. 逐一刪除每個區塊
        4. 統計刪除結果
        
        參數：
            parent_page_id (str, optional): 父頁面 ID
                                           若未提供，則從設定檔讀取
        
        回傳：
            bool: True 表示全部刪除成功，False 表示部分或全部失敗
        
        注意：
            此操作無法復原，請謹慎使用
        
        範例：
            >>> processor = NotionProcessor()
            >>> success = processor.delete_blocks(page_id)
            >>> if success:
            ...     print("頁面已清空")
        """
        # 取得父頁面 ID
        parent_page_id = parent_page_id or notion_config.parent_page_id
        
        if not parent_page_id:
            error_msg = "父頁面 ID 未設定"
            logger.error(error_msg)
            console.print(f"[red]❌ {error_msg}[/red]")
            return False
        
        logger.info("🔍 檢查頁面中的區塊...")
        console.print("[cyan]🔍 正在檢查頁面內容...[/cyan]")
        
        # 呼叫 API 客戶端刪除區塊
        success = self.client.delete_blocks(parent_page_id)
        
        if success:
            console.print("[green]✅ 所有區塊已成功刪除[/green]")
        else:
            console.print("[red]❌ 部分區塊刪除失敗[/red]")
        
        return success

    def create_databases(self, parent_page_id: Optional[str] = None) -> bool:
        """
        建立資料庫
        
        此方法會執行完整的資料庫建立流程：
        1. 載入資料庫架構設定檔
        2. 第一階段：建立所有資料庫（不含關聯欄位）
        3. 第二階段：更新資料庫關聯欄位
        4. 儲存資料庫 ID 到環境變數
        
        為何需要兩階段？
        - 關聯欄位需要目標資料庫的 ID
        - 因此必須先建立所有資料庫，再建立關聯
        
        參數：
            parent_page_id (str, optional): 父頁面 ID
                                           若未提供，則從設定檔讀取
        
        回傳：
            bool: True 表示全部建立成功，False 表示建立失敗
        
        範例：
            >>> processor = NotionProcessor()
            >>> success = processor.create_databases(page_id)
            >>> if success:
            ...     print("所有資料庫已建立完成")
        """
        # 取得父頁面 ID
        parent_page_id = parent_page_id or notion_config.parent_page_id
        
        if not parent_page_id:
            error_msg = "父頁面 ID 未設定"
            logger.error(error_msg)
            console.print(f"[red]❌ {error_msg}[/red]")
            return False
        
        try:
            # 載入資料庫架構設定檔
            logger.info("📂 載入資料庫架構設定檔...")
            schema_path = notion_config.schema_path
            
            if not schema_path.exists():
                error_msg = f"找不到設定檔: {schema_path}"
                logger.error(error_msg)
                console.print(f"[red]❌ {error_msg}[/red]")
                return False
            
            # 讀取並解析 JSON 設定檔
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            
            # 取得資料庫架構列表
            db_schemas = schema.get("databases", [])
            db_count = len(db_schemas)
            
            logger.info(f"✅ 已載入 {db_count} 個資料庫架構定義")
            
            if not db_schemas:
                logger.warning("設定檔中沒有資料庫定義")
                console.print("[yellow]⚠️  設定檔中沒有找到資料庫定義[/yellow]")
                return False
            
            # 用於儲存已建立的資料庫 ID
            created_databases = {}
            
            # ===== 第一階段：建立資料庫（不含關聯欄位）=====
            console.print(f"[cyan]📊 階段 1/2：建立資料庫（共 {db_count} 個）[/cyan]")
            
            for db_schema in tqdm(db_schemas, desc="建立資料庫", unit="個"):
                db_name = db_schema.get("db_name")
                
                if not db_name:
                    logger.warning("跳過未命名的資料庫定義")
                    continue
                
                # 過濾掉關聯欄位（稍後在第二階段處理）
                properties = {}
                for prop_name, prop_details in db_schema.get("properties", {}).items():
                    # 如果屬性定義中包含 relation_placeholder，表示這是關聯欄位
                    # 在第一階段跳過，第二階段再處理
                    if "relation_placeholder" not in prop_details:
                        properties[prop_name] = prop_details
                
                # 取得資料庫標題（預設使用 db_name）
                db_title = db_schema.get("title", db_name)
                
                logger.info(f"📊 建立資料庫: {db_name}")
                
                # 呼叫 API 客戶端建立資料庫
                db_data = self.client.create_database(
                    parent_id=parent_page_id,
                    db_title=db_title,
                    properties_schema=properties
                )
                
                if db_data:
                    # 取得新建立的資料庫 ID
                    new_db_id = db_data.get("id")
                    created_databases[db_name] = new_db_id
                    
                    logger.info(f"✅ 資料庫 '{db_name}' 建立成功")
                    logger.debug(f"   資料庫 ID: {new_db_id}")
                    
                    # 將資料庫 ID 儲存到環境變數（如果有指定 env_key）
                    env_key = db_schema.get("env_key")
                    if env_key:
                        notion_config.set_env(env_key, new_db_id)
                        logger.debug(f"   已儲存環境變數: {env_key} = {new_db_id}")
                else:
                    # 建立失敗
                    error_msg = f"資料庫 '{db_name}' 建立失敗"
                    logger.error(error_msg)
                    console.print(f"[red]❌ {error_msg}[/red]")
                    return False
            
            # ===== 第二階段：更新資料庫關聯欄位 =====
            console.print(f"[cyan]🔗 階段 2/2：更新關聯欄位[/cyan]")
            
            for db_schema in tqdm(db_schemas, desc="更新關聯", unit="個"):
                db_name = db_schema.get("db_name")
                current_db_id = created_databases.get(db_name)
                
                if not current_db_id:
                    continue
                
                # 找出需要更新的關聯欄位
                relation_properties = {}
                
                for prop_name, prop_details in db_schema.get("properties", {}).items():
                    # 檢查是否為關聯欄位
                    if "relation_placeholder" in prop_details:
                        # 取得目標資料庫名稱
                        target_db_name = prop_details["relation_placeholder"].get("db_name")
                        # 從已建立的資料庫中取得目標資料庫 ID
                        target_db_id = created_databases.get(target_db_name)
                        
                        if target_db_id:
                            # 建立關聯欄位定義
                            relation_properties[prop_name] = {
                                "relation": {
                                    "database_id": target_db_id,
                                    "type": "dual_property",
                                    "dual_property": {}
                                }
                            }
                        else:
                            logger.warning(f"找不到目標資料庫: {target_db_name}")
                
                # 如果有關聯欄位需要更新
                if relation_properties:
                    logger.info(f"🔗 更新資料庫 '{db_name}' 的關聯欄位...")
                    
                    # 呼叫 API 更新資料庫（這個方法需要在 client.py 中實作）
                    # 暫時使用 PATCH 請求
                    response = self.client._send_request(
                        "PATCH",
                        f"databases/{current_db_id}",
                        {"properties": relation_properties}
                    )
                    
                    if response and response.status_code == 200:
                        logger.info(f"✅ 資料庫 '{db_name}' 的關聯欄位更新成功")
                    else:
                        logger.warning(f"⚠️  資料庫 '{db_name}' 的關聯欄位更新失敗")
            
            # 所有資料庫建立完成
            logger.info(f"✅ 所有資料庫建立完成（共 {len(created_databases)} 個）")
            console.print(f"[green]✅ 成功建立 {len(created_databases)} 個資料庫[/green]")
            
            return True
            
        except FileNotFoundError as e:
            error_msg = f"檔案讀取錯誤: {e}"
            logger.error(error_msg)
            console.print(f"[red]❌ {error_msg}[/red]")
            return False
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON 格式錯誤: {e}"
            logger.error(error_msg)
            console.print(f"[red]❌ {error_msg}[/red]")
            return False
            
        except Exception as e:
            error_msg = f"發生未預期的錯誤: {e}"
            logger.error(error_msg, exc_info=True)
            console.print(f"[red]❌ {error_msg}[/red]")
            return False
    
    def import_csv_to_database(
        self, 
        database_id: str, 
        csv_content: str,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        從 CSV 內容匯入資料到 Notion 資料庫
        
        此方法會：
        1. 解析 CSV 內容
        2. 將每一列轉換為 Notion 頁面屬性
        3. 建立資料庫記錄
        4. 如果是課程匯入，自動生成課程會話
        5. 統計並回傳匯入結果
        
        支援的欄位類型：
        - Title: 標題欄位（Name, Title, 標題, 名稱）
        - Date: 日期欄位（Date, 日期, Deadline, 截止日期）
        - Status: 狀態欄位（Status, 狀態）
        - Select: 選項欄位（Select, 選項）
        - URL: 網址欄位（URL, 網址, Link, 連結）
        - Email: 電子郵件欄位（Email, 信箱）
        - Phone: 電話欄位（Phone, 電話）
        - Number: 數字欄位（Number, 數字）
        - Rich Text: 富文字欄位（預設類型）
        
        參數：
            database_id (str): 目標資料庫 ID
            csv_content (str): CSV 檔案內容字串
            extra_params (dict, optional): 額外參數，包含：
                - semester_start: 學期開始日期（YYYY-MM-DD）
                - semester_end: 學期結束日期（YYYY-MM-DD）
                - course_sessions_db_id: 課程會話資料庫 ID
        
        回傳：
            dict: 匯入結果字典，包含：
                - success (bool): 是否成功
                - message (str): 結果訊息
                - imported (int): 成功匯入的記錄數
                - failed (int): 失敗的記錄數
                - sessions_created (int): 建立的課程會話數（如果適用）
                - errors (list): 錯誤訊息列表（最多 10 筆）
        
        範例：
            >>> csv_data = "Name,Status\\nTask 1,To Do\\nTask 2,Done"
            >>> result = processor.import_csv_to_database(db_id, csv_data)
            >>> print(f"成功匯入 {result['imported']} 筆記錄")
        """
        try:
            # 解析 CSV 內容
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)
            
            # 驗證 CSV 是否為空
            if not rows:
                logger.warning("CSV 檔案為空，沒有資料可匯入")
                return {
                    "success": False,
                    "message": "CSV 檔案為空",
                    "imported": 0,
                    "failed": 0
                }
            
            # 取得額外參數
            extra_params = extra_params or {}
            
            # 記錄匯入資訊
            logger.info(f"📥 開始匯入 CSV 資料：共 {len(rows)} 筆記錄")
            console.print(f"[cyan]📥 開始匯入 {len(rows)} 筆記錄到資料庫...[/cyan]")
            
            # 統計變數
            imported = 0  # 成功匯入的記錄數
            failed = 0    # 失敗的記錄數
            errors = []   # 錯誤訊息列表
            created_courses = []  # 已建立的課程列表（用於課程會話生成）
            
            # 逐列處理 CSV 資料
            for row_num, row in enumerate(tqdm(rows, desc="匯入資料", unit="筆"), 1):
                try:
                    # 將 CSV 列轉換為 Notion 屬性
                    properties = self._build_properties_from_csv_row(row)
                    
                    # 建立 Notion 頁面（資料庫記錄）
                    page_data = self.client.create_page_in_database(
                        database_id=database_id,
                        properties=properties
                    )
                    
                    if page_data:
                        # 匯入成功
                        imported += 1
                        page_id = page_data.get("id")
                        
                        # 如果是課程匯入，記錄課程資訊以便後續生成會話
                        if extra_params.get('semester_start') and page_id:
                            course_name = row.get('Name', row.get('Title', f'課程 {row_num}'))
                            created_courses.append({
                                'id': page_id,
                                'name': course_name,
                                'row_data': row
                            })
                    else:
                        # 匯入失敗
                        failed += 1
                        error_msg = f"第 {row_num} 列匯入失敗"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                        
                except Exception as e:
                    # 處理個別列的錯誤
                    failed += 1
                    error_msg = f"第 {row_num} 列發生錯誤: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # 如果是課程匯入，自動生成課程會話
            sessions_created = 0
            if created_courses and extra_params.get('semester_start'):
                logger.info(f"📚 開始為 {len(created_courses)} 門課程生成會話...")
                sessions_created = self._generate_course_sessions(
                    created_courses=created_courses,
                    semester_start=extra_params.get('semester_start'),
                    semester_end=extra_params.get('semester_end'),
                    sessions_db_id=extra_params.get('course_sessions_db_id')
                )
            
            # 建立結果訊息
            message = f"匯入完成：成功 {imported} 筆，失敗 {failed} 筆"
            if sessions_created > 0:
                message += f"；已自動生成 {sessions_created} 堂課程會話"
            
            # 組裝回傳結果
            result = {
                "success": imported > 0,
                "message": message,
                "imported": imported,
                "failed": failed,
                "sessions_created": sessions_created,
                "errors": errors[:10] if errors else []  # 只回傳前 10 個錯誤
            }
            
            # 記錄匯入結果
            logger.info(f"✅ {result['message']}")
            
            # 在主控台顯示結果
            if result["success"]:
                console.print(f"[green]✅ {result['message']}[/green]")
            else:
                console.print(f"[red]❌ {result['message']}[/red]")
            
            return result
            
        except Exception as e:
            # 處理整體匯入錯誤
            error_msg = f"CSV 匯入發生錯誤: {str(e)}"
            logger.error(error_msg, exc_info=True)
            console.print(f"[red]❌ {error_msg}[/red]")
            
            return {
                "success": False,
                "message": error_msg,
                "imported": 0,
                "failed": 0
            }
    
    def _build_properties_from_csv_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        將 CSV 列資料轉換為 Notion 頁面屬性
        
        此方法會根據欄位名稱自動判斷屬性類型，並轉換為 Notion API 格式。
        
        屬性類型判斷規則：
        - Title: name, title, 標題, 名稱
        - Date: date, 日期, deadline, 截止日期
        - Status: status, 狀態
        - Select: select, 選項
        - URL: url, 網址, link, 連結
        - Email: email, 信箱
        - Phone: phone, 電話
        - Number: number, 數字
        - Rich Text: 其他所有欄位（預設）
        
        參數：
            row (dict): CSV 列資料，格式為 {欄位名: 值}
        
        回傳：
            dict: Notion 頁面屬性字典
        
        範例：
            >>> row = {"Name": "任務 1", "Status": "進行中", "Date": "2025-12-25"}
            >>> props = processor._build_properties_from_csv_row(row)
        """
        properties = {}
        
        # 逐一處理每個欄位
        for key, value in row.items():
            # 跳過空值
            if not value or value.strip() == "":
                continue
            
            # 清理欄位名稱和值
            key = key.strip()
            value = value.strip()
            
            # 根據欄位名稱判斷屬性類型
            key_lower = key.lower()
            
            if key_lower in ["name", "title", "標題", "名稱"]:
                # Title 類型（標題欄位）
                properties[key] = {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": value}
                        }
                    ]
                }
                
            elif key_lower in ["date", "日期", "deadline", "截止日期"]:
                # Date 類型（日期欄位）
                properties[key] = {
                    "date": {"start": value}
                }
                
            elif key_lower in ["status", "狀態"]:
                # Status 類型（狀態欄位）
                properties[key] = {
                    "status": {"name": value}
                }
                
            elif key_lower in ["select", "選項"]:
                # Select 類型（單選欄位）
                properties[key] = {
                    "select": {"name": value}
                }
                
            elif key_lower in ["url", "網址", "link", "連結"]:
                # URL 類型（網址欄位）
                properties[key] = {
                    "url": value
                }
                
            elif key_lower in ["email", "信箱"]:
                # Email 類型（電子郵件欄位）
                properties[key] = {
                    "email": value
                }
                
            elif key_lower in ["phone", "電話"]:
                # Phone 類型（電話欄位）
                properties[key] = {
                    "phone_number": value
                }
                
            elif key_lower in ["number", "數字"]:
                # Number 類型（數字欄位）
                try:
                    # 嘗試轉換為浮點數
                    properties[key] = {
                        "number": float(value)
                    }
                except ValueError:
                    # 轉換失敗，記錄警告
                    logger.warning(f"無法將 '{value}' 轉換為數字，已跳過")
                    
            else:
                # Rich Text 類型（富文字欄位，預設類型）
                properties[key] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": value}
                        }
                    ]
                }
        
        return properties
    
    def _generate_course_sessions(
        self,
        created_courses: List[Dict[str, Any]],
        semester_start: str,
        semester_end: str,
        sessions_db_id: str
    ) -> int:
        """
        為每門課程自動生成 18 堂課程會話
        
        此方法會：
        1. 計算學期總週數
        2. 平均分配 18 堂課到學期期間
        3. 為每門課程建立會話記錄
        4. 建立課程與會話的關聯
        
        台灣大學課程系統特點：
        - 每學期標準為 18 週
        - 會話日期會平均分配在學期期間
        - 會話會自動關聯到對應的課程
        
        參數：
            created_courses (list): 已建立的課程列表，每個元素包含：
                - id: 課程頁面 ID
                - name: 課程名稱
                - row_data: CSV 原始資料
            semester_start (str): 學期開始日期（格式：YYYY-MM-DD）
            semester_end (str): 學期結束日期（格式：YYYY-MM-DD）
            sessions_db_id (str): 課程會話資料庫 ID
        
        回傳：
            int: 成功建立的課程會話總數
        
        範例：
            >>> courses = [{'id': 'page_id_1', 'name': '資料結構', 'row_data': {...}}]
            >>> count = processor._generate_course_sessions(
            ...     courses, '2025-09-01', '2026-01-15', 'db_id'
            ... )
            >>> print(f"已生成 {count} 堂課程會話")
        """
        # 驗證必要參數
        if not sessions_db_id:
            logger.warning("課程會話資料庫 ID 未設定，跳過會話生成")
            return 0
        
        try:
            # 解析日期字串
            start_date = datetime.strptime(semester_start, "%Y-%m-%d")
            end_date = datetime.strptime(semester_end, "%Y-%m-%d")
            
            # 計算學期總週數
            semester_weeks = (end_date - start_date).days / 7
            
            # 計算每堂課的週間隔（18 堂課平均分配）
            weeks_per_session = max(1, int(semester_weeks / 18))
            
            # 統計變數
            total_sessions_created = 0
            
            logger.info(f"📚 開始為 {len(created_courses)} 門課程生成會話...")
            logger.info(f"   學期週數: {semester_weeks:.1f} 週")
            logger.info(f"   會話間隔: {weeks_per_session} 週")
            
            console.print(f"[cyan]📚 為 {len(created_courses)} 門課程生成 18 堂會話[/cyan]")
            
            # 為每門課程生成會話
            for course in tqdm(created_courses, desc="生成會話", unit="門課"):
                course_name = course.get('name', '未命名課程')
                course_id = course.get('id')
                
                logger.debug(f"為課程 '{course_name}' 生成會話...")
                
                # 生成 18 堂課
                for session_num in range(1, 19):
                    # 計算會話日期
                    session_date = start_date + timedelta(
                        weeks=(session_num - 1) * weeks_per_session
                    )
                    
                    # 確保會話日期不超過學期結束日期
                    if session_date > end_date:
                        session_date = end_date
                    
                    try:
                        # 建立會話屬性
                        session_properties = {
                            "Name": {
                                "title": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": f"{course_name} - 第 {session_num} 週"
                                        }
                                    }
                                ]
                            },
                            "Date": {
                                "date": {
                                    "start": session_date.strftime("%Y-%m-%d")
                                }
                            },
                            "Course": {
                                "relation": [{"id": course_id}]
                            }
                        }
                        
                        # 建立課程會話記錄
                        session_data = self.client.create_page_in_database(
                            database_id=sessions_db_id,
                            properties=session_properties
                        )
                        
                        if session_data:
                            total_sessions_created += 1
                        else:
                            logger.warning(
                                f"無法為課程 '{course_name}' 建立第 {session_num} 週的會話"
                            )
                    
                    except Exception as e:
                        logger.error(f"建立課程會話時發生錯誤: {str(e)}")
            
            # 記錄完成資訊
            logger.info(f"✅ 成功生成 {total_sessions_created} 堂課程會話")
            console.print(
                f"[green]✅ 成功生成 {total_sessions_created} 堂課程會話[/green]"
            )
            
            return total_sessions_created
            
        except ValueError as e:
            # 日期格式錯誤
            logger.error(f"日期格式錯誤: {str(e)}")
            console.print(f"[red]❌ 日期格式錯誤: {str(e)}[/red]")
            console.print("[yellow]日期格式應為 YYYY-MM-DD[/yellow]")
            return 0
            
        except Exception as e:
            # 其他錯誤
            logger.error(f"生成課程會話時發生錯誤: {str(e)}", exc_info=True)
            console.print(f"[red]❌ 生成課程會話失敗: {str(e)}[/red]")
            return 0
    
    @staticmethod
    def generate_csv_sample(database_type: str = "tasks") -> str:
        """
        生成 CSV 範例檔案內容
        
        此方法提供各種資料庫類型的 CSV 範例，方便使用者參考格式。
        
        支援的資料庫類型：
        - tasks: 任務管理
        - courses: 課程資料
        - projects: 專案管理
        - sessions: 課程會話
        - notes: 筆記管理
        - resources: 資源連結
        
        參數：
            database_type (str): 資料庫類型（預設：tasks）
        
        回傳：
            str: CSV 範例內容（包含標題列和資料列）
        
        範例：
            >>> sample_csv = NotionProcessor.generate_csv_sample("courses")
            >>> print(sample_csv)
            Name,Code,Instructor,Schedule,Credits
            資料結構,CS101,王教授,週一 09:00-12:00,3
        """
        # 定義各種類型的 CSV 範例
        samples = {
            "tasks": {
                "headers": ["Name", "Status", "Date", "Priority", "Description"],
                "rows": [
                    ["完成期末報告", "進行中", "2025-12-30", "高", "撰寫並提交期末報告"],
                    ["準備考試", "未開始", "2025-12-28", "高", "複習第 1-10 章內容"],
                    ["小組會議", "已完成", "2025-12-20", "中", "討論專案進度"],
                ]
            },
            "courses": {
                "headers": ["Name", "Code", "Instructor", "Schedule", "Credits"],
                "rows": [
                    ["資料結構", "CS101", "王教授", "週一 09:00-12:00", "3"],
                    ["演算法", "CS201", "李教授", "週三 13:00-16:00", "3"],
                    ["機器學習", "CS301", "陳教授", "週五 09:00-12:00", "3"],
                ]
            },
            "projects": {
                "headers": ["Name", "Status", "Start Date", "End Date", "Team Members"],
                "rows": [
                    ["網站開發專案", "進行中", "2025-09-01", "2025-12-31", "Alice, Bob, Charlie"],
                    ["資料分析報告", "規劃中", "2026-01-01", "2026-03-31", "David, Eve"],
                    ["行動應用程式", "已完成", "2025-03-01", "2025-08-31", "Frank, Grace"],
                ]
            },
            "sessions": {
                "headers": ["Name", "Date", "Time", "Topic", "Location"],
                "rows": [
                    ["第一週課程", "2025-09-05", "09:00", "課程介紹與大綱", "A101 教室"],
                    ["第二週課程", "2025-09-12", "09:00", "基礎概念講解", "A101 教室"],
                    ["第三週課程", "2025-09-19", "09:00", "實作練習", "電腦教室 B"],
                ]
            },
            "notes": {
                "headers": ["Title", "Category", "Date", "Tags", "Summary"],
                "rows": [
                    ["Python 基礎筆記", "程式設計", "2025-09-10", "Python, 基礎", "變數、迴圈、函式基本概念"],
                    ["資料庫設計", "資料庫", "2025-09-15", "SQL, 設計", "正規化與 ER Model"],
                    ["網路協定", "網路", "2025-09-20", "TCP, HTTP", "OSI 七層與常用協定"],
                ]
            },
            "resources": {
                "headers": ["Name", "Type", "URL", "Description", "Category"],
                "rows": [
                    ["Python 官方文件", "文件", "https://docs.python.org", "Python 官方文件", "程式設計"],
                    ["MDN Web Docs", "教學", "https://developer.mozilla.org", "網頁開發資源", "網頁"],
                    ["GitHub", "平台", "https://github.com", "程式碼託管平台", "工具"],
                ]
            }
        }
        
        # 取得指定類型的範例（若不存在則使用 tasks）
        sample = samples.get(database_type, samples["tasks"])
        
        # 生成 CSV 內容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 寫入標題列
        writer.writerow(sample["headers"])
        
        # 寫入資料列
        writer.writerows(sample["rows"])
        
        return output.getvalue()


# ===== 向後相容的函式介面 =====
# 這些函式保留是為了與舊版程式碼相容

def execute_test_connection(api_key: str) -> bool:
    """
    測試 Notion 連線（向後相容函式）
    
    參數：
        api_key (str): Notion API 金鑰
    
    回傳：
        bool: 連線是否成功
    """
    processor = NotionProcessor(api_key)
    return processor.test_connection()


def execute_build_dashboard_layout(api_key: str, parent_page_id: str) -> bool:
    """
    建立儀表板佈局（向後相容函式）
    
    參數：
        api_key (str): Notion API 金鑰
        parent_page_id (str): 父頁面 ID
    
    回傳：
        bool: 是否成功
    """
    processor = NotionProcessor(api_key)
    return processor.build_dashboard_layout(parent_page_id)


def execute_delete_blocks(api_key: str, parent_page_id: str) -> bool:
    """
    刪除頁面區塊（向後相容函式）
    
    參數：
        api_key (str): Notion API 金鑰
        parent_page_id (str): 父頁面 ID
    
    回傳：
        bool: 是否成功
    """
    processor = NotionProcessor(api_key)
    return processor.delete_blocks(parent_page_id)


def execute_create_database(api_key: str, parent_page_id: str) -> bool:
    """
    建立資料庫（向後相容函式）
    
    參數：
        api_key (str): Notion API 金鑰
        parent_page_id (str): 父頁面 ID
    
    回傳：
        bool: 是否成功
    """
    processor = NotionProcessor(api_key)
    return processor.create_databases(parent_page_id)
