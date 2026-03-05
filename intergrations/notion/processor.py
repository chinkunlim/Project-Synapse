"""
Notion 整合模組 - 商業邏輯處理器 (v3.0 - Modular Academic Ecosystem)
=====================================
此模組負責處理 Notion 相關的高階商業邏輯。
最後更新：2026-03
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

logger = logging.getLogger(__name__)
console = Console()
TZ_TAIPEI = timezone(timedelta(hours=8))

class NotionProcessor:
    """Notion 商業邏輯處理器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or notion_config.api_key
        self.client = NotionApiClient(self.api_key)
        logger.debug("✅ Notion 處理器已初始化完成 (v3.0)")
    
    def test_connection(self) -> bool:
        logger.info("🔍 開始測試 Notion API 連線...")
        notion_info = self.client.test_connection()
        if notion_info:
            notion_bot = notion_info.get("name", "未知機器人")
            logger.info(f"✅ 連線測試通過 | 機器人: {notion_bot}")
            console.print(f"[green]✅ Notion 連線測試通過[/green]")
            return True
        else:
            logger.critical("❌ Notion 連線測試失敗")
            console.print("[red]❌ Notion 連線測試失敗[/red]")
            return False

    def build_dashboard_layout(self, parent_page_id: Optional[str] = None) -> bool:
        parent_page_id = parent_page_id or notion_config.parent_page_id
        if not parent_page_id: return False
        try:
            schema_path = notion_config.schema_path
            with open(schema_path, "r", encoding="utf-8") as f:
                layout_schema = json.load(f)
            layout_payload = layout_schema.get("layout", [])
            response = self.client.append_block_children(parent_page_id, layout_payload)
            if response and response.status_code == 200: return True
            return False
        except Exception as e:
            logger.error(f"儀表板佈局建立失敗: {e}")
            return False

    def delete_blocks(self, parent_page_id: Optional[str] = None) -> bool:
        parent_page_id = parent_page_id or notion_config.parent_page_id
        if not parent_page_id: return False
        return self.client.delete_blocks(parent_page_id)

    def create_databases(self, parent_page_id: Optional[str] = None) -> bool:
        parent_page_id = parent_page_id or notion_config.parent_page_id
        if not parent_page_id: return False
        
        try:
            schema_path = notion_config.schema_path
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            
            db_schemas = schema.get("databases", [])
            created_databases = {}
            
            for db_schema in tqdm(db_schemas, desc="建立系統資料庫", unit="個"):
                db_name = db_schema.get("db_name")
                if not db_name: continue
                
                properties = {k: v for k, v in db_schema.get("properties", {}).items() if "relation_placeholder" not in v}
                db_title = db_schema.get("title", db_name)
                
                db_data = self.client.create_database(parent_page_id, db_title, properties)
                if db_data:
                    new_db_id = db_data.get("id")
                    created_databases[db_name] = new_db_id
                    
                    env_key = db_schema.get("env_key")
                    key_mapping = {
                        "SUBJECT_DATABASE_ID": "COURSE_HUB_ID",
                        "COURSE_DATABASE_ID": "CLASS_SESSION_ID",
                        "PROJECTS_DATABASE_ID": "PROJECT_DATABASE_ID",
                        "RESOURCES_DATABASE_ID": "RESOURCE_DATABASE_ID",
                        "NOTE_DB_ID": "NOTE_DATABASE_ID",
                        "THEORY_DB_ID": "THEORY_HUB_ID"
                    }
                    if env_key in key_mapping: env_key = key_mapping[env_key]
                    if env_key: notion_config.set_env(env_key, new_db_id)
            
            for db_schema in db_schemas:
                db_name = db_schema.get("db_name")
                current_db_id = created_databases.get(db_name)
                if not current_db_id: continue
                
                relation_properties = {}
                for prop_name, prop_details in db_schema.get("properties", {}).items():
                    if "relation_placeholder" in prop_details:
                        target_db_name = prop_details["relation_placeholder"].get("db_name")
                        target_db_id = created_databases.get(target_db_name)
                        if target_db_id:
                            relation_properties[prop_name] = {
                                "relation": {"database_id": target_db_id, "type": "dual_property", "dual_property": {}}
                            }
                
                if relation_properties:
                    self.client._send_request("PATCH", f"databases/{current_db_id}", {"properties": relation_properties})
            return True
        except Exception as e:
            logger.error(f"資料庫建立錯誤: {e}")
            return False

    def import_csv_to_database(self, database_id: str, csv_content: str, extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            csv_content = csv_content.lstrip('\ufeff')
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = [row for row in csv_reader if any(str(v).strip() for v in row.values() if v)]
            
            if not rows: return {"success": False, "message": "CSV 為空", "imported": 0, "failed": 0}
            
            extra_params = extra_params or {}
            imported, failed, errors, created_courses = 0, 0, [], []
            
            for row_num, row in enumerate(tqdm(rows, desc="匯入資料"), 1):
                try:
                    properties = self._build_properties_from_csv_row(row)
                    page_data = self.client.create_page_in_database(database_id, properties)
                    
                    if page_data:
                        imported += 1
                        page_id = page_data.get("id")
                        if extra_params.get('course_sessions_db_id') and page_id:
                            course_name = row.get('Course Name', row.get('Title', f'課程 {row_num}'))
                            created_courses.append({'id': page_id, 'name': course_name, 'row_data': row})
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    errors.append(str(e))
            
            sessions_created = 0
            if created_courses and extra_params.get('course_sessions_db_id'):
                sessions_created = self._generate_course_sessions(
                    created_courses=created_courses,
                    sessions_db_id=extra_params.get('course_sessions_db_id'),
                    notes_db_id=extra_params.get('notes_db_id')
                )
            
            return {
                "success": imported > 0, "message": f"成功 {imported} 筆，失敗 {failed} 筆", 
                "imported": imported, "failed": failed, "sessions_created": sessions_created
            }
        except Exception as e:
            return {"success": False, "message": str(e), "imported": 0, "failed": 0}

    def _build_properties_from_csv_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        properties = {}
        key_mapping = {"name": "Course Name", "title": "Course Name", "course name": "Course Name", "code": "Course Code", "course code": "Course Code", "instructor": "Professor", "professor": "Professor", "type": "Type", "semester": "Semester"}
        
        for key, value in row.items():
            if value is None: continue
            clean_key = key.lstrip('\ufeff').strip()
            clean_value = str(value).strip()
            if not clean_value: continue
            
            skip_keys = ["schedule", "remarks", "location", "時間", "地點"]
            if clean_key.lower() in skip_keys: continue
            
            mapped_key = key_mapping.get(clean_key.lower(), clean_key)
            if mapped_key.lower() in ["course name"]:
                 properties[mapped_key] = {"title": [{"text": {"content": clean_value}}]}
            elif mapped_key.lower() in ["semester", "type", "status", "category"]:
                properties[mapped_key] = {"select": {"name": clean_value}}
            else:
                 properties[mapped_key] = {"rich_text": [{"text": {"content": clean_value}}]}
        return properties

    def _generate_course_sessions(self, created_courses: List[Dict[str, Any]], sessions_db_id: str, notes_db_id: Optional[str] = None) -> int:
        if not sessions_db_id: return 0
        total = 0
        
        # 確保導入必要的工具
        from itertools import groupby
        
        for course in created_courses:
            course_name = course.get('name')
            course_id = course.get('id')
            row_data = course.get('row_data', {})
            
            # 保留原本穩定的 Key 值讀取邏輯
            year_str = row_data.get('Year', row_data.get('学年', '114'))
            sem_str = row_data.get('Semester', row_data.get('学期', '1'))
            if '-' in sem_str: year_str, sem_str = sem_str.split('-')
            
            schedule_str = row_data.get('Schedule', row_data.get('上课时间', ''))
            
            if not year_str or not sem_str or not schedule_str:
                logger.warning(f"課程 {course_name} 缺少必要時間資訊，跳過生成。")
                continue
            
            try:
                year, sem = int(year_str), int(sem_str)
                semester_info = get_semester_info(year, sem)
                parsed_schedule = CourseScheduleParser.parse_schedule(schedule_str)
                
                if semester_info and parsed_schedule:
                    class_dates = CourseScheduleParser.get_class_dates(parsed_schedule, year, sem)
                    class_dates.sort(key=lambda x: (x['date'], x['start_time'] or datetime.min.time()))
                    
                    start_date = class_dates[0]['date'] if class_dates else datetime.today()
                    
                    for date_key, group in groupby(class_dates, key=lambda x: x['date']):
                        delta_days = (date_key.date() - start_date.date()).days if hasattr(date_key, 'date') else (date_key - start_date).days
                        current_week = (delta_days // 7) + 1
                        if current_week > 18: continue
                        
                        date_prop = {"start": date_key.strftime("%Y-%m-%d")}
                        
                        # 1. 建立 Class Session
                        session_properties = {
                            "Class Session": {"title": [{"text": {"content": f"{course_name} - Week {current_week}"}}]},
                            "Date & Reminder": {"date": date_prop},
                            "Related to Course Hub": {"relation": [{"id": course_id}]},
                            "Week": {"number": current_week}
                        }
                        
                        session_page = self.client.create_page_in_database(sessions_db_id, session_properties)
                        
                        if session_page and notes_db_id:
                            total += 1
                            session_id = session_page.get('id')
                            
                            # 2. 建立 Lecture Note (包含新屬性)
                            note_properties = {
                                "Note": {"title": [{"text": {"content": f"Lecture Note - {course_name} W{current_week}"}}]},
                                "Class Date": {"date": date_prop},
                                "Favourite": {"checkbox": False},              # 初始化為未收藏
                                "Last reviewed": {"date": None},               # 初始化為空
                                # Last edited time 是系統屬性，Notion 會自動生成，不需寫入
                                "Related to Course Session": {"relation": [{"id": session_id}]},
                                "Related to Course Hub": {"relation": [{"id": course_id}]}
                            }
                            self.client.create_page_in_database(notes_db_id, note_properties)
                            
            except Exception as e:
                logger.error(f"為 {course_name} 生成會話失敗: {e}")
                
        return total

    def generate_onboarding_page(self, parent_page_id: Optional[str] = None) -> bool:
        parent_page_id = parent_page_id or notion_config.parent_page_id
        if not parent_page_id: return False
        
        guide_blocks = [
            {"object": "block", "type": "callout", "callout": {"rich_text": [{"type": "text", "text": {"content": "歡迎使用！原始資料庫存放於 [System] Archive。Dashboard 內容皆為動態視圖。"}}]}},
            {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🧠 筆記模板選用指南"}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "1. Cornell (康乃爾筆記法) —— 適合期末考前大量複習的理論課"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "特色：強迫將記錄與提取分開。右側記錄，左側寫提示問題，底部總結。"}}]}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "2. QEC (提問-證據-結論) —— 適合實驗分析與文獻選讀"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "特色：培養批判性思考。列出 Question, Evidence, Conclusion。"}}]}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "3. Feynman (費曼學習法) —— 適合極度抽象難懂的硬核知識"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "特色：用教導驗證理解。用白話文解釋，卡住的地方就是知識漏洞。"}}]}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "4. Outline (階層大綱式) —— 適合資訊量大、節奏極快的課"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "特色：排版最快，迅速捕捉資訊骨架。"}}]}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "5. Lecture (標準課堂型) —— 適合一般通識或專題討論"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "特色：以行動為導向。記錄評分標準、繳交期限與 Action Items。"}}]}}]}}
        ]
        
        try:
            page_data = self.client.create_page(parent_id=parent_page_id, page_title="📖 Project-Synapse 系統使用指南")
            if page_data:
                self.client.append_block_children(page_data.get("id"), guide_blocks)
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def generate_csv_sample(database_type: str) -> str:
        """新增：生成符合 v3.0 架構的供使用者下載的 CSV 樣本"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        if database_type == 'courses':
            writer.writerow(['Course Name', 'Course Code', 'Professor', 'Semester', 'Type', 'Schedule'])
            writer.writerow(['發展心理學', 'PSY1001', '王教授', '114-1', '必修', '一2/一3/一4'])
            writer.writerow(['認知神經科學', 'PSY2002', '李教授', '114-1', '選修', '三6/三7/三8'])
            writer.writerow(['Python程式設計', 'CSIE1001', '張教授', '114-1', '通識', '五2/五3/五4'])
        elif database_type == 'tasks':
            writer.writerow(['Task', 'Status', 'Deadline'])
            writer.writerow(['閱讀心理學 CH1', 'Not started', '2026-03-10'])
            writer.writerow(['Python 作業一', 'In progress', '2026-03-15'])
        else:
            writer.writerow(['Name', 'Description'])
            writer.writerow(['Sample Item', 'This is a sample format'])
            
        return output.getvalue()

# 向後相容函式
def execute_test_connection(api_key: str) -> bool: return NotionProcessor(api_key).test_connection()
def execute_build_dashboard_layout(api_key: str, parent_page_id: str) -> bool: return NotionProcessor(api_key).build_dashboard_layout(parent_page_id)
def execute_delete_blocks(api_key: str, parent_page_id: str) -> bool: return NotionProcessor(api_key).delete_blocks(parent_page_id)
def execute_create_database(api_key: str, parent_page_id: str) -> bool: return NotionProcessor(api_key).create_databases(parent_page_id)