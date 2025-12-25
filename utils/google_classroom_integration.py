"""
Google Classroom 整合模組
提供課程管理、學生名單導出、主題建立、課件發布等功能
"""

import os
import pickle
import json
from io import BytesIO
from typing import List, Dict, Optional
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import pandas as pd


class GoogleClassroomIntegration:
    """Google Classroom API 整合類"""
    
    # OAuth 2.0 權限範圍
    SCOPES = [
        'https://www.googleapis.com/auth/classroom.courses.readonly',
        'https://www.googleapis.com/auth/classroom.rosters.readonly',
        'https://www.googleapis.com/auth/classroom.topics',
        'https://www.googleapis.com/auth/classroom.courseworkmaterials',
        'https://www.googleapis.com/auth/classroom.coursework.me',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, credentials_path: str = 'config/google_credentials.json'):
        """
        初始化 Google Classroom 整合
        
        Args:
            credentials_path: OAuth 2.0 憑證 JSON 檔案路徑
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path('config/google_token.pickle')
        self.creds = None
        self.classroom_service = None
        self.drive_service = None
        
    def authenticate(self) -> bool:
        """
        執行 OAuth 2.0 認證流程
        
        Returns:
            bool: 認證是否成功
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
            
            # 建立服務物件
            self.classroom_service = build('classroom', 'v1', credentials=self.creds)
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            return True
            
        except Exception as e:
            print(f"❌ 認證失敗: {e}")
            return False

    def set_credentials(self, creds: Credentials) -> bool:
        """
        以既有的 Credentials 完成整合初始化，並持久化憑證

        Args:
            creds: 已完成交換的 Google OAuth 憑證

        Returns:
            bool: 是否初始化成功
        """
        try:
            self.creds = creds

            # 儲存憑證供下次使用
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

            # 建立服務物件
            self.classroom_service = build('classroom', 'v1', credentials=self.creds)
            self.drive_service = build('drive', 'v3', credentials=self.creds)

            return True
        except Exception as e:
            print(f"❌ 初始化憑證失敗: {e}")
            return False
    
    def get_courses(self) -> List[Dict]:
        """
        獲取所有課程列表
        
        Returns:
            List[Dict]: 課程資訊列表，包含 id, name, section 等
        """
        try:
            results = self.classroom_service.courses().list(
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

    def get_my_courses(self, role: str = 'teacher') -> List[Dict]:
        """
        只列出與目前帳號相關的課程

        Args:
            role: 'teacher' 或 'student'

        Returns:
            List[Dict]: 課程資訊列表
        """
        try:
            kwargs = {
                'pageSize': 100,
                'courseStates': ['ACTIVE']
            }
            if role == 'teacher':
                kwargs['teacherId'] = 'me'
            elif role == 'student':
                kwargs['studentId'] = 'me'

            results = self.classroom_service.courses().list(**kwargs).execute()
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

    def export_all_students_to_excel(self, courses: List[Dict], filename: str = 'all_students') -> str:
        """
        將多個課程的學生名單導出至同一個 Excel 檔案（多工作表）

        Args:
            courses: 課程列表，需包含 'id' 與 'name'
            filename: 輸出檔名（不含副檔名）

        Returns:
            str: 生成的 Excel 檔案路徑
        """
        try:
            output_path = f"/tmp/{filename}.xlsx"
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                for course in courses:
                    course_id = course['id']
                    course_name = course.get('name', f"course_{course_id}")
                    # 讀取學生名單
                    results = self.classroom_service.courses().students().list(
                        courseId=course_id,
                        pageSize=200
                    ).execute()
                    students = results.get('students', [])
                    rows = []
                    for s in students:
                        profile = s.get('profile', {})
                        rows.append({
                            'Name': profile.get('name', ''),
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
        依照提供的名稱清單建立主題

        Args:
            course_id: 課程 ID
            names: 主題名稱列表

        Returns:
            List[Dict]: 建立後的主題資訊
        """
        try:
            created = []
            for name in names:
                body = {"name": name}
                topic = self.classroom_service.courses().topics().create(
                    courseId=course_id,
                    body=body
                ).execute()
                created.append(topic)
            return created
        except Exception as e:
            print(f"❌ 依名稱建立主題失敗: {e}")
            return []

    def create_assignment(self, course_id: str, title: str, description: str = "", max_points: Optional[int] = None,
                           due_date: Optional[Dict] = None, topic_id: Optional[str] = None, state: str = 'PUBLISHED') -> Optional[Dict]:
        """
        建立作業（CourseWork）

        Args:
            course_id: 課程 ID
            title: 作業標題
            description: 作業描述
            max_points: 滿分
            due_date: 到期日，格式例如 {"year":2025,"month":1,"day":15}
            topic_id: 主題 ID（選填）
            state: 狀態 'PUBLISHED' 或 'DRAFT'

        Returns:
            Optional[Dict]: 建立的作業物件
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
            if topic_id:
                body["topicId"] = topic_id
            coursework = self.classroom_service.courses().courseWork().create(
                courseId=course_id,
                body=body
            ).execute()
            return coursework
        except Exception as e:
            print(f"❌ 建立作業失敗: {e}")
            return None
    
    def get_students(self, course_id: str) -> List[Dict]:
        """
        獲取指定課程的學生名單
        
        Args:
            course_id: 課程 ID
            
        Returns:
            List[Dict]: 學生資訊列表
        """
        try:
            results = self.classroom_service.courses().students().list(
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
        將學生名單導出為 Excel 檔案
        
        Args:
            course_id: 課程 ID
            course_name: 課程名稱（用於檔案命名）
            
        Returns:
            BytesIO: Excel 檔案的二進制流
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
        批次建立 N 週的主題
        
        Args:
            course_id: 課程 ID
            num_weeks: 週數
            prefix: 主題名稱前綴（預設 "Week"）
            
        Returns:
            List[Dict]: 建立成功的主題列表
        """
        created_topics = []
        
        try:
            for week in range(1, num_weeks + 1):
                topic_name = f"{prefix} {week}"
                
                topic = self.classroom_service.courses().topics().create(
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
        獲取課程的所有主題
        
        Args:
            course_id: 課程 ID
            
        Returns:
            List[Dict]: 主題列表
        """
        try:
            results = self.classroom_service.courses().topics().list(
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
    
    def upload_file_to_drive(self, file_path: str, file_name: str = None) -> Optional[str]:
        """
        上傳檔案到 Google Drive
        
        Args:
            file_path: 本地檔案路徑
            file_name: Drive 中的檔案名稱（若未提供則使用原檔名）
            
        Returns:
            Optional[str]: Drive 檔案 ID，失敗返回 None
        """
        try:
            if not file_name:
                file_name = Path(file_path).name
            
            file_metadata = {'name': file_name}
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.drive_service.files().create(
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
        發布課件（可包含 Drive 檔案或外部連結）
        
        Args:
            course_id: 課程 ID
            title: 課件標題
            description: 課件描述
            topic_id: 主題 ID（選填）
            file_id: Google Drive 檔案 ID（選填）
            link_url: 外部連結 URL（選填）
            state: 發布狀態 ("PUBLISHED" 或 "DRAFT")
            
        Returns:
            Optional[Dict]: 建立的課件資訊
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
            
            material = self.classroom_service.courses().courseWorkMaterials().create(
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
        獲取作業的學生呈交進度統計
        
        Args:
            course_id: 課程 ID
            coursework_id: 作業 ID
            
        Returns:
            Dict: 包含各狀態統計的字典
        """
        try:
            results = self.classroom_service.courses().courseWork().studentSubmissions().list(
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
        獲取課程的所有作業
        
        Args:
            course_id: 課程 ID
            
        Returns:
            List[Dict]: 作業列表
        """
        try:
            results = self.classroom_service.courses().courseWork().list(
                courseId=course_id,
                pageSize=100
            ).execute()
            
            coursework_list = results.get('courseWork', [])
            
            return [{
                'id': work['id'],
                'courseId': work['courseId'],
                'title': work['title'],
                'description': work.get('description', ''),
                'state': work['state'],
                'alternateLink': work['alternateLink'],
                'creationTime': work['creationTime'],
                'updateTime': work['updateTime'],
                'dueDate': work.get('dueDate'),
                'dueTime': work.get('dueTime'),
                'maxPoints': work.get('maxPoints'),
                'workType': work['workType']
            } for work in coursework_list]
            
        except Exception as e:
            print(f"❌ 獲取作業列表失敗: {e}")
            return []
