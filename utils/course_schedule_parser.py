"""
课程时间解析器
将 "三9/三10/三11" 这样的课程时间格式解析为具体的时间信息
"""

import re
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from config.course_schedule_config import (
    CLASS_PERIODS, WEEKDAY_MAP, get_semester_info, get_period_time
)


@dataclass
class ClassSession:
    """单个课堂信息"""
    weekday: int            # 星期（0=一, 1=二, ..., 6=日）
    start_period: int       # 开始节次
    end_period: int         # 结束节次
    start_time: time        # 开始时间
    end_time: time          # 结束时间
    date: Optional[datetime] = None  # 具体日期（如果已计算）
    
    def __str__(self):
        weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        return f"{weekday_names[self.weekday]} 第{self.start_period}-{self.end_period}节 ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"


class CourseScheduleParser:
    """课程时间解析器"""
    
    @staticmethod
    def parse_schedule(schedule_str: str) -> List[ClassSession]:
        """
        解析课程时间字符串
        支持格式：
        - "三9" - 星期三第9节
        - "三9/三10" - 星期三第9-10节
        - "三9/三10/三11" - 星期三第9-11节（连续）
        - "三9,四2" - 多个不连续的时间
        
        Args:
            schedule_str: 课程时间字符串，例："三9/三10/三11" 或 "二2,五4"
            
        Returns:
            ClassSession 列表
        """
        sessions = []
        
        # 按逗号分割（不同的上课时间）
        schedule_parts = [p.strip() for p in schedule_str.split(',')]
        
        for part in schedule_parts:
            # 解析单个时间段（可能包含斜杠表示连续节次）
            sessions.extend(CourseScheduleParser._parse_single_schedule(part))
        
        # 按星期和节次排序
        sessions.sort(key=lambda x: (x.weekday, x.start_period))
        
        return sessions
    
    @staticmethod
    def _parse_single_schedule(schedule_str: str) -> List[ClassSession]:
        """
        解析单个时间段
        例：
        - "三9" -> 星期三第9节
        - "三9/三10/三11" -> 星期三第9-11节
        - "三9/三10" -> 星期三第9-10节
        """
        sessions = []
        
        # 匹配模式：星期 + 节次 (例：三9, Mon4, Wed2)
        # 支持中文和英文星期
        pattern = r'([一二三四五六日a-zA-Z]+)(\d+)'
        matches = re.findall(pattern, schedule_str)
        
        if not matches:
            return sessions
        
        # 提取所有节次
        periods = []
        weekday = None
        
        for match in matches:
            weekday_str, period_str = match
            period = int(period_str)
            
            # 获取星期
            if weekday is None:
                weekday = WEEKDAY_MAP.get(weekday_str)
                if weekday is None:
                    return []  # 无效的星期
            
            periods.append(period)
        
        # 生成连续的节次范围
        if periods:
            min_period = min(periods)
            max_period = max(periods)
            
            # 获取开始和结束时间
            start_time_obj = get_period_time(min_period)
            end_time_obj = get_period_time(max_period)
            
            if start_time_obj and end_time_obj:
                session = ClassSession(
                    weekday=weekday,
                    start_period=min_period,
                    end_period=max_period,
                    start_time=start_time_obj[0],
                    end_time=end_time_obj[1]
                )
                sessions.append(session)
        
        return sessions
    
    @staticmethod
    def get_class_dates(
        sessions: List[ClassSession],
        semester_year: int,
        semester_num: int,
        exclude_dates: Optional[List[datetime]] = None
    ) -> List[Dict]:
        """
        根据课程时间和学期信息，获取该学期所有的上课日期
        
        Args:
            sessions: 课堂时间列表
            semester_year: 学年
            semester_num: 学期（1 或 2）
            exclude_dates: 要排除的日期（假期等）
            
        Returns:
            包含每个上课日期和时间信息的字典列表
        """
        exclude_dates = exclude_dates or []
        semester = get_semester_info(semester_year, semester_num)
        
        if not semester:
            return []
        
        class_dates = []
        current_date = semester.start_date
        
        while current_date <= semester.end_date:
            # 检查是否是课程的上课日期
            for session in sessions:
                if current_date.weekday() == session.weekday:
                    # 检查是否在排除日期中
                    if current_date not in exclude_dates:
                        class_dates.append({
                            'date': current_date,
                            'weekday': session.weekday,
                            'start_time': session.start_time,
                            'end_time': session.end_time,
                            'start_period': session.start_period,
                            'end_period': session.end_period,
                            'session_info': str(session)
                        })
            
            current_date += timedelta(days=1)
        
        return class_dates
    
    @staticmethod
    def format_schedule_display(sessions: List[ClassSession]) -> str:
        """
        格式化课程时间为显示字符串
        
        Args:
            sessions: 课堂时间列表
            
        Returns:
            格式化的显示字符串
        """
        if not sessions:
            return "无上课时间"
        
        return " | ".join(str(session) for session in sessions)


def test_parser():
    """测试解析器"""
    test_cases = [
        "三9/三10/三11",
        "二2,五4",
        "一1",
        "Wed9/Wed10",
    ]
    
    print("===== 课程时间解析测试 =====\n")
    
    for test in test_cases:
        try:
            sessions = CourseScheduleParser.parse_schedule(test)
            print(f"输入: {test}")
            if sessions:
                for session in sessions:
                    print(f"  {session}")
            else:
                print(f"  无法解析")
            print()
        except Exception as e:
            print(f"输入: {test} - 错误: {e}\n")


if __name__ == "__main__":
    test_parser()
