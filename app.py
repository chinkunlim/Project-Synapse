from flask import Flask, render_template
import os
from dotenv import load_dotenv
from notion_client import Client
from datetime import datetime

# 1. 載入 .env 裡的設定
load_dotenv()


app = Flask(__name__)

# 2. 初始化 Notion 客戶端
# 這裡會自動讀取我們剛剛填入的環境變數
try:
    notion = Client(auth=os.getenv("NOTION_API_KEY"))
    database_id = os.getenv("NOTION_DATABASE_ID")
except Exception as e:
    print(f"Notion 初始化失敗: {e}")

def fetch_tasks_from_notion():
    """
    從 Notion Master DB 抓取未完成的任務
    """
    tasks = []
    
    # 如果沒有設定 Key，直接回傳假資料避免報錯
    if not os.getenv("NOTION_API_KEY"):
        return [{"task": "尚未設定 Notion API Key", "status": "Error", "deadline": "---"}]

    try:
        # 呼叫 Notion API 查詢資料庫
        response = notion.databases.query(
            database_id=database_id,
            # 篩選條件：狀態不是「Done」
            # 請確認您的 Notion 完成狀態叫 "Done" 還是 "Completed"
            filter={
                "property": "Status",
                "status": {
                    "does_not_equal": "Done"
                }
            },
            # 排序：依照 Deadline 日期，越早的排越前面
            sorts=[
                {
                    "property": "Deadline",
                    "direction": "ascending"
                }
            ]
        )
        
        # 解析回傳的 JSON 資料
        for page in response["results"]:
            props = page["properties"]
            
            # --- 解析欄位 (請確認 Notion 欄位名稱是否一致) ---
            
            # 1. 任務名稱 (Title) -> 欄位名: Name
            title_list = props.get("Name", {}).get("title", [])
            task_name = title_list[0]["plain_text"] if title_list else "無標題"
            
            # 2. 截止日期 (Date) -> 欄位名: Deadline
            date_prop = props.get("Deadline", {}).get("date", {})
            raw_date = date_prop.get("start", None) if date_prop else None
            
            # 3. 狀態 (Status) -> 欄位名: Status
            status_prop = props.get("Status", {}).get("status", {})
            status = status_prop.get("name", "Unknown") if status_prop else "Unknown"
            
            # 簡單處理日期格式
            deadline_display = raw_date if raw_date else "無日期"

            tasks.append({
                "task": task_name,
                "deadline": deadline_display,
                "status": status
            })
            
        return tasks

    except Exception as e:
        print(f"讀取 Notion 發生錯誤: {e}")
        return [{"task": f"讀取錯誤: {str(e)}", "deadline": "Check Logs", "status": "Error"}]

@app.route('/')
def index():
    # 呼叫上面的函數，抓取真實資料
    real_tasks = fetch_tasks_from_notion()
    
    return render_template('index.html', tasks=real_tasks)

@app.route('/teacher/sync')
def sync_classroom():
    return "正在連結 Google Classroom API... (功能開發中)"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)