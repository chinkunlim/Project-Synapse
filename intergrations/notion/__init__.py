"""
Notion 整合模組
提供 Notion API 的完整整合功能

主要組件:
- NotionConfig: 配置管理
- NotionApiClient: API 客戶端
- NotionProcessor: 高層次處理器
- setup_logging: 日誌配置

使用範例:
    from intergrations.notion import NotionProcessor, setup_logging
    
    # 初始化日誌
    setup_logging()
    
    # 創建處理器
    processor = NotionProcessor()
    
    # 測試連接
    processor.test_connection()
    
    # 構建儀表板
    processor.build_dashboard_layout()
    
    # 創建數據庫
    processor.create_databases()
"""

from .config import NotionConfig, notion_config
from .client import NotionApiClient
from .processor import (
    NotionProcessor,
    execute_test_connection,
    execute_build_dashboard_layout,
    execute_delete_blocks,
    execute_create_database
)
from .logging import setup_logging

__version__ = "2.0.0"
__all__ = [
    # 配置
    "NotionConfig",
    "notion_config",
    
    # API 客戶端
    "NotionApiClient",
    
    # 處理器
    "NotionProcessor",
    
    # 向後兼容的函數
    "execute_test_connection",
    "execute_build_dashboard_layout",
    "execute_delete_blocks",
    "execute_create_database",
    
    # 日誌
    "setup_logging",
]
