# 📑 台湾大学课程自动化系统 - 文档索引

## 🎯 快速导航

### 🚀 我想快速开始
👉 **[QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)** (5 分钟)
- 3 步快速启动
- 时间格式参考
- 常见问题解答

### 📖 我想了解详细用法
👉 **[TAIWAN_COURSE_FORMAT_GUIDE.md](TAIWAN_COURSE_FORMAT_GUIDE.md)** (15 分钟)
- 完整格式说明
- CSV 字段详解
- 高级配置选项
- 故障排除

### 🏗️ 我想了解系统架构
👉 **[TAIWAN_COURSE_SYSTEM_README.md](TAIWAN_COURSE_SYSTEM_README.md)** (20 分钟)
- 系统设计
- 模块说明
- 数据流图
- 扩展指南

### 📊 我想看项目总结
👉 **[SYSTEM_COMPLETION_REPORT.md](SYSTEM_COMPLETION_REPORT.md)** (10 分钟)
- 项目完成度
- 功能清单
- 测试结果
- 后续步骤

### 🔍 我想快速了解全貌
👉 **[SYSTEM_OVERVIEW.txt](SYSTEM_OVERVIEW.txt)** (5 分钟)
- ASCII 格式概览
- 关键特性列表
- 文件结构树
- 测试结果表

---

## 📚 按类别浏览文档

### 快速参考
| 文档 | 内容 | 读时间 |
|-----|------|--------|
| [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) | 3步开始，快速参考 | 5 分钟 |
| [SYSTEM_OVERVIEW.txt](SYSTEM_OVERVIEW.txt) | ASCII 艺术概览 | 5 分钟 |

### 详细指南
| 文档 | 内容 | 读时间 |
|-----|------|--------|
| [TAIWAN_COURSE_FORMAT_GUIDE.md](TAIWAN_COURSE_FORMAT_GUIDE.md) | 完整使用教程 | 15 分钟 |
| [TAIWAN_COURSE_SYSTEM_README.md](TAIWAN_COURSE_SYSTEM_README.md) | 系统架构和设计 | 20 分钟 |
| [SYSTEM_COMPLETION_REPORT.md](SYSTEM_COMPLETION_REPORT.md) | 项目完成报告 | 10 分钟 |
| [GOOGLE_KEEP_LIMITATIONS.md](GOOGLE_KEEP_LIMITATIONS.md) | Google Keep 限制与替代方案 | 5 分钟 |

### 代码和数据
| 文件 | 用途 |
|------|------|
| [samples/course_import_example.csv](samples/course_import_example.csv) | 9 门示例课程（直接使用） |
| [init_taiwan_course_system.py](init_taiwan_course_system.py) | 系统初始化和测试脚本 |

### 配置文件
| 文件 | 用途 |
|------|------|
| [config/course_schedule_config.py](config/course_schedule_config.py) | 节次和学期配置 |
| [utils/course_schedule_parser.py](utils/course_schedule_parser.py) | 时间解析器 |
| [utils/course_import_processor.py](utils/course_import_processor.py) | CSV 处理器 |
| [utils/google_calendar_sync.py](utils/google_calendar_sync.py) | Google Calendar 集成 |

---

## 🎓 学习路径

### 路径 1: 快速使用（推荐新用户）
```
1. 读 QUICK_START_GUIDE.md (5 分钟)
2. 运行 init_taiwan_course_system.py (2 分钟)
3. 按 3 步指南导入课程 (10 分钟)
4. 在 Notion 中查看结果 ✨
```

### 路径 2: 完整理解
```
1. 读 SYSTEM_OVERVIEW.txt (5 分钟) - 了解全貌
2. 读 QUICK_START_GUIDE.md (5 分钟) - 基础操作
3. 读 TAIWAN_COURSE_FORMAT_GUIDE.md (15 分钟) - 详细用法
4. 读 TAIWAN_COURSE_SYSTEM_README.md (20 分钟) - 系统设计
5. 浏览代码文件 - 深入理解实现
```

### 路径 3: 高级配置
```
1. 阅读 TAIWAN_COURSE_FORMAT_GUIDE.md 的"高级配置"部分
2. 选择 Google Calendar 或手动配置
3. 修改 config/course_schedule_config.py
4. 运行 utils/google_calendar_sync.py（如使用 Google Calendar）
```

---

## 📋 常见任务速查

### 任务：导入我的课程
1. 准备 CSV 文件（格式见 QUICK_START_GUIDE.md）
2. 运行 `python3 app.py`
3. 访问 http://localhost:5001/notion
4. 按 3 步指南上传 CSV

📖 详见: [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md#快速开始-3-步)

### 任务：修改节次时间
1. 打开 `config/course_schedule_config.py`
2. 编辑 `CLASS_PERIODS` 字典
3. 保存文件

📖 详见: [TAIWAN_COURSE_FORMAT_GUIDE.md](TAIWAN_COURSE_FORMAT_GUIDE.md#常见问题)

### 任务：添加新学期
1. 打开 `config/course_schedule_config.py`
2. 在 `SEMESTER_DATABASE` 添加新条目
3. 运行 `python3 init_taiwan_course_system.py` 验证

📖 详见: [TAIWAN_COURSE_FORMAT_GUIDE.md](TAIWAN_COURSE_FORMAT_GUIDE.md#常见问题)

### 任务：使用 Google Calendar
1. 在 Google Calendar 中创建学期事件
2. 获取 iCal URL
3. 编辑 `utils/google_calendar_sync.py`
4. 运行同步脚本

📖 详见: [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md#方式-a：google-calendar推荐)

### 任务：故障排除
参考以下文件的故障排除部分：
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md#常见问题)
- [TAIWAN_COURSE_FORMAT_GUIDE.md](TAIWAN_COURSE_FORMAT_GUIDE.md#常见问题)

---

## 🔍 按关键词查找

### 关于时间和节次
- 节次时间表：[QUICK_START_GUIDE.md - 节次时间表](QUICK_START_GUIDE.md#节次时间表)
- 时间格式规则：[QUICK_START_GUIDE.md - 时间格式规则](QUICK_START_GUIDE.md#时间格式规则)
- 星期缩写：[QUICK_START_GUIDE.md - 星期缩写](QUICK_START_GUIDE.md#星期缩写)

### 关于 CSV 导入
- CSV 字段说明：[QUICK_START_GUIDE.md - CSV 字段说明](QUICK_START_GUIDE.md#csv-字段说明)
- 示例 CSV：[samples/course_import_example.csv](samples/course_import_example.csv)
- 导入步骤：[QUICK_START_GUIDE.md - 快速开始](QUICK_START_GUIDE.md#快速开始-3-步)

### 关于学期配置
- 学期选项：[QUICK_START_GUIDE.md - 高级配置](QUICK_START_GUIDE.md#高级配置)
- Google Calendar：[QUICK_START_GUIDE.md - 方式 A](QUICK_START_GUIDE.md#方式-a：google-calendar推荐)
- 手动配置：[QUICK_START_GUIDE.md - 方式 B](QUICK_START_GUIDE.md#方式-b：手动配置)

### 关于调试和日志
- 测试系统：[QUICK_START_GUIDE.md - 测试和验证](QUICK_START_GUIDE.md#测试和验证)
- 查看日志：[QUICK_START_GUIDE.md - 调试和日志](QUICK_START_GUIDE.md#调试和日志)
- 故障排除：[QUICK_START_GUIDE.md - 常见问题](QUICK_START_GUIDE.md#常见问题)

---

## 📊 文档特色

### QUICK_START_GUIDE.md ⭐⭐⭐⭐⭐
**最实用的文档**
- 最快上手
- 包含所有必要信息
- 清晰的分步骤
- Q&A 模块

### TAIWAN_COURSE_FORMAT_GUIDE.md ⭐⭐⭐⭐
**最全面的指南**
- 详细的使用说明
- 完整的格式参考
- 多个实际例子
- 高级配置指导

### TAIWAN_COURSE_SYSTEM_README.md ⭐⭐⭐
**最深入的资源**
- 系统架构解析
- 技术实现细节
- 代码示例
- 扩展指南

### SYSTEM_COMPLETION_REPORT.md ⭐⭐
**项目总结**
- 功能清单
- 测试结果
- 完成状态
- 后续建议

### SYSTEM_OVERVIEW.txt ⭐⭐
**快速参考**
- ASCII 格式
- 一页纸概览
- 关键特性列表
- 快速查找

---

## ⚡ 5 分钟快速入门

1. **阅读 SYSTEM_OVERVIEW.txt**
   ```bash
   cat SYSTEM_OVERVIEW.txt
   ```

2. **运行验证**
   ```bash
   python3 init_taiwan_course_system.py
   ```

3. **查看示例**
   ```bash
   cat samples/course_import_example.csv
   ```

4. **启动应用**
   ```bash
   python3 app.py
   # 访问 http://localhost:5001/notion
   ```

5. **导入课程**
   - 选择 "课程" 数据库
   - 上传 CSV 文件
   - 点击 "上传并导入"

✨ **完成！** 你的课程已自动导入 Notion

---

## 🎯 推荐阅读顺序

| 步骤 | 文档 | 时间 | 目标 |
|------|------|------|------|
| 1 | SYSTEM_OVERVIEW.txt | 5分钟 | 了解全貌 |
| 2 | QUICK_START_GUIDE.md | 5分钟 | 快速开始 |
| 3 | init_taiwan_course_system.py | 2分钟 | 验证系统 |
| 4 | samples/course_import_example.csv | 1分钟 | 查看示例 |
| 5 | TAIWAN_COURSE_FORMAT_GUIDE.md | 15分钟 | 深入了解 |
| 6 | TAIWAN_COURSE_SYSTEM_README.md | 20分钟 | 理解架构 |

**总计**: 48 分钟完全掌握系统 📚

---

## 💡 使用小贴士

### Tip 1: 打开 QUICK_START_GUIDE.md 同时使用系统
大多数操作都可以参考这个文档快速完成

### Tip 2: 保存示例 CSV
`samples/course_import_example.csv` 可以作为模板重复使用

### Tip 3: 定期运行测试
```bash
python3 init_taiwan_course_system.py
```
确保系统正常运行

### Tip 4: 检查日志
系统出现问题时，查看 `logs/` 目录下的日志文件

### Tip 5: 备份配置
修改 `config/course_schedule_config.py` 前，备份一份副本

---

## 🆘 需要帮助？

### 问题 1: 找不到某个功能
→ 查看 [TAIWAN_COURSE_FORMAT_GUIDE.md](TAIWAN_COURSE_FORMAT_GUIDE.md)

### 问题 2: 导入失败
→ 查看 [QUICK_START_GUIDE.md - 常见问题](QUICK_START_GUIDE.md#常见问题)

### 问题 3: 不知道如何开始
→ 按照 [QUICK_START_GUIDE.md - 快速开始](QUICK_START_GUIDE.md#快速开始-3-步) 操作

### 问题 4: 想了解技术细节
→ 查看 [TAIWAN_COURSE_SYSTEM_README.md](TAIWAN_COURSE_SYSTEM_README.md)

### 问题 5: 需要验证系统是否正常
→ 运行 `python3 init_taiwan_course_system.py`

---

## 📞 文件位置速查

```
Project Synapse/
├── 📄 DOCUMENT_INDEX.md ..................... 这个文件
├── 📄 QUICK_START_GUIDE.md ................ ⭐ 从这里开始
├── 📄 TAIWAN_COURSE_FORMAT_GUIDE.md ..... 详细指南
├── 📄 TAIWAN_COURSE_SYSTEM_README.md ... 架构设计
├── 📄 SYSTEM_COMPLETION_REPORT.md ...... 项目总结
├── 📄 SYSTEM_OVERVIEW.txt .............. 快速参考
│
├── 🐍 init_taiwan_course_system.py .... 测试脚本
│
├── config/course_schedule_config.py ... 配置文件
├── utils/course_schedule_parser.py ... 时间解析
├── utils/course_import_processor.py .. CSV处理
├── utils/google_calendar_sync.py .... 日历集成
│
├── samples/course_import_example.csv . 示例数据
└── templates/notion_admin.html ...... Web界面
```

---

## 🚀 现在就开始

**第一步**: 阅读 [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)

**第二步**: 运行 `python3 init_taiwan_course_system.py`

**第三步**: 按照 3 步指南导入你的课程

**第四步**: 在 Notion 中享受自动化的课程管理！

---

**版本**: 1.0  
**状态**: ✅ 完全就绪  
**最后更新**: 2025年1月

**🎓 Project Synapse | Taiwan Course System**
