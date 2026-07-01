from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

from lunar_python import Solar
import re

class BaziCalculator:
    """生辰八字计算器 - 使用 lunar_python 实现"""
    
    # 五行
    FIVE_ELEMENTS = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
        "庚": "金", "辛": "金", "壬": "水", "癸": "水",
        "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
        "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"
    }
    
    def __init__(self):
        pass
    
    def convert_to_solar_time(self, year: int, month: int, day: int, hour: int, minute: int, 
                              longitude: float = 116.4) -> Tuple[int, int, int, int, int]:
        """
        将北京时间转换为真太阳时
        
        Args:
            year: 年份
            month: 月份
            day: 日期
            hour: 小时（北京时间）
            minute: 分钟
            longitude: 经度（默认北京经度116.4度）
        
        Returns:
            (年, 月, 日, 时, 分) 真太阳时
        """
        # 北京时间是东经120度的地方时
        beijing_longitude = 120.0
        
        # 计算经度差导致的时差（每度4分钟）
        longitude_diff = longitude - beijing_longitude
        time_diff_minutes = longitude_diff * 4
        
        # 计算平太阳时
        beijing_time = datetime(year, month, day, hour, minute)
        mean_solar_time = beijing_time + timedelta(minutes=time_diff_minutes)
        
        # 计算真太阳时（考虑均时差）
        day_of_year = mean_solar_time.timetuple().tm_yday
        equation_of_time = self._calculate_equation_of_time(day_of_year)
        
        # 真太阳时 = 平太阳时 + 均时差
        true_solar_time = mean_solar_time + timedelta(minutes=equation_of_time)
        
        return (
            true_solar_time.year,
            true_solar_time.month,
            true_solar_time.day,
            true_solar_time.hour,
            true_solar_time.minute
        )
    
    def _calculate_equation_of_time(self, day_of_year: int) -> float:
        """
        计算均时差（分钟）
        """
        import math
        B = 360.0 / 365.0 * (day_of_year - 81)
        B_rad = math.radians(B)
        
        # 均时差公式（分钟）
        equation = 9.87 * math.sin(2 * B_rad) - 7.53 * math.cos(B_rad) - 1.5 * math.sin(B_rad)
        
        return equation
    
    def calculate_bazi(self, year: int, month: int, day: int, hour: int, minute: int = 0, 
                       use_solar_time: bool = True, longitude: float = 116.4) -> dict[str, int | Any]:
        """
        计算完整的生辰八字（使用 lunar_python）
        包含：四柱、十神、纳音、胎元、命宫、身宫
        
        Args:
            year: 年份
            month: 月份
            day: 日期
            hour: 小时
            minute: 分钟
            use_solar_time: 是否使用真太阳时
            longitude: 经度（用于真太阳时计算）
        
        Returns:
            包含完整八字信息的字典
        """
        # 如果使用真太阳时，先转换时间
        if use_solar_time:
            year, month, day, hour, minute = self.convert_to_solar_time(
                year, month, day, hour, minute, longitude
            )
        
        # 使用 lunar_python 计算八字
        # 创建公历日期对象
        solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
        # 转换为农历并获取八字
        lunar = solar.getLunar()
        eight_char = lunar.getEightChar()
        # 使用流派1认为晚子时日柱算明天
        eight_char.setSect(1)
        # 获取四柱
        year_pillar = eight_char.getYear()
        month_pillar = eight_char.getMonth()
        day_pillar = eight_char.getDay()
        hour_pillar = eight_char.getTime()
        
        # 获取十神体系（天干十神和地支十神）
        ten_gods_dict = {
            "year_gan_ten_god": eight_char.getYearShiShenGan(),
            "year_zhi_ten_god": ", ".join(eight_char.getYearShiShenZhi()) if isinstance(eight_char.getYearShiShenZhi(), list) else str(eight_char.getYearShiShenZhi()),
            "month_gan_ten_god": eight_char.getMonthShiShenGan(),
            "month_zhi_ten_god": ", ".join(eight_char.getMonthShiShenZhi()) if isinstance(eight_char.getMonthShiShenZhi(), list) else str(eight_char.getMonthShiShenZhi()),
            "day_gan_ten_god": eight_char.getDayShiShenGan(),
            "day_zhi_ten_god": ", ".join(eight_char.getDayShiShenZhi()) if isinstance(eight_char.getDayShiShenZhi(), list) else str(eight_char.getDayShiShenZhi()),
            "hour_gan_ten_god": eight_char.getTimeShiShenGan(),
            "hour_zhi_ten_god": ", ".join(eight_char.getTimeShiShenZhi()) if isinstance(eight_char.getTimeShiShenZhi(), list) else str(eight_char.getTimeShiShenZhi())
        }
        
        # 获取纳音
        nayin_dict = {
            "year_nayin": eight_char.getYearNaYin(),
            "month_nayin": eight_char.getMonthNaYin(),
            "day_nayin": eight_char.getDayNaYin(),
            "hour_nayin": eight_char.getTimeNaYin()
        }
        
        # 获取胎元
        tai_yuan = eight_char.getTaiYuan()
        tai_yuan_nayin = eight_char.getTaiYuanNaYin()
        
        # 获取命宫
        ming_gong = eight_char.getMingGong()
        ming_gong_nayin = eight_char.getMingGongNaYin()
        
        # 获取身宫
        shen_gong = eight_char.getShenGong()
        shen_gong_nayin = eight_char.getShenGongNaYin()
        
        # 获取太息（胎息）
        tai_xi = eight_char.getTaiXi()
        tai_xi_nayin = eight_char.getTaiXiNaYin()

        # 空亡（旬空）
        kong_wang = {
            "year": lunar.getYearXunKong(),
            "month": lunar.getMonthXunKong(),
            "day": lunar.getDayXunKong(),
            "time": lunar.getTimeXunKong(),
        }

        # 神煞（基于四柱）
        shen_sha = None
        try:
            from wenjia_agent.core.shensha_extracted import apply_all as _apply_all_shensha

            def _pillar_to_dict(pillar: str) -> dict[str, str]:
                if not pillar or len(pillar) < 2:
                    return {"gan": "", "zhi": "", "value": pillar or ""}
                return {"gan": pillar[0], "zhi": pillar[1], "value": pillar}

            shensha_input = {
                "pillars": {
                    "year": _pillar_to_dict(year_pillar),
                    "month": _pillar_to_dict(month_pillar),
                    "day": _pillar_to_dict(day_pillar),
                    "time": _pillar_to_dict(hour_pillar),
                }
            }
            _apply_all_shensha(shensha_input)
            shen_sha = shensha_input.get("shensha")
        except Exception:
            shen_sha = None
        
        return {
            "year_pillar": year_pillar,
            "month_pillar": month_pillar,
            "day_pillar": day_pillar,
            "hour_pillar": hour_pillar,
            "solar_year": year,
            "solar_month": month,
            "solar_day": day,
            "solar_hour": hour,
            "solar_minute": minute,
            # 十神
            "ten_gods": ten_gods_dict,
            # 纳音
            "nayin": nayin_dict,
            # 胎元
            "tai_yuan": tai_yuan,
            "tai_yuan_nayin": tai_yuan_nayin,
            # 命宫
            "ming_gong": ming_gong,
            "ming_gong_nayin": ming_gong_nayin,
            # 身宫
            "shen_gong": shen_gong,
            "shen_gong_nayin": shen_gong_nayin,
            # 太息（胎息）
            "tai_xi": tai_xi,
            "tai_xi_nayin": tai_xi_nayin,
            # 神煞
            "shen_sha": shen_sha,
            # 空亡（旬空）
            "kong_wang": kong_wang,
        }
    
    def get_five_elements_analysis(self, bazi: Dict[str, str], 
                                   year: int = None, month: int = None, 
                                   day: int = None, hour: int = None, 
                                   minute: int = None) -> Dict[str, int]:
        """
        分析五行分布（更准确的计算）
        包括：天干五行、地支本气五行、地支藏干五行（只算本气）
        
        Args:
            bazi: 包含四柱的字典
            year, month, day, hour, minute: 如果提供，会重新计算eight_char以获得更准确的结果
        """
        elements_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        
        # 如果提供了时间参数，重新计算eight_char以获得更准确的结果
        if year is not None and month is not None and day is not None and hour is not None:
            try:
                solar = Solar.fromYmdHms(year, month, day, hour, minute or 0, 0)
                lunar = solar.getLunar()
                eight_char = lunar.getEightChar()
                
                # 使用eight_char对象进行更准确的计算
                # 处理年柱
                year_gan = eight_char.getYearGan()
                year_zhi = eight_char.getYearZhi()
                year_hide_gan = eight_char.getYearHideGan()
                
                # 天干五行
                if year_gan in self.FIVE_ELEMENTS:
                    elements_count[self.FIVE_ELEMENTS[year_gan]] += 1
                
                # 地支本气五行
                if year_zhi in self.FIVE_ELEMENTS:
                    elements_count[self.FIVE_ELEMENTS[year_zhi]] += 1
                
                # 地支藏干五行（只算第一个，即本气）
                if year_hide_gan and isinstance(year_hide_gan, list) and len(year_hide_gan) > 0:
                    hide_gan = year_hide_gan[0]
                    if hide_gan in self.FIVE_ELEMENTS:
                        elements_count[self.FIVE_ELEMENTS[hide_gan]] += 1
                
                # 处理月柱
                month_gan = eight_char.getMonthGan()
                month_zhi = eight_char.getMonthZhi()
                month_hide_gan = eight_char.getMonthHideGan()
                
                if month_gan in self.FIVE_ELEMENTS:
                    elements_count[self.FIVE_ELEMENTS[month_gan]] += 1
                if month_zhi in self.FIVE_ELEMENTS:
                    elements_count[self.FIVE_ELEMENTS[month_zhi]] += 1
                if month_hide_gan and isinstance(month_hide_gan, list) and len(month_hide_gan) > 0:
                    hide_gan = month_hide_gan[0]
                    if hide_gan in self.FIVE_ELEMENTS:
                        elements_count[self.FIVE_ELEMENTS[hide_gan]] += 1
                
                # 处理日柱
                day_gan = eight_char.getDayGan()
                day_zhi = eight_char.getDayZhi()
                day_hide_gan = eight_char.getDayHideGan()
                
                if day_gan in self.FIVE_ELEMENTS:
                    elements_count[self.FIVE_ELEMENTS[day_gan]] += 1
                if day_zhi in self.FIVE_ELEMENTS:
                    elements_count[self.FIVE_ELEMENTS[day_zhi]] += 1
                if day_hide_gan and isinstance(day_hide_gan, list) and len(day_hide_gan) > 0:
                    hide_gan = day_hide_gan[0]
                    if hide_gan in self.FIVE_ELEMENTS:
                        elements_count[self.FIVE_ELEMENTS[hide_gan]] += 1
                
                # 处理时柱
                hour_gan = eight_char.getTimeGan()
                hour_zhi = eight_char.getTimeZhi()
                hour_hide_gan = eight_char.getTimeHideGan()
                
                if hour_gan in self.FIVE_ELEMENTS:
                    elements_count[self.FIVE_ELEMENTS[hour_gan]] += 1
                if hour_zhi in self.FIVE_ELEMENTS:
                    elements_count[self.FIVE_ELEMENTS[hour_zhi]] += 1
                if hour_hide_gan and isinstance(hour_hide_gan, list) and len(hour_hide_gan) > 0:
                    hide_gan = hour_hide_gan[0]
                    if hide_gan in self.FIVE_ELEMENTS:
                        elements_count[self.FIVE_ELEMENTS[hide_gan]] += 1

                # 纳音五行（从纳音中提取“金木水火土”并计入）
                try:
                    nayins = [
                        eight_char.getYearNaYin(),
                        eight_char.getMonthNaYin(),
                        eight_char.getDayNaYin(),
                        eight_char.getTimeNaYin(),
                    ]
                    for ny in nayins:
                        if not ny:
                            continue
                        m = re.search(r"[金木水火土]", str(ny))
                        if m:
                            wx = m.group(0)
                            if wx in elements_count:
                                elements_count[wx] += 1
                except Exception:
                    # 纳音解析失败时忽略，不影响整体结果
                    pass
                
                return elements_count
            except Exception as e:
                print(f"使用eight_char计算五行失败，回退到简单方法: {e}")
                # 继续使用简单方法
        
        # 回退到原来的简单方法（从字符串解析）
        # 但需要更准确地解析：每个柱由天干+地支组成
        pillar_keys = ["year_pillar", "month_pillar", "day_pillar", "hour_pillar"]
        
        for key in pillar_keys:
            if key in bazi:
                pillar = bazi[key]
                if isinstance(pillar, str) and len(pillar) >= 2:
                    # 每个柱由天干（第1个字符）和地支（第2个字符）组成
                    gan = pillar[0]  # 天干
                    zhi = pillar[1]  # 地支
                    
                    # 天干五行
                    if gan in self.FIVE_ELEMENTS:
                        elements_count[self.FIVE_ELEMENTS[gan]] += 1
                    
                    # 地支本气五行
                    if zhi in self.FIVE_ELEMENTS:
                        elements_count[self.FIVE_ELEMENTS[zhi]] += 1
                    
                    # 地支藏干（需要查表）
                    # 地支藏干表
                    zhi_hide_gan = {
                        "子": ["癸"],  # 子藏癸
                        "丑": ["己", "癸", "辛"],  # 丑藏己癸辛
                        "寅": ["甲", "丙", "戊"],  # 寅藏甲丙戊
                        "卯": ["乙"],  # 卯藏乙
                        "辰": ["戊", "乙", "癸"],  # 辰藏戊乙癸
                        "巳": ["丙", "戊", "庚"],  # 巳藏丙戊庚
                        "午": ["丁", "己"],  # 午藏丁己
                        "未": ["己", "丁", "乙"],  # 未藏己丁乙
                        "申": ["庚", "壬", "戊"],  # 申藏庚壬戊
                        "酉": ["辛"],  # 酉藏辛
                        "戌": ["戊", "辛", "丁"],  # 戌藏戊辛丁
                        "亥": ["壬", "甲"]  # 亥藏壬甲
                    }
                    
                    # 只算本气（第一个藏干）
                    if zhi in zhi_hide_gan and len(zhi_hide_gan[zhi]) > 0:
                        hide_gan = zhi_hide_gan[zhi][0]
                        if hide_gan in self.FIVE_ELEMENTS:
                            elements_count[self.FIVE_ELEMENTS[hide_gan]] += 1
        
        return elements_count
    
    def get_zodiac_animal(self, year: int) -> str:
        """获取生肖"""
        solar = Solar.fromYmd(year, 1, 1)
        lunar = solar.getLunar()
        return lunar.getYearShengXiao()
