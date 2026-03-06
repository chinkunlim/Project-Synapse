from concurrent.futures import ThreadPoolExecutor
import uuid
import copy
from typing import Dict, Any

# Global task executor and task storage
executor = ThreadPoolExecutor(max_workers=5)
# Stores task status: {"status": "processing", ...}
tasks: Dict[str, Dict[str, Any]] = {}

def submit_task(func, *args, **kwargs) -> str:
    """
    Submits a function to be executed in the background.
    Returns a task UUID string.
    """
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "processing"}
    
    def wrapped_func():
        try:
            result = func(*args, **kwargs)
            # Map various return structures to frontend-expected formats
            if isinstance(result, dict):
                res = copy.deepcopy(result)
                if 'success' in res:
                    res['status'] = 'success' if res['success'] else 'error'
                    del res['success']
                elif 'status' not in res:
                    res['status'] = 'success'
                tasks[task_id] = res
            elif isinstance(result, bool):
                if result:
                    tasks[task_id] = {"status": "success", "message": "操作執行成功"}
                else:
                    tasks[task_id] = {"status": "error", "message": "操作執行失敗"}
            else:
                tasks[task_id] = {"status": "success", "message": "操作執行成功", "data": result}
        except Exception as e:
            # If the task throws an Unhandled Exception, log it via our global logger if possible
            from utils.logger import logger
            logger.error(f"Background Task {task_id} Failed: {e}", exc_info=True)
            tasks[task_id] = {"status": "error", "message": f"伺服器背景任務錯誤: {str(e)}"}
            
    executor.submit(wrapped_func)
    return task_id

def get_task_status(task_id: str) -> Dict[str, Any]:
    """Retrieves the current status and result of a task."""
    return tasks.get(task_id, {"status": "error", "message": "任務不存在或已過期"})
