from flask import Blueprint, jsonify, session, redirect, request
from google_auth_oauthlib.flow import Flow
import json
import os
import extensions

ndhu_bp = Blueprint('ndhu', __name__)

@ndhu_bp.route('/api/ndhu/auth/start', methods=['GET'])
def ndhu_auth_start():
    """取得 Google OAuth 授權網址（NDHU Web Flow）"""
    try:
        if not extensions.ndhu_integration:
            return jsonify({
                "status": "error",
                "message": "❌ Google NDHU 整合未初始化"
            }), 500

        # 檢查憑證類型與 redirect_uri
        cred_path = 'config/google_credential_ndhu.json'
        with open(cred_path, 'r') as f:
            cred_json = json.load(f)
        is_web = 'web' in cred_json
        is_installed = 'installed' in cred_json

        # 使用 Web 應用程式流程產生授權網址
        # Note: In production, base URL should be configurable
        redirect_uri = 'http://localhost:5001/api/ndhu/auth/callback'
        if is_web:
            allowed_redirects = cred_json['web'].get('redirect_uris', [])
            if redirect_uri not in allowed_redirects:
                return jsonify({
                    "status": "error",
                    "message": "❌ OAuth 設定錯誤：請在 Google Cloud Console 的 NDHU OAuth 用戶端 (web) 中加入 redirect URI: " + redirect_uri
                }), 400
        elif is_installed:
            return jsonify({
                "status": "error",
                "message": "❌ 目前使用的是 Installed 憑證。請建立 'Web application' 類型的 OAuth 用戶端，並設定 redirect URI: " + redirect_uri
            }), 400
        else:
            return jsonify({
                "status": "error",
                "message": "❌ NDHU 憑證格式不正確，請提供 Google OAuth 用戶端 JSON (web)"
            }), 400
        flow = Flow.from_client_secrets_file(
            'config/google_credential_ndhu.json',
            scopes=extensions.ndhu_integration.SCOPES,
            redirect_uri=redirect_uri
        )

        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent select_account'
        )

        # 保存 state 以便回調驗證
        session['ndhu_oauth_state'] = state

        return jsonify({
            "status": "success",
            "authorization_url": auth_url
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ 產生授權網址失敗: {str(e)}"
        }), 500

@ndhu_bp.route('/api/ndhu/auth/start/redirect', methods=['GET'])
def ndhu_auth_start_redirect():
    """取得授權網址並直接 302 導向（前端備援用）"""
    try:
        if not extensions.ndhu_integration:
            return jsonify({
                "status": "error",
                "message": "❌ Google NDHU 整合未初始化"
            }), 500

        cred_path = 'config/google_credential_ndhu.json'
        with open(cred_path, 'r') as f:
            cred_json = json.load(f)
        is_web = 'web' in cred_json
        is_installed = 'installed' in cred_json

        redirect_uri = 'http://localhost:5001/api/ndhu/auth/callback'
        if is_web:
            allowed_redirects = cred_json['web'].get('redirect_uris', [])
            if redirect_uri not in allowed_redirects:
                return jsonify({
                    "status": "error",
                    "message": "❌ OAuth 設定錯誤：請在 Google Cloud Console 的 NDHU OAuth 用戶端 (web) 中加入 redirect URI: " + redirect_uri
                }), 400
        elif is_installed:
            return jsonify({
                "status": "error",
                "message": "❌ 目前使用的是 Installed 憑證。請建立 'Web application' 類型的 OAuth 用戶端，並設定 redirect URI: " + redirect_uri
            }), 400
        else:
            return jsonify({
                "status": "error",
                "message": "❌ NDHU 憑證格式不正確，請提供 Google OAuth 用戶端 JSON (web)"
            }), 400

        flow = Flow.from_client_secrets_file(
            'config/google_credential_ndhu.json',
            scopes=extensions.ndhu_integration.SCOPES,
            redirect_uri=redirect_uri
        )
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent select_account'
        )
        session['ndhu_oauth_state'] = state
        return redirect(auth_url)
    except Exception as e:
         return jsonify({
            "status": "error",
            "message": f"❌ 產生授權網址失敗: {str(e)}"
        }), 500

@ndhu_bp.route('/api/ndhu/auth/callback', methods=['GET'])
def ndhu_auth_callback():
    """Google OAuth callback handler"""
    try:
        if not extensions.ndhu_integration:
            return "NDHU integration not initialized", 500

        state = session.get('ndhu_oauth_state')
        
        flow = Flow.from_client_secrets_file(
            'config/google_credential_ndhu.json',
            scopes=extensions.ndhu_integration.SCOPES,
            state=state,
            redirect_uri='http://localhost:5001/api/ndhu/auth/callback'
        )

        flow.fetch_token(authorization_response=request.url)

        creds = flow.credentials
        
        # Save credentials using the method in integration class
        extensions.ndhu_integration.set_credentials(creds)
            
        return redirect('/') 

    except Exception as e:
        return f"Authentication failed: {e}", 500

@ndhu_bp.route('/api/ndhu/tasks', methods=['GET'])
def get_ndhu_tasks():
    if not extensions.ndhu_integration:
        return jsonify({"status": "error", "message": "Module not initialized"}), 500
    try:
        tasklist_id = request.args.get('tasklist_id')
        tasks = extensions.ndhu_integration.get_tasks(tasklist_id=tasklist_id)
        return jsonify({"status": "success", "items": tasks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@ndhu_bp.route('/api/ndhu/tasklists', methods=['GET'])
def list_tasklists():
     if not extensions.ndhu_integration: return jsonify({"status": "error"}), 500
     try:
         # Use list_tasklists method
         lists = extensions.ndhu_integration.list_tasklists()
         
         if lists is None:
             return jsonify({"status": "error", "message": "Authentication required"}), 401
             
         return jsonify({"status": "success", "lists": lists})
     except Exception as e:
         return jsonify({"status": "error", "message": str(e)}), 500

@ndhu_bp.route('/api/ndhu/tasks/create', methods=['POST'])
def create_ndhu_task():
    if not extensions.ndhu_integration: return jsonify({"status": "error"}), 500
    try:
        data = request.json
        
        result = extensions.ndhu_integration.create_task(
            tasklist_id=data.get('tasklist_id'),
            title=data.get('title'),
            notes=data.get('notes', ''),
            due_iso=data.get('due')
        )
        return jsonify({"status": "success", "task": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@ndhu_bp.route('/api/ndhu/tasks/complete', methods=['POST'])
def complete_ndhu_task():
    if not extensions.ndhu_integration: return jsonify({"status": "error"}), 500
    try:
        data = request.json
        result = extensions.ndhu_integration.complete_task(
            tasklist_id=data['tasklist_id'],
            task_id=data['task_id']
        )
        return jsonify({"status": "success", "task": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@ndhu_bp.route('/api/ndhu/tasks/delete', methods=['POST'])
def delete_ndhu_task():
    if not extensions.ndhu_integration: return jsonify({"status": "error"}), 500
    try:
        data = request.json
        success = extensions.ndhu_integration.delete_task(
            tasklist_id=data['tasklist_id'],
            task_id=data['task_id']
        )
        return jsonify({"status": "success" if success else "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@ndhu_bp.route('/api/ndhu/auth/reset', methods=['POST'])
def reset_ndhu_auth():
    try:
        if os.path.exists('config/token.json'):
            os.remove('config/token.json')
        # Re-initialize integration to clear service
        from extensions import init_extensions
        # This calls init again, refreshing global variables
        init_extensions()
        return jsonify({"status": "success", "message": "Credentials cleared"})
    except Exception as e:
         return jsonify({"status": "error", "message": str(e)}), 500
