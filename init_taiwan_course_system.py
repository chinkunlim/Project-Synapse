#!/usr/bin/env python3
"""
台湾大学课程自动化系统 - 初始化脚本
用于配置和测试台湾课程格式处理系统
"""

import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_schedule_config():
    """测试节次时间配置"""
    print_header("1️⃣ 测试节次时间配置")
    
    from config.course_schedule_config import CLASS_PERIODS, get_period_time
    
    print(f"✅ 已加载 {len(CLASS_PERIODS)} 个节次\n")
    print("样本节次时间：")
    print(f"  第1节：{CLASS_PERIODS[1][0].strftime('%H:%M')} ~ {CLASS_PERIODS[1][1].strftime('%H:%M')}")
    print(f"  第9节：{CLASS_PERIODS[9][0].strftime('%H:%M')} ~ {CLASS_PERIODS[9][1].strftime('%H:%M')}")
    print(f"  第14节：{CLASS_PERIODS[14][0].strftime('%H:%M')} ~ {CLASS_PERIODS[14][1].strftime('%H:%M')}")
    
    return True


def test_schedule_parser():
    """测试课程时间解析"""
    print_header("2️⃣ 测试课程时间解析器")
    
    from utils.course_schedule_parser import CourseScheduleParser
    
    test_cases = [
        "三9",
        "三9/三10",
        "三9/三10/三11",
        "二2,五4",
        "一2/一3,四9/四10/四11",
    ]
    
    print("解析测试结果：\n")
    for test in test_cases:
        sessions = CourseScheduleParser.parse_schedule(test)
        print(f"输入：{test}")
        print(f"输出：{CourseScheduleParser.format_schedule_display(sessions)}")
        print()
    
    return True


def test_course_import():
    """测试课程导入处理"""
    print_header("3️⃣ 测试课程导入处理器")
    
    from utils.course_import_processor import CourseImportProcessor
    
    test_row = {
        '学年': '114',
        '学期': '1',
        '课程代码': 'CP__20500',
        '课程名称': '諮商理論與技術',
        '教师': '/余振民',
        '上课时间': '三9/三10/三11',
        '上课时数/学分': '3/3'
    }
    
    result = CourseImportProcessor.parse_course_row(test_row)
    
    if result:
        print(f"✅ 解析成功\n")
        print(f"课程名称：{result['name']}")
        print(f"教师：{result['instructor']}")
        print(f"上课时间：{result['schedule_display']}")
        print(f"学分：{result['credits']}")
        print(f"学年学期：{result['year']}-{result['semester']}")
        print()
        return True
    else:
        print(f"❌ 解析失败")
        return False


def test_semester_config():
    """测试学期配置"""
    print_header("4️⃣ 测试学期配置")
    
    from config.course_schedule_config import get_semester_info, get_all_semesters
    
    semesters = get_all_semesters()
    print(f"✅ 已配置 {len(semesters)} 个学期\n")
    print("学期信息：\n")
    
    for (year, semester), info in list(semesters.items())[:3]:  # 只显示前3个
        print(f"学年 {year} 学期 {semester}：")
        print(f"  开始：{info.start_date.strftime('%Y-%m-%d')}")
        print(f"  结束：{info.end_date.strftime('%Y-%m-%d')}")
        print()
    
    return True


def test_csv_import():
    """测试 CSV 导入"""
    print_header("5️⃣ 测试 CSV 导入")
    
    import csv
    from utils.course_import_processor import CourseImportProcessor
    
    csv_file = PROJECT_ROOT / "samples" / "course_import_example.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV 文件不存在：{csv_file}")
        return False
    
    print(f"读取 CSV 文件：{csv_file}\n")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        courses = []
        
        for row in reader:
            result = CourseImportProcessor.parse_course_row(row)
            if result:
                courses.append(result)
        
        if courses:
            print(f"✅ 成功解析 {len(courses)} 门课程\n")
            print("课程列表：\n")
            
            for i, course in enumerate(courses[:5], 1):  # 只显示前5个
                print(f"{i}. {course['name']}")
                print(f"   教师：{course['instructor']}")
                print(f"   时间：{course['schedule_display']}")
                print(f"   学分：{course['credits']}")
                print()
            
            if len(courses) > 5:
                print(f"... 还有 {len(courses) - 5} 门课程")
            
            return True
        else:
            print(f"❌ 无法解析任何课程")
            return False


def print_next_steps():
    """打印后续步骤"""
    print_header("✨ 下一步")
    
    print("""
1. 配置学期信息：
   
   方式 A - Google Calendar（推荐）:
   - 在 Google Calendar 中创建学期事件（格式：114-1-开始）
   - 获取 iCal URL
   - 编辑 utils/google_calendar_sync.py，设置 CALENDAR_URL
   - 运行：python3 utils/google_calendar_sync.py
   
   方式 B - 手动配置：
   - 编辑 config/course_schedule_config.py
   - 修改 SEMESTER_DATABASE 中的学期日期

2. 准备课程 CSV：
   - 参考 samples/course_import_example.csv
   - 按照格式准备你的课程数据

3. 导入课程：
   - 访问 http://localhost:5001/notion
   - 选择"课程"数据库
   - 上传 CSV 文件
   - 点击"上传并导入"

4. 在 Notion 中查看：
   - Course Hub：查看所有课程
   - Course Sessions：查看所有课程会话

📚 详细文档：
   - TAIWAN_COURSE_FORMAT_GUIDE.md - 完整使用指南
   - TAIWAN_COURSE_SYSTEM_README.md - 功能说明
    """)


def main():
    """主函数"""
    print("\n")
    print(" " * 20 + "🎓 台湾大学课程自动化系统")
    print(" " * 20 + "系统初始化和测试")
    print()
    
    tests = [
        ("节次时间配置", test_schedule_config),
        ("课程时间解析", test_schedule_parser),
        ("课程导入处理", test_course_import),
        ("学期配置", test_semester_config),
        ("CSV 导入", test_csv_import),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ {name} 失败：{str(e)}")
            results.append((name, False))
    
    # 打印总结
    print_header("📊 测试总结")
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print(f"\n总计：{passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n✨ 所有测试都通过了！系统已准备就绪。\n")
        print_next_steps()
        return 0
    else:
        print(f"\n❌ 有 {total - passed} 个测试失败，请检查错误信息。\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
