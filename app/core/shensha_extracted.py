# -*- coding: utf-8 -*-
"""
神煞计算模块 (shensha) - Python 版

从 mystilight-8char 的 shensha-extracted.cjs 转写而来。
根据八字 result（含 pillars、可选 currentYun）对 result['shensha'] 进行填充。

注意：
- 这是从 `test/shensha_extracted.py` 迁移到后端可复用服务目录的版本；
- 对外主要使用 `apply_all(result)`。
"""

from __future__ import annotations

import re
from typing import Any

# 天干地支
GANS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHIS = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

KEY_MAP = {"year": "nian", "month": "yue", "day": "ri", "time": "shi"}
PILLAR_KEYS = ["year", "month", "day", "time"]


def _p(result: dict | None, *keys: str) -> Any:
    """Safe get: result['a']['b']['c'] -> _p(result, 'a','b','c')"""

    o: Any = result
    for k in keys:
        o = (o or {}).get(k) if isinstance(o, dict) else None
        if o is None:
            return None
    return o


def _gz(gz: Any) -> tuple[str, str]:
    """ganZhi (list [gan,zhi] or similar) -> (gan, zhi)"""

    if isinstance(gz, (list, tuple)) and len(gz) >= 2:
        return (gz[0] or "", gz[1] or "")
    return ("", "")


def ensure_shensha(result: dict) -> None:
    if not result:
        return
    if "shensha" not in result or result.get("shensha") is None:
        result["shensha"] = {
            "nian": [],
            "yue": [],
            "ri": [],
            "shi": [],
            "current": {"daYun": [], "liuNian": [], "liuYue": [], "liuRi": []},
        }


def apply_tian_yi(result: dict) -> None:
    try:
        TIAN_YI_MAP = {
            "甲": ["丑", "未"],
            "戊": ["丑", "未"],
            "庚": ["丑", "未"],
            "乙": ["子", "申"],
            "己": ["子", "申"],
            "丙": ["亥", "酉"],
            "丁": ["亥", "酉"],
            "壬": ["卯", "巳"],
            "癸": ["卯", "巳"],
            "辛": ["寅", "午"],
        }
        day_gan = _p(result, "pillars", "day", "gan")
        year_gan = _p(result, "pillars", "year", "gan")
        day_branches = TIAN_YI_MAP.get(day_gan, []) if day_gan else []
        year_branches = TIAN_YI_MAP.get(year_gan, []) if year_gan else []
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                hit_day = zhi in day_branches
                hit_year = zhi in year_branches
                arr_key = KEY_MAP[k]
                if hit_day:
                    result["shensha"][arr_key].append("天乙贵人(日)")
                if hit_year:
                    result["shensha"][arr_key].append("天乙贵人(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                gan, zhi = _gz(gz)
                if not obj or not zhi:
                    continue
                if zhi in day_branches:
                    result["shensha"]["current"][name].append("天乙贵人(日)")
                if zhi in year_branches:
                    result["shensha"]["current"][name].append("天乙贵人(年)")
    except Exception:
        pass


def apply_yue_de(result: dict) -> None:
    try:
        YUE_DE_GROUP_BY_MONTH_ZHI = {
            "寅": "丙",
            "午": "丙",
            "戌": "丙",
            "申": "壬",
            "子": "壬",
            "辰": "壬",
            "亥": "甲",
            "卯": "甲",
            "未": "甲",
            "巳": "庚",
            "酉": "庚",
            "丑": "庚",
        }
        month_zhi = _p(result, "pillars", "month", "zhi")
        target_gan = YUE_DE_GROUP_BY_MONTH_ZHI.get(month_zhi) if month_zhi else None
        if not target_gan:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p or p.get("gan") != target_gan:
                    continue
                arr_key = KEY_MAP[k]
                if "月德贵人" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("月德贵人")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                gan, _ = _gz(gz)
                if not obj or gan != target_gan:
                    continue
                if "月德贵人" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("月德贵人")
    except Exception:
        pass


def apply_yue_de_he(result: dict) -> None:
    try:
        YUE_DE_HE_BY_MONTH_ZHI = {
            "寅": "辛",
            "午": "辛",
            "戌": "辛",
            "申": "丁",
            "子": "丁",
            "辰": "丁",
            "巳": "乙",
            "酉": "乙",
            "丑": "乙",
            "亥": "己",
            "卯": "己",
            "未": "己",
        }
        month_zhi = _p(result, "pillars", "month", "zhi")
        target_gan = YUE_DE_HE_BY_MONTH_ZHI.get(month_zhi) if month_zhi else None
        if not target_gan:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p or p.get("gan") != target_gan:
                    continue
                arr_key = KEY_MAP[k]
                if "月德合" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("月德合")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                gan, _ = _gz(gz)
                if not obj or gan != target_gan:
                    continue
                if "月德合" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("月德合")
    except Exception:
        pass


def apply_tian_de(result: dict) -> None:
    try:
        TIAN_DE_BY_MONTH_ZHI = {
            "寅": "丁",
            "卯": "申",
            "辰": "壬",
            "巳": "辛",
            "午": "亥",
            "未": "甲",
            "申": "癸",
            "酉": "寅",
            "戌": "丙",
            "亥": "乙",
            "子": "巳",
            "丑": "庚",
        }
        month_zhi = _p(result, "pillars", "month", "zhi")
        target = TIAN_DE_BY_MONTH_ZHI.get(month_zhi) if month_zhi else None
        if not target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                gan, zhi = p.get("gan"), p.get("zhi")
                arr_key = KEY_MAP[k]
                match = (target in GANS and gan == target) or (target in ZHIS and zhi == target)
                if match and "天德贵人" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("天德贵人")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                gan, zhi = _gz(gz)
                if not obj or (not gan and not zhi):
                    continue
                match = (target in GANS and gan == target) or (target in ZHIS and zhi == target)
                if match and "天德贵人" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("天德贵人")
    except Exception:
        pass


def apply_tai_ji_gui_ren(result: dict) -> None:
    try:
        GAN_TO_ZHI_PLACES = {
            "甲": ["子", "午"],
            "乙": ["子", "午"],
            "丙": ["卯", "酉"],
            "丁": ["卯", "酉"],
            "戊": ["辰", "戌", "丑", "未"],
            "己": ["辰", "戌", "丑", "未"],
            "庚": ["寅", "亥"],
            "辛": ["寅", "亥"],
            "壬": ["申", "巳"],
            "癸": ["申", "巳"],
        }
        day_gan = _p(result, "pillars", "day", "gan")
        year_gan = _p(result, "pillars", "year", "gan")
        day_targets = GAN_TO_ZHI_PLACES.get(day_gan, []) if day_gan else []
        year_targets = GAN_TO_ZHI_PLACES.get(year_gan, []) if year_gan else []
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                hit_day = zhi in day_targets
                hit_year = zhi in year_targets
                if hit_day and "太极贵人(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("太极贵人(日)")
                if hit_year and "太极贵人(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("太极贵人(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                _, zhi = _gz(gz)
                if not obj or not zhi:
                    continue
                if zhi in day_targets and "太极贵人(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("太极贵人(日)")
                if zhi in year_targets and "太极贵人(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("太极贵人(年)")
    except Exception:
        pass


def apply_wen_chang_gui_ren(result: dict) -> None:
    try:
        WEN_CHANG_BY_GAN = {
            "甲": "巳",
            "乙": "午",
            "丙": "申",
            "丁": "酉",
            "戊": "申",
            "己": "酉",
            "庚": "亥",
            "辛": "子",
            "壬": "寅",
            "癸": "卯",
        }
        day_gan = _p(result, "pillars", "day", "gan")
        year_gan = _p(result, "pillars", "year", "gan")
        day_target = WEN_CHANG_BY_GAN.get(day_gan) if day_gan else None
        year_target = WEN_CHANG_BY_GAN.get(year_gan) if year_gan else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if day_target and zhi == day_target and "文昌贵人(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("文昌贵人(日)")
                if year_target and zhi == year_target and "文昌贵人(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("文昌贵人(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                _, zhi = _gz(gz)
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "文昌贵人(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("文昌贵人(日)")
                if year_target and zhi == year_target and "文昌贵人(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("文昌贵人(年)")
    except Exception:
        pass


def apply_guo_yin_gui_ren(result: dict) -> None:
    try:
        GUO_YIN_BY_GAN = {
            "甲": "戌",
            "乙": "亥",
            "丙": "丑",
            "丁": "寅",
            "戊": "丑",
            "己": "寅",
            "庚": "辰",
            "辛": "巳",
            "壬": "未",
            "癸": "申",
        }
        day_gan = _p(result, "pillars", "day", "gan")
        year_gan = _p(result, "pillars", "year", "gan")
        day_target = GUO_YIN_BY_GAN.get(day_gan) if day_gan else None
        year_target = GUO_YIN_BY_GAN.get(year_gan) if year_gan else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if day_target and zhi == day_target and "国印贵人(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("国印贵人(日)")
                if year_target and zhi == year_target and "国印贵人(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("国印贵人(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                _, zhi = _gz(gz)
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "国印贵人(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("国印贵人(日)")
                if year_target and zhi == year_target and "国印贵人(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("国印贵人(年)")
    except Exception:
        pass


def apply_ci_guan(result: dict) -> None:
    try:
        MAP = {
            "甲": ["庚", "寅"],
            "乙": ["辛", "卯"],
            "丙": ["乙", "巳"],
            "丁": ["戊", "午"],
            "戊": ["丁", "巳"],
            "己": ["庚", "午"],
            "庚": ["壬", "申"],
            "辛": ["癸", "酉"],
            "壬": ["癸", "亥"],
            "癸": ["壬", "戌"],
        }
        day_gan = _p(result, "pillars", "day", "gan")
        year_gan = _p(result, "pillars", "year", "gan")
        day_target = MAP.get(day_gan) if day_gan else None
        year_target = MAP.get(year_gan) if year_gan else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                arr_key = KEY_MAP[k]
                hit_day = day_target and p.get("gan") == day_target[0] and p.get("zhi") == day_target[1]
                hit_year = year_target and p.get("gan") == year_target[0] and p.get("zhi") == year_target[1]
                if hit_day and "词馆(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("词馆(日)")
                if hit_year and "词馆(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("词馆(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gan, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not gan or not zhi:
                    continue
                hit_day = day_target and gan == day_target[0] and zhi == day_target[1]
                hit_year = year_target and gan == year_target[0] and zhi == year_target[1]
                if hit_day and "词馆(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("词馆(日)")
                if hit_year and "词馆(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("词馆(年)")
    except Exception:
        pass


def apply_zheng_xue_tang(result: dict) -> None:
    try:
        MAP = {
            "甲": ["己", "亥"],
            "乙": ["壬", "午"],
            "丙": ["丙", "寅"],
            "丁": ["丁", "酉"],
            "戊": ["戊", "寅"],
            "己": ["己", "酉"],
            "庚": ["辛", "巳"],
            "辛": ["甲", "子"],
            "壬": ["甲", "申"],
            "癸": ["乙", "卯"],
        }
        day_gan = _p(result, "pillars", "day", "gan")
        year_gan = _p(result, "pillars", "year", "gan")
        day_target = MAP.get(day_gan) if day_gan else None
        year_target = MAP.get(year_gan) if year_gan else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                arr_key = KEY_MAP[k]
                hit_day = day_target and p.get("gan") == day_target[0] and p.get("zhi") == day_target[1]
                hit_year = year_target and p.get("gan") == year_target[0] and p.get("zhi") == year_target[1]
                if hit_day and "学堂(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("学堂(日)")
                if hit_year and "学堂(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("学堂(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gan, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not gan or not zhi:
                    continue
                hit_day = day_target and gan == day_target[0] and zhi == day_target[1]
                hit_year = year_target and gan == year_target[0] and zhi == year_target[1]
                if hit_day and "学堂(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("学堂(日)")
                if hit_year and "学堂(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("学堂(年)")
    except Exception:
        pass


def apply_lu_shen(result: dict) -> None:
    try:
        LU_SHEN_BY_DAY_GAN = {
            "甲": "寅",
            "乙": "卯",
            "丙": "巳",
            "丁": "午",
            "戊": "巳",
            "己": "午",
            "庚": "申",
            "辛": "酉",
            "壬": "亥",
            "癸": "子",
        }
        day_gan = _p(result, "pillars", "day", "gan")
        day_target = LU_SHEN_BY_DAY_GAN.get(day_gan) if day_gan else None
        if not day_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == day_target and "禄神(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("禄神(日)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi == day_target and "禄神(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("禄神(日)")
    except Exception:
        pass


def apply_yi_ma(result: dict) -> None:
    try:
        YI_MA_BY_ZHI = {
            "申": "寅",
            "子": "寅",
            "辰": "寅",
            "寅": "申",
            "午": "申",
            "戌": "申",
            "巳": "亥",
            "酉": "亥",
            "丑": "亥",
            "亥": "巳",
            "卯": "巳",
            "未": "巳",
        }
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_target = YI_MA_BY_ZHI.get(day_zhi) if day_zhi else None
        year_target = YI_MA_BY_ZHI.get(year_zhi) if year_zhi else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if day_target and zhi == day_target and "驿马(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("驿马(日)")
                if year_target and zhi == year_target and "驿马(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("驿马(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "驿马(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("驿马(日)")
                if year_target and zhi == year_target and "驿马(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("驿马(年)")
    except Exception:
        pass


def apply_tao_hua(result: dict) -> None:
    try:
        TAO_HUA_BY_ZHI = {
            "寅": "卯",
            "午": "卯",
            "戌": "卯",
            "申": "酉",
            "子": "酉",
            "辰": "酉",
            "巳": "午",
            "酉": "午",
            "丑": "午",
            "亥": "子",
            "卯": "子",
            "未": "子",
        }
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_target = TAO_HUA_BY_ZHI.get(day_zhi) if day_zhi else None
        year_target = TAO_HUA_BY_ZHI.get(year_zhi) if year_zhi else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if day_target and zhi == day_target and "桃花(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("桃花(日)")
                if year_target and zhi == year_target and "桃花(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("桃花(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "桃花(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("桃花(日)")
                if year_target and zhi == year_target and "桃花(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("桃花(年)")
    except Exception:
        pass


def apply_hong_luan(result: dict) -> None:
    try:
        HONG_LUAN_BY_ZHI = {
            "子": "卯",
            "丑": "寅",
            "寅": "丑",
            "卯": "子",
            "辰": "亥",
            "巳": "戌",
            "午": "酉",
            "未": "申",
            "申": "未",
            "酉": "午",
            "戌": "巳",
            "亥": "辰",
        }
        year_zhi = _p(result, "pillars", "year", "zhi")
        year_target = HONG_LUAN_BY_ZHI.get(year_zhi) if year_zhi else None
        if not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == year_target and "红鸾(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("红鸾(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi == year_target and "红鸾(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("红鸾(年)")
    except Exception:
        pass


def apply_tian_xi(result: dict) -> None:
    try:
        TIAN_XI_BY_ZHI = {
            "子": "酉",
            "丑": "申",
            "寅": "未",
            "卯": "午",
            "辰": "巳",
            "巳": "辰",
            "午": "卯",
            "未": "寅",
            "申": "丑",
            "酉": "子",
            "戌": "亥",
            "亥": "戌",
        }
        year_zhi = _p(result, "pillars", "year", "zhi")
        year_target = TIAN_XI_BY_ZHI.get(year_zhi) if year_zhi else None
        if not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == year_target and "天喜(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("天喜(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi == year_target and "天喜(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("天喜(年)")
    except Exception:
        pass


def apply_yang_ren(result: dict) -> None:
    try:
        YANG_REN_BY_DAY_GAN = {
            "甲": "卯",
            "乙": "寅",
            "丙": "午",
            "丁": "未",
            "戊": "午",
            "己": "未",
            "庚": "酉",
            "辛": "申",
            "壬": "子",
            "癸": "亥",
        }
        day_gan = _p(result, "pillars", "day", "gan")
        day_target = YANG_REN_BY_DAY_GAN.get(day_gan) if day_gan else None
        if not day_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == day_target and "阳刃(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("阳刃(日)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi == day_target and "阳刃(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("阳刃(日)")
    except Exception:
        pass


def apply_jie_sha(result: dict) -> None:
    try:
        JIE_SHA_BY_ZHI = {
            "寅": "亥",
            "午": "亥",
            "戌": "亥",
            "申": "巳",
            "子": "巳",
            "辰": "巳",
            "巳": "寅",
            "酉": "寅",
            "丑": "寅",
            "亥": "申",
            "卯": "申",
            "未": "申",
        }
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_target = JIE_SHA_BY_ZHI.get(day_zhi) if day_zhi else None
        year_target = JIE_SHA_BY_ZHI.get(year_zhi) if year_zhi else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if day_target and zhi == day_target and "劫煞(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("劫煞(日)")
                if year_target and zhi == year_target and "劫煞(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("劫煞(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "劫煞(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("劫煞(日)")
                if year_target and zhi == year_target and "劫煞(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("劫煞(年)")
    except Exception:
        pass


def _build_ganzhi_60() -> list[tuple[str, str]]:
    arr = []
    s, b = 0, 0
    for _ in range(60):
        arr.append((GANS[s], ZHIS[b]))
        s = (s + 1) % 10
        b = (b + 1) % 12
    return arr


GANZHI_60 = _build_ganzhi_60()
XUN_HEAD_TO_EMPTY = {
    "子": ["戌", "亥"],
    "戌": ["申", "酉"],
    "申": ["午", "未"],
    "午": ["辰", "巳"],
    "辰": ["寅", "卯"],
    "寅": ["子", "丑"],
}


def apply_kong_wang(result: dict) -> None:
    try:

        def find_kong(gan: str, zhi: str) -> list[str]:
            if not gan or not zhi:
                return []
            for i, (g, z) in enumerate(GANZHI_60):
                if g == gan and z == zhi:
                    head_idx = (i // 10) * 10
                    head_zhi = GANZHI_60[head_idx][1]
                    return list(XUN_HEAD_TO_EMPTY.get(head_zhi, []))
            return []

        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_gan = _p(result, "pillars", "year", "gan")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_empties = find_kong(day_gan or "", day_zhi or "")
        year_empties = find_kong(year_gan or "", year_zhi or "")
        if not day_empties and not year_empties:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi in day_empties and "空亡(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("空亡(日)")
                if zhi in year_empties and "空亡(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("空亡(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi in day_empties and "空亡(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("空亡(日)")
                if zhi in year_empties and "空亡(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("空亡(年)")
    except Exception:
        pass


def apply_fu_xing_gui_ren(result: dict) -> None:
    try:
        FUXING_BY_GAN = {
            "甲": ["寅", "子"],
            "丙": ["寅", "子"],
            "乙": ["卯", "丑"],
            "癸": ["卯", "丑"],
            "戊": ["申"],
            "己": ["未"],
            "丁": ["亥"],
            "庚": ["午"],
            "辛": ["巳"],
            "壬": ["辰"],
        }
        year_gan = _p(result, "pillars", "year", "gan")
        day_gan = _p(result, "pillars", "day", "gan")
        year_targets = FUXING_BY_GAN.get(year_gan, []) if year_gan else []
        day_targets = FUXING_BY_GAN.get(day_gan, []) if day_gan else []
        if not year_targets and not day_targets:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi in year_targets and "福星贵人(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("福星贵人(年)")
                if zhi in day_targets and "福星贵人(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("福星贵人(日)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi in year_targets and "福星贵人(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("福星贵人(年)")
                if zhi in day_targets and "福星贵人(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("福星贵人(日)")
    except Exception:
        pass


def apply_tian_chu_gui_ren(result: dict) -> None:
    try:
        TIAN_CHU_BY_GAN = {
            "甲": ["巳"],
            "乙": ["午"],
            "丙": ["巳"],
            "丁": ["午"],
            "戊": ["申"],
            "庚": ["亥"],
            "辛": ["子"],
            "壬": ["寅"],
            "癸": ["卯"],
        }
        day_gan = _p(result, "pillars", "day", "gan")
        year_gan = _p(result, "pillars", "year", "gan")
        day_targets = TIAN_CHU_BY_GAN.get(day_gan, []) if day_gan else []
        year_targets = TIAN_CHU_BY_GAN.get(year_gan, []) if year_gan else []
        if not day_targets and not year_targets:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi in day_targets and "天厨贵人(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("天厨贵人(日)")
                if zhi in year_targets and "天厨贵人(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("天厨贵人(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi in day_targets and "天厨贵人(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("天厨贵人(日)")
                if zhi in year_targets and "天厨贵人(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("天厨贵人(年)")
    except Exception:
        pass


def apply_de_xiu_gui_ren(result: dict) -> None:
    try:
        MAP = {
            "寅": {"de": ["丙", "丁"], "xiu": ["戊", "癸"]},
            "午": {"de": ["丙", "丁"], "xiu": ["戊", "癸"]},
            "戌": {"de": ["丙", "丁"], "xiu": ["戊", "癸"]},
            "申": {"de": ["壬", "癸", "戊", "己"], "xiu": ["丙", "辛", "甲", "己"]},
            "子": {"de": ["壬", "癸", "戊", "己"], "xiu": ["丙", "辛", "甲", "己"]},
            "辰": {"de": ["壬", "癸", "戊", "己"], "xiu": ["丙", "辛", "甲", "己"]},
            "巳": {"de": ["庚", "辛"], "xiu": ["乙", "庚"]},
            "酉": {"de": ["庚", "辛"], "xiu": ["乙", "庚"]},
            "丑": {"de": ["庚", "辛"], "xiu": ["乙", "庚"]},
            "亥": {"de": ["甲", "乙"], "xiu": ["丁", "壬"]},
            "卯": {"de": ["甲", "乙"], "xiu": ["丁", "壬"]},
            "未": {"de": ["甲", "乙"], "xiu": ["丁", "壬"]},
        }
        month_zhi = _p(result, "pillars", "month", "zhi")
        config = MAP.get(month_zhi) if month_zhi else None
        if not config:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                gan = p.get("gan")
                arr_key = KEY_MAP[k]
                hit = gan in config["de"] or gan in config["xiu"]
                if hit and "德秀贵人(月)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("德秀贵人(月)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gan, _ = _gz((obj or {}).get("ganZhi"))
                if not obj or not gan:
                    continue
                hit = gan in config["de"] or gan in config["xiu"]
                if hit and "德秀贵人(月)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("德秀贵人(月)")
    except Exception:
        pass


def apply_tian_yi_star(result: dict) -> None:
    try:
        month_zhi = _p(result, "pillars", "month", "zhi")
        if not month_zhi:
            return
        idx = ZHIS.index(month_zhi) if month_zhi in ZHIS else -1
        if idx < 0:
            return
        target_zhi = ZHIS[(idx - 1 + 12) % 12]
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "天医(月)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("天医(月)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi == target_zhi and "天医(月)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("天医(月)")
    except Exception:
        pass


def apply_tian_de_he(result: dict) -> None:
    try:
        TIAN_DE_HE_BY_MONTH_ZHI = {
            "寅": "壬",
            "卯": "巳",
            "辰": "丁",
            "巳": "丙",
            "午": "寅",
            "未": "己",
            "申": "戊",
            "酉": "亥",
            "戌": "辛",
            "亥": "庚",
            "子": "申",
            "丑": "乙",
        }
        month_zhi = _p(result, "pillars", "month", "zhi")
        target = TIAN_DE_HE_BY_MONTH_ZHI.get(month_zhi) if month_zhi else None
        if not target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                arr_key = KEY_MAP[k]
                match = (target in GANS and p.get("gan") == target) or (target in ZHIS and p.get("zhi") == target)
                if match and "天德合" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("天德合")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                gan, zhi = _gz(gz)
                if not obj or not gz:
                    continue
                match = (target in GANS and gan == target) or (target in ZHIS and zhi == target)
                if match and "天德合" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("天德合")
    except Exception:
        pass


def apply_san_qi_gui_ren(result: dict) -> None:
    try:
        TRIADS = [["甲", "戊", "庚"], ["乙", "丙", "丁"], ["壬", "癸", "辛"]]

        def is_ordered_triad(arr: list) -> bool:
            if not isinstance(arr, list) or len(arr) != 3:
                return False
            return any(all(arr[i] == t[i] for i in range(3)) for t in TRIADS)

        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            yg = _p(result, "pillars", "year", "gan")
            mg = _p(result, "pillars", "month", "gan")
            dg = _p(result, "pillars", "day", "gan")
            tg = _p(result, "pillars", "time", "gan")
            win1 = [yg, mg, dg]
            win2 = [mg, dg, tg]
            if all(win1) and is_ordered_triad(win1):
                for k in ["year", "month", "day"]:
                    p = pillars.get(k)
                    if not p:
                        continue
                    arr_key = KEY_MAP[k]
                    if "三奇贵人" not in result["shensha"][arr_key]:
                        result["shensha"][arr_key].append("三奇贵人")
            if all(win2) and is_ordered_triad(win2):
                for k in ["month", "day", "time"]:
                    p = pillars.get(k)
                    if not p:
                        continue
                    arr_key = KEY_MAP[k]
                    if "三奇贵人" not in result["shensha"][arr_key]:
                        result["shensha"][arr_key].append("三奇贵人")
        current_yun = _p(result, "currentYun")
        if current_yun:

            def get_gan(gz):
                return gz[0] if isinstance(gz, (list, tuple)) and len(gz) >= 1 else ""

            cwin1 = [
                get_gan((current_yun.get("daYun") or {}).get("ganZhi")),
                get_gan((current_yun.get("liuNian") or {}).get("ganZhi")),
                get_gan((current_yun.get("liuYue") or {}).get("ganZhi")),
            ]
            cwin2 = [
                get_gan((current_yun.get("liuNian") or {}).get("ganZhi")),
                get_gan((current_yun.get("liuYue") or {}).get("ganZhi")),
                get_gan((current_yun.get("liuRi") or {}).get("ganZhi")),
            ]
            if all(cwin1) and is_ordered_triad(cwin1):
                for n in ["daYun", "liuNian", "liuYue"]:
                    if "三奇贵人" not in result["shensha"]["current"][n]:
                        result["shensha"]["current"][n].append("三奇贵人")
            if all(cwin2) and is_ordered_triad(cwin2):
                for n in ["liuNian", "liuYue", "liuRi"]:
                    if "三奇贵人" not in result["shensha"]["current"][n]:
                        result["shensha"]["current"][n].append("三奇贵人")
    except Exception:
        pass


# 以下为其余神煞的占位实现，逻辑与 JS 版一致，可按需从 shensha-extracted.cjs 逐项补全
def apply_jiang_xing(result: dict) -> None:
    try:
        MAP = {"寅": "午", "午": "午", "戌": "午", "申": "子", "子": "子", "辰": "子", "巳": "酉", "酉": "酉", "丑": "酉", "亥": "卯", "卯": "卯", "未": "卯"}
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_target = MAP.get(day_zhi) if day_zhi else None
        year_target = MAP.get(year_zhi) if year_zhi else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                hit_day = day_target and zhi == day_target and k != "day"
                hit_year = year_target and zhi == year_target and k != "year"
                if hit_day and "将星(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("将星(日)")
                if hit_year and "将星(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("将星(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "将星(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("将星(日)")
                if year_target and zhi == year_target and "将星(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("将星(年)")
    except Exception:
        pass


def apply_hua_gai(result: dict) -> None:
    try:
        MAP = {"寅": "戌", "午": "戌", "戌": "戌", "亥": "未", "卯": "未", "未": "未", "申": "辰", "子": "辰", "辰": "辰", "巳": "丑", "酉": "丑", "丑": "丑"}
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_target = MAP.get(day_zhi) if day_zhi else None
        year_target = MAP.get(year_zhi) if year_zhi else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                hit_day = day_target and zhi == day_target and k != "day"
                hit_year = year_target and zhi == year_target and k != "year"
                if hit_day and "华盖(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("华盖(日)")
                if hit_year and "华盖(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("华盖(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "华盖(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("华盖(日)")
                if year_target and zhi == year_target and "华盖(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("华盖(年)")
    except Exception:
        pass


def apply_tian_luo_di_wang(result: dict) -> None:
    try:
        TIAN_LUO = {"戌": "亥", "亥": "戌"}
        DI_WANG = {"辰": "巳", "巳": "辰"}
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_tian = TIAN_LUO.get(day_zhi) if day_zhi else None
        day_di = DI_WANG.get(day_zhi) if day_zhi else None
        year_tian = TIAN_LUO.get(year_zhi) if year_zhi else None
        year_di = DI_WANG.get(year_zhi) if year_zhi else None
        if not day_tian and not day_di and not year_tian and not year_di:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                hit_dt = day_tian and zhi == day_tian and k != "day"
                hit_dd = day_di and zhi == day_di and k != "day"
                hit_yt = year_tian and zhi == year_tian and k != "year"
                hit_yd = year_di and zhi == year_di and k != "year"
                if hit_dt and "天罗(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("天罗(日)")
                if hit_dd and "地网(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("地网(日)")
                if hit_yt and "天罗(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("天罗(年)")
                if hit_yd and "地网(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("地网(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if day_tian and zhi == day_tian and "天罗(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("天罗(日)")
                if day_di and zhi == day_di and "地网(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("地网(日)")
                if year_tian and zhi == year_tian and "天罗(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("天罗(年)")
                if year_di and zhi == year_di and "地网(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("地网(年)")
    except Exception:
        pass


def apply_kui_gang(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        if not day_gan or not day_zhi:
            return
        is_kui = (day_gan == "庚" and day_zhi in ("戌", "辰")) or (day_gan == "戊" and day_zhi == "戌") or (day_gan == "壬" and day_zhi == "辰")
        if not is_kui:
            return
        ensure_shensha(result)
        day_pillar = _p(result, "pillars", "day")
        if day_pillar is not None and isinstance(day_pillar, dict):
            day_pillar["isKuiGangByDay"] = True
        if "魁罡(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("魁罡(日)")
    except Exception:
        pass


def apply_tian_she_ri(result: dict) -> None:
    try:
        SPRING, SUMMER, AUTUMN, WINTER = ["寅", "卯", "辰"], ["巳", "午", "未"], ["申", "酉", "戌"], ["亥", "子", "丑"]
        month_zhi = _p(result, "pillars", "month", "zhi")
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        if not month_zhi or not day_gan or not day_zhi:
            return
        day_pair = day_gan + day_zhi
        hit = (month_zhi in SPRING and day_pair == "戊寅") or (month_zhi in SUMMER and day_pair == "甲午") or (month_zhi in AUTUMN and day_pair == "戊申") or (month_zhi in WINTER and day_pair == "甲子")
        if not hit:
            return
        ensure_shensha(result)
        day_pillar = _p(result, "pillars", "day")
        if day_pillar is not None and isinstance(day_pillar, dict):
            day_pillar["isTianSheRiByDay"] = True
        if "天赦日(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("天赦日(日)")
    except Exception:
        pass


def apply_jin_shen(result: dict) -> None:
    try:
        TARGETS = ["乙丑", "己巳", "癸酉"]
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            day_gan = pillars.get("day", {}).get("gan")
            day_zhi = pillars.get("day", {}).get("zhi")
            time_gan = pillars.get("time", {}).get("gan")
            time_zhi = pillars.get("time", {}).get("zhi")
            day_pair = (day_gan or "") + (day_zhi or "")
            time_pair = (time_gan or "") + (time_zhi or "")
            if day_pair in TARGETS and "金神(日)" not in result["shensha"]["ri"]:
                result["shensha"]["ri"].append("金神(日)")
            if time_pair in TARGETS and "金神(时)" not in result["shensha"]["shi"]:
                result["shensha"]["shi"].append("金神(时)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                pair = ""
                if isinstance(gz, (list, tuple)) and len(gz) >= 2:
                    pair = (gz[0] or "") + (gz[1] or "")
                if pair in TARGETS and "金神" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("金神")
    except Exception:
        pass


def apply_liu_xia(result: dict) -> None:
    try:
        MAP = {"甲": "酉", "乙": "戌", "丙": "未", "丁": "申", "戊": "巳", "己": "午", "庚": "辰", "辛": "卯", "壬": "亥", "癸": "寅"}
        day_gan = _p(result, "pillars", "day", "gan")
        day_target = MAP.get(day_gan) if day_gan else None
        if not day_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == day_target and "流霞(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("流霞(日)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi == day_target and "流霞(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("流霞(日)")
    except Exception:
        pass


def apply_hong_yan_sha(result: dict) -> None:
    try:
        MAP = {"甲": "午", "乙": "午", "丙": "寅", "丁": "未", "戊": "辰", "己": "辰", "庚": "戌", "辛": "酉", "壬": "子", "癸": "申"}
        day_gan = _p(result, "pillars", "day", "gan")
        target_zhi = MAP.get(day_gan) if day_gan else None
        if not target_zhi:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "红艳煞(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("红艳煞(日)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi == target_zhi and "红艳煞(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("红艳煞(日)")
    except Exception:
        pass


def apply_jin_yu(result: dict) -> None:
    try:
        MAP = {"甲": ["辰"], "乙": ["巳"], "丙": ["未"], "戊": ["未"], "丁": ["申"], "己": ["申"], "庚": ["戌"], "辛": ["亥"], "壬": ["丑"], "癸": ["寅"]}
        day_gan = _p(result, "pillars", "day", "gan")
        year_gan = _p(result, "pillars", "year", "gan")
        day_targets = MAP.get(day_gan, []) if day_gan else []
        year_targets = MAP.get(year_gan, []) if year_gan else []
        if not day_targets and not year_targets:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi in day_targets and "金舆(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("金舆(日)")
                if zhi in year_targets and "金舆(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("金舆(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if zhi in day_targets and "金舆(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("金舆(日)")
                if zhi in year_targets and "金舆(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("金舆(年)")
    except Exception:
        pass


def apply_wang_shen(result: dict) -> None:
    try:
        MAP = {"寅": "巳", "午": "巳", "戌": "巳", "亥": "寅", "卯": "寅", "未": "寅", "巳": "申", "酉": "申", "丑": "申", "申": "亥", "子": "亥", "辰": "亥"}
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_target = MAP.get(day_zhi) if day_zhi else None
        year_target = MAP.get(year_zhi) if year_zhi else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if day_target and zhi == day_target and "亡神(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("亡神(日)")
                if year_target and zhi == year_target and "亡神(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("亡神(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "亡神(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("亡神(日)")
                if year_target and zhi == year_target and "亡神(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("亡神(年)")
    except Exception:
        pass


# 其余神煞：占位实现（仅 ensure_shensha），与 JS 同名函数对应，可按需从 shensha-extracted.cjs 补全
def apply_fei_ren(result: dict) -> None:
    try:
        YANG_REN = {"甲": "卯", "乙": "寅", "丙": "午", "丁": "未", "戊": "午", "己": "未", "庚": "酉", "辛": "申", "壬": "子", "癸": "亥"}
        CHONG = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅", "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}
        day_gan = _p(result, "pillars", "day", "gan")
        if not day_gan:
            return
        yang_zhi = YANG_REN.get(day_gan)
        target_zhi = CHONG.get(yang_zhi) if yang_zhi else None
        if not target_zhi:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p or p.get("zhi") != target_zhi:
                    continue
                arr_key = KEY_MAP[k]
                if "飞刃(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("飞刃(日)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "飞刃(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("飞刃(日)")
    except Exception:
        pass


def apply_xue_ren(result: dict) -> None:
    try:
        MAP = {"寅": "丑", "卯": "未", "辰": "寅", "巳": "申", "午": "卯", "未": "酉", "申": "辰", "酉": "戌", "戌": "巳", "亥": "亥", "子": "午", "丑": "子"}
        month_zhi = _p(result, "pillars", "month", "zhi")
        target_zhi = MAP.get(month_zhi) if month_zhi else None
        if not target_zhi:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in ["year", "day", "time"]:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "血刃(月)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("血刃(月)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "血刃(月)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("血刃(月)")
    except Exception:
        pass


def apply_gou_jiao_sha(result: dict) -> None:
    try:
        MAP = {"寅": "亥", "午": "亥", "戌": "亥", "申": "巳", "子": "巳", "辰": "巳", "巳": "寅", "酉": "寅", "丑": "寅", "亥": "申", "卯": "申", "未": "申"}
        day_zhi = _p(result, "pillars", "day", "zhi")
        year_zhi = _p(result, "pillars", "year", "zhi")
        day_target = MAP.get(day_zhi) if day_zhi else None
        year_target = MAP.get(year_zhi) if year_zhi else None
        if not day_target and not year_target:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in PILLAR_KEYS:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if day_target and zhi == day_target and "勾绞煞(日)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("勾绞煞(日)")
                if year_target and zhi == year_target and "勾绞煞(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("勾绞煞(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi:
                    continue
                if day_target and zhi == day_target and "勾绞煞(日)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("勾绞煞(日)")
                if year_target and zhi == year_target and "勾绞煞(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("勾绞煞(年)")
    except Exception:
        pass


def apply_yuan_chen(result: dict) -> None:
    try:
        CHONG = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅", "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}
        year_zhi = _p(result, "pillars", "year", "zhi")
        year_gan = _p(result, "pillars", "year", "gan")
        if not year_zhi:
            return
        chong_zhi = CHONG.get(year_zhi)
        if not chong_zhi:
            return
        ch_idx = ZHIS.index(chong_zhi) if chong_zhi in ZHIS else -1
        if ch_idx < 0:
            return
        yang_gans = ["甲", "丙", "戊", "庚", "壬"]
        is_yang = year_gan in yang_gans if year_gan else False
        target_zhi = ZHIS[(ch_idx + 1) % 12] if is_yang else ZHIS[(ch_idx - 1 + 12) % 12]
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in ["month", "day", "time"]:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "元辰(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("元辰(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "元辰(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("元辰(年)")
    except Exception:
        pass


def apply_gu_chen(result: dict) -> None:
    try:
        MAP = {"寅": "巳", "卯": "巳", "辰": "巳", "巳": "申", "午": "申", "未": "申", "申": "亥", "酉": "亥", "戌": "亥", "亥": "寅", "子": "寅", "丑": "寅"}
        year_zhi = _p(result, "pillars", "year", "zhi")
        target_zhi = MAP.get(year_zhi) if year_zhi else None
        if not target_zhi:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in ["month", "day", "time"]:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "孤辰(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("孤辰(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "孤辰(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("孤辰(年)")
    except Exception:
        pass


def apply_sang_men(result: dict) -> None:
    try:
        year_zhi = _p(result, "pillars", "year", "zhi")
        if not year_zhi or year_zhi not in ZHIS:
            return
        idx = ZHIS.index(year_zhi)
        target_zhi = ZHIS[(idx + 2) % 12]
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in ["month", "day", "time"]:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "丧门(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("丧门(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "丧门(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("丧门(年)")
    except Exception:
        pass


def apply_zai_sha(result: dict) -> None:
    try:
        GROUPS = {"申子辰": "午", "亥卯未": "酉", "寅午戌": "子", "巳酉丑": "卯"}
        year_zhi = _p(result, "pillars", "year", "zhi")
        if not year_zhi:
            return
        target_zhi = None
        for g, t in GROUPS.items():
            if year_zhi in g:
                target_zhi = t
                break
        if not target_zhi:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in ["month", "day", "time"]:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "灾煞(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("灾煞(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "灾煞(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("灾煞(年)")
    except Exception:
        pass


def apply_diao_ke(result: dict) -> None:
    try:
        year_zhi = _p(result, "pillars", "year", "zhi")
        if not year_zhi or year_zhi not in ZHIS:
            return
        idx = ZHIS.index(year_zhi)
        target_zhi = ZHIS[(idx + 10) % 12]
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in ["month", "day", "time"]:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "吊客(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("吊客(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "吊客(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("吊客(年)")
    except Exception:
        pass


def apply_pi_ma(result: dict) -> None:
    try:
        year_zhi = _p(result, "pillars", "year", "zhi")
        if not year_zhi or year_zhi not in ZHIS:
            return
        idx = ZHIS.index(year_zhi)
        target_zhi = ZHIS[(idx + 9) % 12]
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in ["month", "day", "time"]:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "披麻(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("披麻(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "披麻(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("披麻(年)")
    except Exception:
        pass


def apply_tong_zi_sha(result: dict) -> None:
    try:
        month_zhi = _p(result, "pillars", "month", "zhi")
        day_zhi = _p(result, "pillars", "day", "zhi")
        time_zhi = _p(result, "pillars", "time", "zhi")
        year_na_yin = (_p(result, "pillars", "year") or {}).get("naYin") or ""
        ensure_shensha(result)
        targets_season = set()
        if month_zhi:
            if month_zhi in ["寅", "卯", "辰"] or month_zhi in ["申", "酉", "戌"]:
                targets_season |= {"寅", "子"}
            elif month_zhi in ["巳", "午", "未"] or month_zhi in ["亥", "子", "丑"]:
                targets_season |= {"卯", "未", "辰"}
        m = re.search(r"[金木水火土]", year_na_yin)
        nayin_wuxing = m.group(0) if m else ""
        targets_nayin = set()
        if nayin_wuxing:
            if nayin_wuxing in "金木":
                targets_nayin |= {"午", "卯"}
            elif nayin_wuxing in "水火":
                targets_nayin |= {"酉", "戌"}
            elif nayin_wuxing == "土":
                targets_nayin |= {"辰", "巳"}
        targets = targets_season | targets_nayin
        if not targets:
            return
        for k, zhi in [("day", day_zhi), ("time", time_zhi)]:
            if not zhi:
                continue
            arr_key = "ri" if k == "day" else "shi"
            if zhi in targets and "童子煞" not in result["shensha"][arr_key]:
                result["shensha"][arr_key].append("童子煞")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                gz = (obj or {}).get("ganZhi")
                _, zhi = _gz(gz)
                if zhi and zhi in targets and "童子煞" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("童子煞")
    except Exception:
        pass


def apply_shi_ling_ri(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        day_gz = (day_gan or "") + (day_zhi or "")
        LIST = {"甲辰", "乙亥", "丙辰", "丁酉", "戊午", "庚戌", "庚寅", "辛亥", "壬寅", "癸未"}
        if not day_gz or day_gz not in LIST:
            return
        ensure_shensha(result)
        if "十灵日(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("十灵日(日)")
        current_yun = _p(result, "currentYun")
        liu_ri = (current_yun or {}).get("liuRi")
        if current_yun and liu_ri:
            gz = (liu_ri or {}).get("ganZhi")
            gan, zhi = _gz(gz)
            cur_gz = (gan or "") + (zhi or "")
            if cur_gz in LIST and "十灵日(日)" not in result["shensha"]["current"]["liuRi"]:
                result["shensha"]["current"]["liuRi"].append("十灵日(日)")
    except Exception:
        pass


def apply_ba_zhuan_ri(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        day_gz = (day_gan or "") + (day_zhi or "")
        LIST = {"甲寅", "乙卯", "丁未", "戊戌", "己未", "庚申", "辛酉", "癸丑"}
        if not day_gz or day_gz not in LIST:
            return
        ensure_shensha(result)
        if "八专日(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("八专日(日)")
        current_yun = _p(result, "currentYun")
        liu_ri = (current_yun or {}).get("liuRi")
        if current_yun and liu_ri:
            gz = (liu_ri or {}).get("ganZhi")
            gan, zhi = _gz(gz)
            cur_gz = (gan or "") + (zhi or "")
            if cur_gz in LIST and "八专日(日)" not in result["shensha"]["current"]["liuRi"]:
                result["shensha"]["current"]["liuRi"].append("八专日(日)")
    except Exception:
        pass


def apply_liu_xiu_ri(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        day_gz = (day_gan or "") + (day_zhi or "")
        LIST = {"丙午", "丁未", "戊子", "戊午", "己丑", "己未"}
        if not day_gz or day_gz not in LIST:
            return
        ensure_shensha(result)
        if "六秀日(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("六秀日(日)")
        current_yun = _p(result, "currentYun")
        liu_ri = (current_yun or {}).get("liuRi")
        if current_yun and liu_ri:
            gz = (liu_ri or {}).get("ganZhi")
            gan, zhi = _gz(gz)
            cur_gz = (gan or "") + (zhi or "")
            if cur_gz in LIST and "六秀日(日)" not in result["shensha"]["current"]["liuRi"]:
                result["shensha"]["current"]["liuRi"].append("六秀日(日)")
    except Exception:
        pass


def apply_jiu_chou_ri(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        day_gz = (day_gan or "") + (day_zhi or "")
        LIST = {"丁酉", "戊子", "戊午", "己卯", "己酉", "辛卯", "辛酉", "壬子", "壬午"}
        if not day_gz or day_gz not in LIST:
            return
        ensure_shensha(result)
        if "九丑日(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("九丑日(日)")
        current_yun = _p(result, "currentYun")
        liu_ri = (current_yun or {}).get("liuRi")
        if current_yun and liu_ri:
            gz = (liu_ri or {}).get("ganZhi")
            gan, zhi = _gz(gz)
            cur_gz = (gan or "") + (zhi or "")
            if cur_gz in LIST and "九丑日(日)" not in result["shensha"]["current"]["liuRi"]:
                result["shensha"]["current"]["liuRi"].append("九丑日(日)")
    except Exception:
        pass


def apply_si_fei_ri(result: dict) -> None:
    try:
        SPRING, SUMMER, AUTUMN, WINTER = {"寅", "卯", "辰"}, {"巳", "午", "未"}, {"申", "酉", "戌"}, {"亥", "子", "丑"}
        SEASON_MAP = {"SPRING": {"庚申", "辛酉"}, "SUMMER": {"壬子", "癸亥"}, "AUTUMN": {"甲寅", "乙卯"}, "WINTER": {"丙午", "丁巳"}}
        month_zhi = _p(result, "pillars", "month", "zhi")
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        day_gz = (day_gan or "") + (day_zhi or "")
        if not month_zhi or not day_gz:
            return
        season_key = ""
        if month_zhi in SPRING:
            season_key = "SPRING"
        elif month_zhi in SUMMER:
            season_key = "SUMMER"
        elif month_zhi in AUTUMN:
            season_key = "AUTUMN"
        elif month_zhi in WINTER:
            season_key = "WINTER"
        if not season_key or day_gz not in SEASON_MAP.get(season_key, set()):
            return
        ensure_shensha(result)
        if "四废日(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("四废日(日)")
        current_yun = _p(result, "currentYun")
        ly = (current_yun or {}).get("liuYue")
        lr = (current_yun or {}).get("liuRi")
        if current_yun and ly and lr:
            zhi_yue = _gz((ly or {}).get("ganZhi"))[1]
            gan_ri, zhi_ri = _gz((lr or {}).get("ganZhi"))
            cur_gz = (gan_ri or "") + (zhi_ri or "")
            cur_season = ""
            if zhi_yue in SPRING:
                cur_season = "SPRING"
            elif zhi_yue in SUMMER:
                cur_season = "SUMMER"
            elif zhi_yue in AUTUMN:
                cur_season = "AUTUMN"
            elif zhi_yue in WINTER:
                cur_season = "WINTER"
            cur_targets = SEASON_MAP.get(cur_season, set()) if cur_season else set()
            if cur_gz in cur_targets and "四废日(日)" not in result["shensha"]["current"]["liuRi"]:
                result["shensha"]["current"]["liuRi"].append("四废日(日)")
    except Exception:
        pass


def apply_shi_e_da_bai_ri(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        day_gz = (day_gan or "") + (day_zhi or "")
        LIST = {"甲辰", "乙巳", "丙申", "丁亥", "戊戌", "己丑", "庚辰", "辛巳", "壬申", "癸亥"}
        if not day_gz or day_gz not in LIST:
            return
        ensure_shensha(result)
        if "十恶大败(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("十恶大败(日)")
        current_yun = _p(result, "currentYun")
        liu_ri = (current_yun or {}).get("liuRi")
        if current_yun and liu_ri:
            gz = (liu_ri or {}).get("ganZhi")
            gan, zhi = _gz(gz)
            cur_gz = (gan or "") + (zhi or "")
            if cur_gz in LIST and "十恶大败(日)" not in result["shensha"]["current"]["liuRi"]:
                result["shensha"]["current"]["liuRi"].append("十恶大败(日)")
    except Exception:
        pass


def apply_yin_cha_yang_cuo_ri(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        day_gz = (day_gan or "") + (day_zhi or "")
        LIST = {"丙子", "丙午", "丁丑", "丁未", "戊寅", "戊申", "辛卯", "辛酉", "壬辰", "壬戌", "癸巳", "癸亥"}
        if not day_gz or day_gz not in LIST:
            return
        ensure_shensha(result)
        if "阴差阳错(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("阴差阳错(日)")
        current_yun = _p(result, "currentYun")
        liu_ri = (current_yun or {}).get("liuRi")
        if current_yun and liu_ri:
            gz = (liu_ri or {}).get("ganZhi")
            gan, zhi = _gz(gz)
            cur_gz = (gan or "") + (zhi or "")
            if cur_gz in LIST and "阴差阳错(日)" not in result["shensha"]["current"]["liuRi"]:
                result["shensha"]["current"]["liuRi"].append("阴差阳错(日)")
    except Exception:
        pass


def apply_gu_luan_sha_ri(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        day_gz = (day_gan or "") + (day_zhi or "")
        LIST = {"甲寅", "乙巳", "丙午", "丁巳", "戊午", "戊申", "辛亥", "壬子"}
        if not day_gz or day_gz not in LIST:
            return
        ensure_shensha(result)
        if "孤鸾(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("孤鸾(日)")
    except Exception:
        pass


def apply_gong_lu_ri_shi(result: dict) -> None:
    try:
        day_gan = _p(result, "pillars", "day", "gan")
        day_zhi = _p(result, "pillars", "day", "zhi")
        time_gan = _p(result, "pillars", "time", "gan")
        time_zhi = _p(result, "pillars", "time", "zhi")
        if not day_gan or not day_zhi or not time_gan or not time_zhi:
            return
        day_gz = day_gan + day_zhi
        time_gz = time_gan + time_zhi
        PAIRS = [
            ("癸亥", "癸丑", "壬子禄"),
            ("癸丑", "癸亥", "壬子禄"),
            ("丁巳", "丁未", "壬午禄"),
            ("己未", "己巳", "壬午禄"),
            ("戊辰", "戊午", "壬巳禄"),
        ]
        hit = None
        for d, t, tag in PAIRS:
            if d == day_gz and t == time_gz:
                hit = tag
                break
        if not hit:
            return
        ensure_shensha(result)
        if hit not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append(hit)
        if hit not in result["shensha"]["shi"]:
            result["shensha"]["shi"].append(hit)
    except Exception:
        pass


def apply_di_zhuan_ri_yue_zhi(result: dict) -> None:
    try:
        if not result or not result.get("pillars"):
            return
        month_zhi = (result.get("pillars") or {}).get("month") or {}
        month_zhi = month_zhi.get("zhi") if isinstance(month_zhi, dict) else None
        day_val = (result.get("pillars") or {}).get("day") or {}
        day_val = day_val.get("value") if isinstance(day_val, dict) else None
        if not month_zhi or not day_val:
            return
        SEASON_ZHI = {"春": ["寅", "卯", "辰"], "夏": ["巳", "午", "未"], "秋": ["申", "酉", "戌"], "冬": ["亥", "子", "丑"]}
        SEASON_DAY = {"春": ["乙卯", "辛卯"], "夏": ["丙午", "戊午"], "秋": ["辛酉", "癸酉"], "冬": ["壬子", "丙子"]}
        season = None
        for s, zhis in SEASON_ZHI.items():
            if month_zhi in zhis:
                season = s
                break
        if not season or day_val not in SEASON_DAY.get(season, []):
            return
        ensure_shensha(result)
        result["shensha"].setdefault("ri", [])
        if "地转日(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("地转日(日)")
    except Exception:
        pass


def apply_tian_zhuan_ri_yue_zhi(result: dict) -> None:
    try:
        if not result or not result.get("pillars"):
            return
        month_zhi = (result.get("pillars") or {}).get("month") or {}
        month_zhi = month_zhi.get("zhi") if isinstance(month_zhi, dict) else None
        day_val = (result.get("pillars") or {}).get("day") or {}
        day_val = day_val.get("value") if isinstance(day_val, dict) else None
        if not month_zhi or not day_val:
            return
        SEASON_ZHI = {"春": ["寅", "卯", "辰"], "夏": ["巳", "午", "未"], "秋": ["申", "酉", "戌"], "冬": ["亥", "子", "丑"]}
        SEASON_DAY = {"春": ["乙卯", "辛卯"], "夏": ["丙午", "戊午"], "秋": ["辛酉", "癸酉"], "冬": ["壬子", "丙子"]}
        season = None
        for s, zhis in SEASON_ZHI.items():
            if month_zhi in zhis:
                season = s
                break
        if not season or day_val not in SEASON_DAY.get(season, []):
            return
        ensure_shensha(result)
        result["shensha"].setdefault("ri", [])
        if "天转日(日)" not in result["shensha"]["ri"]:
            result["shensha"]["ri"].append("天转日(日)")
    except Exception:
        pass


def apply_gua_su(result: dict) -> None:
    try:
        MAP = {"寅": "丑", "卯": "丑", "辰": "丑", "巳": "辰", "午": "辰", "未": "辰", "申": "未", "酉": "未", "戌": "未", "亥": "戌", "子": "戌", "丑": "戌"}
        year_zhi = _p(result, "pillars", "year", "zhi")
        target_zhi = MAP.get(year_zhi) if year_zhi else None
        if not target_zhi:
            return
        ensure_shensha(result)
        pillars = _p(result, "pillars")
        if pillars:
            for k in ["month", "day", "time"]:
                p = pillars.get(k)
                if not p:
                    continue
                zhi = p.get("zhi")
                arr_key = KEY_MAP[k]
                if zhi == target_zhi and "寡宿(年)" not in result["shensha"][arr_key]:
                    result["shensha"][arr_key].append("寡宿(年)")
        current_yun = _p(result, "currentYun")
        if current_yun:
            for name in ["daYun", "liuNian", "liuYue", "liuRi"]:
                obj = current_yun.get(name)
                _, zhi = _gz((obj or {}).get("ganZhi"))
                if not obj or not zhi or zhi != target_zhi:
                    continue
                if "寡宿(年)" not in result["shensha"]["current"][name]:
                    result["shensha"]["current"][name].append("寡宿(年)")
    except Exception:
        pass


# 与 JS 导出顺序一致的全部神煞应用函数
SHENSHA_APPLIERS = [
    apply_tian_yi,
    apply_yue_de,
    apply_yue_de_he,
    apply_tian_de,
    apply_tian_de_he,
    apply_tai_ji_gui_ren,
    apply_wen_chang_gui_ren,
    apply_guo_yin_gui_ren,
    apply_zheng_xue_tang,
    apply_ci_guan,
    apply_fu_xing_gui_ren,
    apply_tian_chu_gui_ren,
    apply_de_xiu_gui_ren,
    apply_san_qi_gui_ren,
    apply_jiang_xing,
    apply_hua_gai,
    apply_tian_luo_di_wang,
    apply_kui_gang,
    apply_tian_she_ri,
    apply_jin_shen,
    apply_tian_yi_star,
    apply_lu_shen,
    apply_liu_xia,
    apply_yi_ma,
    apply_tao_hua,
    apply_hong_yan_sha,
    apply_jin_yu,
    apply_hong_luan,
    apply_tian_xi,
    apply_yang_ren,
    apply_fei_ren,
    apply_jie_sha,
    apply_kong_wang,
    apply_xue_ren,
    apply_gou_jiao_sha,
    apply_yuan_chen,
    apply_gu_chen,
    apply_sang_men,
    apply_zai_sha,
    apply_diao_ke,
    apply_pi_ma,
    apply_tong_zi_sha,
    apply_shi_ling_ri,
    apply_ba_zhuan_ri,
    apply_liu_xiu_ri,
    apply_jiu_chou_ri,
    apply_si_fei_ri,
    apply_shi_e_da_bai_ri,
    apply_yin_cha_yang_cuo_ri,
    apply_gu_luan_sha_ri,
    apply_gong_lu_ri_shi,
    apply_di_zhuan_ri_yue_zhi,
    apply_tian_zhuan_ri_yue_zhi,
    apply_gua_su,
    apply_wang_shen,
]


def apply_all(result: dict) -> None:
    """对 result 依次应用全部神煞，填充 result['shensha']。"""

    for fn in SHENSHA_APPLIERS:
        try:
            fn(result)
        except Exception:
            pass


__all__ = [
    "GANS",
    "ZHIS",
    "KEY_MAP",
    "ensure_shensha",
    "apply_all",
    "SHENSHA_APPLIERS",
] + [f.__name__ for f in SHENSHA_APPLIERS]

