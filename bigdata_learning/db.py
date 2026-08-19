# -*- coding: utf-8 -*-
"""SQLite 持久化层：进度、任务状态、XP、徽章、打卡（纯标准库）"""
import os
import sqlite3
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "learning.db")
if os.environ.get("DS_E2E_TMPDB") == "1":
    # 端到端测试模式：使用临时数据库，绝不触碰真实学习数据
    import tempfile as _tmp
    DB_PATH = os.path.join(_tmp.gettempdir(), "dsh_e2e_learning.db")


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = connect()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS user_state (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS task_state (
        task_id TEXT PRIMARY KEY,
        attempts INTEGER NOT NULL DEFAULT 0,
        solved INTEGER NOT NULL DEFAULT 0,
        best_xp INTEGER NOT NULL DEFAULT 0,
        first_solved_at TEXT
    );
    CREATE TABLE IF NOT EXISTS hands_state (chapter_id TEXT PRIMARY KEY, done_at TEXT);
    CREATE TABLE IF NOT EXISTS badges (badge_id TEXT PRIMARY KEY, earned_at TEXT);
    CREATE TABLE IF NOT EXISTS xp_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, ref TEXT, xp INTEGER, at TEXT
    );
    """)
    conn.commit()
    conn.close()


def get(key, default=None):
    conn = connect()
    try:
        row = conn.execute("SELECT value FROM user_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set(key, value):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO user_state(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        conn.commit()
    finally:
        conn.close()


def add_xp(kind, ref, xp):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO xp_events(kind,ref,xp,at) VALUES(?,?,?,?)",
            (kind, ref, xp, date.today().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def total_xp():
    conn = connect()
    try:
        return conn.execute("SELECT COALESCE(SUM(xp),0) FROM xp_events").fetchone()[0]
    finally:
        conn.close()


def get_task_state(task_id):
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM task_state WHERE task_id=?", (task_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def all_task_states():
    conn = connect()
    try:
        return {r["task_id"]: dict(r) for r in conn.execute("SELECT * FROM task_state")}
    finally:
        conn.close()


def record_attempt(task_id, attempts):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO task_state(task_id, attempts, solved, best_xp, first_solved_at) "
            "VALUES(?,?,0,0,NULL) "
            "ON CONFLICT(task_id) DO UPDATE SET attempts=excluded.attempts",
            (task_id, attempts),
        )
        conn.commit()
    finally:
        conn.close()


def record_solve(task_id, attempts, xp):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO task_state(task_id, attempts, solved, best_xp, first_solved_at) "
            "VALUES(?,?,1,?,?) "
            "ON CONFLICT(task_id) DO UPDATE SET "
            " attempts=excluded.attempts, solved=1,"
            " best_xp=CASE WHEN excluded.best_xp > task_state.best_xp THEN excluded.best_xp ELSE task_state.best_xp END,"
            " first_solved_at=CASE WHEN task_state.first_solved_at IS NULL THEN excluded.first_solved_at ELSE task_state.first_solved_at END",
            (task_id, attempts, xp, date.today().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def mark_hands_done(chapter_id):
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO hands_state(chapter_id, done_at) VALUES(?,?)",
            (chapter_id, date.today().isoformat()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def hands_done_set():
    conn = connect()
    try:
        return {r["chapter_id"] for r in conn.execute("SELECT chapter_id FROM hands_state")}
    finally:
        conn.close()


def add_badge(badge_id):
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO badges(badge_id, earned_at) VALUES(?,?)",
            (badge_id, date.today().isoformat()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_badges():
    conn = connect()
    try:
        return [r["badge_id"] for r in conn.execute("SELECT badge_id FROM badges ORDER BY earned_at")]
    finally:
        conn.close()


def touch_active():
    """更新活跃记录与连续学习天数，返回当前连续天数"""
    today = date.today()
    last = get("last_active")
    try:
        streak = int(get("streak", "0") or 0)
    except ValueError:
        streak = 0
    if last == today.isoformat():
        return streak
    try:
        if last and date.fromisoformat(last) == today - timedelta(days=1):
            streak += 1
        else:
            streak = 1
    except ValueError:
        streak = 1
    set("last_active", today.isoformat())
    set("streak", streak)
    return streak


def checkin_today():
    return get("checkin_date") == date.today().isoformat()


def do_checkin():
    """执行今日打卡，返回 (是否新打卡, 连续天数)"""
    today = date.today().isoformat()
    if get("checkin_date") == today:
        return False, touch_active()
    set("checkin_date", today)
    streak = touch_active()
    add_xp("checkin", today, 10)
    return True, streak


def reset_all():
    conn = connect()
    try:
        conn.executescript(
            "DROP TABLE IF EXISTS user_state; DROP TABLE IF EXISTS task_state; "
            "DROP TABLE IF EXISTS hands_state; DROP TABLE IF EXISTS badges; "
            "DROP TABLE IF EXISTS xp_events;"
        )
        conn.commit()
    finally:
        conn.close()
    init()
