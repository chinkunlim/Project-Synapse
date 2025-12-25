from flask import Blueprint, render_template, request, jsonify, Response
import os
from dotenv import set_key
from pathlib import Path
import extensions
from utils.google_calendar_sync import GoogleCalendarIntegration
import json

notion_bp = Blueprint('notion', __name__)

ENV_PATH = Path('.env').resolve()

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

@notion_bp.route('/api/notion/setup', methods=['POST'])
def setup_notion():
    """初始化 Notion 環境"""
    try:
        if not extensions.notion_processor:
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
            "test_connection": extensions.notion_processor.test_connection(),
            "build_layout": extensions.notion_processor.build_dashboard_layout(parent_id),
            "create_databases": extensions.notion_processor.create_databases(parent_id)
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

@notion_bp.route('/notion')
def notion_management():
    """Notion 管理頁面"""
    # 取得環境變數
    api_key = os.getenv("NOTION_API_KEY")
    parent_id = os.getenv("PARENT_PAGE_ID")
    task_db = os.getenv("TASK_DATABASE_ID")

    # 建立狀態清單（隱藏完整 ID 以保護隱私）
    config_status = {
        "api_key": "Connected / 已設定" if api_key else "Missing / 未設定",
        "parent_id": "Set / 已設定" if parent_id else "Missing / 未設定",
        "task_db": "Ready / 已設定" if task_db else "Pending / 待初始化"
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

@notion_bp.route('/api/notion/action', methods=['POST'])
def handle_notion_action():
    """處理 Notion 相關操作"""
    try:
        if not extensions.notion_processor:
            return jsonify({
                "status": "error",
                "message": "❌ Notion 處理器未初始化",
                "error": "請檢查 NOTION_API_KEY 是否已設置"
            }), 500
        
        action = request.json.get("action")
        parent_id = os.getenv("PARENT_PAGE_ID")
        
        # 測試連接
        if action == "test_connection":
            result = extensions.notion_processor.test_connection()
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
            result = extensions.notion_processor.build_dashboard_layout(parent_id)
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
            result = extensions.notion_processor.create_databases(parent_id)
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
            test_result = extensions.notion_processor.test_connection()
            logs.append(f"{'✅' if test_result else '❌'} 連接測試")
            
            layout_result = extensions.notion_processor.build_dashboard_layout(parent_id)
            logs.append(f"{'✅' if layout_result else '❌'} 佈局構建")
            
            db_result = extensions.notion_processor.create_databases(parent_id)
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
            result = extensions.notion_processor.delete_blocks(parent_id)
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
            clean_result = extensions.notion_processor.delete_blocks(parent_id)
            logs.append(f"{'✅' if clean_result else '❌'} 清空頁面")
            
            # 步驟 2: 重新構建佈局
            layout_result = extensions.notion_processor.build_dashboard_layout(parent_id)
            logs.append(f"{'✅' if layout_result else '❌'} 重建佈局")
            
            # 步驟 3: 重新創建數據庫
            db_result = extensions.notion_processor.create_databases(parent_id)
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

@notion_bp.route('/api/notion/csv/upload', methods=['POST'])
def upload_csv_to_notion():
    """上傳 CSV 到 Notion 數據庫"""
    try:
        if not extensions.notion_processor:
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
        result = extensions.notion_processor.import_csv_to_database(database_id, csv_content, extra_params)
        
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

@notion_bp.route('/api/notion/env/all', methods=['GET'])
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


@notion_bp.route('/api/notion/env/update', methods=['POST'])
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

@notion_bp.route('/api/notion/csv/sample/<database_type>')
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
