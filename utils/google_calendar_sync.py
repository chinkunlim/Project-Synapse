"""
Google Calendar 集成
从 Google Calendar 读取学年学期信息
"""

import re
from datetime import datetime
from typing import Optional, Dict, Tuple
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# 确保可以从项目根目录导入 config 模块
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class GoogleCalendarIntegration:
    """Google Calendar 集成"""
    
    @staticmethod
    def extract_semester_from_ical_url(ical_url: str) -> Dict[Tuple[int, int], Dict]:
        """
        从 Google Calendar iCal URL 提取学年学期信息
        
        Google Calendar 分享链接格式：
        https://calendar.google.com/calendar/u/0/r
        
        iCal URL 格式：
        https://calendar.google.com/calendar/ical/{calendar-id}/public/basic.ics
        
        Args:
            ical_url: Google Calendar 的 iCal URL
            
        Returns:
            {(year, semester): {'start': datetime, 'end': datetime}} 的字典
        """
        try:
            import requests
            
            # 获取 iCal 数据
            response = requests.get(ical_url, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.error(f"无法访问 Google Calendar URL: {response.status_code}")
                return {}
            
            return GoogleCalendarIntegration._parse_ical_events(response.text)
            
        except Exception as e:
            logger.error(f"从 Google Calendar 读取数据失败: {str(e)}")
            return {}
    
    @staticmethod
    def _parse_ical_events(ical_content: str) -> Dict[Tuple[int, int], Dict]:
        """
        解析 iCal 格式的日历数据。
        支持的事件标题示例：
        - "114-1-开始" / "114-1-结束"
        - "108學年度第一學期開始"
        - "第1學期結束"（会根据日期推算学年度）
        """
        semesters: Dict[Tuple[int, int], Dict] = {}

        lines = ical_content.split('\n')
        current_event: Dict[str, str] = {}

        for line in lines:
            line = line.strip()

            if line.startswith('BEGIN:VEVENT'):
                current_event = {}
            elif line.startswith('END:VEVENT'):
                if 'SUMMARY' in current_event and 'DTSTART' in current_event:
                    GoogleCalendarIntegration._process_event(current_event, semesters)
            elif line.startswith('SUMMARY:'):
                current_event['SUMMARY'] = line[8:]
            elif line.startswith('DTSTART'):
                date_match = re.search(r'(\d{8})', line)
                if date_match:
                    date_str = date_match.group(1)
                    try:
                        current_event['DTSTART'] = datetime.strptime(date_str, '%Y%m%d')
                    except ValueError:
                        pass

        return semesters
    
    @staticmethod
    def _process_event(event: Dict, semesters: Dict):
        """处理单个日历事件，支持多种命名模式。"""
        summary = event.get('SUMMARY', '').strip()
        date: datetime = event.get('DTSTART')

        if not date:
            return

        # 模式 A: "114-1-开始" / "114-1-结束"
        m = re.match(r'(\d+)-([12])-(开始|结束|start|end)', summary, re.IGNORECASE)
        if m:
            year = int(m.group(1))
            semester = int(m.group(2))
            event_type = m.group(3).lower()
            is_start = event_type in ['开始', 'start']
            GoogleCalendarIntegration._store_semester_date(semesters, year, semester, date, is_start)
            return

        # 模式 B: "108學年度第一學期開始" / "108學年度第二學期開始"
        m = re.match(r'(\d{3})學年度第?[一二12]學期(開始|開學|開課|開始日)?', summary)
        if m:
            year = int(m.group(1))
            sem_token = re.search(r'第?([一二12])學期', summary)
            semester = 1 if sem_token and sem_token.group(1) in ['一', '1'] else 2
            GoogleCalendarIntegration._store_semester_date(semesters, year, semester, date, is_start=True)
            return

        # 模式 C: "第1學期結束" / "第2學期結束"（无学年度，需根据日期推算）
        m = re.match(r'第?([一二12])學期(結束|結束日|終止|end|END)', summary, re.IGNORECASE)
        if m:
            semester = 1 if m.group(1) in ['一', '1'] else 2
            year = GoogleCalendarIntegration._infer_roc_year_from_date(date, semester)
            if year:
                GoogleCalendarIntegration._store_semester_date(semesters, year, semester, date, is_start=False)

    @staticmethod
    def _infer_roc_year_from_date(date: datetime, semester: int) -> Optional[int]:
        """根据公历日期推断学年度（民国年）。"""
        if semester == 1:
            # 第1学期通常 8 月开学，次年 1 月结束
            return date.year - 1911 if date.month >= 8 else date.year - 1912
        else:
            # 第2学期通常 2 月开学，7 月结束，学年度与 8 月前的年份对应
            return date.year - 1912

    @staticmethod
    def _store_semester_date(semesters: Dict[Tuple[int, int], Dict], year: int, semester: int, date: datetime, is_start: bool):
        if (year, semester) not in semesters:
            semesters[(year, semester)] = {}
        if is_start:
            semesters[(year, semester)]['start'] = date
        else:
            semesters[(year, semester)]['end'] = date
    
    @staticmethod
    def validate_semester_data(semesters: Dict[Tuple[int, int], Dict]) -> Dict[Tuple[int, int], Dict]:
        """
        验证学期数据的完整性
        确保每个学期都有开始和结束日期
        """
        valid_semesters = {}
        
        for key, value in semesters.items():
            if 'start' in value and 'end' in value:
                if value['start'] < value['end']:
                    valid_semesters[key] = value
                else:
                    logger.warning(f"学期 {key} 的开始日期晚于结束日期，已跳过")
        
        return valid_semesters
    
    @staticmethod
    def apply_semesters_to_config(semesters: Dict[Tuple[int, int], Dict]):
        """
        将 Google Calendar 读取的学期信息应用到系统配置
        
        Args:
            semesters: {(year, semester): {'start': datetime, 'end': datetime}}
        """
        from config.course_schedule_config import update_semester_info
        
        valid_semesters = GoogleCalendarIntegration.validate_semester_data(semesters)
        
        for (year, semester), dates in valid_semesters.items():
            update_semester_info(year, semester, dates['start'], dates['end'])
            logger.info(f"已更新学年 {year} 第 {semester} 学期: {dates['start'].date()} 至 {dates['end'].date()}")


# 使用示例
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 你的 Google Calendar iCal URL
    # 可以通过以下步骤获得：
    # 1. 打开 Google Calendar
    # 2. 在左侧找到你的日历，点击选项 → 设置
    # 3. 向下滚动找到 "日历集成" 或 "Calendar Address"
    # 4. 复制 iCal 格式的 URL（.ics 链接）
    
    # 提供的公開 iCal URL（東華大學日曆）
    CALENDAR_URL = "https://calendar.google.com/calendar/ical/ndhuoaa%40gmail.com/public/basic.ics"
    
    print("正在从 Google Calendar 读取学期信息...\n")
    
    semesters = GoogleCalendarIntegration.extract_semester_from_ical_url(CALENDAR_URL)
    
    if semesters:
        print("✅ 成功读取学期信息：\n")
        for (year, semester), dates in semesters.items():
            print(f"学年 {year} 第 {semester} 学期:")
            print(f"  开始: {dates.get('start', '未设置')}")
            print(f"  结束: {dates.get('end', '未设置')}\n")
        
        # 应用到系统配置
        GoogleCalendarIntegration.apply_semesters_to_config(semesters)
        print("✅ 已应用到系统配置")
    else:
        print("❌ 无法读取学期信息，请检查 Google Calendar URL")
