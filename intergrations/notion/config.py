"""
Notion 整合模組 - 設定管理
=====================================
此模組負責統一管理所有 Notion 相關的設定，包括：
- API 金鑰與連線設定
- 資料庫 ID 管理
- 日誌系統設定
- 環境變數讀取與寫入
- INI 設定檔解析

作者：Project Synapse Team
版本：2.0
最後更新：2025-12-25
"""

import os
import configparser
from pathlib import Path
from dotenv import load_dotenv, set_key, find_dotenv
import logging

# 設定日誌記錄器
logger = logging.getLogger(__name__)


class NotionConfig:
    """
    Notion 設定管理類別
    
    此類別負責管理所有 Notion 相關的設定，提供：
    - 環境變數的讀取與寫入
    - INI 設定檔的解析
    - 設定值的快速存取（透過屬性）
    - 設定檔路徑的自動解析
    
    屬性：
        config (ConfigParser): INI 設定檔解析器
        project_root (Path): 專案根目錄路徑
        ini_path (Path): INI 設定檔完整路徑
    """
    
    def __init__(self, ini_path="config/notion_config.ini"):
        """
        初始化設定管理器
        
        此方法會：
        1. 建立 ConfigParser 實例
        2. 解析專案根目錄路徑
        3. 載入 INI 設定檔
        4. 載入環境變數檔案（.env）
        
        參數：
            ini_path (str): INI 設定檔的相對路徑（相對於專案根目錄）
                           預設值："config/notion_config.ini"
        
        範例：
            >>> config = NotionConfig()
            >>> api_key = config.api_key
            >>> print(f"API 金鑰: {api_key}")
        """
        # 建立 INI 設定檔解析器
        self.config = configparser.ConfigParser()
        
        # 解析專案根目錄路徑
        # __file__ 是此檔案的完整路徑
        # parent.parent.parent 往上三層到達專案根目錄
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        # 組合 INI 設定檔的完整路徑
        self.ini_path = self.project_root / ini_path
        
        # 載入 INI 設定檔
        if self.ini_path.exists():
            self.config.read(self.ini_path, encoding="utf-8")
            logger.debug(f"✅ 已載入設定檔: {self.ini_path}")
        else:
            logger.warning(f"⚠️  找不到設定檔: {self.ini_path}")
        
        # 載入環境變數
        self._load_env()
    
    def _load_env(self):
        """
        載入環境變數檔案（.env）
        
        此方法會：
        1. 搜尋專案目錄中的 .env 檔案
        2. 將檔案中的環境變數載入到系統環境中
        3. 記錄載入結果日誌
        
        注意：
            .env 檔案通常位於專案根目錄
            檔案格式為：KEY=VALUE（每行一個設定）
        
        範例 .env 檔案內容：
            NOTION_API_KEY=secret_xxx...
            PARENT_PAGE_ID=abc123...
        """
        # 搜尋 .env 檔案
        dotenv_path = find_dotenv()
        
        if dotenv_path:
            # 載入環境變數
            load_dotenv(dotenv_path)
            logger.debug(f"✅ 已載入環境變數檔案: {dotenv_path}")
        else:
            # 找不到 .env 檔案
            logger.warning("⚠️  找不到 .env 檔案，將使用系統環境變數")
    
    def get_config(self, key, section=None, default=None):
        """
        從 INI 設定檔讀取設定值
        
        此方法用於從 notion_config.ini 檔案中讀取設定。
        
        INI 檔案格式範例：
            [Notion]
            base_url = https://api.notion.com/v1
            api_version = 2022-06-28
            
            [Logging]
            log_level = INFO
        
        參數：
            key (str): 設定項目的鍵名
            section (str, optional): 設定區段名稱（例如：Notion, Logging）
            default (Any, optional): 若找不到設定時的預設值
        
        回傳：
            Any: 設定值或預設值
        
        範例：
            >>> config = NotionConfig()
            >>> api_version = config.get_config('api_version', 'Notion')
            >>> print(api_version)  # 輸出: 2022-06-28
        """
        # 檢查設定區段與鍵名是否存在
        if section and self.config.has_option(section, key):
            return self.config.get(section, key)
        
        # 若不存在，回傳預設值
        return default
    
    def get_env(self, key, default=None):
        """
        讀取環境變數
        
        此方法用於從系統環境變數或 .env 檔案中讀取設定值。
        
        參數：
            key (str): 環境變數名稱（例如：NOTION_API_KEY）
            default (Any, optional): 若環境變數不存在時的預設值
        
        回傳：
            str: 環境變數的值，或預設值
        
        範例：
            >>> config = NotionConfig()
            >>> api_key = config.get_env('NOTION_API_KEY')
            >>> if api_key:
            ...     print("API 金鑰已設定")
        """
        return os.getenv(key, default)
    
    def set_env(self, key, value):
        """
        設定環境變數並寫入 .env 檔案
        
        此方法會：
        1. 更新 .env 檔案中的環境變數
        2. 同時更新系統環境變數（立即生效）
        3. 若 .env 檔案不存在，則自動建立
        
        參數：
            key (str): 環境變數名稱（例如：NOTION_API_KEY）
            value (str): 環境變數的值
        
        回傳：
            bool: True 表示設定成功，False 表示設定失敗
        
        範例：
            >>> config = NotionConfig()
            >>> success = config.set_env('NOTION_API_KEY', 'secret_xxx...')
            >>> if success:
            ...     print("API 金鑰已儲存")
        """
        # 搜尋 .env 檔案
        dotenv_path = find_dotenv()
        
        if not dotenv_path:
            # 若 .env 檔案不存在，則在專案根目錄建立
            dotenv_path = self.project_root / '.env'
            dotenv_path.touch(exist_ok=True)
            logger.info(f"📝 建立新的 .env 檔案: {dotenv_path}")
        
        # 將環境變數寫入 .env 檔案
        success = set_key(str(dotenv_path), key, value)
        
        if success:
            # 同時更新系統環境變數（立即生效）
            os.environ[key] = value
            logger.info(f"✅ 成功設定環境變數: {key}")
            return True
        else:
            # 設定失敗
            logger.error(f"❌ 設定環境變數失敗: {key}")
            return False
    
    def get_all_env_vars(self):
        """
        取得所有 Notion 相關的環境變數
        
        此方法會回傳所有與 Notion 相關的環境變數及其值。
        只包含已設定的環境變數（未設定的會被過濾掉）。
        
        回傳：
            dict: 環境變數字典，格式為 {變數名: 值}
        
        範例：
            >>> config = NotionConfig()
            >>> env_vars = config.get_all_env_vars()
            >>> for key, value in env_vars.items():
            ...     print(f"{key}: {value[:20]}...")  # 只顯示前 20 個字元
        """
        # 定義所有 Notion 相關的環境變數名稱
        env_keys = [
            "NOTION_API_KEY",        # Notion API 金鑰
            "PARENT_PAGE_ID",        # 父頁面 ID
            "TASK_DATABASE_ID",      # 任務資料庫 ID
            "COURSE_HUB_ID",         # 課程中心資料庫 ID
            "CLASS_SESSION_ID",      # 課程會話資料庫 ID
            "NOTE_DATABASE_ID",      # 筆記資料庫 ID
            "PROJECT_DATABASE_ID",   # 專案資料庫 ID
            "RESOURCE_DATABASE_ID",  # 資源資料庫 ID
        ]
        
        # 只回傳已設定的環境變數
        return {key: os.getenv(key) for key in env_keys if os.getenv(key)}
    
    # ===== Notion API 相關設定 =====
    
    @property
    def api_key(self):
        """
        取得 Notion API 金鑰
        
        回傳：
            str: API 金鑰（從環境變數 NOTION_API_KEY 讀取）
        
        範例：
            >>> config = NotionConfig()
            >>> print(config.api_key)
        """
        return self.get_env("NOTION_API_KEY")
    
    @property
    def parent_page_id(self):
        """
        取得父頁面 ID
        
        回傳：
            str: 父頁面 ID（從環境變數 PARENT_PAGE_ID 讀取）
        
        範例：
            >>> config = NotionConfig()
            >>> print(config.parent_page_id)
        """
        return self.get_env("PARENT_PAGE_ID")
    
    @property
    def base_url(self):
        """
        取得 Notion API 基礎 URL
        
        回傳：
            str: API 基礎 URL（預設：https://api.notion.com/v1）
        """
        return self.get_config("base_url", "Notion", "https://api.notion.com/v1")
    
    @property
    def api_version(self):
        """
        取得 Notion API 版本
        
        回傳：
            str: API 版本號（預設：2022-06-28）
        """
        return self.get_config("api_version", "Notion", "2022-06-28")
    
    @property
    def content_type(self):
        """
        取得 HTTP 請求的內容類型
        
        回傳：
            str: 內容類型（預設：application/json）
        """
        return self.get_config("content_type", "Notion", "application/json")
    
    # ===== 日誌系統相關設定 =====
    
    @property
    def log_folder(self):
        """
        取得日誌資料夾路徑
        
        回傳：
            Path: 日誌資料夾的完整路徑（預設：專案根目錄/logs）
        """
        folder = self.get_config("log_folder", "Logging", "logs")
        return self.project_root / folder
    
    @property
    def log_filename(self):
        """
        取得日誌檔案名稱
        
        回傳：
            str: 日誌檔案名稱（預設：app.log）
        """
        return self.get_config("log_filename", "Logging", "app.log")
    
    @property
    def log_level(self):
        """
        取得日誌記錄等級
        
        回傳：
            str: 日誌等級（DEBUG, INFO, WARNING, ERROR, CRITICAL）
                預設：INFO
        """
        return self.get_config("log_level", "Logging", "INFO").upper()
    
    @property
    def log_format(self):
        """
        取得日誌格式字串
        
        回傳：
            str: Python logging 格式字串
                預設：%(asctime)s - %(name)s - %(levelname)s - %(message)s
        """
        return self.get_config("log_format", "Logging", 
                              "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    @property
    def log_encoding(self):
        """
        取得日誌檔案編碼
        
        回傳：
            str: 檔案編碼（預設：utf-8）
        """
        return self.get_config("log_encoding", "Logging", "utf-8")
    
    # ===== Schema 相關設定 =====
    
    @property
    def schema_path(self):
        """
        取得 Schema JSON 設定檔路徑
        
        此檔案包含：
        - 儀表板佈局定義
        - 資料庫架構定義
        - 欄位屬性設定
        
        回傳：
            Path: Schema JSON 檔案的完整路徑
                  （專案根目錄/config/notion_schema.json）
        """
        return self.project_root / "config" / "notion_schema.json"


# ===== 全域設定實例 =====
# 建立一個全域的設定物件供其他模組使用
notion_config = NotionConfig()
