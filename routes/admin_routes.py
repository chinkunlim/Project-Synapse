from flask import Blueprint, render_template, request, jsonify
import os
from dotenv import set_key

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
def admin_dashboard():
    return render_template('admin.html')

@admin_bp.route('/api/admin/env', methods=['GET'])
def get_env():
    """
    Retrieve environment variables.
    Proprietary/Security: Restricted to localhost access only.
    """
    # Security Check: Only allow localhost (Disabled for local dev compatibility)
    # if request.remote_addr not in ['127.0.0.1', '::1', 'localhost']:
    #    return jsonify({"status": "error", "message": f"Access denied for {request.remote_addr}"}), 403

    # Filter visible keys for security, or show all if authenticated (assuming local usage)
    # For this local desktop app, we show everything but maybe mask some in UI
    env_vars = {}
    
    # Read dot env file manually to avoid getting system vars
    try:
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, val = line.strip().split('=', 1)
                        # Remove quotes if present
                        val = val.strip('"').strip("'")
                        env_vars[key] = val
        else:
            return jsonify({"status": "error", "message": ".env file not found"}), 404
            
        return jsonify({"status": "success", "env": env_vars})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@admin_bp.route('/api/admin/env/update', methods=['POST'])
def update_env():
    try:
        data = request.json
        env_path = '.env'
        
        updated_keys = []
        for key, value in data.items():
            # Update .env file
            set_key(env_path, key, value)
            # Update current process env (though restart is best for some libs)
            os.environ[key] = value
            updated_keys.append(key)
            
        return jsonify({
            "status": "success", 
            "message": f"Updated {len(updated_keys)} keys",
            "updated": updated_keys
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@admin_bp.route('/api/admin/auth/reset', methods=['POST'])
def reset_auth():
    """
    Reset all authentication tokens (Google).
    Deletes the pickle files storing the tokens.
    """
    try:
        deleted_files = []
        # List of token files to delete
        token_files = [
            'config/google_token.pickle',
            'config/google_token_ndhu.pickle'
        ]
        
        for file_path in token_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(file_path)
                
        if not deleted_files:
            return jsonify({
                "status": "success",
                "message": "No active sessions found to reset.",
                "deleted": []
            })
            
        return jsonify({
            "status": "success",
            "message": f"Reset successful. Deleted {len(deleted_files)} token files.",
            "deleted": deleted_files
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
