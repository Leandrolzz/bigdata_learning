# -*- coding: utf-8 -*-
"""每日学习计划：把全部章节铺到 123 天的日程上（每天约 2 小时 = 120 分钟）"""
from datetime import date, timedelta

import db


def build_schedule(stages):
    """返回按天排序的计划列表：
    [{day, stage_id, stage_title, chapter_id, chapter_title, parts:[{label, min}]}]
    """
    days = []
    day_no = 0
    for stage in stages:
        for ch in stage["chapters"]:
            plan_days = max(1, int(ch.get("plan_days", 1)))
            br = ch.get("plan_breakdown", {})
            theory = int(br.get("theory_min", 40))
            tasks = int(br.get("tasks_min", 50))
            hands = int(br.get("hands_on_min", 20))
            review = int(br.get("review_min", 10))
            for i in range(plan_days):
                day_no += 1
                if plan_days == 1:
                    parts = [("理论学习", theory), ("交互闯关", tasks), ("动手实践", hands), ("回顾总结", review)]
                elif i == 0:
                    parts = [("理论学习", theory), ("交互闯关（前半）", max(1, tasks // 2))]
                elif i == plan_days - 1:
                    parts = [
                        ("交互闯关（后半）", max(1, tasks - tasks // 2)),
                        ("动手实践", hands),
                        ("回顾总结", review),
                    ]
                else:
                    parts = [
                        ("交互闯关 + 复习", max(1, tasks // 2 + review // 2)),
                        ("动手实践（可选）", max(1, hands // 2)),
                    ]
                days.append({
                    "day": day_no,
                    "stage_id": stage["stage_id"],
                    "stage_title": stage["title"],
                    "chapter_id": ch["chapter_id"],
                    "chapter_title": ch["title"],
                    "parts": [{"label": lb, "min": mn} for lb, mn in parts],
                })
    return days


def current_day_index():
    """根据开始日期计算今天是第几天（1 起）"""
    today = date.today()
    start = db.get("start_date")
    if not start:
        db.set("start_date", today.isoformat())
        return 1
    try:
        return max(1, (today - date.fromisoformat(start)).days + 1)
    except ValueError:
        return 1
