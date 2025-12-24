# Notion 整合模組 v2.0

重構後的 Notion 整合模組，提供更清晰、更易維護的架構。

## 📁 模組結構

```
intergrations/notion/
├── __init__.py          # 模組入口，統一導出介面
├── config.py            # 配置管理（統一管理所有配置）
├── client.py            # API 客戶端（處理 HTTP 請求）
├── processor.py         # 業務處理器（高層次操作）
├── logging.py           # 日誌系統配置
└── README.md           # 本文件
```

## ✨ 主要改進

### 1. **統一配置管理**
- ✅ 消除了重複的 Config 類別
- ✅ 集中管理所有環境變數和 INI 配置
- ✅ 提供便捷的屬性訪問介面

### 2. **清晰的職責分離**
- `config.py` - 配置管理
- `client.py` - API 通訊
- `processor.py` - 業務邏輯
- `logging.py` - 日誌記錄

### 3. **完善的錯誤處理**
- ✅ 所有關鍵操作都有錯誤處理
- ✅ 詳細的日誌記錄
- ✅ 友好的錯誤提示

### 4. **更好的類型提示**
- ✅ 使用 typing 模組提供類型提示
- ✅ 更好的 IDE 支持和代碼補全

### 5. **向後兼容**
- ✅ 保留舊的函數接口（execute_* 系列）
- ✅ 現有代碼無需修改即可運行

## 🚀 快速開始

### 基本使用

```python
from intergrations.notion import NotionProcessor, setup_logging

# 1. 初始化日誌（可選，建議在應用啟動時調用一次）
setup_logging()

# 2. 創建處理器
processor = NotionProcessor()

# 3. 測試連接
if processor.test_connection():
    print("Notion 連接成功！")

# 4. 構建儀表板佈局
processor.build_dashboard_layout()

# 5. 創建數據庫
processor.create_databases()

# 6. 清空頁面（如需要）
processor.delete_blocks()
```

### 使用自定義 API Key

```python
from intergrations.notion import NotionProcessor

# 使用自定義 API Key（而非環境變數）
processor = NotionProcessor(api_key="your_api_key_here")
processor.test_connection()
```

### 直接使用 API 客戶端

```python
from intergrations.notion import NotionApiClient

# 創建客戶端
client = NotionApiClient()

# 測試連接
user_info = client.test_connection()
print(f"用戶名稱: {user_info['name']}")

# 獲取頁面內容
response = client.get_block_children("page_id")
if response:
    blocks = response.json()["results"]
    print(f"找到 {len(blocks)} 個區塊")
```

### 訪問配置

```python
from intergrations.notion import notion_config

# 訪問配置值
print(f"API URL: {notion_config.base_url}")
print(f"API 版本: {notion_config.api_version}")
print(f"日誌級別: {notion_config.log_level}")

# 獲取環境變數
api_key = notion_config.api_key
parent_page_id = notion_config.parent_page_id

# 設置環境變數
notion_config.set_env("NEW_DATABASE_ID", "abc123...")

# 獲取所有 Notion 相關環境變數
env_vars = notion_config.get_all_env_vars()
```

## 🔧 配置文件

### config/notion_config.ini

```ini
[Logging]
log_folder = logs
log_filename = app.log
log_level = debug
log_format  = %%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s
log_encoding = utf-8

[Notion]
base_url = https://api.notion.com/v1
content_type = application/json
api_version = 2022-06-28
```

### 環境變數 (.env)

```bash
# Notion API
NOTION_API_KEY=your_api_key_here
PARENT_PAGE_ID=your_parent_page_id

# 數據庫 ID（初始化後自動填寫）
TASK_DATABASE_ID=
NOTION_DATABASE_ID=
COURSE_HUB_ID=
CLASS_SESSION_ID=
NOTE_DB_ID=
PROJECT_DB_ID=
RESOURCE_DB_ID=
```

## 📊 Schema 配置

數據庫結構定義在 `config/notion_schema.json` 中：

```json
{
  "layout": [ /* 頁面佈局配置 */ ],
  "databases": [
    {
      "db_name": "tasks",
      "title": "任務管理",
      "env_key": "TASK_DATABASE_ID",
      "properties": {
        "Name": { "title": {} },
        "Status": { "status": {} },
        "Date": { "date": {} }
      }
    }
  ]
}
```

## 🔄 遷移指南

### 舊代碼（v1.0）

```python
from intergrations.notion.processor import execute_test_connection
import os

api_key = os.getenv("NOTION_API_KEY")
execute_test_connection(api_key)
```

### 新代碼（v2.0 - 推薦）

```python
from intergrations.notion import NotionProcessor

processor = NotionProcessor()
processor.test_connection()
```

### 向後兼容（v2.0 - 仍可使用）

```python
from intergrations.notion import execute_test_connection
import os

api_key = os.getenv("NOTION_API_KEY")
execute_test_connection(api_key)  # 仍然可用！
```

## 📝 API 參考

### NotionConfig

| 方法/屬性 | 說明 |
|---------|------|
| `get_config(key, section, default)` | 從 INI 獲取配置 |
| `get_env(key, default)` | 獲取環境變數 |
| `set_env(key, value)` | 設置環境變數 |
| `api_key` | Notion API Key |
| `parent_page_id` | 父頁面 ID |
| `base_url` | API 基礎 URL |
| `schema_path` | Schema 文件路徑 |

### NotionApiClient

| 方法 | 說明 |
|-----|------|
| `test_connection()` | 測試 API 連接 |
| `append_block_children(page_id, blocks)` | 添加子區塊 |
| `get_block_children(page_id)` | 獲取子區塊 |
| `delete_block(block_id)` | 刪除區塊 |
| `create_database(payload)` | 創建數據庫 |
| `update_database(db_id, properties)` | 更新數據庫 |

### NotionProcessor

| 方法 | 說明 |
|-----|------|
| `test_connection()` | 測試連接 |
| `build_dashboard_layout(page_id)` | 構建儀表板佈局 |
| `create_databases(page_id)` | 創建所有數據庫 |
| `delete_blocks(page_id)` | 刪除所有區塊 |

## 🐛 故障排除

### 問題：找不到配置文件

```
ERROR: 找不到配置文件: config/notion_config.ini
```

**解決方案**：確保配置文件存在於正確的路徑，或使用默認值。

### 問題：API Key 未設置

```
ValueError: Notion API Key 未設置
```

**解決方案**：
1. 檢查 `.env` 文件中是否設置了 `NOTION_API_KEY`
2. 或在創建 Processor 時手動提供：`NotionProcessor(api_key="your_key")`

### 問題：日誌級別過高

如果看不到詳細日誌，調整 `config/notion_config.ini`：

```ini
[Logging]
log_level = DEBUG
```

## 📄 許可

此模組是 Project Synapse 的一部分。

## 🔗 相關資源

- [Notion API 文檔](https://developers.notion.com/)
- [Project Synapse 主頁](../../../README.md)
