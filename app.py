from flask import Flask, render_template
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    # 模擬資料 (之後會改為從 Notion API 抓取)
    student_tasks = [
        {"task": "人工智慧概論期末報告", "status": "進行中", "deadline": "2025-01-10"},
        {"task": "DocuGenius v2.0 開發", "status": "待辦", "deadline": "2025-01-15"}
    ]
    
    return render_template('index.html', tasks=student_tasks)

@app.route('/teacher/sync')
def sync_classroom():
    # 預留給 Google Classroom 的功能接口
    return "正在連結 Google Classroom API... (功能開發中)"

if __name__ == '__main__':
    # host='0.0.0.0' 是 Docker 運行的關鍵
    app.run(host='0.0.0.0', port=5000, debug=True)