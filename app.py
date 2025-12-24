from flask import Flask, render_template, request
import os
import requests
from dotenv import load_dotenv
from notion_client import Client

# 1. 載入環境變數
load_dotenv()

app = Flask(__name__)

# 2. 初始化 Notion (若失敗不影響 App 啟動)
try:
    notion = Client(auth=os.getenv("NOTION_API_KEY"))
    database_id = os.getenv("NOTION_DATABASE_ID")
except Exception:
    notion = None
    database_id = None

def fetch_tasks_from_notion():
    """從 Notion 讀取任務"""
    tasks = []
    if not notion or not database_id:
        return []
    try:
        response = notion.databases.query(
            database_id=database_id,
            filter={"property": "Status", "status": {"does_not_equal": "Done"}},
            sorts=[{"property": "Date", "direction": "ascending"}]
        )
        for page in response["results"]:
            props = page["properties"]
            title_list = props.get("Name", {}).get("title", [])
            task_name = title_list[0]["plain_text"] if title_list else "無標題"
            date_prop = props.get("Date", {}).get("date", {})
            raw_date = date_prop.get("start", "無日期") if date_prop else "無日期"
            status_prop = props.get("Status", {}).get("status", {})
            status = status_prop.get("name", "Unknown") if status_prop else "Unknown"
            tasks.append({"task": task_name, "deadline": raw_date, "status": status})
        return tasks
    except Exception as e:
        print(f"Notion Error: {e}")
        return []

# === 路由定義 ===

@app.route('/')
def index():
    real_tasks = fetch_tasks_from_notion()
    return render_template('index.html', tasks=real_tasks)

@app.route('/trigger-n8n', methods=['POST'])
def trigger_n8n():
    try:
        n8n_url = "http://n8n:5678/webhook-test/sync-classroom"
        response = requests.post(n8n_url, json={"source": "Dashboard", "action": "sync_grades"})
        return "✅ 指令已發送！" if response.status_code == 200 else f"⚠️ N8N 錯誤: {response.status_code}"
    except Exception as e:
        return f"❌ 連線失敗: {e}"

@app.route('/student/submit', methods=['POST'])
def submit_homework():
    try:
        n8n_url = "http://n8n:5678/webhook-test/submit-homework"
        uploaded_file = request.files.get('homework_file')
        if not uploaded_file: return "❌ 未選擇檔案"
        
        files = {'file': (uploaded_file.filename, uploaded_file.stream, uploaded_file.content_type)}
        data = {
            'student': request.form.get('student_name'),
            'task': request.form.get('task_name'),
            'source': 'Student Dashboard'
        }
        response = requests.post(n8n_url, files=files, data=data)
        return "✅ 作業繳交成功！" if response.status_code == 200 else f"⚠️ 繳交失敗: {response.status_code}"
    except Exception as e:
        return f"❌ 系統錯誤: {e}"

# --- 論文工廠相關路由 ---

@app.route('/thesis')
def thesis_page():
    return render_template('thesis.html')

@app.route('/thesis/convert', methods=['POST'])
def thesis_convert():
    try:
        # Docker 內部網路 Worker 位址
        worker_url = "http://pdf-worker:5002/convert"
        
        # (A) 轉發文字欄位
        data = request.form.to_dict()
        
        # (B) 轉發檔案 (Markdown + Bib + Figures)
        files = []
        
        # 1. Markdown (必填檢查)
        md = request.files.get('md_file')
        if md and md.filename: 
            files.append(('md_file', (md.filename, md.stream, md.content_type)))
        else:
            return "❌ 錯誤：未上傳 Markdown 內文檔案 (md_file)", 400
            
        # 2. BibTeX (強制必填檢查)
        bib = request.files.get('bib_file')
        if bib and bib.filename:
            files.append(('bib_file', (bib.filename, bib.stream, bib.content_type)))
        else:
            # 若無上傳，直接擋下，確保文獻來源正確
            return "❌ 錯誤：請務必上傳參考文獻 (.bib) 檔案", 400
        
        # 3. Figures (選填)
        figs = request.files.getlist('figures')
        for fig in figs:
            if fig.filename:
                files.append(('figures', (fig.filename, fig.stream, fig.content_type)))

        print("🔄 正在呼叫 PDF 工廠...")
        # 設定 stream=True 以便直接轉發，避免記憶體問題
        response = requests.post(worker_url, data=data, files=files, stream=True)
        
        if response.status_code == 200:
            return (response.content, 200, {
                'Content-Type': 'application/pdf',
                'Content-Disposition': 'attachment; filename=thesis_output.pdf'
            })
        else:
            return f"❌ 編譯失敗 (Worker): {response.text}", 500

    except Exception as e:
        return f"❌ 連線錯誤: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)