from flask import Blueprint, render_template, request
import requests

thesis_bp = Blueprint('thesis', __name__)

@thesis_bp.route('/thesis')
def thesis_page():
    return render_template('thesis.html')

@thesis_bp.route('/thesis/convert', methods=['POST'])
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
            return "❌ 錯誤：請務必上傳參考文獻 (.bib) 檔案", 400
        
        # 3. Figures (選填)
        figs = request.files.getlist('figures')
        for fig in figs:
            if fig.filename:
                files.append(('figures', (fig.filename, fig.stream, fig.content_type)))

        print("🔄 正在呼叫 PDF 工廠...")
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
