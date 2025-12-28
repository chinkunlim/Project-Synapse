
import sys
import os
import logging
from unittest.mock import MagicMock
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

# Mock logging to capture output
sys.modules['intergrations.notion.logging'] = MagicMock()
# Create a real logger to see output in console
real_logger = logging.getLogger("intergrations.notion.processor")
real_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(message)s'))
real_logger.addHandler(handler)

sys.modules['intergrations.notion.logging'].get_logger.return_value = real_logger

# Mock client
sys.modules['intergrations.notion.client'] = MagicMock()

from intergrations.notion.processor import NotionProcessor

def test_user_csv_import():
    print("🚀 Starting User CSV Verification...")
    
    # 1. Create Test CSV
    csv_content = """Name,Semester,Schedule,Code,Instructor,Credits,Type,Location,Remarks,,,
諮商理論與技術,114-1,"三9,三10,三11",CP__20500,余振民,3,核心學程,,法律社會、犯罪防治與觀護 / 諮商與臨床心理學核心,,,
人格心理學,114-1,"二9,二10,二11",CP__20700,林繼偉,3,核心學程,,諮商與臨床心理學核心學程,,,
中文能力與涵養AC,113-2,"一4,一5,一6",CLC_6232AC,謝明陽,3,中文必修,,中文必修,,,
認識宇宙AB,113-1,"一9,一10",GC__6347AB,葉振斌 等,2,通識(理性),,理性思維,,,
"""
    csv_path = "user_test_data.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    print(f"📄 Created test CSV at {csv_path}")

    # 2. Setup Processor with Mock Client
    processor = NotionProcessor(api_key="fake_key")
    processor.client = MagicMock()

    # Mock Create Page to print what it would do
    def mock_create_page(database_id=None, properties=None):
        if not database_id:
             # Fallback if somehow called differently (e.g. only keyword args but python binds them?)
             return {"id": "unknown"}
        
        db_id = database_id
        # properties is already bound
        
        if db_id == "COURSE_DB":
            name = properties['Name']['title'][0]['text']['content']
            print(f"✅ [MOCK] Creating COURSE: {name}")
            return {"id": f"course_{name}"}
            
        elif db_id == "SESSION_DB":
            name = properties['Name']['title'][0]['text']['content']
            date = properties['Date']['date']['start']
            print(f"   📅 [MOCK] Creating SESSION: {name} | Date: {date}")
            return {"id": f"session_{name}"}
            
        elif db_id == "NOTE_DB":
            title = properties['Note Title']['title'][0]['text']['content']
            sem = properties['Semester']['select']['name']
            week = properties['Week']['number']
            print(f"      📝 [MOCK] Creating NOTE: {title} | Sem: {sem} | Week: {week}")
            return {"id": "note_123"}
            
        return {"id": "unknown"}

    processor.client.create_page_in_database.side_effect = mock_create_page
    processor.client.query_database.return_value = [] # Assume no existing courses

    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 3. Run Import
    print("\n🔄 Running Import Process...")
    processor.import_csv_to_database(
        csv_content=content,
        database_id="COURSE_DB",
        extra_params={
            "course_sessions_db_id": "SESSION_DB",
            "notes_db_id": "NOTE_DB"
        }
    )

    # Cleanup
    os.remove(csv_path)
    print("\n✨ Verification Complete.")

if __name__ == "__main__":
    test_user_csv_import()
