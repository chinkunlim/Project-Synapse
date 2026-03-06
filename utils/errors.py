from flask import jsonify
from werkzeug.exceptions import HTTPException
from utils.logger import logger
import uuid

def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Generate a unique trace ID for debugging
        trace_id = str(uuid.uuid4())
        
        # Log the full traceback
        logger.error(f"Trace ID: {trace_id} | Exception: {e}", exc_info=True)
        
        # Pass through HTTP errors
        if isinstance(e, HTTPException):
            return jsonify({
                "status": "error",
                "message": e.description,
                "trace_id": trace_id
            }), e.code

        # For non-HTTP exceptions, return 500
        return jsonify({
            "status": "error",
            "message": "伺服器發生非預期錯誤，請聯繫系統管理員",
            "trace_id": trace_id,
            "error_detail": str(e) # In development, you might want this. In production, maybe hide it. Leaving for now since previous behavior was returning str(e)
        }), 500
