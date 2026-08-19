# -*- coding: utf-8 -*-
"""徽章系统：根据进度快照自动颁发"""
import db
import content

RULES = [
    {"id": "first_task", "icon": "🎯", "name": "初出茅庐", "desc": "完成第 1 个闯关任务",
     "check": lambda c: c["solved_total"] >= 1},
    {"id": "sql_20", "icon": "🗄️", "name": "SQL 小能手", "desc": "完成 20 个 SQL 闯关任务",
     "check": lambda c: c["by_type"].get("sql", 0) >= 20},
    {"id": "python_20", "icon": "🐍", "name": "Python 编程家", "desc": "完成 20 个 Python 编程任务",
     "check": lambda c: c["by_type"].get("python", 0) >= 20},
    {"id": "hands_10", "icon": "🛠️", "name": "动手达人", "desc": "完成 10 次动手实践",
     "check": lambda c: c["hands"] >= 10},
    {"id": "streak_3", "icon": "📅", "name": "三日之约", "desc": "连续打卡 3 天",
     "check": lambda c: c["streak"] >= 3},
    {"id": "streak_7", "icon": "⏰", "name": "一周坚持", "desc": "连续打卡 7 天",
     "check": lambda c: c["streak"] >= 7},
    {"id": "streak_30", "icon": "🏆", "name": "月度全勤", "desc": "连续打卡 30 天",
     "check": lambda c: c["streak"] >= 30},
    {"id": "stage_5", "icon": "🚀", "name": "阶段王者", "desc": "通关 5 个阶段（每阶段任务完成 ≥80%）",
     "check": lambda c: c["stages_done"] >= 5},
    {"id": "journey_half", "icon": "🧭", "name": "半程勇士", "desc": "完成全部闯关任务的一半",
     "check": lambda c: c["total"] > 0 and c["solved_total"] >= max(1, c["total"] // 2)},
    {"id": "journey_done", "icon": "👑", "name": "大数据毕业", "desc": "完成全部闯关任务",
     "check": lambda c: c["total"] > 0 and c["solved_total"] >= c["total"]},
    {"id": "xp_3000", "icon": "💎", "name": "经验收藏家", "desc": "累计获得 3000 XP",
     "check": lambda c: c["xp"] >= 3000},
]


def _context():
    tasks_state = db.all_task_states()
    solved_total = 0
    by_type = {}
    stage_counts = {}
    total = 0
    for t in content.TASKS:
        total += 1
        sid = t["stage_id"]
        c = stage_counts.setdefault(sid, [0, 0])
        c[1] += 1
        st = tasks_state.get(t["task_id"])
        if st and st["solved"]:
            solved_total += 1
            by_type[t["type"]] = by_type.get(t["type"], 0) + 1
            c[0] += 1
    stages_done = sum(1 for (s, t) in stage_counts.values() if t > 0 and s / t >= 0.8)
    return {
        "solved_total": solved_total,
        "by_type": by_type,
        "total": total,
        "hands": len(db.hands_done_set()),
        "streak": int(db.get("streak", "0") or 0),
        "stages_done": stages_done,
        "xp": db.total_xp(),
    }


def refresh():
    """重算并颁发新徽章，返回本次新获得的徽章列表"""
    ctx = _context()
    new = []
    for rule in RULES:
        if rule["check"](ctx):
            if db.add_badge(rule["id"]):
                new.append({"id": rule["id"], "icon": rule["icon"], "name": rule["name"], "desc": rule["desc"]})
    return new


def all_rules():
    return [{k: r[k] for k in ("id", "icon", "name", "desc")} for r in RULES]
