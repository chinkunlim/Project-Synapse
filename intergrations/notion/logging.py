"""
Notion 整合模組 - 日誌系統
配置和管理日誌記錄
"""
import logging
from pathlib import Path
from rich.logging import RichHandler

from .config import notion_config


def setup_logging():
    """
    配置日誌系統
    
    設置文件日誌和控制台日誌（使用 Rich 格式化）
    """
    # 獲取配置
    log_dir = notion_config.log_folder
    log_file = log_dir / notion_config.log_filename
    log_level = notion_config.log_level
    log_format = notion_config.log_format
    log_encoding = notion_config.log_encoding
    
    # 創建日誌目錄
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日誌
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, mode="a", encoding=log_encoding),
            RichHandler(rich_tracebacks=True, markup=True)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("日誌系統已初始化")
    logger.info(f"日誌目錄: {log_dir}")
    logger.info(f"日誌文件: {log_file.name}")
    logger.info(f"日誌級別: {log_level}")
    logger.info("=" * 60)
    
    return logger


# 自動配置日誌（當模組被導入時）
_logger = setup_logging()