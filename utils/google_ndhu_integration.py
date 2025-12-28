"""
Google NDHU Account Integration (Google Tasks)
Used for reading and operating Google Tasks
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Optional
import threading

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GoogleNDHUIntegration:
    """Google Tasks Integration Class"""

    # OAuth 2.0 Scopes (Tasks Read/Write)
    SCOPES = [
        'https://www.googleapis.com/auth/tasks'
    ]

    def __init__(self, credentials_path: str = 'config/google_credential_ndhu.json'):
        """
        Initialize Google NDHU Integration (Tasks only)
        
        Args:
            credentials_path: Path to OAuth 2.0 credentials JSON file
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path('config/google_token_ndhu.pickle')
        self.creds = None
        self._thread_local = threading.local()
        
        # Try to auto-load token
        self._try_load_token()

    def _try_load_token(self):
        """Try to load Token from file and auto-refresh"""
        try:
            if self.token_path.exists():
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
                
                if self.creds:
                    # If expired and has refresh_token, try to refresh
                    if self.creds.expired and self.creds.refresh_token:
                        try:
                            self.creds.refresh(Request())
                            # Save new Token after refresh
                            with open(self.token_path, 'wb') as token:
                                pickle.dump(self.creds, token)
                        except Exception as e:
                            print(f"⚠️ NDHU Token refresh failed: {e}")
                            self.creds = None
                    

            if self.creds and self.creds.valid:
                # Validated successfully
                print("✅ Google NDHU (Tasks) Token loaded successfully")
        except Exception as e:
            print(f"⚠️ NDHU Token load failed: {e}")

    def _get_tasks_service(self):
        """Get Tasks Service for current thread"""
        if not self.creds:
            return None
            
        if not hasattr(self._thread_local, 'service'):
            try:
                self._thread_local.service = build('tasks', 'v1', credentials=self.creds)
            except Exception as e:
                print(f"❌ Failed to create Thread-Local Tasks Service: {e}")
                return None
                
        return self._thread_local.service

    @property
    def tasks_service(self):
        """Property to access the thread-local tasks service (backward compatibility)"""
        return self._get_tasks_service()

    def authenticate(self) -> bool:
        """
        Execute OAuth 2.0 Authentication Flow
        
        Returns:
            bool: Whether authentication was successful
        """
        try:
            # Load existing credentials
            if self.token_path.exists():
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # If credentials invalid or not exist, execute auth flow
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                    except Exception:
                        # Refresh failed, force re-auth
                        print("⚠️ Token refresh failed, forcing re-authentication...")
                        self.creds = None
                
                if not self.creds:
                    if not self.credentials_path.exists():
                        print(f"❌ Credential file not found: {self.credentials_path}")
                        return False
                    
                    # Re-run Flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), 
                        self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                # Save credentials
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            # Clear thread local service
            if hasattr(self._thread_local, 'service'):
                del self._thread_local.service
            
            return True
            
        except Exception as e:
            print(f"❌ NDHU Authentication failed: {e}")
            return False


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

            # Save credentials
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

            # Clear thread local service
            if hasattr(self._thread_local, 'service'):
                 del self._thread_local.service

            return True
        except Exception as e:
            print(f"❌ NDHU Credential Initialization failed: {e}")
            return False

    def get_tasks(self, tasklist_id: Optional[str] = None) -> List[Dict]:
        """
        Get Google Tasks
        
        Args:
            tasklist_id: If specified, get tasks for that list only; otherwise get tasks for all lists
            
        Returns:
            List[Dict]: List of tasks
        """
        try:
            service = self._get_tasks_service()
            if not service:
                return []

            all_tasks = []
            
            # Determine which lists to query
            if tasklist_id:
                # Get title for single list
                try:
                    meta = service.tasklists().get(tasklist=tasklist_id).execute()
                    target_lists = [{'id': tasklist_id, 'title': meta.get('title', 'Unknown')}]
                except:
                   return []
            else:
                # Get all lists
                results = service.tasklists().list(maxResults=50).execute()
                target_lists = results.get('items', [])

            for tasklist in target_lists:
                t_id = tasklist['id']
                t_title = tasklist.get('title', 'Untitled')

                # Get tasks in list
                task_results = service.tasks().list(
                    tasklist=t_id,
                    showCompleted=True,
                    maxResults=100
                ).execute()

                tasks = task_results.get('items', [])
                for task in tasks:
                    all_tasks.append({
                        'id': task.get('id'),
                        'title': task.get('title', 'No Title'),
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
            print(f"❌ Failed to read Google Tasks: {e}")
            return []

    def get_all_tasks(self) -> List[Dict]:
        """
        Get all Google Tasks
        
        Returns:
            List[Dict]: List of tasks
        """
        return self.get_tasks()

    def list_tasklists(self) -> Optional[List[Dict]]:
        """List task lists"""
        try:
            service = self._get_tasks_service()
            if not service:
                return None  # Signal not authenticated
            results = service.tasklists().list(maxResults=50).execute()
            lists = results.get('items', [])
            return [{'id': l.get('id'), 'title': l.get('title', 'Untitled')} for l in lists]
        except Exception as e:
            print(f"❌ Failed to read Task Lists: {e}")
            return None

    def create_task(self, tasklist_id: str, title: str, notes: Optional[str] = None,
                     due_iso: Optional[str] = None, parent_id: Optional[str] = None) -> Optional[Dict]:
        """Create a task"""
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
            
            service = self._get_tasks_service()
            if not service: return None
            
            task = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
            return task
        except Exception as e:
            print(f"❌ Failed to create Task: {e}")
            return None

    def complete_task(self, tasklist_id: str, task_id: str) -> Optional[Dict]:
        """Mark task as completed"""
        try:
            service = self._get_tasks_service()
            if not service: return None
            
            task = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
            task['status'] = 'completed'
            updated = service.tasks().update(tasklist=tasklist_id, task=task_id, body=task).execute()
            return updated
        except Exception as e:
            print(f"❌ Failed to complete Task: {e}")
            return None

    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        """Delete a task"""
        try:
            service = self._get_tasks_service()
            if service:
                service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
            return True
        except Exception as e:
            print(f"❌ Failed to delete Task: {e}")
            return False
