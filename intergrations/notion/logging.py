"""
Notion 整合模組 - 日誌系統
=====================================
此模組負責設定與管理整個應用程式的日誌系統，包括：
- 檔案日誌記錄
- 主控台日誌輸出（使用 Rich 美化）
- 日誌格式設定
- 日誌等級控制

作者：Project Synapse Team
版本：2.0
最後更新：2025-12-25
"""

import logging
from pathlib import Path
from rich.logging import RichHandler

from .config import notion_config


def setup_logging():
    """
    設定日誌系統
    
    此函式會執行完整的日誌系統初始化：
    1. 從設定檔讀取日誌相關設定
    2. 建立日誌資料夾（若不存在）
    3. 設定檔案日誌處理器
    4. 設定主控台日誌處理器（使用 Rich 美化）
    5. 記錄初始化完成訊息
    
    日誌系統特點：
    - 雙重輸出：同時寫入檔案與顯示在主控台
    - Rich 格式化：主控台輸出包含顏色與格式美化
    - 追蹤堆疊：自動記錄錯誤的完整堆疊追蹤
    - UTF-8 編碼：支援繁體中文等多語系字元
    
    回傳：
        Logger: 初始化完成的日誌記錄器實例
    
    範例：
        >>> from intergrations.notion.logging import setup_logging
        >>> logger = setup_logging()
        >>> logger.info("這是一則測試訊息")
    """
    # 從設定檔讀取日誌相關設定
    log_dir = notion_config.log_folder          # 日誌資料夾路徑
    log_file = log_dir / notion_config.log_filename  # 日誌檔案完整路徑
    log_level = notion_config.log_level         # 日誌等級（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    log_format = notion_config.log_format       # 日誌格式字串
    log_encoding = notion_config.log_encoding   # 檔案編碼（utf-8）
    
    # 建立日誌資料夾（若不存在則建立，包含所有父目錄）
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 設定日誌系統
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),  # 設定日誌等級
        format=log_format,                                  # 設定日誌格式
        handlers=[
            # 檔案日誌處理器：將日誌寫入檔案
            logging.FileHandler(
                log_file,
                mode="a",                    # 附加模式（不會覆蓋舊日誌）
                encoding=log_encoding        # UTF-8 編碼支援中文
            ),
            # 主控台日誌處理器：使用 Rich 美化輸出
            RichHandler(
                rich_tracebacks=True,        # 啟用豐富的錯誤追蹤顯示
                markup=True                  # 支援 Rich 標記語法
            )
        ]
    )
    
    # 取得日誌記錄器實例
    logger = logging.getLogger(__name__)
    
    # 記錄日誌系統初始化完成訊息
    logger.info("=" * 60)
    logger.info("🚀 日誌系統已初始化完成")
    logger.info(f"📁 日誌資料夾: {log_dir}")
    logger.info(f"📄 日誌檔案: {log_file.name}")
    logger.info(f"📊 日誌等級: {log_level}")
    logger.info(f"🔤 檔案編碼: {log_encoding}")
    logger.info("=" * 60)
    
    return logger


# ===== 自動初始化日誌系統 =====
# 當此模組被匯入時，自動執行日誌系統初始化
# 這樣其他模組只需要 import logging 就可以使用設定好的日誌系統
_logger = setup_logging()
