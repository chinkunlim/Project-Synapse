from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
from dotenv import load_dotenv, set_key
from pathlib import Path
from notion_client import Client

# 導入重構後的 Notion 模組
from intergrations.notion import (
    NotionApiClient, 
    NotionProcessor,
    setup_logging
)
from utils.google_calendar_sync import GoogleCalendarIntegration
from utils.google_classroom_integration import GoogleClassroomIntegration

# 初始化日誌系統
setup_logging()

# 載入環境變數
load_dotenv()
ENV_PATH = Path('.env').resolve()

# 初始化 Flask 應用
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret')

# 初始化 Notion 客戶端（若失敗不影響 App 啟動）
try:
    notion = Client(auth=os.getenv("NOTION_API_KEY"))
    database_id = os.getenv("NOTION_DATABASE_ID")
    notion_processor = NotionProcessor()
except Exception as e:
    print(f"Notion 初始化警告: {e}")
    notion = None
    database_id = None
    notion_processor = None

# 初始化 Google Classroom 整合（若失敗不影響 App 啟動）
try:
    classroom_integration = GoogleClassroomIntegration()
except Exception as e:
    print(f"Google Classroom 初始化警告: {e}")
    classroom_integration = None

def fetch_tasks_from_notion():
    """從 Notion 讀取任務"""
    tasks = []
    if not notion or not database_id:
        return []
    try:
        # 不使用排序，避免欄位不存在的錯誤
        response = notion.databases.query(
            database_id=database_id,
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
    
@app.route('/api/notion/setup', methods=['POST'])
def setup_notion():
    """初始化 Notion 環境"""
    try:
        if not notion_processor:
            return jsonify({
                "status": "error", 
                "message": "Notion 處理器未初始化，請檢查 API Key"
            }), 500
        
        parent_id = os.getenv("PARENT_PAGE_ID")
        if not parent_id:
            return jsonify({
                "status": "error", 
                "message": "未設置 PARENT_PAGE_ID 環境變數"
            }), 400
        
        # 執行初始化流程
        results = {
            "test_connection": notion_processor.test_connection(),
            "build_layout": notion_processor.build_dashboard_layout(parent_id),
            "create_databases": notion_processor.create_databases(parent_id)
        }
        
        if all(results.values()):
            return jsonify({
                "status": "success", 
                "message": "✅ Notion 環境初始化成功！",
                "details": results
            })
        else:
            return jsonify({
                "status": "partial", 
                "message": "⚠️ 部分步驟失敗，請查看日誌",
                "details": results
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"❌ 初始化失敗: {str(e)}"
        }), 500

@app.route('/notion')
def notion_management():
    """Notion 管理頁面"""
    # 取得環境變數
    api_key = os.getenv("NOTION_API_KEY")
    parent_id = os.getenv("PARENT_PAGE_ID")
    task_db = os.getenv("TASK_DATABASE_ID")

    # 建立狀態清單（隱藏完整 ID 以保護隱私）
    config_status = {
        "api_key": "✅ 已設定" if api_key else "❌ 未設定",
        "parent_id": "✅ 已設定" if parent_id else "❌ 未設定",
        "task_db": "✅ 已設定" if task_db else "⏳ 待初始化"
    }
    
    # 傳遞數據庫 ID 供 CSV 上傳使用
    database_ids = {
        "task_db_id": os.getenv("TASK_DATABASE_ID", ""),
        "course_hub_id": os.getenv("COURSE_HUB_ID", ""),
        "project_db_id": os.getenv("PROJECT_DATABASE_ID", ""),
        "class_session_id": os.getenv("CLASS_SESSION_ID", ""),
        "note_db_id": os.getenv("NOTE_DATABASE_ID", ""),
        "resource_db_id": os.getenv("RESOURCE_DATABASE_ID", "")
    }

    return render_template('notion_admin.html', status=config_status, **database_ids)


def _get_env_values():
    keys = [
        "NOTION_API_KEY",
        "PARENT_PAGE_ID",
        "TASK_DATABASE_ID",
        "COURSE_HUB_ID",
        "PROJECT_DATABASE_ID",
        "CLASS_SESSION_ID",
        "NOTE_DATABASE_ID",
        "RESOURCE_DATABASE_ID",
        "CALENDAR_ICAL_URL",
    ]
    return {k: os.getenv(k, "") for k in keys}

@app.route('/api/notion/action', methods=['POST'])
def handle_notion_action():
    """處理 Notion 相關操作"""
    try:
        if not notion_processor:
            return jsonify({
                "status": "error",
                "message": "❌ Notion 處理器未初始化",
                "error": "請檢查 NOTION_API_KEY 是否已設置"
            }), 500
        
        action = request.json.get("action")
        parent_id = os.getenv("PARENT_PAGE_ID")
        
        # 測試連接
        if action == "test_connection":
            result = notion_processor.test_connection()
            if result:
                return jsonify({
                    "status": "success",
                    "message": "✅ Notion API 連接成功！"
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "❌ 連接測試失敗"
                }), 500
        
        # 以下操作需要 parent_id
        if not parent_id:
            return jsonify({
                "status": "error",
                "message": "❌ 未設置 PARENT_PAGE_ID",
                "error": "請在 .env 文件中設置 PARENT_PAGE_ID"
            }), 400

        # 構建儀表板佈局
        if action == "build_layout":
            result = notion_processor.build_dashboard_layout(parent_id)
            if result:
                return jsonify({
                    "status": "success",
                    "message": "✅ 儀表板佈局構建成功！"
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "❌ 佈局構建失敗"
                }), 500

        # 創建數據庫
        elif action == "create_databases":
            result = notion_processor.create_databases(parent_id)
            if result:
                return jsonify({
                    "status": "success",
                    "message": "✅ 所有數據庫創建成功！"
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "❌ 數據庫創建失敗"
                }), 500

        # 完整初始化
        elif action == "init_all":
            logs = []
            test_result = notion_processor.test_connection()
            logs.append(f"{'✅' if test_result else '❌'} 連接測試")
            
            layout_result = notion_processor.build_dashboard_layout(parent_id)
            logs.append(f"{'✅' if layout_result else '❌'} 佈局構建")
            
            db_result = notion_processor.create_databases(parent_id)
            logs.append(f"{'✅' if db_result else '❌'} 數據庫創建")
            
            if test_result and layout_result and db_result:
                return jsonify({
                    "status": "success",
                    "message": "✅ 所有資料庫與佈局初始化完成！",
                    "logs": logs
                })
            else:
                return jsonify({
                    "status": "partial",
                    "message": "⚠️ 部分步驟失敗，請查看日誌",
                    "logs": logs
                }), 500

        # 清空頁面內容
        elif action == "clean":
            result = notion_processor.delete_blocks(parent_id)
            if result:
                return jsonify({
                    "status": "success",
                    "message": "🧹 頁面內容已清空"
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "❌ 清空失敗"
                }), 500

        # 重置所有設置（清空 + 重新初始化）
        elif action == "reset_all":
            logs = []
            
            # 步驟 1: 清空頁面
            clean_result = notion_processor.delete_blocks(parent_id)
            logs.append(f"{'✅' if clean_result else '❌'} 清空頁面")
            
            # 步驟 2: 重新構建佈局
            layout_result = notion_processor.build_dashboard_layout(parent_id)
            logs.append(f"{'✅' if layout_result else '❌'} 重建佈局")
            
            # 步驟 3: 重新創建數據庫
            db_result = notion_processor.create_databases(parent_id)
            logs.append(f"{'✅' if db_result else '❌'} 重建數據庫")
            
            if clean_result and layout_result and db_result:
                return jsonify({
                    "status": "success",
                    "message": "🔄 重置完成！所有設置已重新初始化",
                    "logs": logs
                })
            else:
                return jsonify({
                    "status": "partial",
                    "message": "⚠️ 重置過程中部分步驟失敗",
                    "logs": logs
                }), 500

        # 列出數據庫
        elif action == "list_databases":
            from intergrations.notion import notion_config
            env_vars = notion_config.get_all_env_vars()
            
            database_info = []
            for key, value in env_vars.items():
                if 'DATABASE' in key or 'DB' in key:
                    database_info.append(f"{key}: {'已設置' if value else '未設置'}")
            
            return jsonify({
                "status": "success",
                "message": "📊 數據庫列表",
                "logs": database_info if database_info else ["未找到數據庫配置"]
            })

        # 檢查 Schema 配置
        elif action == "check_schema":
            import json
            from intergrations.notion import notion_config
            
            schema_path = notion_config.schema_path
            
            if not schema_path.exists():
                return jsonify({
                    "status": "error",
                    "message": f"❌ Schema 文件不存在: {schema_path}"
                }), 404
            
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                
                logs = [
                    f"✅ Schema 文件: {schema_path.name}",
                    f"📐 佈局區塊: {len(schema.get('layout', []))} 個",
                    f"📊 數據庫配置: {len(schema.get('databases', []))} 個"
                ]
                
                # 列出數據庫名稱
                for db in schema.get('databases', []):
                    db_name = db.get('db_name', 'Unknown')
                    db_title = db.get('title', 'Unknown')
                    logs.append(f"  • {db_name}: {db_title}")
                
                return jsonify({
                    "status": "success",
                    "message": "✅ Schema 配置檢查完成",
                    "logs": logs
                })
            except json.JSONDecodeError as e:
                return jsonify({
                    "status": "error",
                    "message": f"❌ Schema JSON 解析錯誤: {str(e)}"
                }), 500

        # 顯示環境變數
        elif action == "show_env":
            from intergrations.notion import notion_config
            env_vars = notion_config.get_all_env_vars()
            
            logs = ["🔧 環境變數配置:"]
            for key, value in env_vars.items():
                if value:
                    # 隱藏敏感信息
                    if len(value) > 10:
                        masked = f"{value[:4]}...{value[-4:]}"
                    else:
                        masked = "***"
                    logs.append(f"  {key}: {masked}")
                else:
                    logs.append(f"  {key}: ❌ 未設置")
            
            return jsonify({
                "status": "success",
                "message": "📋 環境變數狀態",
                "logs": logs
            })

        # 同步學期日期（Google Calendar）
        elif action == "sync_calendar":
            calendar_url = os.getenv(
                "CALENDAR_ICAL_URL",
                "https://calendar.google.com/calendar/ical/ndhuoaa%40gmail.com/public/basic.ics"
            )

            semesters = GoogleCalendarIntegration.extract_semester_from_ical_url(calendar_url)
            if not semesters:
                return jsonify({
                    "status": "error",
                    "message": "❌ 無法從 Google Calendar 取得學期資訊，請確認 iCal URL 是否公開"
                }), 500

            valid_semesters = GoogleCalendarIntegration.validate_semester_data(semesters)
            if not valid_semesters:
                return jsonify({
                    "status": "error",
                    "message": "❌ 未找到有效的開始/結束日期配對"
                }), 500

            GoogleCalendarIntegration.apply_semesters_to_config(valid_semesters)

            logs = []
            for (year, sem), dates in sorted(valid_semesters.items()):
                logs.append(f"學年 {year} 第 {sem} 學期: {dates['start'].date()} ~ {dates['end'].date()}")

            return jsonify({
                "status": "success",
                "message": "✅ 學期日期已同步（Google Calendar）",
                "logs": logs
            })

        # 取得環境變數（可編輯）
        elif action == "get_env":
            return jsonify({
                "status": "success",
                "data": _get_env_values()
            })

        else:
            return jsonify({
                "status": "error",
                "message": f"❌ 未知指令: {action}"
            }), 400
            
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": f"❌ 操作失敗: {str(e)}",
            "error": traceback.format_exc()
        }), 500

@app.route('/api/notion/csv/upload', methods=['POST'])
def upload_csv_to_notion():
    """上傳 CSV 到 Notion 數據庫"""
    try:
        if not notion_processor:
            return jsonify({
                "status": "error",
                "message": "❌ Notion 處理器未初始化"
            }), 500
        
        # 檢查文件
        if 'csv_file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "❌ 未上傳 CSV 文件"
            }), 400
        
        csv_file = request.files['csv_file']
        database_id = request.form.get('database_id')
        database_type = request.form.get('database_type', '')
        
        if not database_id:
            return jsonify({
                "status": "error",
                "message": "❌ 未指定目標數據庫"
            }), 400
        
        if csv_file.filename == '':
            return jsonify({
                "status": "error",
                "message": "❌ 未選擇文件"
            }), 400
        
        # 讀取 CSV 內容
        try:
            csv_content = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            # 嘗試其他編碼
            csv_file.seek(0)
            csv_content = csv_file.read().decode('big5')
        
        # 為課程導入準備額外參數
        extra_params = {}
        if database_type == 'courses':
            semester_start = request.form.get('semester_start')
            semester_end = request.form.get('semester_end')
            
            if semester_start and semester_end:
                extra_params['semester_start'] = semester_start
                extra_params['semester_end'] = semester_end
                extra_params['course_sessions_db_id'] = os.getenv("CLASS_SESSION_ID", "")
        
        # 導入到 Notion
        result = notion_processor.import_csv_to_database(database_id, csv_content, extra_params)
        
        if result["success"]:
            return jsonify({
                "status": "success",
                "message": result["message"],
                "details": {
                    "imported": result["imported"],
                    "failed": result["failed"],
                    "errors": result.get("errors", [])
                }
            })
        else:
            return jsonify({
                "status": "error",
                "message": result["message"],
                "details": result
            }), 500
            
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": f"❌ CSV 上傳失敗: {str(e)}",
            "error": traceback.format_exc()
        }), 500


@app.route('/api/notion/env/all', methods=['GET'])
def list_env_vars():
    """取得 Notion 相關環境變數（可編輯）"""
    try:
        return jsonify({
            "status": "success",
            "data": _get_env_values()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 讀取環境變數失敗: {str(e)}"
        }), 500


@app.route('/api/notion/env/update', methods=['POST'])
def update_env_vars():
    """更新 Notion 相關環境變數，並寫回 .env"""
    try:
        payload = request.json or {}
        current = _get_env_values()

        # 只允許白名單中的 key
        for key in current.keys():
            if key in payload:
                value = payload[key] if payload[key] is not None else ""
                os.environ[key] = value
                # 持久化到 .env
                set_key(str(ENV_PATH), key, value)

        return jsonify({
            "status": "success",
            "message": "✅ 環境變數已更新並寫入 .env",
            "data": _get_env_values()
        })
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": f"❌ 更新失敗: {str(e)}",
            "error": traceback.format_exc()
        }), 500

@app.route('/api/notion/csv/sample/<database_type>')
def download_csv_sample(database_type):
    """下載 CSV 樣本文件"""
    try:
        from intergrations.notion import NotionProcessor
        from flask import Response
        
        # 生成 CSV 樣本
        csv_content = NotionProcessor.generate_csv_sample(database_type)
        
        # 返回文件
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={database_type}_sample.csv',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 生成樣本失敗: {str(e)}"
        }), 500

# === Google Classroom 路由 ===

@app.route('/classroom')
def classroom_page():
    """Google Classroom 管理頁面"""
    return render_template('classroom.html')

@app.route('/api/classroom/auth/start', methods=['GET'])
def classroom_auth_start():
    """取得 Google OAuth 授權網址（Web Flow）"""
    try:
        from google_auth_oauthlib.flow import Flow
        from flask import session

        if not classroom_integration:
            return jsonify({
                "status": "error",
                "message": "❌ Google Classroom 整合未初始化"
            }), 500

        # 使用 Web 應用程式流程產生授權網址
        redirect_uri = 'http://localhost:5001/api/classroom/auth/callback'
        flow = Flow.from_client_secrets_file(
            'config/google_credentials.json',
            scopes=classroom_integration.SCOPES,
            redirect_uri=redirect_uri
        )

        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        # 保存 state 以便回調驗證
        session['oauth_state'] = state

        return jsonify({
            "status": "success",
            "authorization_url": auth_url
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 產生授權網址失敗: {str(e)}"
        }), 500

@app.route('/api/classroom/auth/callback', methods=['GET'])
def classroom_auth_callback():
    """Google OAuth 回調（Web Flow）"""
    try:
        from google_auth_oauthlib.flow import Flow
        from flask import session, redirect

        if not classroom_integration:
            return jsonify({
                "status": "error",
                "message": "❌ Google Classroom 整合未初始化"
            }), 500

        redirect_uri = 'http://localhost:5001/api/classroom/auth/callback'
        state = session.get('oauth_state')

        flow = Flow.from_client_secrets_file(
            'config/google_credentials.json',
            scopes=classroom_integration.SCOPES,
            redirect_uri=redirect_uri,
            state=state
        )

        # 使用完整的回調 URL 完成 token 交換
        flow.fetch_token(authorization_response=request.url)

        # 初始化整合並保存憑證
        success = classroom_integration.set_credentials(flow.credentials)
        if not success:
            return jsonify({
                "status": "error",
                "message": "❌ 保存憑證失敗"
            }), 500

        # 回到管理頁
        return redirect('/classroom')

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 認證回調錯誤: {str(e)}"
        }), 500

@app.route('/api/classroom/authenticate', methods=['POST'])
def classroom_authenticate():
    """執行 Google Classroom OAuth 認證"""
    try:
        if not classroom_integration:
            return jsonify({
                "status": "error",
                "message": "❌ Google Classroom 整合未初始化"
            }), 500
        
        success = classroom_integration.authenticate()
        
        if success:
            return jsonify({
                "status": "success",
                "message": "✅ Google Classroom 認證成功！"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "❌ 認證失敗，請檢查憑證設定"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 認證錯誤: {str(e)}"
        }), 500

@app.route('/api/classroom/courses', methods=['GET'])
def get_courses():
    """獲取所有課程列表"""
    try:
        if not classroom_integration:
            return jsonify({
                "status": "error",
                "message": "❌ Google Classroom 整合未初始化"
            }), 500
        
        # 確保已認證
        if not classroom_integration.classroom_service:
            success = classroom_integration.authenticate()
            if not success:
                return jsonify({
                    "status": "error",
                    "message": "❌ 請先完成認證"
                }), 401
        
        courses = classroom_integration.get_courses()
        
        return jsonify({
            "status": "success",
            "courses": courses,
            "count": len(courses)
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 獲取課程失敗: {str(e)}"
        }), 500

@app.route('/api/classroom/students/<course_id>', methods=['GET'])
def get_students(course_id):
    """獲取指定課程的學生名單"""
    try:
        if not classroom_integration or not classroom_integration.classroom_service:
            return jsonify({
                "status": "error",
                "message": "❌ 請先完成認證"
            }), 401
        
        students = classroom_integration.get_students(course_id)
        
        return jsonify({
            "status": "success",
            "students": students,
            "count": len(students)
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 獲取學生名單失敗: {str(e)}"
        }), 500

@app.route('/api/classroom/students/<course_id>/export', methods=['GET'])
def export_students(course_id):
    """導出學生名單為 Excel 檔案"""
    try:
        if not classroom_integration or not classroom_integration.classroom_service:
            return jsonify({
                "status": "error",
                "message": "❌ 請先完成認證"
            }), 401
        
        course_name = request.args.get('course_name', 'students')
        
        excel_file = classroom_integration.export_students_to_excel(course_id, course_name)
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{course_name}_學生名單.xlsx'
        )
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 導出失敗: {str(e)}"
        }), 500

@app.route('/api/classroom/topics/create', methods=['POST'])
def create_topics():
    """批次建立主題"""
    try:
        if not classroom_integration or not classroom_integration.classroom_service:
            return jsonify({
                "status": "error",
                "message": "❌ 請先完成認證"
            }), 401
        
        data = request.json
        course_id = data.get('course_id')
        num_weeks = data.get('num_weeks', 18)
        prefix = data.get('prefix', 'Week')
        
        if not course_id:
            return jsonify({
                "status": "error",
                "message": "❌ 缺少 course_id 參數"
            }), 400
        
        topics = classroom_integration.create_topics(course_id, num_weeks, prefix)
        
        return jsonify({
            "status": "success",
            "message": f"✅ 成功建立 {len(topics)} 個主題",
            "topics": topics
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 建立主題失敗: {str(e)}"
        }), 500

@app.route('/api/classroom/topics/<course_id>', methods=['GET'])
def get_topics(course_id):
    """獲取課程的所有主題"""
    try:
        if not classroom_integration or not classroom_integration.classroom_service:
            return jsonify({
                "status": "error",
                "message": "❌ 請先完成認證"
            }), 401
        
        topics = classroom_integration.get_topics(course_id)
        
        return jsonify({
            "status": "success",
            "topics": topics,
            "count": len(topics)
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 獲取主題失敗: {str(e)}"
        }), 500

@app.route('/api/classroom/material/create', methods=['POST'])
def create_course_material():
    """發布課件"""
    try:
        if not classroom_integration or not classroom_integration.classroom_service:
            return jsonify({
                "status": "error",
                "message": "❌ 請先完成認證"
            }), 401
        
        data = request.json
        course_id = data.get('course_id')
        title = data.get('title')
        description = data.get('description', '')
        topic_id = data.get('topic_id')
        link_url = data.get('link_url')
        state = data.get('state', 'PUBLISHED')
        
        if not course_id or not title:
            return jsonify({
                "status": "error",
                "message": "❌ 缺少必要參數 (course_id, title)"
            }), 400
        
        # 處理檔案上傳（若有）
        file_id = None
        if 'file' in request.files:
            uploaded_file = request.files['file']
            if uploaded_file.filename:
                # 暫存檔案
                temp_path = f"/tmp/{uploaded_file.filename}"
                uploaded_file.save(temp_path)
                
                # 上傳到 Drive
                file_id = classroom_integration.upload_file_to_drive(temp_path, uploaded_file.filename)
                
                # 刪除暫存檔案
                os.remove(temp_path)
        
        material = classroom_integration.create_course_material(
            course_id=course_id,
            title=title,
            description=description,
            topic_id=topic_id,
            file_id=file_id,
            link_url=link_url,
            state=state
        )
        
        if material:
            return jsonify({
                "status": "success",
                "message": "✅ 課件發布成功！",
                "material": material
            })
        else:
            return jsonify({
                "status": "error",
                "message": "❌ 課件發布失敗"
            }), 500
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 發布失敗: {str(e)}"
        }), 500

@app.route('/api/classroom/coursework/<course_id>', methods=['GET'])
def get_coursework(course_id):
    """獲取課程的所有作業"""
    try:
        if not classroom_integration or not classroom_integration.classroom_service:
            return jsonify({
                "status": "error",
                "message": "❌ 請先完成認證"
            }), 401
        
        coursework = classroom_integration.get_all_coursework(course_id)
        
        return jsonify({
            "status": "success",
            "coursework": coursework,
            "count": len(coursework)
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 獲取作業失敗: {str(e)}"
        }), 500

@app.route('/api/classroom/submissions/<course_id>/<coursework_id>', methods=['GET'])
def get_submissions(course_id, coursework_id):
    """獲取作業的呈交進度統計"""
    try:
        if not classroom_integration or not classroom_integration.classroom_service:
            return jsonify({
                "status": "error",
                "message": "❌ 請先完成認證"
            }), 401
        
        stats = classroom_integration.get_coursework_submissions(course_id, coursework_id)
        
        return jsonify({
            "status": "success",
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 獲取呈交進度失敗: {str(e)}"
        }), 500

if __name__ == '__main__':
    # 使用非調試模式並改用 5001 端口，避免與 pdf_service 衝突
    app.run(host='0.0.0.0', port=5001)