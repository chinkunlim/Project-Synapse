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
            db_ids = self._create_databases_logic(parent_page_id, db_schemas)
            return bool(db_ids)
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
            {"object": "block", "type": "callout", "callout": {"rich_text": [{"type": "text", "text": {"content": "歡迎使用 Project-Synapse！本系統包含七大核心資料庫，透過雙向關聯自動串接所有學習資訊。Dashboard 內容皆為動態視圖，原始資料庫存放於 [System] Archive。"}}], "color": "blue_background"}},
            {"object": "block", "type": "divider", "divider": {}},
            {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🗄️ 資料庫功能說明 (Databases)"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Course Hub (課程大廳)"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：總管所有註冊班級、學分、教授資訊與學期成績。"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Class Sessions (課程會話)"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：記錄每一堂（每週）課的具體進度與出席狀況。"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Lecture Notes (筆記庫)"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：存放所有課堂筆記，並支援套用多種筆記模板。"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Theory Hub (理論庫)"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：歸納與整理跨課程的核心理論、公式與硬核知識點。"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Projects (專案庫)"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：追蹤與管理大型期末報告、專題研究及長期目標。"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Resources (資源庫)"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：統一存放參考書目、講義檔案、網路教材與文獻連結。"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Tasks (任務庫)"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：統籌所有的作業、考試及個人待辦事項 (Action Items)。"}}]}},
            {"object": "block", "type": "divider", "divider": {}},
            {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🔗 資料庫關聯指南 (Relationships)"}}]}},
            {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "系統的核心在於自動化跨資料庫關聯，您在建立資料時可以遵循以下邏輯："}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "以「課程」為中心"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：所有的筆記、任務、專案、資源都可以（也應該）關聯回到特定的 "}}, {"type": "text", "text": {"content": "Course Hub"}, "annotations": {"code": True}}, {"type": "text", "text": {"content": "，這樣進入特定課程頁面時就能一次看見所有相關內容。"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "當堂筆記與作業"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：在 "}}, {"type": "text", "text": {"content": "Class Sessions"}, "annotations": {"code": True}}, {"type": "text", "text": {"content": " 內可同步建立當天的 "}}, {"type": "text", "text": {"content": "Lecture Notes"}, "annotations": {"code": True}}, {"type": "text", "text": {"content": " 和延伸出來的 "}}, {"type": "text", "text": {"content": "Tasks"}, "annotations": {"code": True}}, {"type": "text", "text": {"content": "。"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "理論與資源支撐"}, "annotations": {"bold": True}}, {"type": "text", "text": {"content": "：遇到難懂的概念，可獨立寫入 "}}, {"type": "text", "text": {"content": "Theory Hub"}, "annotations": {"code": True}}, {"type": "text", "text": {"content": "，並在筆記庫中 @ 關聯它；參考資料則存入 "}}, {"type": "text", "text": {"content": "Resources"}, "annotations": {"code": True}}, {"type": "text", "text": {"content": " 供專案與任務提取。"}}]}},
            {"object": "block", "type": "divider", "divider": {}},
            {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🧠 筆記模板選用指南 (Note Templates)"}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "1. Cornell (康乃爾筆記法) —— 適合期末考前大量複習的理論課"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "特色：強迫將記錄與提取分開。右側記錄，左側寫提示問題，底部總結。"}}]}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "2. QEC (提問-證據-結論) —— 適合實驗分析與文獻選讀"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "特色：培養批判性思考。列出 Question, Evidence, Conclusion。"}}]}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "3. Feynman (費曼學習法) —— 適合極度抽象難懂的硬核知識"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "特色：用教導驗證理解。用白話文解釋，卡住的地方就是知識漏洞。"}}]}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "4. Outline (階層大綱式) —— 適合資訊量大、節奏極快的課"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "特色：排版最快，迅速捕捉資訊骨架。"}}]}}]}},
            {"object": "block", "type": "toggle", "toggle": {"rich_text": [{"type": "text", "text": {"content": "5. Lecture (標準課堂型) —— 適合一般通識或專題討論"}}], "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "特色：以行動為導向。記錄評分標準、繳交期限與 Action Items。"}}]}}]}}
        ]
        
        try:
            page_data = self.client.create_page(parent_id=parent_page_id, page_title="📖 Project-Synapse 系統使用指南")
            if page_data:
                self.client.append_block_children(page_data.get("id"), guide_blocks)
                return True
            return False
        except Exception:
            return False

    
    def generate_csv_sample(self, database_id: str) -> str:
        """
        動態獲取 Notion 資料庫最新結構並生成 CSV 範本文字
        """
        if not database_id:
            return "Error: 無法生成範本，因為資料庫 ID 為空。請先初始化系統。"

        db_info = self.client.retrieve_database(database_id)
        if not db_info:
            return "Error: 無法讀取 Notion 資料庫結構。請確認 API Key 是否正確且已邀請機器人加入該頁面。"

        properties = db_info.get("properties", {})
        
        # 提取所有欄位名稱，並確保 'title' 類型的欄位排在第一位
        headers = []
        for name, prop in properties.items():
            if prop.get("type") == "title":
                headers.insert(0, name)
            else:
                headers.append(name)

        # 使用 CSV 模組生成字串內容
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers) # 寫入表頭 (與 Notion 欄位名稱完全一致)
        
        # 寫入一行範例資料
        sample_row = []
        for h in headers:
            p_type = properties[h].get("type")
            if p_type == "title": sample_row.append("範例標題")
            elif p_type == "date": sample_row.append(datetime.now().strftime("%Y-%m-%d"))
            elif p_type == "select": sample_row.append("選項一")
            elif p_type == "checkbox": sample_row.append("false")
            else: sample_row.append("範例內容")
        
        writer.writerow(sample_row)
        return output.getvalue()

    def _convert_block_to_payload(self, block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """轉換 Block 為佈局格式，增加對子頁面、圖示與巢狀子區塊的支援"""
        b_type = block.get('type')
        if not b_type or b_type in ('child_database', 'child_page', 'unsupported'): return None
        
        content = block.get(b_type, {})
        payload = {"object": "block", "type": b_type, b_type: {}}

        # 處理子頁面
        if b_type == 'child_page':
            payload[b_type] = {"title": content.get("title", "未命名頁面")}
        
        # 處理通用文字屬性
        if "rich_text" in content:
            payload[b_type]["rich_text"] = content.get("rich_text", [])
        if "color" in content:
            payload[b_type]["color"] = content.get("color")
            
        # 處理特定區塊的特別屬性
        if b_type == 'callout' and "icon" in content:
            payload[b_type]["icon"] = content["icon"]
        if b_type == 'to_do' and "checked" in content:
            payload[b_type]["checked"] = content["checked"]
            
        # 處理其他常見屬性
        for attr in ["url", "expression", "caption", "type"]:
            if attr in content:
                payload[b_type][attr] = content[attr]

        # 資源類型的處理 (image, video, file, pdf)
        if b_type in ['image', 'video', 'file', 'pdf']:
            if 'external' in content:
                payload[b_type]['external'] = content['external']
            elif 'file' in content:
                # Notion API 限制無法直接複製託管的 file，此處先保留原始 URL，後續建立時未必成功
                payload[b_type]['external'] = {"url": content['file'].get('url')}

        # 遞迴處理子區塊 (支援 toggle, column_list, column 等巢狀結構)
        if block.get("has_children"):
            block_id = block.get("id")
            if block_id:
                # 這裡調用 client 去抓取子層級
                child_blocks = self.client.get_block_children(block_id)
                if child_blocks:
                    children_payload = []
                    for cb in child_blocks:
                        converted = self._convert_block_to_payload(cb)
                        if converted:
                            children_payload.append(converted)
                    if children_payload:
                        payload[b_type]["children"] = children_payload
                        
        return payload

    def sync_notion_to_local_schema(self) -> bool:
        """同步資料庫結構 + 首頁佈局 (含拖入的子頁面)"""
        try:
            parent_id = notion_config.parent_page_id
            schema_path = notion_config.schema_path
            latest_path = schema_path.parent / "notion_schema_latest.json"
            
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)

            # 同步資料庫 (修正 v3.0 的 Key 映射)
            key_map = {
                "SUBJECT_DATABASE_ID": "COURSE_HUB_ID", 
                "COURSE_DATABASE_ID": "CLASS_SESSION_ID", 
                "NOTE_DB_ID": "NOTE_DATABASE_ID", 
                "THEORY_DB_ID": "THEORY_HUB_ID",
                "PROJECTS_DATABASE_ID": "PROJECT_DATABASE_ID", # 補上
                "RESOURCES_DATABASE_ID": "RESOURCE_DATABASE_ID", # 補上
                "TASK_DB_ID": "TASK_DATABASE_ID" # 補上
            }
            
            for db in schema.get("databases", []):
                actual_key = key_map.get(db.get("env_key"), db.get("env_key"))
                db_id = notion_config.get_env(actual_key)
                if db_id:
                    info = self.client.retrieve_database(db_id)
                    if info: 
                        new_props = {}
                        for n, v in info.get("properties", {}).items():
                            p_type = v.get("type")
                            # If the original schema had relation_placeholder, preserve it for rebuilding
                            orig_prop = db.get("properties", {}).get(n, {})
                            if "relation_placeholder" in orig_prop:
                                new_props[n] = {"relation_placeholder": orig_prop["relation_placeholder"]}
                            else:
                                new_props[n] = {p_type: {}}
                        db["properties"] = new_props

            # 同步首頁佈局 (Layout) - 包含您拖入的頁面與新區塊
            blocks = self.client.get_block_children(parent_id)
            if blocks:
                schema["layout"] = [self._convert_block_to_payload(b) for b in blocks if self._convert_block_to_payload(b)]

            with open(latest_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"同步失敗: {e}"); return False

    def initialize_system(self, parent_page_id: str, use_latest: bool = False) -> Dict[str, Any]:
        """核心修復：根據選擇的版本初始化系統"""
        logs = []
        try:
            # 1. 確定 Schema 來源
            schema_file = "notion_schema_latest.json" if use_latest else "notion_schema.json"
            schema_path = notion_config.schema_path.parent / schema_file
            
            if use_latest and not schema_path.exists():
                logs.append("⚠️ 找不到最新同步版，自動退回使用初始版設定")
                schema_path = notion_config.schema_path
            
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_data = json.load(f)
            
            # 2. 徹底清空父頁面 (確保權限正確)
            logs.append(f"🗑️ 正在清空頁面並準備使用「{schema_file}」...")
            if not self.client.delete_blocks(parent_page_id):
                return {"success": False, "message": "無法清空頁面，請檢查 PARENT_PAGE_ID 或機器人權限", "logs": logs}

            # 3. 建立資料庫 (使用傳入的 schema 資料)
            db_ids = self._create_databases_logic(parent_page_id, schema_data.get("databases", []))
            if not db_ids:
                return {"success": False, "message": "資料庫建立失敗", "logs": logs}
            logs.append(f"✅ 成功建立 {len(db_ids)} 個資料庫並更新環境變數")

            # 4. 構建佈局 (Layout) - 這是讓頁面「有反應」的關鍵
            layout_payload = schema_data.get("layout", [])
            if layout_payload:
                self.client.append_block_children(parent_page_id, layout_payload)
                logs.append(f"✅ 佈局構建完成 (共 {len(layout_payload)} 個區塊)")

            # 5. 生成指南
            self.generate_onboarding_page(parent_page_id)
            logs.append("✅ 系統指南已生成")

            return {"success": True, "message": "系統初始化完全成功", "logs": logs}
        except Exception as e:
            logger.error(f"初始化崩潰: {e}")
            return {"success": False, "message": str(e), "logs": logs}

    def _create_databases_logic(self, parent_id: str, db_configs: List[Dict]) -> Dict[str, str]:
        """私有方法：執行資料庫建立與雙向關聯設置"""
        created_dbs = {}
        
        # 建立 Archive 容器子頁面
        logger.info("📁 正在建立 Database 存放資料庫...")
        archive_page = self.client.create_page(parent_id, "Database")
        archive_id = archive_page.get("id") if archive_page else parent_id
        
        # 步驟 A: 建立基礎資料庫
        for db_cfg in db_configs:
            db_name = db_cfg.get("db_name")
            props = {k: v for k, v in db_cfg.get("properties", {}).items() if "relation_placeholder" not in v and "relation" not in v}
            res = self.client.create_database(archive_id, db_cfg.get("title", db_name), props)
            if res:
                new_id = res.get("id")
                created_dbs[db_name] = new_id
                # 更新環境變數 (需對應 v3.0 的 Key)
                env_key = db_cfg.get("env_key")
                # 補全 6 個核心資料庫的映射
                key_map = {
                    "SUBJECT_DATABASE_ID": "COURSE_HUB_ID",
                    "COURSE_DATABASE_ID": "CLASS_SESSION_ID",
                    "NOTE_DB_ID": "NOTE_DATABASE_ID",
                    "THEORY_DB_ID": "THEORY_HUB_ID",
                    "PROJECTS_DATABASE_ID": "PROJECT_DATABASE_ID",
                    "RESOURCES_DATABASE_ID": "RESOURCE_DATABASE_ID",
                    "TASK_DB_ID": "TASK_DATABASE_ID"  # 確保包含 Task
                }
                actual_key = key_map.get(env_key, env_key)
                if actual_key: notion_config.set_env(actual_key, new_id)
        
        # 步驟 B: 建立關聯
        for db_cfg in db_configs:
            db_id = created_dbs.get(db_cfg.get("db_name"))
            rel_props = {}
            for p_n, p_d in db_cfg.get("properties", {}).items():
                if "relation_placeholder" in p_d:
                    target_id = created_dbs.get(p_d["relation_placeholder"].get("db_name"))
                    if target_id:
                        rel_props[p_n] = {"relation": {"database_id": target_id, "type": "dual_property", "dual_property": {}}}
            if rel_props:
                self.client._send_request("PATCH", f"databases/{db_id}", {"properties": rel_props})
        return created_dbs
    
    def find_database_by_title(self, title: str) -> Optional[str]:
        """
        透過標題搜尋資料庫，先嘗試從PARENT_PAGE_ID的所有子頁面中尋找，
        找不到才降格到 Notion 搜尋 API（search）。
        這樣可以確保即使資料庫位於巢狀子頁面中也能被找到。
        """
        import os
        parent_page_id = os.getenv('PARENT_PAGE_ID', '')
        
        # 1. 先嘗試直接遍歷父頁面子孫
        if parent_page_id:
            db_id = self._find_db_in_children(parent_page_id, title, depth=2)
            if db_id:
                return db_id

        # 2. 降格到全域搜尋 API
        results = self.client.search(query=title, filter_type="database")
        if results:
            for db in results:
                notion_title = "".join([t.get('plain_text', '') for t in db.get('title', [])])
                if notion_title == title:
                    return db.get('id')
        return None

    def _find_db_in_children(self, page_id: str, title: str, depth: int = 1) -> Optional[str]:
        """
        遞迴地在指定頁面的子區塊中尋找特定標題的資料庫。
        depth 控制遞迴深度。
        """
        children = self.client.get_block_children(page_id)
        if not children:
            return None

        sub_pages = []
        for block in children:
            btype = block.get('type')
            bid = block.get('id')

            if btype == 'child_database':
                db_title = block.get('child_database', {}).get('title', '')
                if db_title == title:
                    return bid

            elif btype == 'child_page' and depth > 0:
                sub_pages.append(bid)

        # 遞迴搜尋子頁面
        for sub_id in sub_pages:
            result = self._find_db_in_children(sub_id, title, depth=depth - 1)
            if result:
                return result

        return None

# 向後相容函式
def execute_test_connection(api_key: str) -> bool: return NotionProcessor(api_key).test_connection()
def execute_build_dashboard_layout(api_key: str, parent_page_id: str) -> bool: return NotionProcessor(api_key).build_dashboard_layout(parent_page_id)
def execute_delete_blocks(api_key: str, parent_page_id: str) -> bool: return NotionProcessor(api_key).delete_blocks(parent_page_id)
def execute_create_database(api_key: str, parent_page_id: str) -> bool: return NotionProcessor(api_key).create_databases(parent_page_id)