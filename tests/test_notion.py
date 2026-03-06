"""
Notion 模組測試腳本
用於測試重構後的 Notion 整合模組功能
"""
import os
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from integrations.notion import (
    NotionProcessor,
    NotionConfig,
    notion_config,
    setup_logging
)

def test_config():
    """測試配置管理"""
    print("\n" + "="*60)
    print("測試 1: 配置管理")
    print("="*60)
    
    # 測試配置屬性
    print(f"✓ API 基礎 URL: {notion_config.base_url}")
    print(f"✓ API 版本: {notion_config.api_version}")
    print(f"✓ 日誌級別: {notion_config.log_level}")
    print(f"✓ Schema 路徑: {notion_config.schema_path}")
    
    # 測試環境變數
    api_key = notion_config.api_key
    parent_id = notion_config.parent_page_id
    print(f"✓ API Key: {'已設置' if api_key else '未設置'}")
    print(f"✓ 父頁面 ID: {'已設置' if parent_id else '未設置'}")
    
    if not api_key:
        print("\n⚠️  警告: NOTION_API_KEY 未設置")
        print("   請在 .env 文件中設置 NOTION_API_KEY")
        return False
    
    if not parent_id:
        print("\n⚠️  警告: PARENT_PAGE_ID 未設置")
        print("   請在 .env 文件中設置 PARENT_PAGE_ID")
        return False
    
    print("\n✅ 配置測試通過")
    return True


def test_connection():
    """測試 Notion 連接"""
    print("\n" + "="*60)
    print("測試 2: Notion API 連接")
    print("="*60)
    
    try:
        processor = NotionProcessor()
        result = processor.test_connection()
        
        if result:
            print("✅ Notion API 連接測試通過")
            return True
        else:
            print("❌ Notion API 連接測試失敗")
            return False
            
    except Exception as e:
        print(f"❌ 連接測試出錯: {e}")
        return False


def test_schema_loading():
    """測試 Schema 文件載入"""
    print("\n" + "="*60)
    print("測試 3: Schema 文件載入")
    print("="*60)
    
    import json
    
    schema_path = notion_config.schema_path
    
    if not schema_path.exists():
        print(f"❌ Schema 文件不存在: {schema_path}")
        return False
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # 檢查 Schema 結構
        has_layout = 'layout' in schema
        has_databases = 'databases' in schema
        
        print(f"✓ Schema 文件存在: {schema_path}")
        print(f"✓ 包含佈局配置: {has_layout}")
        print(f"✓ 包含數據庫配置: {has_databases}")
        
        if has_databases:
            db_count = len(schema['databases'])
            print(f"✓ 數據庫數量: {db_count}")
            
            # 列出數據庫名稱
            for db in schema['databases']:
                db_name = db.get('db_name', 'Unknown')
                db_title = db.get('title', 'Unknown')
                print(f"  - {db_name}: {db_title}")
        
        print("\n✅ Schema 文件載入測試通過")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Schema JSON 解析錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ Schema 載入出錯: {e}")
        return False


def test_module_imports():
    """測試模組導入"""
    print("\n" + "="*60)
    print("測試 4: 模組導入")
    print("="*60)
    
    try:
        from integrations.notion import (
            NotionConfig,
            notion_config,
            NotionApiClient,
            NotionProcessor,
            execute_test_connection,
            execute_build_dashboard_layout,
            execute_delete_blocks,
            execute_create_database,
            setup_logging
        )
        
        print("✓ NotionConfig 類別")
        print("✓ notion_config 實例")
        print("✓ NotionApiClient 類別")
        print("✓ NotionProcessor 類別")
        print("✓ execute_test_connection 函數")
        print("✓ execute_build_dashboard_layout 函數")
        print("✓ execute_delete_blocks 函數")
        print("✓ execute_create_database 函數")
        print("✓ setup_logging 函數")
        
        print("\n✅ 所有模組導入成功")
        return True
        
    except ImportError as e:
        print(f"❌ 模組導入失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("\n" + "="*60)
    print("Notion 整合模組測試")
    print("="*60)
    
    # 載入環境變數
    load_dotenv()
    print("✓ 環境變數已載入")
    
    # 初始化日誌系統
    setup_logging()
    print("✓ 日誌系統已初始化")
    
    # 執行測試
    tests = [
        ("模組導入", test_module_imports),
        ("配置管理", test_config),
        ("Schema 載入", test_schema_loading),
        ("API 連接", test_connection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ 測試 '{test_name}' 出現異常: {e}")
            results.append((test_name, False))
    
    # 顯示測試結果摘要
    print("\n" + "="*60)
    print("測試結果摘要")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status} - {test_name}")
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！Notion 模組重構成功！")
        return 0
    else:
        print("\n⚠️  部分測試失敗，請檢查錯誤訊息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
