from flask import Blueprint, render_template, request, jsonify, current_app
import requests
import os
import markdown
import glob
import extensions

main_bp = Blueprint('main', __name__)

def fetch_tasks_from_notion():
    """從 Notion 讀取任務"""
    tasks = []
    if not extensions.notion or not extensions.database_id:
        return []
    try:
        response = extensions.notion.databases.query(
            database_id=extensions.database_id,
            filter={"property": "Status", "status": {"does_not_equal": "Done"}}
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

@main_bp.route('/')
def index():
    """
    Render main dashboard.
    
    Fetches tasks from Notion and Google Tasks (NDHU) to display on the dashboard.
    Also fetches Google Keep notes if available.
    
    Returns:
        Rendered HTML template 'index.html' with tasks data.
    """
    real_tasks = fetch_tasks_from_notion()
    
    # 嘗試取得 NDHU 任務
    ndhu_tasks = []
    
    if extensions.ndhu_integration:
        try:
            ndhu_tasks = extensions.ndhu_integration.get_all_tasks()
        except Exception as e:
            print(f"NDHU 任務讀取失敗: {e}")
    
    return render_template('index.html', tasks=real_tasks, ndhu_tasks=ndhu_tasks)

@main_bp.route('/trigger-n8n', methods=['POST'])
def trigger_n8n():
    """
    Trigger N8N workflow for Classroom sync.
    
    Sends a webhook to the local N8N instance to start the grade sync process.
    
    Returns:
        str: Success or error message.
    """
    try:
        n8n_url = "http://n8n:5678/webhook-test/sync-classroom"
        response = requests.post(n8n_url, json={"source": "Dashboard", "action": "sync_grades"})
        return "✅ 指令已發送！" if response.status_code == 200 else f"⚠️ N8N 錯誤: {response.status_code}"
    except Exception as e:
        return f"❌ 連線失敗: {e}"

@main_bp.route('/student/submit', methods=['POST'])
def submit_homework():
    """
    Handle student homework submission.
    
    Receives a file upload and metadata, then forwards it to an N8N webhook.
    
    Returns:
        str: Success or error message.
    """
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

@main_bp.route('/api/status')
def check_status():
    """
    Check connection status for Notion, Google Tasks, N8N, and Google Classroom.
    """
    status = {
        "notion": {"connected": False, "msg": "Not initialized"},
        "google_tasks": {"connected": False, "msg": "Not initialized"},
        "n8n": {"connected": False, "msg": "Not initialized"},
        "classroom": {"connected": False, "msg": "Not initialized"}
    }
    
    # Check Notion
    if extensions.notion:
        try:
            extensions.notion.users.me()
            status["notion"] = {"connected": True, "msg": "Connected"}
        except Exception as e:
            status["notion"] = {"connected": False, "msg": str(e)}
            
    # Check Google Tasks
    if extensions.ndhu_integration and extensions.ndhu_integration.tasks_service:
        try:
            # Lightweight check: list tasklists (limit 1)
            extensions.ndhu_integration.tasks_service.tasklists().list(maxResults=1).execute()
            status["google_tasks"] = {"connected": True, "msg": "Connected"}
        except Exception as e:
            status["google_tasks"] = {"connected": False, "msg": str(e)}

    # Check N8N
    try:
        # Pinging local N8N container/service
        # Try service name first (Docker), then localhost (Local Dev)
        try:
            resp = requests.get("http://n8n:5678/", timeout=2)
        except:
             resp = requests.get("http://localhost:5678/", timeout=2)
             
        # 200 is OK, 401/403 means it's there but maybe auth required (still connected)
        # We assume if we get a response, it's alive.
        status["n8n"] = {"connected": True, "msg": f"Connected (Status {resp.status_code})"}
    except Exception as e:
        status["n8n"] = {"connected": False, "msg": f"Unreachable: {str(e)}"}

    # Check Google Classroom
    if extensions.classroom_integration and extensions.classroom_integration.classroom_service:
        try:
            # Check by listing 1 course
            extensions.classroom_integration.classroom_service.courses().list(pageSize=1).execute()
            status["classroom"] = {"connected": True, "msg": "Connected"}
        except Exception as e:
             status["classroom"] = {"connected": False, "msg": str(e)}
    
    return jsonify(status)

# --- Documentation Viewer Route ---

@main_bp.route('/docs')
def docs_viewer():
    """Documentation Viewer"""
    
    docs_dir = os.path.join(current_app.root_path, 'docs')
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        
    doc_files = []
    
    # Get all MD and TXT files in docs directory
    for ext in ['*.md', '*.txt']:
        for filepath in glob.glob(os.path.join(docs_dir, ext)):
            filename = os.path.basename(filepath)
            title = filename.replace('_', ' ').replace('-', ' ').replace('.md', '').replace('.txt', '').title()
            doc_files.append({
                'filename': filename,
                'title': title
            })
            
    doc_files.sort(key=lambda x: x['title'])
    
    current_file = request.args.get('file')
    content = ""
    
    if not current_file and doc_files:
        current_file = doc_files[0]['filename']
        
    if current_file:
        # Security check: ensure filename doesn't have path traversal
        if any(d['filename'] == current_file for d in doc_files):
            try:
                full_path = os.path.join(docs_dir, current_file)
                with open(full_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    content = markdown.markdown(
                        text, 
                        extensions=['fenced_code', 'tables', 'toc']
                    )
            except Exception as e:
                content = f"Error reading file: {str(e)}"
        else:
            content = "File not found or access denied."
            
    return render_template('docs.html', docs=doc_files, current_file=current_file, content=content)
