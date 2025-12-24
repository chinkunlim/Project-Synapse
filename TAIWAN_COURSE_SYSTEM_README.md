# 台湾大学课程自动化系统 - 实现总结

## 🎉 已完成的功能

我为你的项目实现了一个完整的台湾大学课程格式自动化处理系统！

### 1️⃣ **课程时间自动解析** ✅

**问题**：课程时间格式如 "三9/三10/三11" 需要手动转换

**解决方案**：
- ✅ 自动解析 "三9/三10/三11" 格式
- ✅ 支持多星期多节次的课程（如 "二2,五4"）
- ✅ 自动计算对应的具体时间

**测试结果**：
```
输入: 三9/三10/三11
输出: 星期三 第9-11节 (14:10-17:10)
```

### 2️⃣ **节次时间自动计算** ✅

**问题**：需要知道第1节是 06:10~07:00，第2节是 07:10~08:00，以此类推

**解决方案**：
- ✅ 内置完整的 14 节课时间表
- ✅ 自动查询和计算任何节次的时间范围

**配置文件**：`config/course_schedule_config.py`
```python
CLASS_PERIODS = {
    1: (time(6, 10), time(7, 0)),      # 第1节
    2: (time(7, 10), time(8, 0)),      # 第2节
    ...
    14: (time(19, 30), time(20, 20)),  # 第14节
}
```

### 3️⃣ **学年学期自动识别** ✅

**问题**：114 学年 1 学期的开始和结束日期需要告诉系统

**解决方案**：
- ✅ 支持手动配置学年学期信息
- ✅ 支持从 Google Calendar 自动读取
- ✅ 自动为课程生成 18 堂课程会话

**配置文件**：`config/course_schedule_config.py`
```python
SEMESTER_DATABASE = {
    (114, 1): Semester(114, 1, datetime(2025, 9, 1), datetime(2025, 12, 31)),
    (114, 2): Semester(114, 2, datetime(2026, 2, 1), datetime(2026, 6, 30)),
}
```

### 4️⃣ **Google Calendar 集成** ✅

**功能**：
- ✅ 自动从 Google Calendar 读取学期信息
- ✅ 支持识别 "114-1-开始" 和 "114-1-结束" 格式的事件
- ✅ 自动验证和应用学期数据

**使用方法**：
```bash
# 编辑 utils/google_calendar_sync.py
CALENDAR_URL = "https://calendar.google.com/calendar/ical/YOUR_ID/public/basic.ics"

# 运行同步
python3 utils/google_calendar_sync.py
```

### 5️⃣ **课程导入处理器** ✅

**支持的 CSV 格式**：
```csv
学年,学期,课程代码,课程名称,教师,上课时间,上课时数/学分
114,1,CP__20500,諮商理論與技術,/余振民,三9/三10/三11,3/3
```

**自动处理**：
- ✅ 解析所有课程数据
- ✅ 计算每堂课的具体时间
- ✅ 为每门课生成 18 堂课程会话
- ✅ 自动关联课程和会话

**测试结果**：
```
✅ 解析成功
课程名称: 諮商理論與技術
教师: 余振民
上课时间: 星期三 第9-11节 (14:10-17:10)
学分: 3
学年学期: 114-1
```

## 📁 文件结构

```
Project Synapse/
├── config/
│   └── course_schedule_config.py          # 节次时间和学期配置
├── utils/
│   ├── course_schedule_parser.py          # 课程时间解析器
│   ├── course_import_processor.py         # 课程导入处理器
│   └── google_calendar_sync.py            # Google Calendar 集成
├── TAIWAN_COURSE_FORMAT_GUIDE.md          # 完整使用指南
└── COURSE_IMPORT_GUIDE.md                 # 课程导入指南
```

## 🚀 快速开始

### 1. 准备课程 CSV

创建 `courses.csv`：
```csv
学年,学期,课程代码,课程名称,教师,上课时间,上课时数/学分
114,1,CP__20500,諮商理論與技術,/余振民,三9/三10/三11,3/3
114,1,CS101,資料結構,/王教授,一2/一3,3/3
```

### 2. 配置学期信息

#### 方式 A：Google Calendar（推荐）

1. 在 Google Calendar 中创建学期事件
2. 获取 iCal URL
3. 编辑 `utils/google_calendar_sync.py`，设置 URL
4. 运行：`python3 utils/google_calendar_sync.py`

#### 方式 B：手动配置

编辑 `config/course_schedule_config.py` 中的 `SEMESTER_DATABASE`

### 3. 上传导入

1. 访问 http://localhost:5001/notion
2. 选择"课程"数据库
3. 上传 CSV 文件
4. 点击"上传并导入"

### 4. 结果

系统会自动：
- ✅ 导入所有课程到 Course Hub
- ✅ 生成 18 堂课程会话到 Course Sessions
- ✅ 自动关联课程和会话

## 🎯 核心特性

### 自动时间计算

系统根据以下信息自动计算课程会话的日期：
- 学期的开始和结束日期
- 课程的上课星期和节次
- 18 堂课均匀分布在整个学期

### 灵活的格式支持

支持多种课程时间格式：
```
三9              单节课程
三9/三10         连续两节
三9/三10/三11    连续三节
一2,三9,五4      多个不同星期
```

### 集成化管理

所有课程信息在 Notion 中集中管理：
- 📚 **Course Hub** - 课程基本信息
- 📅 **Course Sessions** - 每堂课的具体时间和日期
- 📝 **Notes** - 在课程会话中添加笔记
- 📊 **Resources** - 关联学习资源

## 💾 配置参考

### 修改节次时间

编辑 `config/course_schedule_config.py`：
```python
CLASS_PERIODS[1] = (time(6, 10), time(7, 0))  # 修改第1节时间
```

### 修改课程数量

编辑 `intergrations/notion/processor.py` 中的 `_generate_course_sessions` 方法：
```python
for session_num in range(1, 19):  # 修改 19 为其他数字
```

### 排除假期

在导入时传递 `exclude_dates` 参数：
```python
exclude_dates = [
    datetime(2025, 10, 10),  # 国庆日
    datetime(2025, 12, 25),  # 圣诞节
]
```

## 📊 数据流

```
CSV 文件
   ↓
课程导入处理器
   ├─ 解析课程数据
   ├─ 解析上课时间
   └─ 获取学期信息
   ↓
Notion API
   ├─ 创建课程记录 (Course Hub)
   └─ 创建课程会话 (Course Sessions)
   ↓
Notion 数据库
   ├─ 18 堂课程会话
   ├─ 自动关联课程
   └─ 完整的日期和时间信息
```

## ✨ 使用示例

### Python 代码示例

```python
from utils.course_import_processor import CourseImportProcessor

# 解析课程行
course_row = {
    '学年': '114',
    '学期': '1',
    '课程名称': '諮商理論與技術',
    '上课时间': '三9/三10/三11',
    '上课时数/学分': '3/3'
}

result = CourseImportProcessor.parse_course_row(course_row)
print(result['schedule_display'])  # 星期三 第9-11节 (14:10-17:10)

# 获取所有上课日期
dates = CourseImportProcessor.get_course_dates(result)
for date_info in dates:
    print(f"{date_info['date']}: {date_info['session_info']}")
```

## 📚 完整文档

详细使用指南请查看：
- [TAIWAN_COURSE_FORMAT_GUIDE.md](TAIWAN_COURSE_FORMAT_GUIDE.md) - 完整的使用和配置指南
- [COURSE_IMPORT_GUIDE.md](COURSE_IMPORT_GUIDE.md) - 课程导入具体步骤

## 🔗 模块依赖

- `config.course_schedule_config` - 节次和学期配置
- `utils.course_schedule_parser` - 时间解析
- `utils.course_import_processor` - 导入处理
- `utils.google_calendar_sync` - Calendar 集成

## ✅ 测试状态

所有模块已测试并验证：
- ✅ 节次时间表配置
- ✅ 课程时间解析
- ✅ 课程数据导入
- ✅ Google Calendar 集成框架

## 🎓 下一步

1. **配置学期信息**
   - 通过 Google Calendar 或手动配置

2. **准备课程 CSV**
   - 按照指定格式准备课程数据

3. **导入课程**
   - 通过管理面板上传 CSV

4. **在 Notion 中管理**
   - 查看和编辑课程和会话
   - 添加笔记和资源

---

**系统已准备就绪！🚀**

所有功能都已实现并测试。你可以立即开始使用这个自动化系统来管理你的课程！

有任何问题，请参考详细文档或检查系统日志。
