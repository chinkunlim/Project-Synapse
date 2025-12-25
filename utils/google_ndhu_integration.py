"""
Google NDHU 帳戶整合（Google Tasks）
用於讀取與操作 Google Tasks 任務
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GoogleNDHUIntegration:
    """Google Tasks + Keep 整合類"""

    # OAuth 2.0 權限範圍（Tasks 讀寫）
    SCOPES = [
        'https://www.googleapis.com/auth/tasks'
    ]

    def __init__(self, credentials_path: str = 'config/google_credential_ndhu.json'):
        """
        初始化 Google NDHU 整合 (僅 Tasks)
        
        Args:
            credentials_path: OAuth 2.0 憑證 JSON 檔案路徑
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path('config/google_token_ndhu.pickle')
        self.creds = None
        self.tasks_service = None
        
        # 嘗試自動載入 Token
        self._try_load_token()

    def _try_load_token(self):
        """嘗試從檔案載入 Token 並自動 Refresh"""
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
                            print(f"⚠️ NDHU Token 刷新失敗: {e}")
                            self.creds = None
                    
                    if self.creds and self.creds.valid:
                        self.tasks_service = build('tasks', 'v1', credentials=self.creds)
                        print("✅ Google NDHU (Tasks) Token 載入成功")
        except Exception as e:
            print(f"⚠️ NDHU Token 載入失敗: {e}")

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
                    try:
                        self.creds.refresh(Request())
                    except Exception:
                        # Refresh 失敗（可能是 Scope 變更），強制重新認證
                        print("⚠️ Token refresh failed, forcing re-authentication...")
                        self.creds = None
                
                # 如果仍無有效憑證
                if not self.creds:
                    if not self.credentials_path.exists():
                        print(f"❌ 憑證檔不存在: {self.credentials_path}")
                        return False
                    
                    # 重新執行 Flow
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
            self.tasks_service = build('tasks', 'v1', credentials=self.creds)
            
            return True
            
        except Exception as e:
            print(f"❌ NDHU 認證失敗: {e}")
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
            self.tasks_service = build('tasks', 'v1', credentials=self.creds)

            return True
        except Exception as e:
            print(f"❌ NDHU 初始化憑證失敗: {e}")
            return False

    def get_tasks(self, tasklist_id: Optional[str] = None) -> List[Dict]:
        """
        取得 Google Tasks 的任務
        
        Args:
            tasklist_id: 若指定，僅取得該清單的任務；否則取得所有清單的任務
            
        Returns:
            List[Dict]: 任務列表
        """
        try:
            if not self.tasks_service:
                return []

            all_tasks = []
            
            # Determine which lists to query
            if tasklist_id:
                # Get title for single list
                try:
                    meta = self.tasks_service.tasklists().get(tasklist=tasklist_id).execute()
                    target_lists = [{'id': tasklist_id, 'title': meta.get('title', 'Unknown')}]
                except:
                   return []
            else:
                # Get all lists
                results = self.tasks_service.tasklists().list(maxResults=50).execute()
                target_lists = results.get('items', [])

            for tasklist in target_lists:
                t_id = tasklist['id']
                t_title = tasklist.get('title', 'Untitled')

                # 獲取該任務清單中的任務
                task_results = self.tasks_service.tasks().list(
                    tasklist=t_id,
                    showCompleted=True,
                    maxResults=100
                ).execute()

                tasks = task_results.get('items', [])
                for task in tasks:
                    all_tasks.append({
                        'id': task.get('id'),
                        'title': task.get('title', '無標題'),
                        'description': task.get('notes', ''),
                        'due': task.get('due'),
                        'status': task.get('status', 'needsAction'),
                        'tasklist': t_title,
                        'tasklistId': t_id,
                        'parent': task.get('parent'),
                        'source': 'Google Tasks'
                    })

            return all_tasks

        except Exception as e:
            print(f"❌ 讀取 Google Tasks 失敗: {e}")
            return []

    def get_all_tasks(self) -> List[Dict]:
        """
        取得所有 Google Tasks 任務

        Returns:
            List[Dict]: 任務列表
        """
        return self.get_tasks()

    # 已移除 Keep 相關功能（受限 scope 無法授權）

    def list_tasklists(self) -> Optional[List[Dict]]:
        """列出任務清單"""
        try:
            if not self.tasks_service:
                return None  # Signal not authenticated
            results = self.tasks_service.tasklists().list(maxResults=50).execute()
            lists = results.get('items', [])
            return [{'id': l.get('id'), 'title': l.get('title', 'Untitled')} for l in lists]
        except Exception as e:
            print(f"❌ 讀取 Tasks 清單失敗: {e}")
            return None

    def create_task(self, tasklist_id: str, title: str, notes: Optional[str] = None,
                     due_iso: Optional[str] = None, parent_id: Optional[str] = None) -> Optional[Dict]:
        """建立任務"""
        try:
            body: Dict = {
                'title': title
            }
            if notes:
                body['notes'] = notes
            if due_iso:
                body['due'] = due_iso
            if parent_id:
                body['parent'] = parent_id
            task = self.tasks_service.tasks().insert(tasklist=tasklist_id, body=body).execute()
            return task
        except Exception as e:
            print(f"❌ 建立 Tasks 任務失敗: {e}")
            return None

    def complete_task(self, tasklist_id: str, task_id: str) -> Optional[Dict]:
        """將任務標記為完成"""
        try:
            task = self.tasks_service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
            task['status'] = 'completed'
            updated = self.tasks_service.tasks().update(tasklist=tasklist_id, task=task_id, body=task).execute()
            return updated
        except Exception as e:
            print(f"❌ 完成 Tasks 任務失敗: {e}")
            return None

    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        """刪除任務"""
        try:
            self.tasks_service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
            return True
        except Exception as e:
            print(f"❌ 刪除 Tasks 任務失敗: {e}")
            return False
