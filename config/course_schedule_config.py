"""
课程时间表配置
定义每个节次的时间映射和学年学期信息
"""

from datetime import time, datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# ===============================
# 节次时间定义
# ===============================
CLASS_PERIODS = {
    1: (time(6, 10), time(7, 0)),      # 第1节：06:10~07:00
    2: (time(7, 10), time(8, 0)),      # 第2节：07:10~08:00
    3: (time(8, 10), time(9, 0)),      # 第3节：08:10~09:00
    4: (time(9, 10), time(10, 0)),     # 第4节：09:10~10:00
    5: (time(10, 20), time(11, 10)),   # 第5节：10:20~11:10
    6: (time(11, 20), time(12, 10)),   # 第6节：11:20~12:10
    7: (time(12, 10), time(13, 0)),    # 第7节：12:10~13:00
    8: (time(13, 10), time(14, 0)),    # 第8节：13:10~14:00
    9: (time(14, 10), time(15, 0)),    # 第9节：14:10~15:00
    10: (time(15, 10), time(16, 0)),   # 第10节：15:10~16:00
    11: (time(16, 20), time(17, 10)),  # 第11节：16:20~17:10
    12: (time(17, 20), time(18, 10)),  # 第12节：17:20~18:10
    13: (time(18, 30), time(19, 20)),  # 第13节：18:30~19:20
    14: (time(19, 30), time(20, 20)),  # 第14节：19:30~20:20
}

# ===============================
# 星期映射
# ===============================
WEEKDAY_MAP = {
    '一': 0,   # 星期一
    '二': 1,   # 星期二
    '三': 2,   # 星期三
    '四': 3,   # 星期四
    '五': 4,   # 星期五
    '六': 5,   # 星期六
    '日': 6,   # 星期日
    'Mon': 0, 'Monday': 0,
    'Tue': 1, 'Tuesday': 1,
    'Wed': 2, 'Wednesday': 2,
    'Thu': 3, 'Thursday': 3,
    'Fri': 4, 'Friday': 4,
    'Sat': 5, 'Saturday': 5,
    'Sun': 6, 'Sunday': 6,
}

# ===============================
# 学年学期信息
# ===============================
@dataclass
class Semester:
    """学期信息数据类"""
    year: int              # 学年（例：114）
    semester: int          # 学期（1 或 2）
    start_date: datetime   # 学期开始日期
    end_date: datetime     # 学期结束日期
    
    def __str__(self):
        return f"学年 {self.year} 第 {self.semester} 学期 ({self.start_date.strftime('%Y-%m-%d')} 到 {self.end_date.strftime('%Y-%m-%d')})"


# 默认学年学期配置
# 可以从 Google Calendar 或数据库动态更新
SEMESTER_DATABASE = {
    (113, 1): Semester(113, 1, datetime(2024, 9, 1), datetime(2025, 1, 31)),
    (113, 2): Semester(113, 2, datetime(2025, 2, 1), datetime(2025, 6, 30)),
    (114, 1): Semester(114, 1, datetime(2025, 9, 1), datetime(2026, 1, 31)),
    (114, 2): Semester(114, 2, datetime(2026, 2, 23), datetime(2026, 6, 30)),
    (115, 1): Semester(115, 1, datetime(2026, 9, 1), datetime(2027, 1, 31)),
    (115, 2): Semester(115, 2, datetime(2027, 2, 1), datetime(2027, 6, 30)),
}


def get_period_time(period: int) -> Optional[Tuple[time, time]]:
    """
    获取指定节次的时间范围
    
    Args:
        period: 节次号（1-14）
        
    Returns:
        (开始时间, 结束时间) 或 None
    """
    return CLASS_PERIODS.get(period)


def get_semester_info(year: int, semester: int) -> Optional[Semester]:
    """
    获取指定学年学期的信息
    
    Args:
        year: 学年
        semester: 学期
        
    Returns:
        Semester 对象或 None
    """
    return SEMESTER_DATABASE.get((year, semester))


def update_semester_info(year: int, semester: int, start_date: datetime, end_date: datetime):
    """
    更新或添加学期信息
    
    Args:
        year: 学年
        semester: 学期
        start_date: 学期开始日期
        end_date: 学期结束日期
    """
    SEMESTER_DATABASE[(year, semester)] = Semester(year, semester, start_date, end_date)


def get_all_semesters() -> Dict[Tuple[int, int], Semester]:
    """获取所有学期信息"""
    return SEMESTER_DATABASE.copy()


if __name__ == "__main__":
    # 测试
    print("===== 节次时间表 =====")
    for period, (start, end) in CLASS_PERIODS.items():
        print(f"第 {period:2d} 节：{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}")
    
    print("\n===== 学期信息 =====")
    for (year, semester), info in SEMESTER_DATABASE.items():
        print(f"{info}")
