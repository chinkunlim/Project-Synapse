"""
课程导入处理器
处理台湾大学格式的课程 CSV 导入
支持自动解析课程时间和生成课程会话
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

from utils.course_schedule_parser import CourseScheduleParser
from config.course_schedule_config import get_semester_info

logger = logging.getLogger(__name__)


class CourseImportProcessor:
    """课程导入处理器"""
    
    @staticmethod
    def parse_course_row(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        解析课程 CSV 行数据
        
        预期格式：
        {
            '学年': '114',
            '学期': '1',
            '课程代码': 'CP__20500',
            '课程名称': '諮商理論與技術',
            '教师': '余振民',
            '上课时间': '三9/三10/三11',
            '上课时数/学分': '3/3'
        }
        
        Args:
            row: CSV 行数据
            
        Returns:
            解析后的课程信息字典或 None
        """
        try:
            # 提取字段（支持多种字段名）
            year = row.get('学年') or row.get('Year') or row.get('year')
            semester = row.get('学期') or row.get('Semester') or row.get('semester')
            code = row.get('课程代码') or row.get('Code') or row.get('code')
            name = row.get('课程名称') or row.get('Name') or row.get('name')
            instructor = row.get('教师') or row.get('Instructor') or row.get('instructor')
            schedule_str = row.get('上课时间') or row.get('Schedule') or row.get('schedule')
            credits_str = row.get('上课时数/学分') or row.get('Credits') or row.get('credits')
            
            if not all([year, semester, name, schedule_str]):
                return None
            
            try:
                year = int(year)
                semester = int(semester)
            except ValueError:
                logger.warning(f"无法解析学年或学期: {year}, {semester}")
                return None
            
            # 解析课程时间
            schedule_sessions = CourseScheduleParser.parse_schedule(schedule_str)
            
            if not schedule_sessions:
                logger.warning(f"无法解析课程时间: {schedule_str}")
                return None
            
            # 解析学分
            hours = None
            credits = None
            if credits_str:
                try:
                    parts = credits_str.split('/')
                    hours = int(parts[0]) if len(parts) > 0 else None
                    credits = int(parts[1]) if len(parts) > 1 else None
                except (ValueError, IndexError):
                    pass
            
            return {
                'year': year,
                'semester': semester,
                'code': code,
                'name': name.strip('/') if name else '',  # 移除前缀斜杠
                'instructor': instructor.strip('/') if instructor else '',  # 移除前缀斜杠
                'schedule_str': schedule_str,
                'schedule_sessions': schedule_sessions,
                'hours': hours,
                'credits': credits,
                'schedule_display': CourseScheduleParser.format_schedule_display(schedule_sessions)
            }
            
        except Exception as e:
            logger.error(f"解析课程行数据失败: {str(e)}")
            return None
    
    @staticmethod
    def get_course_dates(
        course_data: Dict[str, Any],
        exclude_dates: Optional[List[datetime]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取课程在整个学期内的所有上课日期
        
        Args:
            course_data: 解析后的课程数据
            exclude_dates: 要排除的日期（假期等）
            
        Returns:
            包含每个上课日期信息的字典列表
        """
        year = course_data['year']
        semester = course_data['semester']
        sessions = course_data['schedule_sessions']
        
        # 获取学期信息
        semester_info = get_semester_info(year, semester)
        if not semester_info:
            logger.warning(f"找不到学年 {year} 学期 {semester} 的信息")
            return []
        
        # 获取所有上课日期
        class_dates = CourseScheduleParser.get_class_dates(
            sessions,
            year,
            semester,
            exclude_dates
        )
        
        return class_dates
    
    @staticmethod
    def format_course_for_notion(course_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将解析后的课程数据格式化为 Notion 属性
        
        Args:
            course_data: 解析后的课程数据
            
        Returns:
            Notion 页面属性字典
        """
        properties = {
            'Name': {
                'title': [{'type': 'text', 'text': {'content': course_data['name']}}]
            },
            'Code': {
                'rich_text': [{'type': 'text', 'text': {'content': course_data.get('code', '')}}]
            },
            'Instructor': {
                'rich_text': [{'type': 'text', 'text': {'content': course_data.get('instructor', '')}}]
            },
            'Schedule': {
                'rich_text': [{'type': 'text', 'text': {'content': course_data['schedule_display']}}]
            },
            'Year': {
                'number': course_data['year']
            },
            'Semester': {
                'select': {'name': f'学期 {course_data["semester"]}'}
            }
        }
        
        if course_data.get('credits'):
            properties['Credits'] = {
                'number': course_data['credits']
            }
        
        if course_data.get('hours'):
            properties['Hours'] = {
                'number': course_data['hours']
            }
        
        return properties


def test_parser():
    """测试解析"""
    test_row = {
        '学年': '114',
        '学期': '1',
        '课程代码': 'CP__20500',
        '课程名称': '諮商理論與技術',
        '教师': '余振民',
        '上课时间': '三9/三10/三11',
        '上课时数/学分': '3/3'
    }
    
    print("===== 课程数据解析测试 =====\n")
    
    result = CourseImportProcessor.parse_course_row(test_row)
    
    if result:
        print(f"✅ 解析成功")
        print(f"课程名称: {result['name']}")
        print(f"教师: {result['instructor']}")
        print(f"上课时间: {result['schedule_display']}")
        print(f"学分: {result['credits']}")
        print(f"学年学期: {result['year']}-{result['semester']}")
    else:
        print(f"❌ 解析失败")


if __name__ == "__main__":
    test_parser()
