# Force Reload: 2025-12-28 v4
from flask import Flask, request, Response
import os
from extensions import init_extensions
from config.config import config
from routes.main_routes import main_bp
from routes.notion_routes import notion_bp
from routes.ndhu_routes import ndhu_bp
from routes.classroom_routes import classroom_bp
from routes.thesis_routes import thesis_bp
from routes.admin_routes import admin_bp
from routes.n8n_routes import n8n_bp

def create_app(config_name='default'):
    """
    Factory function to create the Flask application.
    
    Args:
        config_name (str): The configuration mode ('development', 'production').
    """
    app = Flask(__name__)
    
    # Load Configuration
    app.config.from_object(config[config_name])
    
    # Apply special env vars from config
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = app.config.get('OAUTHLIB_INSECURE_TRANSPORT', '0')
    
    # Initialize Data Directory
    app.config['DATA_DIR'].mkdir(exist_ok=True)
    
    # Initialize Extensions
    init_extensions()
    
    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(notion_bp)
    app.register_blueprint(ndhu_bp)
    app.register_blueprint(classroom_bp)
    app.register_blueprint(thesis_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(n8n_bp)
    
    # Global Security Headers
    @app.after_request
    def add_security_headers(response: Response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # HSTS (Strict-Transport-Security) - Only valid on HTTPS, but good practice to add
        if not app.debug:
             response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
        
    return app

# Check ENV to select config
env_name = os.getenv('FLASK_ENV', 'default')
app = create_app(env_name)

if __name__ == '__main__':
    # Use strict_slashes=False to forgive missing/extra slashes
    app.url_map.strict_slashes = False
    app.run(host='0.0.0.0', port=5001)