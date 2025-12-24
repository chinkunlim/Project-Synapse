"""
Notion 整合模組 - 配置管理
統一管理所有 Notion 相關的配置設定
"""
import os
import configparser
from pathlib import Path
from dotenv import load_dotenv, set_key, find_dotenv
import logging

logger = logging.getLogger(__name__)


class NotionConfig:
    """Notion 配置管理類別"""
    
    def __init__(self, ini_path="config/notion_config.ini"):
        """
        初始化配置管理器
        
        Args:
            ini_path: 配置文件路徑
        """
        self.config = configparser.ConfigParser()
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.ini_path = self.project_root / ini_path
        
        # 載入 INI 配置
        if self.ini_path.exists():
            self.config.read(self.ini_path, encoding="utf-8")
            logger.debug(f"已載入配置文件: {self.ini_path}")
        else:
            logger.warning(f"找不到配置文件: {self.ini_path}")
        
        # 載入環境變數
        self._load_env()
    
    def _load_env(self):
        """載入 .env 文件"""
        dotenv_path = find_dotenv()
        if dotenv_path:
            load_dotenv(dotenv_path)
            logger.debug(f"已載入環境變數: {dotenv_path}")
        else:
            logger.warning("找不到 .env 文件")
    
    def get_config(self, key, section=None, default=None):
        """
        從 INI 文件獲取配置值
        
        Args:
            key: 配置鍵名
            section: 配置段名
            default: 默認值
            
        Returns:
            配置值或默認值
        """
        if section and self.config.has_option(section, key):
            return self.config.get(section, key)
        return default
    
    def get_env(self, key, default=None):
        """
        獲取環境變數
        
        Args:
            key: 環境變數名
            default: 默認值
            
        Returns:
            環境變數值或默認值
        """
        return os.getenv(key, default)
    
    def set_env(self, key, value):
        """
        設置環境變數並寫入 .env 文件
        
        Args:
            key: 環境變數名
            value: 環境變數值
            
        Returns:
            是否成功設置
        """
        dotenv_path = find_dotenv()
        if not dotenv_path:
            dotenv_path = self.project_root / '.env'
            dotenv_path.touch(exist_ok=True)
            logger.info(f"創建新的 .env 文件: {dotenv_path}")
        
        success = set_key(str(dotenv_path), key, value)
        
        if success:
            os.environ[key] = value
            logger.info(f"成功設置環境變數: {key}")
            return True
        else:
            logger.error(f"設置環境變數失敗: {key}")
            return False
    
    def get_all_env_vars(self):
        """
        獲取所有 Notion 相關環境變數
        
        Returns:
            環境變數字典
        """
        env_keys = [
            "NOTION_API_KEY",
            "PARENT_PAGE_ID",
            "NOTION_DATABASE_ID",
            "TASK_DATABASE_ID",
            "COURSE_HUB_ID",
            "CLASS_SESSION_ID",
            "NOTE_DB_ID",
            "PROJECT_DB_ID",
            "RESOURCE_DB_ID",
        ]
        return {key: os.getenv(key) for key in env_keys if os.getenv(key)}
    
    # Notion API 相關配置
    @property
    def api_key(self):
        """獲取 Notion API Key"""
        return self.get_env("NOTION_API_KEY")
    
    @property
    def parent_page_id(self):
        """獲取父頁面 ID"""
        return self.get_env("PARENT_PAGE_ID")
    
    @property
    def base_url(self):
        """獲取 Notion API 基礎 URL"""
        return self.get_config("base_url", "Notion", "https://api.notion.com/v1")
    
    @property
    def api_version(self):
        """獲取 Notion API 版本"""
        return self.get_config("api_version", "Notion", "2022-06-28")
    
    @property
    def content_type(self):
        """獲取內容類型"""
        return self.get_config("content_type", "Notion", "application/json")
    
    # 日誌相關配置
    @property
    def log_folder(self):
        """獲取日誌文件夾路徑"""
        folder = self.get_config("log_folder", "Logging", "logs")
        return self.project_root / folder
    
    @property
    def log_filename(self):
        """獲取日誌文件名"""
        return self.get_config("log_filename", "Logging", "app.log")
    
    @property
    def log_level(self):
        """獲取日誌級別"""
        return self.get_config("log_level", "Logging", "INFO").upper()
    
    @property
    def log_format(self):
        """獲取日誌格式"""
        return self.get_config("log_format", "Logging", 
                              "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    @property
    def log_encoding(self):
        """獲取日誌編碼"""
        return self.get_config("log_encoding", "Logging", "utf-8")
    
    # Schema 相關配置
    @property
    def schema_path(self):
        """獲取 Schema JSON 文件路徑"""
        return self.project_root / "config" / "notion_schema.json"


# 全局配置實例
notion_config = NotionConfig()
