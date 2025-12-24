"""
Notion 整合模組 - 處理器
處理 Notion 相關的高層次操作
"""
import logging
import json
import csv
import io
from typing import Optional, List, Dict, Any
from pathlib import Path
from rich.console import Console
from tqdm import tqdm

from .client import NotionApiClient
from .config import notion_config

logger = logging.getLogger(__name__)
console = Console()


class NotionProcessor:
    """Notion 處理器類別"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Notion 處理器
        
        Args:
            api_key: Notion API Key，若未提供則從配置中獲取
        """
        self.api_key = api_key or notion_config.api_key
        self.client = NotionApiClient(self.api_key)
        logger.debug("Notion 處理器已初始化")
    
    def test_connection(self) -> bool:
        """
        測試 Notion API 連接
        
        Returns:
            連接是否成功
        """
        logger.info("開始測試 Notion 連接...")
        notion_info = self.client.test_connection()
        
        if notion_info:
            notion_bot = notion_info.get("name", "Unknown")
            logger.info(f"✅ 連接成功 - Bot 名稱: {notion_bot}")
            console.print(f"[green]✅ Notion 連接測試通過[/green]")
            console.print(f"[cyan]Bot 名稱: {notion_bot}[/cyan]")
            return True
        else:
            logger.critical("❌ Notion 連接測試失敗")
            console.print("[red]❌ Notion 連接測試失敗[/red]")
            return False

    def build_dashboard_layout(self, parent_page_id: Optional[str] = None) -> bool:
        """
        構建儀表板佈局
        
        Args:
            parent_page_id: 父頁面 ID，若未提供則從配置中獲取
            
        Returns:
            是否成功構建
        """
        parent_page_id = parent_page_id or notion_config.parent_page_id
        if not parent_page_id:
            logger.error("父頁面 ID 未設置")
            console.print("[red]❌ 父頁面 ID 未設置[/red]")
            return False
        
        try:
            logger.info("載入佈局配置...")
            schema_path = notion_config.schema_path
            
            if not schema_path.exists():
                logger.error(f"找不到配置文件: {schema_path}")
                console.print(f"[red]❌ 找不到配置文件: {schema_path}[/red]")
                return False
            
            with open(schema_path, "r", encoding="utf-8") as f:
                layout_schema = json.load(f)
            
            layout_payload = layout_schema.get("layout", [])
            logger.info(f"已載入 {len(layout_payload)} 個佈局區塊")
            
            console.print(f"[cyan]📐 開始構建儀表板佈局...[/cyan]")
            response = self.client.append_block_children(parent_page_id, layout_payload)
            
            if response and response.status_code == 200:
                logger.info("✅ 儀表板佈局構建成功")
                console.print("[green]✅ 儀表板佈局構建成功[/green]")
                return True
            else:
                logger.error("❌ 儀表板佈局構建失敗")
                console.print("[red]❌ 儀表板佈局構建失敗[/red]")
                return False
                
        except FileNotFoundError as e:
            logger.error(f"文件讀取錯誤: {e}")
            console.print(f"[red]❌ 文件讀取錯誤: {e}[/red]")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析錯誤: {e}")
            console.print(f"[red]❌ JSON 解析錯誤: {e}[/red]")
            return False
        except Exception as e:
            logger.error(f"未預期的錯誤: {e}")
            console.print(f"[red]❌ 未預期的錯誤: {e}[/red]")
            return False

    def delete_blocks(self, parent_page_id: Optional[str] = None) -> bool:
        """
        刪除頁面中的所有區塊
        
        Args:
            parent_page_id: 父頁面 ID，若未提供則從配置中獲取
            
        Returns:
            是否成功刪除
        """
        parent_page_id = parent_page_id or notion_config.parent_page_id
        if not parent_page_id:
            logger.error("父頁面 ID 未設置")
            console.print("[red]❌ 父頁面 ID 未設置[/red]")
            return False
        
        logger.info("檢測頁面中的區塊...")
        console.print("[cyan]🔍 檢測頁面中的區塊...[/cyan]")
        
        response = self.client.get_block_children(parent_page_id)
        
        if not response or response.status_code != 200:
            logger.error("獲取頁面內容失敗")
            console.print("[red]❌ 獲取頁面內容失敗[/red]")
            return False
        
        blocks = response.json().get("results", [])
        
        if len(blocks) == 0:
            logger.info("頁面中沒有區塊")
            console.print("[yellow]⚠️ 頁面中沒有區塊[/yellow]")
            return True
        
        logger.warning(f"檢測到 {len(blocks)} 個區塊待刪除")
        console.print(f"[yellow]⚠️ 檢測到 {len(blocks)} 個區塊待刪除[/yellow]")
        
        # 開始刪除區塊
        success_count = 0
        for block in tqdm(blocks, desc="刪除區塊"):
            block_id = block.get("id")
            if block_id:
                delete_response = self.client.delete_block(block_id)
                if delete_response and delete_response.status_code == 200:
                    success_count += 1
        
        logger.info(f"成功刪除 {success_count}/{len(blocks)} 個區塊")
        console.print(f"[green]✅ 成功刪除 {success_count}/{len(blocks)} 個區塊[/green]")
        
        return success_count == len(blocks)

    def create_databases(self, parent_page_id: Optional[str] = None) -> bool:
        """
        創建數據庫
        
        Args:
            parent_page_id: 父頁面 ID，若未提供則從配置中獲取
            
        Returns:
            是否成功創建所有數據庫
        """
        parent_page_id = parent_page_id or notion_config.parent_page_id
        if not parent_page_id:
            logger.error("父頁面 ID 未設置")
            console.print("[red]❌ 父頁面 ID 未設置[/red]")
            return False
        
        try:
            logger.info("載入數據庫配置...")
            schema_path = notion_config.schema_path
            
            if not schema_path.exists():
                logger.error(f"找不到配置文件: {schema_path}")
                console.print(f"[red]❌ 找不到配置文件: {schema_path}[/red]")
                return False
            
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            
            db_schemas = schema.get("databases", [])
            logger.info(f"已載入 {len(db_schemas)} 個數據庫配置")
            
            if not db_schemas:
                logger.warning("沒有找到數據庫配置")
                console.print("[yellow]⚠️ 沒有找到數據庫配置[/yellow]")
                return False
            
            created_databases = {}
            
            # 第一階段：創建數據庫（不包含關聯屬性）
            console.print(f"[cyan]📊 創建數據庫... (第 1/2 階段)[/cyan]")
            for db_schema in tqdm(db_schemas, desc="創建數據庫"):
                db_name = db_schema.get("db_name")
                if not db_name:
                    logger.warning("跳過沒有名稱的數據庫配置")
                    continue
                
                # 過濾掉關聯屬性（第二階段才添加）
                properties = {}
                for prop_name, prop_details in db_schema.get("properties", {}).items():
                    if "relation_placeholder" not in prop_details:
                        properties[prop_name] = prop_details
                
                # 構建創建數據庫的 payload
                payload = {
                    "parent": {"type": "page_id", "page_id": parent_page_id},
                    "title": [{"type": "text", "text": {"content": db_schema.get("title", db_name)}}],
                    "properties": properties
                }
                
                logger.info(f"創建數據庫: {db_name}")
                response = self.client.create_database(payload)
                
                if response:
                    new_db_id = response.get("id")
                    created_databases[db_name] = new_db_id
                    logger.info(f"✅ 成功創建 '{db_name}' - ID: {new_db_id[:8]}...")
                    
                    # 保存數據庫 ID 到環境變數
                    env_key = db_schema.get("env_key")
                    if env_key:
                        notion_config.set_env(env_key, new_db_id)
                        logger.debug(f"已保存環境變數: {env_key}")
                else:
                    logger.error(f"❌ 創建數據庫失敗: {db_name}")
                    console.print(f"[red]❌ 創建數據庫失敗: {db_name}[/red]")
                    return False
            
            # 第二階段：更新數據庫關聯屬性
            console.print(f"[cyan]🔗 更新數據庫關聯... (第 2/2 階段)[/cyan]")
            for db_schema in tqdm(db_schemas, desc="更新關聯"):
                db_name = db_schema.get("db_name")
                current_db_id = created_databases.get(db_name)
                
                if not current_db_id:
                    continue
                
                # 找出需要更新的關聯屬性
                properties = {}
                for prop_name, prop_details in db_schema.get("properties", {}).items():
                    if "relation_placeholder" in prop_details:
                        target_db_name = prop_details["relation_placeholder"].get("db_name")
                        target_db_id = created_databases.get(target_db_name)
                        
                        if target_db_id:
                            properties[prop_name] = {
                                "relation": {
                                    "database_id": target_db_id,
                                    "type": "dual_property",
                                    "dual_property": {}
                                }
                            }
                        else:
                            logger.warning(f"找不到目標數據庫: {target_db_name}")
                
                # 如果有關聯屬性需要更新
                if properties:
                    logger.info(f"更新數據庫關聯: {db_name}")
                    update_response = self.client.update_database(current_db_id, properties)
                    
                    if update_response:
                        logger.info(f"✅ 成功更新 '{db_name}' 的關聯屬性")
                    else:
                        logger.error(f"❌ 更新 '{db_name}' 的關聯屬性失敗")
            
            logger.info("✅ 所有數據庫創建完成")
            console.print(f"[green]✅ 成功創建 {len(created_databases)} 個數據庫[/green]")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"文件讀取錯誤: {e}")
            console.print(f"[red]❌ 文件讀取錯誤: {e}[/red]")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析錯誤: {e}")
            console.print(f"[red]❌ JSON 解析錯誤: {e}[/red]")
            return False
        except Exception as e:
            logger.error(f"未預期的錯誤: {e}", exc_info=True)
            console.print(f"[red]❌ 未預期的錯誤: {e}[/red]")
            return False
    
    def import_csv_to_database(
        self, 
        database_id: str, 
        csv_content: str
    ) -> Dict[str, Any]:
        """
        從 CSV 內容導入數據到 Notion 數據庫
        
        Args:
            database_id: 目標數據庫 ID
            csv_content: CSV 文件內容
            
        Returns:
            導入結果字典，包含成功和失敗的記錄
        """
        try:
            # 解析 CSV
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)
            
            if not rows:
                logger.warning("CSV 文件為空")
                return {
                    "success": False,
                    "message": "CSV 文件為空",
                    "imported": 0,
                    "failed": 0
                }
            
            logger.info(f"開始導入 {len(rows)} 筆記錄...")
            console.print(f"[cyan]📥 開始導入 {len(rows)} 筆記錄...[/cyan]")
            
            imported = 0
            failed = 0
            errors = []
            
            for row_num, row in enumerate(tqdm(rows, desc="導入數據"), 1):
                try:
                    # 構建 Notion 頁面屬性
                    properties = self._build_properties_from_csv_row(row)
                    
                    # 創建頁面
                    payload = {
                        "parent": {"database_id": database_id},
                        "properties": properties
                    }
                    
                    response = self.client._send_request("POST", "pages", payload)
                    
                    if response and response.status_code == 200:
                        imported += 1
                    else:
                        failed += 1
                        errors.append(f"第 {row_num} 行導入失敗")
                        
                except Exception as e:
                    failed += 1
                    error_msg = f"第 {row_num} 行錯誤: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # 返回結果
            result = {
                "success": imported > 0,
                "message": f"導入完成：成功 {imported} 筆，失敗 {failed} 筆",
                "imported": imported,
                "failed": failed,
                "errors": errors[:10] if errors else []  # 只返回前 10 個錯誤
            }
            
            logger.info(result["message"])
            console.print(f"[green]✅ {result['message']}[/green]")
            
            return result
            
        except Exception as e:
            error_msg = f"CSV 導入錯誤: {str(e)}"
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
        從 CSV 行構建 Notion 屬性
        
        Args:
            row: CSV 行數據
            
        Returns:
            Notion 屬性字典
        """
        properties = {}
        
        # 處理不同類型的屬性
        for key, value in row.items():
            if not value or value.strip() == "":
                continue
            
            key = key.strip()
            value = value.strip()
            
            # 根據列名判斷屬性類型
            if key.lower() in ["name", "title", "標題", "名稱"]:
                # Title 類型
                properties[key] = {
                    "title": [{"type": "text", "text": {"content": value}}]
                }
            elif key.lower() in ["date", "日期", "deadline", "截止日期"]:
                # Date 類型
                properties[key] = {
                    "date": {"start": value}
                }
            elif key.lower() in ["status", "狀態"]:
                # Status 類型
                properties[key] = {
                    "status": {"name": value}
                }
            elif key.lower() in ["select", "選項"]:
                # Select 類型
                properties[key] = {
                    "select": {"name": value}
                }
            elif key.lower() in ["url", "網址", "link", "連結"]:
                # URL 類型
                properties[key] = {
                    "url": value
                }
            elif key.lower() in ["email", "信箱"]:
                # Email 類型
                properties[key] = {
                    "email": value
                }
            elif key.lower() in ["phone", "電話"]:
                # Phone 類型
                properties[key] = {
                    "phone_number": value
                }
            elif key.lower() in ["number", "數字"]:
                # Number 類型
                try:
                    properties[key] = {
                        "number": float(value)
                    }
                except ValueError:
                    logger.warning(f"無法將 '{value}' 轉換為數字")
            else:
                # 預設為 Rich Text 類型
                properties[key] = {
                    "rich_text": [{"type": "text", "text": {"content": value}}]
                }
        
        return properties
    
    @staticmethod
    def generate_csv_sample(database_type: str = "tasks") -> str:
        """
        生成 CSV 樣本文件內容
        
        Args:
            database_type: 數據庫類型 (tasks, courses, projects 等)
            
        Returns:
            CSV 樣本內容
        """
        samples = {
            "tasks": {
                "headers": ["Name", "Status", "Date", "Priority", "Description"],
                "rows": [
                    ["完成期末報告", "In Progress", "2025-12-30", "High", "撰寫並提交期末報告"],
                    ["準備考試", "Not Started", "2025-12-28", "High", "複習第1-10章內容"],
                    ["小組會議", "Done", "2025-12-20", "Medium", "討論專案進度"],
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
                    ["網站開發專案", "Active", "2025-09-01", "2025-12-31", "Alice, Bob, Charlie"],
                    ["資料分析報告", "Planning", "2026-01-01", "2026-03-31", "David, Eve"],
                    ["行動應用程式", "Completed", "2025-03-01", "2025-08-31", "Frank, Grace"],
                ]
            },
            "sessions": {
                "headers": ["Name", "Date", "Time", "Topic", "Location"],
                "rows": [
                    ["第一週課程", "2025-09-05", "09:00", "課程介紹與大綱", "A101教室"],
                    ["第二週課程", "2025-09-12", "09:00", "基礎概念講解", "A101教室"],
                    ["第三週課程", "2025-09-19", "09:00", "實作練習", "電腦教室B"],
                ]
            },
            "notes": {
                "headers": ["Title", "Category", "Date", "Tags", "Summary"],
                "rows": [
                    ["Python 基礎筆記", "Programming", "2025-09-10", "Python, Basics", "變數、迴圈、函數基本概念"],
                    ["資料庫設計", "Database", "2025-09-15", "SQL, Design", "正規化與 ER Model"],
                    ["網路協定", "Networking", "2025-09-20", "TCP, HTTP", "OSI 七層與常用協定"],
                ]
            },
            "resources": {
                "headers": ["Name", "Type", "URL", "Description", "Category"],
                "rows": [
                    ["Python 官方文檔", "Documentation", "https://docs.python.org", "Python 官方文檔", "Programming"],
                    ["MDN Web Docs", "Tutorial", "https://developer.mozilla.org", "網頁開發資源", "Web"],
                    ["GitHub", "Platform", "https://github.com", "代碼託管平台", "Tools"],
                ]
            }
        }
        
        # 預設使用 tasks
        sample = samples.get(database_type, samples["tasks"])
        
        # 生成 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(sample["headers"])
        writer.writerows(sample["rows"])
        
        return output.getvalue()


# 為了向後兼容，保留舊的函數接口
def execute_test_connection(api_key: str) -> bool:
    """向後兼容的函數"""
    processor = NotionProcessor(api_key)
    return processor.test_connection()


def execute_build_dashboard_layout(api_key: str, parent_page_id: str) -> bool:
    """向後兼容的函數"""
    processor = NotionProcessor(api_key)
    return processor.build_dashboard_layout(parent_page_id)


def execute_delete_blocks(api_key: str, parent_page_id: str) -> bool:
    """向後兼容的函數"""
    processor = NotionProcessor(api_key)
    return processor.delete_blocks(parent_page_id)


def execute_create_database(api_key: str, parent_page_id: str) -> bool:
    """向後兼容的函數"""
    processor = NotionProcessor(api_key)
    return processor.create_databases(parent_page_id)