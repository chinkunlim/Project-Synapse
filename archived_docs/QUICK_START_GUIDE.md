# 🎓 台湾大学课程自动化系统 - 快速参考

## ✅ 系统状态

所有 5 个核心测试都已通过：
- ✅ 节次时间配置 (14个节次)
- ✅ 课程时间解析 (支持复杂格式)
- ✅ 课程导入处理 (自动转换格式)
- ✅ 学期配置 (支持多学期)
- ✅ CSV 导入 (已验证 9 门示例课程)

## 🚀 快速开始 (3 步)

### 1️⃣ 启动应用
```bash
cd /Users/limchinkun/Desktop/Project\ Synapse
python3 app.py
# 访问 http://localhost:5001/notion
```

### 2️⃣ 准备课程 CSV
使用提供的模板格式：
```csv
学年,学期,课程代码,课程名称,教师,上课时间,上课时数/学分
114,1,CP__20500,諮商理論與技術,/余振民,三9/三10/三11,3/3
114,1,CS101,資料結構,/王教授,一2/一3,3/3
```

**参考文件**：`samples/course_import_example.csv`

### 3️⃣ 导入课程
1. 进入 http://localhost:5001/notion
2. 在"Notion 数据库"部分找到"导入 CSV"
3. 选择"课程"（Course Hub）数据库
4. 选择学期：输入开始日期和结束日期
5. 上传 CSV 文件
6. 点击"上传并导入"

**结果**：
- 每门课程自动导入到 Course Hub
- 每门课程自动生成 18 个 class sessions
- 所有时间和日期自动计算

---

## 📅 台湾课程时间格式

### 节次时间表
| 节次 | 开始 | 结束 | 节次 | 开始 | 结束 |
|-----|------|------|-----|------|------|
| 1 | 06:10 | 07:00 | 8 | 12:10 | 13:00 |
| 2 | 07:10 | 08:00 | 9 | 14:10 | 15:00 |
| 3 | 08:10 | 09:00 | 10 | 15:10 | 16:00 |
| 4 | 09:10 | 10:00 | 11 | 16:10 | 17:00 |
| 5 | 10:10 | 11:00 | 12 | 17:10 | 18:00 |
| 6 | 11:10 | 12:00 | 13 | 18:10 | 19:00 |
| 7 | 12:00 | 12:50 | 14 | 19:30 | 20:20 |

### 时间格式规则

#### 基本格式
- **一2** = 星期一第2节 (07:10-08:00)
- **三9** = 星期三第9节 (14:10-15:00)
- **五11** = 星期五第11节 (16:10-17:00)

#### 连续节次
- **一2/一3** = 星期一第2-3节 (07:10-09:00)
- **三9/三10/三11** = 星期三第9-11节 (14:10-17:10)

#### 多个时间块
- **一2,五4** = 星期一第2节 + 星期五第4节
- **一2/一3,四9/四10** = 星期一第2-3节 + 星期四第9-10节

### 星期缩写
| 中文 | English | 代码 |
|------|---------|------|
| 星期一 | Monday | 一 |
| 星期二 | Tuesday | 二 |
| 星期三 | Wednesday | 三 |
| 星期四 | Thursday | 四 |
| 星期五 | Friday | 五 |
| 星期六 | Saturday | 六 |
| 星期日 | Sunday | 日 |

---

## 📊 CSV 字段说明

### 必填字段
| 字段 | 说明 | 例子 |
|------|------|------|
| 学年 | 民国年 | 114 |
| 学期 | 1 或 2 | 1 |
| 课程代码 | 课程编号 | CP__20500 |
| 课程名称 | 课程中文名称 | 諮商理論與技術 |
| 教师 | 授课教师（支持 `/` 前缀） | /余振民 或 余振民 |
| 上课时间 | 台湾格式时间 | 三9/三10/三11 |
| 上课时数/学分 | 格式：时数/学分 | 3/3 |

### 示例行
```
114,1,CP__20500,諮商理論與技術,/余振民,三9/三10/三11,3/3
```

---

## 🔧 高级配置

### 方式 A：Google Calendar（推荐）

#### 步骤 1：创建学期事件
在 Google Calendar 中为每个学期创建事件，格式为：
- **开始事件**：`114-1-开始` (设置为学期第一天)
- **结束事件**：`114-1-结束` (设置为学期最后一天)

#### 步骤 2：获取 iCal URL
1. Google Calendar → 设置 → 日历
2. 在"日历地址"部分找到"私密 iCal 地址"
3. 复制 URL

#### 步骤 3：配置系统
编辑 `utils/google_calendar_sync.py`：
```python
CALENDAR_URL = "你的_iCal_URL"
```

#### 步骤 4：同步学期
```bash
cd /Users/limchinkun/Desktop/Project\ Synapse
python3 utils/google_calendar_sync.py
```

### 方式 B：手动配置

编辑 `config/course_schedule_config.py`：

```python
from datetime import datetime

SEMESTER_DATABASE = {
    (114, 1): Semester(
        year=114,
        semester=1,
        start_date=datetime(2025, 9, 1),   # 学期开始日期
        end_date=datetime(2025, 12, 31)    # 学期结束日期
    ),
    (114, 2): Semester(
        year=114,
        semester=2,
        start_date=datetime(2026, 2, 1),
        end_date=datetime(2026, 6, 30)
    ),
}
```

---

## 📚 文件结构

```
config/
├── course_schedule_config.py      # 节次配置和学期数据库
└── notion_config.ini              # Notion API 配置

utils/
├── course_schedule_parser.py      # 时间解析引擎
├── course_import_processor.py     # CSV 处理器
└── google_calendar_sync.py        # Google Calendar 集成

intergrations/notion/
├── processor.py                   # Notion API（已更新支持课程导入）
└── client.py

templates/
├── notion_admin.html              # 管理界面（已更新课程导入UI）
└── index.html

samples/
└── course_import_example.csv      # 9 门示例课程

app.py                             # Flask 应用入口
init_taiwan_course_system.py       # 初始化和测试脚本
```

---

## 🧪 测试和验证

### 运行完整系统测试
```bash
python3 init_taiwan_course_system.py
```

输出应包括：
- ✅ 5/5 个测试通过
- 详细的解析示例
- 所有 9 个示例课程的解析结果

### 单独测试组件

#### 测试时间解析
```bash
python3 << 'EOF'
from utils.course_schedule_parser import CourseScheduleParser

result = CourseScheduleParser.parse_schedule("三9/三10/三11")
display = CourseScheduleParser.format_schedule_display(result)
print(display)  # 星期三 第9-11节 (14:10-17:10)
EOF
```

#### 测试课程导入
```bash
python3 << 'EOF'
from utils.course_import_processor import CourseImportProcessor

row = {
    '学年': '114',
    '学期': '1',
    '课程代码': 'CP__20500',
    '课程名称': '諮商理論與技術',
    '教师': '/余振民',
    '上课时间': '三9/三10/三11',
    '上课时数/学分': '3/3'
}

result = CourseImportProcessor.parse_course_row(row)
print(f"课程名称：{result['name']}")
print(f"上课时间：{result['schedule_display']}")
EOF
```

---

## 🐛 常见问题

### Q: CSV 导入后找不到课程？
**A**: 确认：
1. 在 Notion 中创建了 "Course Hub" 数据库
2. CSV 格式正确（参考 `samples/course_import_example.csv`）
3. 学年/学期与配置中的学期匹配
4. 检查应用日志是否有错误

### Q: 时间显示不正确？
**A**: 检查：
1. 节次配置是否正确（见时间表）
2. 时间格式是否按照台湾格式（例如 "三9/三10"）
3. 学期日期是否正确设置

### Q: 如何添加新的学期？
**A**: 编辑 `config/course_schedule_config.py`：
```python
SEMESTER_DATABASE[(115, 1)] = Semester(
    year=115,
    semester=1,
    start_date=datetime(2026, 9, 1),
    end_date=datetime(2026, 12, 31)
)
```

### Q: 能否修改节次时间？
**A**: 能。编辑 `config/course_schedule_config.py` 的 `CLASS_PERIODS` 字典，例如：
```python
CLASS_PERIODS[9] = (time(14, 10), time(15, 0))  # 修改第9节时间
```

---

## 📞 调试和日志

应用日志位置：`logs/` 目录

查看最新日志：
```bash
tail -f logs/app.log
```

启用调试模式（编辑 `app.py`）：
```python
app.run(debug=True, port=5001)
```

---

## ✨ 下一步

1. **立即尝试**：运行示例 CSV 导入
2. **配置学期**：设置你的学期日期（Google Calendar 或手动）
3. **准备数据**：将你的课程数据转换为 CSV 格式
4. **批量导入**：上传你的完整课程列表
5. **在 Notion 中使用**：开始规划和管理课程

---

## 📖 详细文档

- **TAIWAN_COURSE_FORMAT_GUIDE.md** - 完整使用指南和示例
- **TAIWAN_COURSE_SYSTEM_README.md** - 系统架构和设计文档
- **samples/course_import_example.csv** - 可直接使用的示例数据

---

**版本**: 1.0  
**最后更新**: 2025年1月  
**状态**: 生产就绪 ✅
