from flask import Blueprint, jsonify, request, session, redirect, render_template
import extensions # Import module to allow dynamic access to globals
import pandas as pd
from io import BytesIO
from flask import send_file
import os

classroom_bp = Blueprint('classroom', __name__)

@classroom_bp.route('/classroom')
def classroom_dashboard():
    """
    Render the Google Classroom management dashboard.
    
    Returns:
        Rendered HTML template 'classroom.html'.
    """
    return render_template('classroom.html')

@classroom_bp.route('/api/classroom/auth/start', methods=['GET'])
def auth_start():
    if not extensions.classroom_integration:
        return jsonify({"status": "error", "message": "Classroom 模組未初始化"}), 500

    try:
        # Define callback URL (adjust port/domain as needed for production)
        redirect_uri = 'http://localhost:5001/api/classroom/auth/callback'
        
        flow = extensions.classroom_integration.get_oauth_flow(redirect_uri=redirect_uri)
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent select_account'
        )
        
        session['classroom_oauth_state'] = state
        
        return jsonify({
            "status": "success",
            "authorization_url": auth_url
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Auth Start Error: {str(e)}"}), 500

@classroom_bp.route('/api/classroom/auth/callback', methods=['GET'])
def auth_callback():
    if not extensions.classroom_integration:
        return "Integration not initialized", 500
        
    try:
        state = session.get('classroom_oauth_state')
        redirect_uri = 'http://localhost:5001/api/classroom/auth/callback'
        
        flow = extensions.classroom_integration.get_oauth_flow(redirect_uri=redirect_uri)
        flow.fetch_token(authorization_response=request.url)
        
        creds = flow.credentials
        extensions.classroom_integration.set_credentials(creds)
        
        return redirect('/classroom')
    except Exception as e:
        return f"Authentication failed: {str(e)}", 500

@classroom_bp.route('/api/classroom/courses')
def list_courses():
    """
    List all active courses for the current user.
    
    Query Params:
        role (str): 'teacher' or 'student' (default: 'teacher').
        
    Returns:
        JSON: List of courses or error message.
    """
    if not extensions.classroom_integration:
        return jsonify({"status": "error", "message": "Google Classroom integration not initialized"}), 500
        
    role = request.args.get('role', 'teacher')
    
    # The original code had 'all' role logic, but the provided snippet simplifies it.
    # Assuming get_my_courses can handle the role parameter as needed.
    courses = extensions.classroom_integration.get_my_courses(role=role)
    
    if courses is None:
        return jsonify({"status": "error", "message": "尚未連接 Google Classroom", "needs_auth": True}), 401
        
    return jsonify({
        "status": "success",
        "count": len(courses),
        "role": role,
        "courses": courses
    })

@classroom_bp.route('/api/classroom/students/<course_id>')
def list_students(course_id):
    """
    List students for a specific course.
    
    Args:
        course_id (str): Google Classroom Course ID.
        
    Returns:
        JSON: List of students or error message.
    """
    if not extensions.classroom_integration:
        return jsonify({"status": "error", "message": "Google Classroom integration not initialized"}), 500
        
    students = extensions.classroom_integration.get_students(course_id)
    return jsonify({
        "status": "success",
        "count": len(students),
        "students": students
    })

@classroom_bp.route('/api/classroom/students/<course_id>/export', methods=['GET'])
def export_students(course_id):
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    course_name = request.args.get('course_name', course_id)
    try:
        excel_io = extensions.classroom_integration.export_students_to_excel(course_id, course_name)
        return send_file(
            excel_io,
            as_attachment=True,
            download_name=f"{course_name}_students.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@classroom_bp.route('/api/classroom/students/export_all', methods=['GET'])
def export_all_students():
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    role = request.args.get('role', 'teacher')
    try:
        if role == 'all':
            courses = extensions.classroom_integration.get_courses()
        else:
            courses = extensions.classroom_integration.get_my_courses(role)
            
        file_path = extensions.classroom_integration.export_all_students_to_excel(courses)
        if file_path and os.path.exists(file_path):
             return send_file(
                file_path,
                as_attachment=True,
                download_name=f"All_Students_{role}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
             return jsonify({"status": "error", "message": "導出失敗"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@classroom_bp.route('/api/classroom/topics/<course_id>', methods=['GET'])
def get_topics(course_id):
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    topics = extensions.classroom_integration.get_topics(course_id)
    return jsonify({"status": "success", "topics": topics})

@classroom_bp.route('/api/classroom/topics/create', methods=['POST'])
def create_topics():
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    data = request.json
    created = extensions.classroom_integration.create_topics(
        data['course_id'], 
        data.get('num_weeks', 18), 
        data.get('prefix', 'Week')
    )
    return jsonify({"status": "success", "message": f"已建立 {len(created)} 個主題"})

@classroom_bp.route('/api/classroom/assignment/create', methods=['POST'])
def create_assignment():
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    
    # Handle both JSON and Form Data
    if request.content_type.startswith('multipart/form-data'):
        data = request.form
        file = request.files.get('file')
    else:
        data = request.json
        file = None

    course_id = data.get('course_id')
    course_name = data.get('course_name', 'Unknown Course') # Frontend should pass this
    
    # File Upload Handling with Folder Structure
    drive_file_ids = []
    if file:
        filename = file.filename
        upload_path = os.path.join('/tmp', filename)
        file.save(upload_path)
        
        # Determine Folder: Classroom/<Course>/Assignments
        folder_id = extensions.classroom_integration.ensure_course_folder_structure(course_name, "Assignments")
        
        file_id = extensions.classroom_integration.upload_file_to_drive(upload_path, parent_id=folder_id)
        if file_id:
            drive_file_ids.append(file_id)
        
        # Cleanup temp file
        if os.path.exists(upload_path):
            os.remove(upload_path)

    # Pre-process max_points
    max_pts = data.get('max_points')
    if max_pts == '' or max_pts is None: max_pts = None
    
    # Handle due date/time parsing if JSON string
    import json
    due_date = data.get('due_date')
    if isinstance(due_date, str):
        try: due_date = json.loads(due_date)
        except: due_date = None
        
    due_time = data.get('due_time')
    if isinstance(due_time, str):
        try: due_time = json.loads(due_time)
        except: due_time = None

    # Handle Student IDs (FormData sends same key multiple times for lists, usually)
    # However, our frontend sends a comma-separated string or multiple keys.
    # If using FormData.append('student_ids', id), getlist works.
    student_ids = []
    if request.content_type.startswith('multipart/form-data'):
         student_ids = request.form.getlist('student_ids')
    else:
         student_ids = data.get('student_ids')

    res = extensions.classroom_integration.create_assignment(
        course_id=course_id,
        title=data['title'],
        description=data.get('description', ''),
        max_points=max_pts,
        topic_id=data.get('topic_id'),
        state=data.get('state', 'PUBLISHED'),
        due_date=due_date,
        due_time=due_time,
        grade_category_id=data.get('grade_category_id'),
        assignee_mode=data.get('assignee_mode', 'ALL_STUDENTS'),
        student_ids=student_ids, 
        drive_file_ids=drive_file_ids
    )
    
    if res:
        return jsonify({"status": "success", "message": "作業已建立", "data": res})
    else:
        return jsonify({"status": "error", "message": "建立作業失敗"}), 500

@classroom_bp.route('/api/classroom/material/create', methods=['POST'])
def create_material():
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    
    # Handle both JSON and Form Data
    if request.content_type.startswith('multipart/form-data'):
        data = request.form
        file = request.files.get('file')
    else:
        data = request.json
        file = None
        
    course_id = data.get('course_id')
    course_name = data.get('course_name', 'Unknown Course')

    # File Upload to 'Materials' folder
    file_id = None
    if file:
        filename = file.filename
        upload_path = os.path.join('/tmp', filename)
        file.save(upload_path)
        
        # Determine Folder
        folder_id = extensions.classroom_integration.ensure_course_folder_structure(course_name, "Materials")
        file_id = extensions.classroom_integration.upload_file_to_drive(upload_path, parent_id=folder_id)
        
        if os.path.exists(upload_path):
            os.remove(upload_path)

    res = extensions.classroom_integration.create_course_material(
        course_id=course_id,
        title=data['title'],
        description=data.get('description', ''),
        topic_id=data.get('topic_id'),
        link_url=data.get('link'),
        file_id=file_id,
        state=data.get('state', 'PUBLISHED')
    )
    if res:
         return jsonify({"status": "success", "message": "課件已發布", "data": res})
    else:
        return jsonify({"status": "error", "message": "發布課件失敗"}), 500

@classroom_bp.route('/api/classroom/coursework/<course_id>', methods=['GET'])
def get_coursework(course_id):
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    work = extensions.classroom_integration.get_all_coursework(course_id)
    return jsonify({"status": "success", "coursework": work})

@classroom_bp.route('/api/classroom/submission_stats/<course_id>/<coursework_id>', methods=['GET'])
def get_submission_stats(course_id, coursework_id):
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    stats = extensions.classroom_integration.get_coursework_submissions(course_id, coursework_id)
    return jsonify({"status": "success", "stats": stats})

@classroom_bp.route('/api/classroom/dashboard/<course_id>', methods=['GET'])
def get_course_dashboard(course_id):
    if not extensions.classroom_integration: return jsonify({"status": "error"}), 500
    try:
        data = extensions.classroom_integration.get_course_full_view(course_id)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
         return jsonify({"status": "error", "message": str(e)}), 500
