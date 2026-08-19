# -*- coding: utf-8 -*-
"""恢复学习进度（v1.4 的一次性工具）
根据 e2e 测试时捕获的快照重建 data/learning.db，恢复用户真实进度。
"""
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "learning.db")

# 快照数据（来自 2026-08-18 e2e 输出）：
# task_id -> (attempts, solved, best_xp, first_solved_at)
TASKS = {
    "s01c01t01": (2, 1, 30, "2026-08-17"), "s01c01t02": (1, 1, 30, "2026-08-17"),
    "s01c01t03": (1, 1, 30, "2026-08-17"), "s01c01t04": (1, 1, 30, "2026-08-17"),
    "s01c01t05": (1, 1, 30, "2026-08-17"), "s01c01t06": (1, 1, 30, "2026-08-17"),
    "s01c01t07": (1, 1, 30, "2026-08-17"), "s01c01t08": (2, 1, 27, "2026-08-17"),
    "s01c01t09": (1, 1, 45, "2026-08-17"), "s01c01t10": (3, 1, 14, "2026-08-17"),
    "s01c02t01": (1, 1, 30, "2026-08-17"), "s01c02t02": (1, 1, 30, "2026-08-17"),
    "s01c02t03": (1, 1, 30, "2026-08-17"), "s01c02t04": (2, 1, 27, "2026-08-17"),
    "s01c02t05": (2, 1, 27, "2026-08-17"), "s01c02t06": (1, 1, 45, "2026-08-17"),
    "s01c02t07": (1, 1, 30, "2026-08-17"), "s01c02t08": (1, 1, 45, "2026-08-17"),
    "s01c02t09": (1, 1, 45, "2026-08-17"),
    "s01c03t01": (1, 1, 45, "2026-08-17"), "s01c03t02": (1, 1, 45, "2026-08-17"),
    "s01c03t03": (1, 1, 30, "2026-08-17"), "s01c03t04": (1, 1, 45, "2026-08-17"),
    "s01c03t05": (1, 1, 45, "2026-08-17"), "s01c03t06": (1, 1, 45, "2026-08-17"),
    "s01c03t07": (1, 1, 30, "2026-08-17"), "s01c03t08": (1, 1, 45, "2026-08-17"),
    "s01c03t09": (1, 1, 45, "2026-08-17"),
    "s01c04t01": (1, 1, 45, "2026-08-17"), "s01c04t02": (1, 1, 45, "2026-08-17"),
    "s01c04t03": (1, 1, 45, "2026-08-17"), "s01c04t04": (2, 1, 27, "2026-08-17"),
    "s01c04t05": (2, 1, 18, "2026-08-17"), "s01c04t06": (2, 1, 18, "2026-08-17"),
    "s01c04t07": (1, 1, 45, "2026-08-17"), "s01c04t08": (1, 1, 45, "2026-08-17"),
    "s01c04t09": (1, 1, 45, "2026-08-17"),
    "s01c05t01": (1, 1, 45, "2026-08-17"), "s01c05t02": (1, 1, 45, "2026-08-17"),
    "s01c05t03": (1, 1, 30, "2026-08-17"), "s01c05t04": (2, 1, 27, "2026-08-17"),
    "s01c05t05": (1, 1, 45, "2026-08-17"), "s01c05t06": (1, 1, 45, "2026-08-17"),
    "s01c05t07": (1, 1, 45, "2026-08-17"), "s01c05t08": (1, 1, 45, "2026-08-17"),
    "s01c05t09": (1, 1, 45, "2026-08-17"),
    "s01c06t01": (1, 1, 60, "2026-08-17"), "s01c06t02": (2, 1, 27, "2026-08-17"),
    "s01c06t03": (1, 1, 30, "2026-08-17"),
    "s02c01t01": (2, 1, 45, "2026-08-18"),
}

# 已完成的动手实践章节（含 e2e 补做的 s01c01）
HANDS = ["s01c01", "s01c02", "s01c03", "s01c04", "s01c05", "s01c06"]

TOTAL_XP = 2107  # 快照中的总 XP


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE user_state (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE task_state (
        task_id TEXT PRIMARY KEY,
        attempts INTEGER NOT NULL DEFAULT 0,
        solved INTEGER NOT NULL DEFAULT 0,
        best_xp INTEGER NOT NULL DEFAULT 0,
        first_solved_at TEXT
    );
    CREATE TABLE hands_state (chapter_id TEXT PRIMARY KEY, done_at TEXT);
    CREATE TABLE badges (badge_id TEXT PRIMARY KEY, earned_at TEXT);
    CREATE TABLE xp_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, ref TEXT, xp INTEGER, at TEXT
    );
    """)
    # 用户状态：开始日期 2026-08-16、连续 2 天、今日已打卡
    for k, v in [("start_date", "2026-08-16"), ("last_active", "2026-08-18"),
                 ("streak", "2"), ("checkin_date", "2026-08-18")]:
        conn.execute("INSERT INTO user_state(key,value) VALUES(?,?)", (k, v))
    # 任务状态
    for tid, (attempts, solved, xp, at) in TASKS.items():
        conn.execute(
            "INSERT INTO task_state(task_id,attempts,solved,best_xp,first_solved_at) VALUES(?,?,?,?,?)",
            (tid, attempts, solved, xp, at))
    # 动手实践
    for cid in HANDS:
        conn.execute("INSERT INTO hands_state(chapter_id,done_at) VALUES(?,?)",
                     (cid, "2026-08-17" if cid != "s01c01" else "2026-08-18"))
    # XP（重建为一条恢复记录，总额与快照一致）
    conn.execute("INSERT INTO xp_events(kind,ref,xp,at) VALUES('restore','v1.4-progress-restore',?,?)",
                 (TOTAL_XP, "2026-08-18"))
    # 徽章（与快照一致：仅初出茅庐）
    conn.execute("INSERT INTO badges(badge_id,earned_at) VALUES('first_task','2026-08-17')")
    conn.commit()
    conn.close()
    print("✅ 进度已恢复：%d 个任务、总 XP %d、连续 %d 天、动手实践 %d 次"
          % (len(TASKS), TOTAL_XP, 2, len(HANDS)))


if __name__ == "__main__":
    main()
