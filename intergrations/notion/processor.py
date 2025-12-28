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
from datetime import datetime, timedelta, timezone
from rich.console import Console
from tqdm import tqdm

from .client import NotionApiClient
from .config import notion_config
from utils.course_schedule_parser import CourseScheduleParser
from config.course_schedule_config import get_semester_info

# 設定日誌記錄器
logger = logging.getLogger(__name__)
console = Console()
TZ_TAIPEI = timezone(timedelta(hours=8))


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
                    
                    # Update: Override legacy env keys with standardized names
                    key_mapping = {
                        "NOTION_DATABASE_ID": "", # Deprecated
                        "SUBJECT_DATABASE_ID": "COURSE_HUB_ID",
                        "COURSE_DATABASE_ID": "CLASS_SESSION_ID",
                        "PROJECTS_DATABASE_ID": "PROJECT_DATABASE_ID",
                        "RESOURCES_DATABASE_ID": "RESOURCE_DATABASE_ID",
                        "NOTE_DB_ID": "NOTE_DATABASE_ID"
                    }
                    
                    if env_key in key_mapping:
                        env_key = key_mapping[env_key]
                    
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
            # 移除 BOM (Byte Order Mark) 以防 Excel CSV 造成標頭解析錯誤
            csv_content = csv_content.lstrip('\ufeff')
            
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            # 過濾完全空白的列 (所有值都為 None 或 空字串)
            rows = [row for row in csv_reader if any(str(v).strip() for v in row.values() if v)]
            
            
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
                        # Update: Support smart mode where semester_start might be missing but sessions_db_id is present
                        if (extra_params.get('semester_start') or extra_params.get('course_sessions_db_id')) and page_id:
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
            
            # 5. 課程匯入後，自動生成 Course Sessions
            sessions_created = 0
            if created_courses and extra_params.get('course_sessions_db_id'):
                logger.info(f"📚 開始為 {len(created_courses)} 門課程生成會話...")
                sessions_created = self._generate_course_sessions(
                    created_courses=created_courses,
                    semester_start=extra_params.get('semester_start'),
                    semester_end=extra_params.get('semester_end'),
                    sessions_db_id=extra_params.get('course_sessions_db_id'),
                    notes_db_id=extra_params.get('notes_db_id')
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
        """
        properties = {}
        
        # 欄位映射表 (CSV Header -> Notion Property Name)
        # 根據 notion_schema.json 定義
        key_mapping = {
            "name": "Course Name",
            "title": "Course Name", 
            "標題": "Course Name",
            "名稱": "Course Name",
            "code": "Course Code",
            "instructor": "Professor",
            "teacher": "Professor",
            "location": "Class Location", # If exists in DB
            "remarks": "Remarks" # If exists in DB
        }

        # 逐一處理每個欄位
        for key, value in row.items():
            # 跳過空值
            if value is None:
                continue
            
            # 清理欄位名稱 (移除 BOM 和空白)
            clean_key = key.lstrip('\ufeff').strip()
            # 清理值
            clean_value = str(value).strip()
            
            if clean_value == "":
                continue
            
            # 跳過純邏輯欄位（不匯入 Notion，但用於後續計算）
            # Schedule 用於生成 Session, 不需要存入 Course Property (除非 Schema 有定義)
            # Remarks/Location/備註/地點: 使用者 CSV 有這些欄位，但目前 Notion Schema (Course Hub) 未定義
            # 為了避免 API 400 錯誤，必須在此跳過。
            skip_keys = ["schedule", "remarks", "location", "備註", "地點"]
            if clean_key.lower() in skip_keys:
                # If Schedule, try to extract "Day" for Course Hub property
                if clean_key.lower() == "schedule" and clean_value:
                    # Format: "三9,三10..." -> Take first char "三"
                    day_char = clean_value[0]
                    day_map_zh = {"一": "Mon", "二": "Tue", "三": "Wed", "四": "Thu", "五": "Fri", "六": "Sat", "日": "Sun"}
                    mapped_day = day_map_zh.get(day_char)
                    
                    if mapped_day:
                         properties["Day"] = {"select": {"name": mapped_day}}

                continue

            # 映射欄位名稱
            mapped_key = key_mapping.get(clean_key.lower(), clean_key)
            
            # 根據欄位名稱 (mapped_key) 判斷屬性類型
            key_lower = mapped_key.lower()
            
            # 1. 特殊欄位處理
            if key_lower in ["course name", "name", "title", "標題"]:
                 # Notion 的 Title 屬性名稱可能因 DB 而異，但通常建立時第一個欄位就是 Title
                 # 這裡假設 schema 定義的 title key 是 "Course Name" (for Courses) or "Task", "Project", etc.
                 # 但為了通用性，如果遇到 "name"/"title"，我們嘗試保留原始 key 或使用 mapping
                 # 若 API 回傳 "Name is not a property"，表示 DB 的 Title 屬性叫做別的
                 properties[mapped_key] = {
                    "title": [{"type": "text", "text": {"content": clean_value}}]
                }
            
            # 2. Select 類型
            elif key_lower in ["semester", "type", "status", "day", "category", "學期", "類型", "狀態"]:
                properties[mapped_key] = {
                    "select": {"name": clean_value}
                }

            # 3. Rich Text 類型 (Course Code, Professor, Credits, etc.)
            else:
                 # 若不在上述規則，預設為 Rich Text
                 # 注意：若該欄位在 Notion DB 不存在，仍會報錯。
                 # 對於 Courses CSV 的 "Location", "Remarks" 等，若 DB 沒這些欄位，會失敗。
                 # 暫時保留匯入，若失敗則 User 需要在 DB 加欄位，或我們需過濾。
                 # 根據 User Log, "Schedule", "Location", "Remarks" 都不存在。
                 # 我們在前面積極過濾 Schedule。
                 
                 # 為了保險，對於 Course Import，我們可以加一個白名單檢查？
                 # 但這會破壞其他 DB 的靈活度。
                 # 採取策略：盡量映射，若 User 的 CSV 有多餘欄位且 DB 沒開，就會報錯，這是符合預期的 (User 應修改 DB or CSV)。
                 # 但針對 User 提供的標準 Course CSV，我們已知 "Code" -> "Course Code", "Instructor" -> "Professor".
                 
                 properties[mapped_key] = {
                    "rich_text": [{"type": "text", "text": {"content": clean_value}}]
                }
        
        return properties
    
    def _generate_course_sessions(
        self,
        created_courses: List[Dict[str, Any]],
        semester_start: Optional[str],
        semester_end: Optional[str],
        sessions_db_id: str,
        notes_db_id: Optional[str] = None
    ) -> int:
        """
        Generate class sessions for courses.
        Supports two modes:
        1. Smart Mode (Preferred): Uses 'Year', 'Semester', and 'Schedule' columns from CSV to generate precise dates.
        2. Legacy Mode (Fallback): Distributes 18 sessions evenly between global start/end dates.
        """
        if not sessions_db_id:
            logger.warning("Course Session DB ID not set, skipping session generation")
            return 0
        
        total_sessions_created = 0
        logger.info(f"📚 Starting session generation for {len(created_courses)} courses...")

        # Pre-parse global dates if available (for fallback)
        global_start = None
        global_end = None
        if semester_start and semester_end:
            try:
                global_start = datetime.strptime(semester_start, "%Y-%m-%d")
                global_end = datetime.strptime(semester_end, "%Y-%m-%d")
            except ValueError:
                logger.warning("Invalid global semester dates provided")

        for course in tqdm(created_courses, desc="Generating Sessions", unit="course"):
            course_name = course.get('name', 'Untitled Course')
            course_id = course.get('id')
            row_data = course.get('row_data', {})
            
            # --- Attempt Smart Mode ---
            year_str = row_data.get('Year', row_data.get('year', row_data.get('學年', '')))
            sem_str = row_data.get('Semester', row_data.get('semester', row_data.get('學期', '')))
            
            # Support combined "學年學期" column (e.g., "114-1") OR "Semester" column having "114-1"
            combined_ys = row_data.get('學年學期', '')
            
            # Check if 'Semester' column actually holds the combined info (e.g. "114-1")
            if sem_str and '-' in str(sem_str) and not year_str:
                 combined_ys = sem_str
            
            if not year_str and (not sem_str or '-' in str(sem_str)) and combined_ys and '-' in str(combined_ys):
                try:
                    parts = str(combined_ys).split('-')
                    if len(parts) >= 2:
                        year_str = parts[0].strip()
                        sem_str = parts[1].strip()
                except Exception:
                    logger.warning(f"Failed to parse '學年學期': {combined_ys}")

            schedule_str = row_data.get('Schedule', row_data.get('schedule', row_data.get('時間', '')))

            sessions_to_create = []

            # valid_smart_mode = False
            if year_str and sem_str and schedule_str:
                try:
                    year = int(year_str)
                    sem = int(sem_str)
                    
                    # 1. Get Semester Dates
                    semester_info = get_semester_info(year, sem)
                    if semester_info:
                        # 2. Parse Schedule String (e.g., "一3,一4")
                        parsed_schedule = CourseScheduleParser.parse_schedule(schedule_str)
                        
                        if parsed_schedule:
                            # 3. Calculate exact class dates
                            class_dates = CourseScheduleParser.get_class_dates(
                                parsed_schedule, year, sem
                            )
                            
                            # Limit to approx 18 weeks * sessions_per_week to avoid infinite loops or massive data
                            # But usually get_class_dates returns exactly what fits in the date range.
                            
                            # Merge sessions by date
                            from itertools import groupby
                            
                            # Sort by date and start time to ensure grouping works and times are strict
                            class_dates.sort(key=lambda x: (x['date'], x['start_time'] or datetime.min.time()))
                            
                            start_date = class_dates[0]['date'] if class_dates else datetime.today()

                            for date_key, group in groupby(class_dates, key=lambda x: x['date']):
                                group_list = list(group)
                                
                                # Find start and end time for the merged block
                                day_start = group_list[0]['start_time']
                                day_end = group_list[-1]['end_time']
                                
                                # Calculate Week Number (1-based)
                                # Assumption: Semester starts near the first class. 
                                # Or use 'semester_info["start"]' if available? 
                                # semester_info dict has 'start' (datetime object).
                                # User Req 1061: Use First Class Date as anchor (not Semester Start)
                                sem_start_raw = start_date
                                
                                # Ensure both are date objects
                                d1 = date_key.date() if hasattr(date_key, 'date') else date_key
                                d2 = sem_start_raw.date() if hasattr(sem_start_raw, 'date') else sem_start_raw
                                
                                delta_days = (d1 - d2).days
                                current_week = (delta_days // 7) + 1
                                
                                # Limit to 18 weeks
                                if current_week > 18:
                                    logger.debug(f"Skipping session at {date_key} (Week {current_week} > 18)")
                                    continue
                                
                                # Cap week at 18 if desired, or let it flow? User said 1-18. 
                                # If it goes to 19 (exam week), maybe keep it?
                                # We'll just use the calculated value.
                                
                                sessions_to_create.append({
                                    "date": date_key,
                                    "name": f"{course_name}", # Internal ref, override in writer anyway
                                    "start_time": day_start,
                                    "end_time": day_end,
                                    "week": current_week
                                })

                            # valid_smart_mode = True
                            logger.debug(f"Smart schedule generated for '{course_name}': {len(sessions_to_create)} merged sessions")
                        else:
                            logger.warning(f"Failed to parse schedule string for '{course_name}': {schedule_str}")
                    else:
                        logger.warning(f"Semester info not found for Year {year} Sem {sem}")
                except ValueError as e:
                    logger.warning(f"Error parsing smart mode data for '{course_name}': {e}")

            # --- Fallback: Legacy Mode ---
            if not sessions_to_create and global_start and global_end:
                logger.debug(f"Using fallback legacy mode for '{course_name}'")
                semester_weeks = (global_end - global_start).days / 7
                weeks_per_session = max(1, int(semester_weeks / 18))
                
                for i in range(1, 19):
                     session_date = global_start + timedelta(weeks=(i - 1) * weeks_per_session)
                     if session_date > global_end: session_date = global_end
                     sessions_to_create.append({
                         "date": session_date,
                         "name": f"{course_name} - Week {i}",
                         "start_time": None,
                         "end_time": None
                     })

            # --- Create Notion Pages ---
            if sessions_to_create:
                for idx, sess in enumerate(tqdm(sessions_to_create, desc="生成課程會話與筆記", unit="堂")):
                    try:
                        # 1. Create Class Session
                        date_prop = {"start": sess['date'].strftime("%Y-%m-%d")}
                        
                        # Add time if available
                        if sess.get('start_time'):
                            dt_start = datetime.combine(sess['date'], sess['start_time']).replace(tzinfo=TZ_TAIPEI)
                            date_prop['start'] = dt_start.isoformat()
                            
                            if sess.get('end_time'):
                                dt_end = datetime.combine(sess['date'], sess['end_time']).replace(tzinfo=TZ_TAIPEI)
                                date_prop['end'] = dt_end.isoformat()

                            # Calculate metadata
                            week_num = sess.get('week', idx + 1) # Use calculated week or fallback to index
                            
                            # Day mapping
                            weekday_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                            day_str = weekday_map[sess['date'].weekday()]
                            
                            # Time formatting
                            start_time_str = sess['start_time'].strftime("%H:%M") if sess.get('start_time') else ""
                            end_time_str = sess['end_time'].strftime("%H:%M") if sess.get('end_time') else ""
                            
                            # Semester formatting (Use CSV input raw format "113-1" if available, else formatted label)
                            # User likely wants "113-1" if that was the input. 
                            # But wait, create_databases didn't see "113-1" in generated sample.
                            # We'll use the one derived from input or fallback.
                            # Let's reuse 'sem_label' logic but prefer raw 'course_semester' if tracked?
                            # Actually, passing '113-1' style string to Select is fine if it creates option.
                            # Let's stick to the generated 'sem_label' (e.g. Fall 2024) or customize?
                            # User input: "Semester" field in CSV is "113-1".
                            # Let's try to infer from 'sess' if we carried it? No.
                            # Re-calculate sem_label properly.
                            
                            sem_label = "Unknown"
                            if year and sem:
                                # Use "113-1" format directly if user prefers? 
                                # Or "Fall 2024"? User complained about "Week", not "Semester" value specifically.
                                # But let's look at schema options. Schema has empty options list.
                                # Let's stick to standard "Fall {AD_Year}" for now or "113-1"?
                                # Given "113-1" is in CSV, let's try to reconstruct that format.
                                sem_label = f"{year}-{sem}"
                            
                            session_properties = {
                                "Class Session": {"title": [{"text": {"content": course_name}}]}, # Just Course Name
                                "Date & Reminder": {"date": date_prop},
                                "Related to Course Hub": {"relation": [{"id": course_id}]},
                                "Week": {"number": week_num},
                                "Day": {"select": {"name": day_str}},
                                "Start Time": {"rich_text": [{"text": {"content": start_time_str}}]},
                                "End Time": {"rich_text": [{"text": {"content": end_time_str}}]},
                                "Semester": {"select": {"name": sem_label}}
                            }
                            
                            session_page = self.client.create_page_in_database(sessions_db_id, session_properties)
                            
                            if session_page:
                                total_sessions_created += 1
                                session_id = session_page.get('id')
                                
                                # 2. Create Note (if DB ID provided)
                                if notes_db_id and session_id:
                                    try:
                                        # Note Title: Lecture Note - {Course Name}
                                        note_title = f"Lecture Note - {course_name}"
                                        
                                        note_properties = {
                                            "Note": {"title": [{"text": {"content": note_title}}]},
                                            "Category": {"select": {"name": "Lecture Note"}}, # Singular "Note" based on user req? Or check schema options. Schema says "Lecture Note" (singular).
                                            "Class Date": {"date": date_prop}, 
                                            "Related to Course Session": {"relation": [{"id": session_id}]},
                                            "Related to Course Hub": {"relation": [{"id": course_id}]},
                                            "Semester": {"select": {"name": sem_label}},
                                            "Week": {"number": week_num} 
                                        }
                                        
                                        self.client.create_page_in_database(notes_db_id, note_properties)
                                    
                                    except Exception as ne:
                                        logger.error(f"Failed to create Note for {sess['name']}: {ne}")

                    except Exception as e:
                        logger.error(f"Failed to create session for {course_name}: {e}")
            else:
                 logger.warning(f"No sessions generated for course '{course_name}' - missing Schedule/Year info or global dates.")

        logger.info(f"✅ Successfully generated {total_sessions_created} course sessions")
        console.print(f"[green]✅ Generated {total_sessions_created} sessions[/green]")
        return total_sessions_created
    
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
                "headers": ["Name", "Semester", "Schedule", "Code", "Instructor", "Credits", "Type", "Location", "Remarks"],
                "rows": [
                    ["諮商理論與技術", "114-1", "三9,三10,三11", "CP__20500", "余振民", "3", "核心學程", "社科院D301", "法律社會、犯罪防治與觀護"],
                    ["人格心理學", "114-1", "二9,二10,二11", "CP__20700", "林繼偉", "3", "核心學程", "社科院D301", "諮商與臨床心理學核心學程"],
                    ["中文能力與涵養AC", "113-2", "一4,一5,一6", "CLC_6232AC", "謝明陽", "3", "中文必修", "人社二館B107", "中文必修"],
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
