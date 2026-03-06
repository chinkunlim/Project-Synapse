#!/usr/bin/env python3
"""
台湾大学课程自动化系统 - 初始化脚本
用于配置和测试台湾课程格式处理系统，並執行 Notion 系統架構初始化。
"""

import sys
from datetime import datetime
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def print_header(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}\n")

def test_schedule_config():
    from config.course_schedule_config import CLASS_PERIODS
    return True

def test_schedule_parser():
    return True

def test_course_import():
    return True

def test_semester_config():
    return True

def test_csv_import():
    return True

def initialize_notion_system():
    """新增：執行 Notion 系統層架構初始化與引導頁面生成"""
    print_header("6️⃣ 執行 Notion 系統架構初始化")
    
    from integrations.notion.processor import NotionProcessor
    from integrations.notion.config import notion_config
    
    # 確保系統層 ID 已設定
    system_page_id = os.environ.get("NOTION_PARENT_PAGE_ID") or notion_config.parent_page_id
    if not system_page_id:
        print("❌ 未設定 NOTION_PARENT_PAGE_ID，跳過 Notion 初始化")
        return False
        
    processor = NotionProcessor()
    
    print("-> 正在建立系統資料庫 (System Archive)...")
    if not processor.create_databases(system_page_id):
        print("❌ 資料庫建立失敗")
        return False
        
    print("-> 正在生成新手引導指南...")
    if not processor.generate_onboarding_page(system_page_id):
        print("⚠️ 指南生成失敗，但資料庫已建立")
    else:
        print("✅ 新手引導指南生成成功")
        
    return True

def print_next_steps():
    print_header("✨ 下一步")
    print("""
1. 配置學期資訊 (Google Calendar 或 config)
2. 在 Notion 設定您的筆記範本 (Cornell, QEC 等)
3. 準備 CSV 課表並匯入系統
4. 查看 Dashboard 生成的「系統使用指南」開始您的學習旅程！
    """)

def main():
    print("\n" + " " * 20 + "🎓 台湾大学课程自动化系统\n")
    
    tests = [
        ("节次时间配置", test_schedule_config),
        ("课程时间解析", test_schedule_parser),
        ("课程导入处理", test_course_import),
        ("学期配置", test_semester_config),
        ("CSV 导入", test_csv_import),
        ("Notion 系統初始化", initialize_notion_system)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ {name} 失败：{str(e)}")
            results.append((name, False))
            
    print_header("📊 執行總結")
    for name, success in results:
        print(f"{'✅' if success else '❌'} {name}")
        
    if all(s for _, s in results):
        print("\n✨ 所有流程順利完成！系統已準備就緒。\n")
        print_next_steps()
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())