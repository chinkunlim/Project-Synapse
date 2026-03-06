from functools import wraps
from flask import request
from werkzeug.exceptions import BadRequest

def validate_json_params(*required_params):
    """
    Decorator to ensure that the required parameters are present in the JSON payload.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise BadRequest("Request must be JSON")
            
            data = request.get_json()
            missing = [p for p in required_params if p not in data or data[p] in (None, "")]
            
            if missing:
                raise BadRequest(f"Missing required parameters: {', '.join(missing)}")
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_form_params(*required_params):
    """
    Decorator to ensure that the required parameters are present in either form data or JSON.
    Useful for endpoints like file uploads that might use multipart/form-data.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.content_type and request.content_type.startswith('multipart/form-data'):
                data = request.form
            elif request.is_json:
                data = request.get_json()
            else:
                data = request.values
                
            missing = [p for p in required_params if p not in data or data[p] in (None, "")]
            
            if missing:
                raise BadRequest(f"Missing required parameters: {', '.join(missing)}")
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
