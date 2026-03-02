from flask import Blueprint, render_template, request, jsonify, Response
import os
from dotenv import set_key, load_dotenv
from pathlib import Path
import extensions
from utils.google_calendar_sync import GoogleCalendarIntegration
import json

notion_bp = Blueprint('notion', __name__)
ENV_PATH = Path('.env').resolve()

def _get_env_values():
    """統一管理當前 v3.0 架構下有效的所有環境變數"""
    keys = [
        "NOTION_API_KEY",
        "PARENT_PAGE_ID",
        "COURSE_HUB_ID",
        "CLASS_SESSION_ID",
        "THEORY_HUB_ID",
        "NOTE_DATABASE_ID",
        "TASK_DATABASE_ID",
        "RESOURCE_DATABASE_ID",
        "CALENDAR_ICAL_URL",
    ]
    return {k: os.getenv(k, "") for k in keys}

@notion_bp.route('/api/notion/setup', methods=['POST'])
def setup_notion():
    try:
        if not extensions.notion_processor:
            return jsonify({"status": "error", "message": "Notion 處理器未初始化，請檢查 API Key"}), 500
        parent_id = os.getenv("PARENT_PAGE_ID")
        if not parent_id:
            return jsonify({"status": "error", "message": "未設置 PARENT_PAGE_ID 環境變數"}), 400
        
        results = {
            "test_connection": extensions.notion_processor.test_connection(),
            "build_layout": extensions.notion_processor.build_dashboard_layout(parent_id),
            "create_databases": extensions.notion_processor.create_databases(parent_id),
            "generate_guide": extensions.notion_processor.generate_onboarding_page(parent_id)
        }
        
        if all(results.values()):
            return jsonify({"status": "success", "message": "✅ Notion 環境初始化成功！", "details": results})
        return jsonify({"status": "partial", "message": "⚠️ 部分步驟失敗，請查看日誌", "details": results}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"❌ 初始化失敗: {str(e)}"}), 500

@notion_bp.route('/notion')
def notion_management():
    load_dotenv(override=True)
    api_key = os.getenv("NOTION_API_KEY")
    parent_id = os.getenv("PARENT_PAGE_ID")
    task_db = os.getenv("TASK_DATABASE_ID")

    config_status = {
        "api_key": "Connected / 已設定" if api_key else "Missing / 未設定",
        "parent_id": "Set / 已設定" if parent_id else "Missing / 未設定",
        "task_db": "Ready / 已設定" if task_db else "Pending / 待初始化"
    }
    
    database_ids = {
        "task_db_id": os.getenv("TASK_DATABASE_ID", ""),
        "course_hub_id": os.getenv("COURSE_HUB_ID", ""),
        "class_session_id": os.getenv("CLASS_SESSION_ID", ""),
        "note_db_id": os.getenv("NOTE_DATABASE_ID", ""),
        "resource_db_id": os.getenv("RESOURCE_DATABASE_ID", ""),
        "theory_hub_id": os.getenv("THEORY_HUB_ID", "")
    }
    return render_template('notion_admin.html', status=config_status, **database_ids)

@notion_bp.route('/api/notion/action', methods=['POST'])
def handle_notion_action():
    load_dotenv(override=True)
    try:
        if not extensions.notion_processor:
            return jsonify({"status": "error", "message": "❌ Notion 處理器未初始化"}), 500
        
        action = request.json.get("action")
        parent_id = os.getenv("PARENT_PAGE_ID")
        
        if action == "test_connection":
            result = extensions.notion_processor.test_connection()
            return jsonify({"status": "success", "message": "✅ Notion API 連接成功！"}) if result else jsonify({"status": "error", "message": "❌ 連接測試失敗"}), 500
        
        if not parent_id: return jsonify({"status": "error", "message": "❌ 未設置 PARENT_PAGE_ID"}), 400

        if action == "build_layout":
            result = extensions.notion_processor.build_dashboard_layout(parent_id)
            return jsonify({"status": "success", "message": "✅ 佈局構建成功！"}) if result else jsonify({"status": "error", "message": "❌ 佈局構建失敗"}), 500

        elif action == "create_databases":
            result = extensions.notion_processor.create_databases(parent_id)
            return jsonify({"status": "success", "message": "✅ 數據庫創建成功！"}) if result else jsonify({"status": "error", "message": "❌ 數據庫創建失敗"}), 500

        elif action == "init_all":
            logs = []
            tests = [
                ("連接測試", extensions.notion_processor.test_connection()),
                ("佈局構建", extensions.notion_processor.build_dashboard_layout(parent_id)),
                ("數據庫創建", extensions.notion_processor.create_databases(parent_id)),
                ("生成指南", extensions.notion_processor.generate_onboarding_page(parent_id))
            ]
            for name, res in tests: logs.append(f"{'✅' if res else '❌'} {name}")
            if all(r for _, r in tests): return jsonify({"status": "success", "message": "✅ 初始化完成！", "logs": logs})
            return jsonify({"status": "partial", "message": "⚠️ 部分步驟失敗", "logs": logs}), 500

        elif action == "clean":
            result = extensions.notion_processor.delete_blocks(parent_id)
            return jsonify({"status": "success", "message": "🧹 頁面內容與資料庫已清空封存"}) if result else jsonify({"status": "error", "message": "❌ 清空失敗"}), 500

        # 修改：重置系統現在只執行「清空」與「解除綁定」，不再自動重建
        elif action == "reset_all":
            logs = []
            
            # 步驟 1: 清空頁面與封存舊資料庫
            clean_result = extensions.notion_processor.delete_blocks(parent_id)
            logs.append(f"{'✅' if clean_result else '❌'} 清空頁面與舊資料庫")
            
            # 步驟 2: 清除 .env 中的資料庫 ID 紀錄
            keys_to_clear = [
                "COURSE_HUB_ID", "CLASS_SESSION_ID", "THEORY_HUB_ID",
                "NOTE_DATABASE_ID", "TASK_DATABASE_ID", "RESOURCE_DATABASE_ID"
            ]
            for key in keys_to_clear:
                if key in os.environ:
                    os.environ[key] = ""
                    set_key(str(ENV_PATH), key, "")
            logs.append("✅ 解除舊資料庫綁定")
            
            if clean_result:
                return jsonify({"status": "success", "message": "🧹 系統已重置！頁面已清空且解除綁定。", "logs": logs})
            return jsonify({"status": "partial", "message": "⚠️ 清空過程中發生錯誤", "logs": logs}), 500

        elif action == "list_databases":
            env_vars = _get_env_values()
            info = [f"{k}: {'已設置' if v else '未設置'}" for k, v in env_vars.items() if '_ID' in k or 'KEY' in k]
            return jsonify({"status": "success", "message": "📊 數據庫列表", "logs": info or ["未找到配置"]})

        elif action == "check_schema":
            from intergrations.notion import notion_config
            schema_path = notion_config.schema_path
            if not schema_path.exists(): return jsonify({"status": "error", "message": f"❌ Schema 不存在"}), 404
            with open(schema_path, 'r', encoding='utf-8') as f: schema = json.load(f)
            logs = [f"✅ Schema 文件: {schema_path.name}", f"📊 數據庫配置: {len(schema.get('databases', []))} 個"]
            return jsonify({"status": "success", "message": "✅ 檢查完成", "logs": logs})

        elif action == "show_env":
            env_vars = _get_env_values()
            logs = ["🔧 環境變數配置:"]
            for k, v in env_vars.items():
                logs.append(f"  {k}: {f'{v[:4]}...{v[-4:]}' if v and len(v)>10 else ('***' if v else '❌ 未設置')}")
            return jsonify({"status": "success", "message": "📋 狀態", "logs": logs})

        elif action == "sync_calendar":
            calendar_url = os.getenv("CALENDAR_ICAL_URL", "https://calendar.google.com/calendar/ical/ndhuoaa%40gmail.com/public/basic.ics")
            semesters = GoogleCalendarIntegration.extract_semester_from_ical_url(calendar_url)
            if not semesters: return jsonify({"status": "error", "message": "❌ 無法取得學期資訊"}), 500
            valid = GoogleCalendarIntegration.validate_semester_data(semesters)
            if not valid: return jsonify({"status": "error", "message": "❌ 未找到有效日期配對"}), 500
            GoogleCalendarIntegration.apply_semesters_to_config(valid)
            logs = [f"學年 {y} 第 {s} 學期: {d['start'].date()} ~ {d['end'].date()}" for (y, s), d in sorted(valid.items())]
            return jsonify({"status": "success", "message": "✅ 學期同步成功", "logs": logs})

        elif action == "get_env":
            return jsonify({"status": "success", "data": _get_env_values()})
        else:
            return jsonify({"status": "error", "message": f"❌ 未知指令: {action}"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"❌ 失敗: {str(e)}"}), 500

@notion_bp.route('/api/notion/csv/upload', methods=['POST'])
def upload_csv_to_notion():
    load_dotenv(override=True)
    try:
        if not extensions.notion_processor: return jsonify({"status": "error", "message": "❌ 未初始化"}), 500
        if 'csv_file' not in request.files: return jsonify({"status": "error", "message": "❌ 未上傳 CSV"}), 400
        
        csv_file = request.files['csv_file']
        database_id = request.form.get('database_id')
        database_type = request.form.get('database_type', '')
        
        if not database_id or csv_file.filename == '': return jsonify({"status": "error", "message": "❌ 參數錯誤"}), 400
        
        try: csv_content = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            csv_file.seek(0)
            csv_content = csv_file.read().decode('big5')
            
        extra_params = {}
        if database_type == 'courses':
            extra_params['course_sessions_db_id'] = os.getenv("CLASS_SESSION_ID", "")
            extra_params['notes_db_id'] = os.getenv("NOTE_DATABASE_ID", "")
            
        result = extensions.notion_processor.import_csv_to_database(database_id, csv_content, extra_params)
        return jsonify({"status": "success" if result["success"] else "error", "message": result["message"], "details": result}), 200 if result["success"] else 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"❌ 上傳失敗: {str(e)}"}), 500

@notion_bp.route('/api/notion/env/all', methods=['GET'])
def list_env_vars():
    return jsonify({"status": "success", "data": _get_env_values()})

@notion_bp.route('/api/notion/env/update', methods=['POST'])
def update_env_vars():
    try:
        payload = request.json or {}
        for key in _get_env_values().keys():
            if key in payload:
                value = payload[key] if payload[key] is not None else ""
                os.environ[key] = value
                set_key(str(ENV_PATH), key, value)
        return jsonify({"status": "success", "message": "✅ 更新成功", "data": _get_env_values()})
    except Exception as e:
        return jsonify({"status": "error", "message": f"❌ 更新失敗: {str(e)}"}), 500

@notion_bp.route('/api/notion/csv/sample/<database_type>')
def download_csv_sample(database_type):
    from intergrations.notion import NotionProcessor
    return Response(NotionProcessor.generate_csv_sample(database_type), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename={database_type}_sample.csv'})