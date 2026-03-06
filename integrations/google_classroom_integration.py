"""
Google Classroom Integration Module
Provides functionality for course management, student list export, topic creation, coursework publication, etc.
"""

import os
import pickle
import json
from io import BytesIO
from typing import List, Dict, Optional
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import pandas as pd
import threading


class GoogleClassroomIntegration:
    """Google Classroom API Integration Class"""
    
    # OAuth 2.0 權限範圍
    SCOPES = [
        'https://www.googleapis.com/auth/classroom.courses.readonly',
        'https://www.googleapis.com/auth/classroom.rosters.readonly',
        'https://www.googleapis.com/auth/classroom.profile.emails',
        'https://www.googleapis.com/auth/classroom.topics',
        'https://www.googleapis.com/auth/classroom.courseworkmaterials',
        'https://www.googleapis.com/auth/classroom.coursework.me',
        'https://www.googleapis.com/auth/classroom.coursework.students',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, credentials_path: str = 'config/google_credentials.json'):
        """
        Initialize Google Classroom Integration
        
        Args:
            credentials_path: Path to OAuth 2.0 credentials JSON file
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path('config/google_token.pickle')
        self.creds = None
        self._thread_local = threading.local()
        
        # 嘗試自動載入 Token
        self._try_load_token()
        
    def _try_load_token(self):
        """Try to load Token from file"""
        try:
            if self.token_path.exists():
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
                
                if self.creds:
                    # 如果過期且有 refresh_token，嘗試刷新
                    if self.creds.expired and self.creds.refresh_token:
                        try:
                            self.creds.refresh(Request())
                            # 刷新後保存新的 Token
                            with open(self.token_path, 'wb') as token:
                                pickle.dump(self.creds, token)
                        except Exception as e:
                             print(f"⚠️ Classroom Token 刷新失敗: {e}")
                             self.creds = None


                    if self.creds and self.creds.valid:
                        # 驗證成功，延遲建立 service
                        print("✅ Google Classroom Token 載入成功")
        except Exception as e:
            print(f"⚠️ Token 載入失敗: {e}")

    def _get_classroom_service(self):
        """Get Classroom Service for current thread"""
        if not self.creds: return None
        if not hasattr(self._thread_local, 'classroom'):
            try:
                self._thread_local.classroom = build('classroom', 'v1', credentials=self.creds)
            except Exception as e:
                print(f"❌ 建立 Thread-Local Classroom Service 失敗: {e}")
                return None
        return self._thread_local.classroom

    def _get_drive_service(self):
        """Get Drive Service for current thread"""
        if not self.creds: return None
        if not hasattr(self._thread_local, 'drive'):
            try:
                self._thread_local.drive = build('drive', 'v3', credentials=self.creds)
            except Exception as e:
                print(f"❌ 建立 Thread-Local Drive Service 失敗: {e}")
                return None
        return self._thread_local.drive

    @property
    def classroom_service(self):
        """Property to access the thread-local classroom service (backward compatibility)"""
        return self._get_classroom_service()

    @property
    def drive_service(self):
        """Property to access the thread-local drive service (backward compatibility)"""
        return self._get_drive_service()

    def authenticate(self) -> bool:
        """
        Execute OAuth 2.0 Authentication Flow
        
        Returns:
            bool: Whether authentication was successful
        """
        try:
            # 載入已存在的憑證
            if self.token_path.exists():
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # 如果憑證無效或不存在，執行認證流程
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        raise FileNotFoundError(
                            f"OAuth 憑證檔案不存在: {self.credentials_path}\n"
                            "請到 Google Cloud Console 下載憑證並放置於 config/ 資料夾"
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), 
                        self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                # 儲存憑證供下次使用
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            # 建立服務物件 (清除 thread local cache)
            if hasattr(self._thread_local, 'classroom'): del self._thread_local.classroom
            if hasattr(self._thread_local, 'drive'): del self._thread_local.drive
            
            return True
            
        except Exception as e:
            print(f"❌ 認證失敗: {e}")
            return False

    def get_oauth_flow(self, redirect_uri: str = None) -> Flow:
        """
        Create Web OAuth Flow Object
        
        Args:
            redirect_uri: Callback URL
        """
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"Credential file not found: {self.credentials_path}")
            
        return Flow.from_client_secrets_file(
            str(self.credentials_path),
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )

    def set_credentials(self, creds: Credentials) -> bool:
        """
        Initialize integration with existing Credentials and persist them.

        Args:
            creds: Exchanged Google OAuth credentials

        Returns:
            bool: Whether initialization was successful
        """
        try:
            self.creds = creds

            # 儲存憑證供下次使用
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

            # 建立服務物件 (清除 thread local cache)
            if hasattr(self._thread_local, 'classroom'): del self._thread_local.classroom
            if hasattr(self._thread_local, 'drive'): del self._thread_local.drive

            return True
        except Exception as e:
            print(f"❌ 初始化憑證失敗: {e}")
            return False
    
    def get_courses(self) -> Optional[List[Dict]]:
        """
        Get all courses list
        
        Returns:
            List[Dict]: List of course info including id, name, section etc. Returns None if not authenticated.
        """
        try:
            service = self._get_classroom_service()
            if not service:
                return None

            results = service.courses().list(
                pageSize=100,
                courseStates=['ACTIVE']
            ).execute()
            
            courses = results.get('courses', [])
            
            return [{
                'id': course['id'],
                'name': course['name'],
                'section': course.get('section', ''),
                'descriptionHeading': course.get('descriptionHeading', ''),
                'room': course.get('room', ''),
                'ownerId': course['ownerId'],
                'creationTime': course['creationTime'],
                'updateTime': course['updateTime'],
                'enrollmentCode': course.get('enrollmentCode', ''),
                'courseState': course['courseState'],
                'alternateLink': course['alternateLink']
            } for course in courses]
            
        except Exception as e:
            print(f"❌ 獲取課程列表失敗: {e}")
            return []

    def get_my_courses(self, role: str = 'teacher') -> Optional[List[Dict]]:
        """
        List courses related to the current account.

        Args:
            role: 'teacher' or 'student'

        Returns:
            List[Dict]: List of course info. Returns None if not authenticated.
        """
        try:
            service = self._get_classroom_service()
            if not service:
                return None

            kwargs = {
                'pageSize': 100,
                'courseStates': ['ACTIVE']
            }
            if role == 'teacher':
                kwargs['teacherId'] = 'me'
            elif role == 'student':
                kwargs['studentId'] = 'me'

            results = service.courses().list(**kwargs).execute()
            courses = results.get('courses', [])

            return [{
                'id': course['id'],
                'name': course['name'],
                'section': course.get('section', ''),
                'descriptionHeading': course.get('descriptionHeading', ''),
                'room': course.get('room', ''),
                'ownerId': course['ownerId'],
                'creationTime': course['creationTime'],
                'updateTime': course['updateTime'],
                'enrollmentCode': course.get('enrollmentCode', ''),
                'courseState': course['courseState'],
                'alternateLink': course['alternateLink']
            } for course in courses]
        except Exception as e:
            print(f"❌ 獲取我的課程列表失敗: {e}")
            return []

    def get_grade_categories(self, course_id: str) -> List[Dict]:
        """
        Get grade categories for a course
        """
        try:
            service = self._get_classroom_service()
            if not service: return []
            course = service.courses().get(id=course_id).execute()
            return course.get('gradeCategories', [])
        except Exception as e:
            print(f"❌ 獲取成績類別失敗: {e}")
            return []

    def export_all_students_to_excel(self, courses: List[Dict], filename: str = 'all_students') -> str:
        """
        Export student lists of multiple courses to a single Excel file (multiple sheets)

        Args:
            courses: List of courses, must contain 'id' and 'name'
            filename: Output filename (without extension)

        Returns:
            str: Path to the generated Excel file
        """
        try:
            output_path = f"/tmp/{filename}.xlsx"
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                service = self._get_classroom_service()
                if not service: return ""
                
                for course in courses:
                    course_id = course['id']
                    course_name = course.get('name', f"course_{course_id}")
                    # 讀取學生名單
                    results = service.courses().students().list(
                        courseId=course_id,
                        pageSize=200
                    ).execute()
                    students = results.get('students', [])
                    rows = []
                    for s in students:
                        profile = s.get('profile', {})
                        name_obj = profile.get('name', {}) if isinstance(profile.get('name'), dict) else {}
                        full_name = name_obj.get('fullName') or profile.get('name') or ''
                        rows.append({
                            'Name': full_name,
                            'Email': profile.get('emailAddress', ''),
                            'UserId': profile.get('id', ''),
                        })
                    df = pd.DataFrame(rows)
                    if df.empty:
                        df = pd.DataFrame([{'Name': '', 'Email': '', 'UserId': ''}])
                    # 工作表名稱避免過長
                    sheet_name = course_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    # 調整欄寬
                    worksheet = writer.sheets[sheet_name]
                    worksheet.set_column('A:A', 24)
                    worksheet.set_column('B:B', 30)
                    worksheet.set_column('C:C', 24)
            return output_path
        except Exception as e:
            print(f"❌ 導出所有學生名單失敗: {e}")
            return ""

    def create_topics_from_names(self, course_id: str, names: List[str]) -> List[Dict]:
        """
        Create topics from a list of names

        Args:
            course_id: Course ID
            names: List of topic names

        Returns:
            List[Dict]: Information of created topics
        """
        try:
            service = self._get_classroom_service()
            if not service: return []
            
            created = []
            for name in names:
                body = {"name": name}
                topic = service.courses().topics().create(
                    courseId=course_id,
                    body=body
                ).execute()
                created.append(topic)
            return created
        except Exception as e:
            print(f"❌ 依名稱建立主題失敗: {e}")
            return []

    def create_assignment(self, course_id: str, title: str, description: str = "", max_points: Optional[int] = None,
                           due_date: Optional[Dict] = None, due_time: Optional[Dict] = None, topic_id: Optional[str] = None,
                           state: str = 'PUBLISHED', drive_file_ids: Optional[List[str]] = None, links: Optional[List[str]] = None,
                           assignee_mode: str = 'ALL_STUDENTS', student_ids: Optional[List[str]] = None,
                           grade_category_id: Optional[str] = None, grading_period_id: Optional[str] = None) -> Optional[Dict]:
        """
        Create Assignment (CourseWork)

        Args:
            course_id: Course ID
            title: Assignment title
            description: Assignment description
            max_points: Maximum points
            due_date: Due date, e.g. {"year":2025,"month":1,"day":15}
            topic_id: Topic ID (optional)
            state: State 'PUBLISHED' or 'DRAFT'

        Returns:
            Optional[Dict]: Created assignment object
        """
        try:
            body = {
                "title": title,
                "description": description,
                "workType": "ASSIGNMENT",
                "state": state
            }
            if max_points is not None:
                body["maxPoints"] = int(max_points)
            if due_date:
                body["dueDate"] = due_date
            if due_time:
                body["dueTime"] = due_time
            if topic_id:
                body["topicId"] = topic_id
            if grade_category_id:
                body["gradeCategoryId"] = grade_category_id
            if grading_period_id:
                body["gradingPeriodId"] = grading_period_id

            # 附件材料
            materials = []
            if drive_file_ids:
                for fid in drive_file_ids:
                    if fid:
                        materials.append({
                            "driveFile": {
                                "driveFile": {"id": fid}
                            }
                        })
            if links:
                for url in links:
                    if url:
                        materials.append({
                            "link": {"url": url}
                        })
            if materials:
                body["materials"] = materials

            # 指派對象
            if assignee_mode == 'INDIVIDUAL_STUDENTS' and student_ids:
                body["assigneeMode"] = 'INDIVIDUAL_STUDENTS'
                body["individualStudentsOptions"] = {"studentIds": student_ids}
            else:
                body["assigneeMode"] = 'ALL_STUDENTS'
            
            service = self._get_classroom_service()
            if not service: return None
            
            coursework = service.courses().courseWork().create(
                courseId=course_id,
                body=body
            ).execute()
            return coursework
        except Exception as e:
            print(f"❌ 建立作業失敗: {e}")
            return None
    
    def get_students(self, course_id: str) -> List[Dict]:
        """
        Get student list for a specific course
        
        Args:
            course_id: Course ID
            
        Returns:
            List[Dict]: List of student info
        """
        try:
            service = self._get_classroom_service()
            if not service: return []
            
            results = service.courses().students().list(
                courseId=course_id,
                pageSize=100
            ).execute()
            
            students = results.get('students', [])
            
            return [{
                'courseId': student['courseId'],
                'userId': student['userId'],
                'profile': {
                    'id': student['profile']['id'],
                    'name': student['profile']['name']['fullName'],
                    'emailAddress': student['profile'].get('emailAddress', ''),
                    'photoUrl': student['profile'].get('photoUrl', '')
                }
            } for student in students]
            
        except Exception as e:
            print(f"❌ 獲取學生名單失敗: {e}")
            return []
    
    def export_students_to_excel(self, course_id: str, course_name: str) -> BytesIO:
        """
        Export student list to an Excel file
        
        Args:
            course_id: Course ID
            course_name: Course Name (used for filename)
            
        Returns:
            BytesIO: Binary stream of the Excel file
        """
        students = self.get_students(course_id)
        
        if not students:
            raise ValueError("無學生資料可導出")
        
        # 轉換為 DataFrame
        data = []
        for student in students:
            data.append({
                '姓名': student['profile']['name'],
                'Email': student['profile']['emailAddress'],
                '用戶 ID': student['userId'],
                '課程 ID': student['courseId']
            })
        
        df = pd.DataFrame(data)
        
        # 寫入 Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='學生名單', index=False)
            
            # 調整欄寬
            worksheet = writer.sheets['學生名單']
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(idx, idx, max_len)
        
        output.seek(0)
        return output
    
    def create_topics(self, course_id: str, num_weeks: int, prefix: str = "Week") -> List[Dict]:
        """
        Batch create topics for N weeks
        
        Args:
            course_id: Course ID
            num_weeks: Number of weeks
            prefix: Topic name prefix (default "Week")
            
        Returns:
            List[Dict]: List of created topics
        """
        created_topics = []
        
        try:
            service = self._get_classroom_service()
            if not service: return created_topics

            # 從最後一項開始建立（反向）
            for week in range(num_weeks, 0, -1):
                topic_name = f"{prefix} {week}"
                
                topic = service.courses().topics().create(
                    courseId=course_id,
                    body={'name': topic_name}
                ).execute()
                
                created_topics.append({
                    'topicId': topic['topicId'],
                    'name': topic['name'],
                    'courseId': topic['courseId'],
                    'updateTime': topic['updateTime']
                })
                
                print(f"✅ 已建立主題: {topic_name}")
            
            return created_topics
            
        except Exception as e:
            print(f"❌ 建立主題失敗: {e}")
            return created_topics
    
    def get_topics(self, course_id: str) -> List[Dict]:
        """
        Get all topics of a course
        
        Args:
            course_id: Course ID
            
        Returns:
            List[Dict]: List of topics
        """
        try:
            service = self._get_classroom_service()
            if not service: return []
            
            results = service.courses().topics().list(
                courseId=course_id,
                pageSize=100
            ).execute()
            
            topics = results.get('topic', [])
            
            return [{
                'topicId': topic['topicId'],
                'name': topic['name'],
                'courseId': topic['courseId'],
                'updateTime': topic['updateTime']
            } for topic in topics]
            
        except Exception as e:
            print(f"❌ 獲取主題列表失敗: {e}")
            return []
    
    def _find_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find a folder in a specific parent folder, create if not exists

        Args:
            folder_name: Folder name
            parent_id: Parent folder ID (Root if None)

        Returns:
            str: Folder ID
        """
        try:
            service = self._get_drive_service()
            if not service: return None

            q = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            if parent_id:
                q += f" and '{parent_id}' in parents"
            
            results = service.files().list(q=q, fields="files(id)").execute()
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            
            # create
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                metadata['parents'] = [parent_id]
                
            if parent_id:
                metadata['parents'] = [parent_id]
                
            folder = service.files().create(body=metadata, fields='id').execute()
            return folder.get('id')
            
        except Exception as e:
            print(f"❌ 尋找/建立資料夾失敗 ({folder_name}): {e}")
            return None

    def ensure_course_folder_structure(self, course_name: str, subfolder: str) -> Optional[str]:
        """
        Ensure structure Classroom/<Course>/<Subfolder> exists in Drive

        Args:
            course_name: Course Name
            subfolder: Subfolder Name (Materials or Assignments)

        Returns:
            str: Target folder ID
        """
        # 1. Ensure 'Classroom' root folder
        classroom_id = self._find_or_create_folder("Classroom")
        if not classroom_id: return None
        
        # 2. Ensure Course folder
        course_folder_id = self._find_or_create_folder(course_name, parent_id=classroom_id)
        if not course_folder_id: return None
        
        # 3. Ensure Target Subfolder
        target_id = self._find_or_create_folder(subfolder, parent_id=course_folder_id)
        return target_id

    def upload_file_to_drive(self, file_path: str, file_name: str = None, parent_id: str = None) -> Optional[str]:
        """
        Upload file to Google Drive

        Args:
            file_path: Local file path
            file_name: File name in Drive
            parent_id: Target folder ID to upload to

        Returns:
            Optional[str]: Drive File ID, returns None if failed
        """
        try:
            if not file_name:
                file_name = Path(file_path).name

            file_metadata = {'name': file_name}
            if parent_id:
                file_metadata['parents'] = [parent_id]
                
            media = MediaFileUpload(file_path, resumable=True)

            service = self._get_drive_service()
            if not service: return None

            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            file_id = file.get('id')
            print(f"✅ 檔案已上傳至 Drive: {file_name} (ID: {file_id})")

            return file_id
        except Exception as e:
            print(f"❌ 上傳檔案失敗: {e}")
            return None

    def list_drive_files(self, query: Optional[str] = None, page_size: int = 50) -> List[Dict]:
        """
        Get list of Google Drive files (excluding folders)

        Args:
            query: Drive search query string (None for no filter)
            page_size: Number of items per page

        Returns:
            List[Dict]: File information
        """
        try:
            q = "trashed = false and mimeType != 'application/vnd.google-apps.folder'"
            if query:
                # 基本名稱搜尋
                safe_query = query.replace("'", "\\'")
                q += f" and name contains '{safe_query}'"
            
            service = self._get_drive_service()
            if not service: return []

            results = service.files().list(
                q=q,
                pageSize=page_size,
                fields="files(id, name, mimeType, modifiedTime, owners(emailAddress, displayName))"
            ).execute()
            return results.get('files', [])
        except Exception as e:
            print(f"❌ 讀取 Drive 檔案失敗: {e}")
            return []
    
    def create_course_material(
        self, 
        course_id: str, 
        title: str, 
        description: str = "",
        topic_id: str = None,
        file_id: str = None,
        link_url: str = None,
        state: str = "PUBLISHED"
    ) -> Optional[Dict]:
        """
        Publish Course Material (can include Drive files or external links)
        
        Args:
            course_id: Course ID
            title: Material Title
            description: Material Description
            topic_id: Topic ID (optional)
            file_id: Google Drive File ID (optional)
            link_url: External Link URL (optional)
            state: Publish state ("PUBLISHED" or "DRAFT")
            
        Returns:
            Optional[Dict]: Created material info
        """
        try:
            body = {
                'title': title,
                'description': description,
                'state': state,
                'materials': []
            }
            
            if topic_id:
                body['topicId'] = topic_id
            
            # 添加 Drive 檔案
            if file_id:
                body['materials'].append({
                    'driveFile': {
                        'driveFile': {
                            'id': file_id
                        },
                        'shareMode': 'VIEW'
                    }
                })
            
            # 添加外部連結
            if link_url:
                body['materials'].append({
                    'link': {
                        'url': link_url
                    }
                })
            
            service = self._get_classroom_service()
            if not service: return None
            
            material = service.courses().courseWorkMaterials().create(
                courseId=course_id,
                body=body
            ).execute()
            
            print(f"✅ 課件已發布: {title}")
            
            return {
                'id': material['id'],
                'courseId': material['courseId'],
                'title': material['title'],
                'state': material['state'],
                'alternateLink': material['alternateLink'],
                'creationTime': material['creationTime'],
                'updateTime': material['updateTime']
            }
            
        except Exception as e:
            print(f"❌ 發布課件失敗: {e}")
            return None
    
    def get_coursework_submissions(self, course_id: str, coursework_id: str) -> Dict:
        """
        Get student submission progress stats for a CourseWork
        
        Args:
            course_id: Course ID
            coursework_id: CourseWork ID
            
        Returns:
            Dict: Dictionary containing stats for each state
        """
        try:
            service = self._get_classroom_service()
            if not service: return {'total': 0, 'error': "Authentication failed"}

            results = service.courses().courseWork().studentSubmissions().list(
                courseId=course_id,
                courseWorkId=coursework_id,
                pageSize=100
            ).execute()
            
            submissions = results.get('studentSubmissions', [])
            
            # 統計各狀態
            stats = {
                'total': len(submissions),
                'new': 0,
                'created': 0,
                'turned_in': 0,
                'returned': 0,
                'reclaimed_by_student': 0,
                'late': 0
            }
            
            for submission in submissions:
                state = submission.get('state', 'NEW')
                stats[state.lower()] += 1
                
                if submission.get('late', False):
                    stats['late'] += 1
            
            # 計算百分比
            if stats['total'] > 0:
                stats['turned_in_percentage'] = round(stats['turned_in'] / stats['total'] * 100, 2)
                stats['late_percentage'] = round(stats['late'] / stats['total'] * 100, 2)
            else:
                stats['turned_in_percentage'] = 0
                stats['late_percentage'] = 0
            
            return stats
            
        except Exception as e:
            print(f"❌ 獲取呈交進度失敗: {e}")
            return {'total': 0, 'error': str(e)}
    
    def get_all_coursework(self, course_id: str) -> List[Dict]:
        """
        Get all CourseWork for a course
        
        Args:
            course_id: Course ID
            
        Returns:
            List[Dict]: List of CourseWork
        """
        try:
            service = self._get_classroom_service()
            if not service: return []

            results = service.courses().courseWork().list(
                courseId=course_id,
                orderBy='dueDate desc',
                pageSize=100
            ).execute()
            
            return results.get('courseWork', [])
            
        except Exception as e:
            print(f"❌ 獲取作業列表失敗: {e}")
            return []

    def get_course_full_view(self, course_id: str) -> Dict:
        """
        Aggregate all data for a course dashboard using Google Batch API.
        Step 1: Batch fetch Metadata (Students, Topics, CourseInfo, CourseWork).
        Step 2: Batch fetch Stats for the retrieved CourseWork.
        """
        from googleapiclient.http import BatchHttpRequest

        data = {
            "students": [], "topics": [], "gradeCategories": [], 
            "coursework": [], "stats": {}
        }
        
        if not self.creds: return data
        service = self._get_classroom_service()
        if not service: return data

        # --- Step 1: Metadata Batch ---
        def cb_students(request_id, response, exception):
            if exception: print(f"Error fetching students: {exception}")
            else: 
                data["students"] = [{
                    'courseId': s['courseId'], 'userId': s['userId'],
                    'profile': {
                        'id': s['profile']['id'],
                        'name': s['profile']['name']['fullName'],
                        'emailAddress': s['profile'].get('emailAddress', ''),
                        'photoUrl': s['profile'].get('photoUrl', '')
                    }
                } for s in response.get('students', [])]

        def cb_topics(request_id, response, exception):
            if exception: print(f"Error fetching topics: {exception}")
            else: 
                data["topics"] = [{
                    'topicId': t['topicId'], 'name': t['name'],
                    'courseId': t['courseId'], 'updateTime': t['updateTime']
                } for t in response.get('topic', [])]

        def cb_course(request_id, response, exception):
            if exception: print(f"Error fetching course info: {exception}")
            else: data["gradeCategories"] = response.get('gradeCategories', [])

        def cb_coursework(request_id, response, exception):
            if exception: print(f"Error fetching coursework: {exception}")
            else: 
                data["coursework"] = [{
                    'id': w['id'], 'courseId': w['courseId'], 'title': w['title'],
                    'description': w.get('description', ''), 'state': w['state'],
                    'alternateLink': w['alternateLink'], 'creationTime': w['creationTime'],
                    'updateTime': w['updateTime'], 'dueDate': w.get('dueDate'),
                    'dueTime': w.get('dueTime'), 'maxPoints': w.get('maxPoints'),
                    'workType': w['workType']
                } for w in response.get('courseWork', [])]

        batch1 = service.new_batch_http_request()
        
        # Add requests to Batch 1
        batch1.add(service.courses().students().list(courseId=course_id, pageSize=100), callback=cb_students)
        batch1.add(service.courses().topics().list(courseId=course_id, pageSize=100), callback=cb_topics)
        batch1.add(service.courses().get(id=course_id), callback=cb_course)
        batch1.add(service.courses().courseWork().list(courseId=course_id, pageSize=100), callback=cb_coursework)
        
        try:
            batch1.execute()
        except Exception as e:
            print(f"Batch 1 execution failed: {e}")
            return data

        # --- Step 2: Stats Batch (Dependent on CourseWork) ---
        if not data["coursework"]: return data

        submission_stats = {}
        
        def cb_stats(request_id, response, exception):
            if exception:
                submission_stats[request_id] = {'error': str(exception)}
            else:
                subs = response.get('studentSubmissions', [])
                total = len(subs)
                stats = {'total': total, 'turned_in': 0, 'new': 0, 'created': 0, 
                         'reclaimed_by_student': 0, 'returned': 0, 'late': 0}
                
                for s in subs:
                    state = s.get('state', 'NEW').lower()
                    stats[state] = stats.get(state, 0) + 1
                    if s.get('late'): stats['late'] += 1
                
                if total > 0:
                    stats['turned_in_percentage'] = round(stats['turned_in'] / total * 100, 2)
                else:
                    stats['turned_in_percentage'] = 0
                
                submission_stats[request_id] = stats

        batch2 = service.new_batch_http_request(callback=cb_stats)
        
        for cw in data["coursework"]:
            batch2.add(
                service.courses().courseWork().studentSubmissions().list(
                    courseId=course_id, 
                    courseWorkId=cw['id'], 
                    pageSize=100
                ), 
                request_id=cw['id']
            )
        
        try:
            batch2.execute()
            data["stats"] = submission_stats
        except Exception as e:
            print(f"Batch 2 execution failed: {e}")

        return data

