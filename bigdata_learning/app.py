# -*- coding: utf-8 -*-
"""
大数据学习闯关平台 —— 本地 Web 服务器
纯 Python 标准库实现，无需安装任何第三方依赖。
启动：双击 start.bat，或命令行执行 python app.py
访问：http://127.0.0.1:8321
"""
import json
import math
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import badges
import checker
import content
import db
import plan

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DEFAULT_PORT = 8321

LEVEL_BASE = 150            # 等级经验基数：level n 需要 (n-1)^2 * LEVEL_BASE
XP_BY_DIFF = {1: 30, 2: 45, 3: 60, 4: 80, 5: 100}
ATTEMPT_MULT = (1.0, 0.6, 0.3, 0.15, 0.05)
HANDS_XP = 40
CHECKIN_XP = 10

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


def level_of(xp):
    return max(1, int(math.sqrt(xp / LEVEL_BASE)) + 1)


def level_progress(xp):
    level = level_of(xp)
    cur = (level - 1) ** 2 * LEVEL_BASE
    nxt = level ** 2 * LEVEL_BASE
    return {"level": level, "cur": cur, "nxt": nxt, "ratio": min(1.0, (xp - cur) / max(1, nxt - cur))}


def build_snapshot():
    """汇总进度快照（供 bootstrap 与每次操作后刷新）"""
    tasks_state = db.all_task_states()
    hands = db.hands_done_set()
    xp = db.total_xp()
    try:
        streak = int(db.get("streak", "0") or 0)
    except ValueError:
        streak = 0

    all_tasks = content.TASKS
    solved_total = 0
    solved_by_type = {}
    for t in all_tasks:
        st = tasks_state.get(t["task_id"])
        if st and st["solved"]:
            solved_total += 1
            solved_by_type[t["type"]] = solved_by_type.get(t["type"], 0) + 1

    stages_summary = []
    for i, st in enumerate(content.STAGES):
        stage_tasks = [t for ch in st["chapters"] for t in ch.get("tasks", [])]
        stage_solved = sum(1 for t in stage_tasks if tasks_state.get(t["task_id"], {}).get("solved"))
        locked = False  # v1.1：取消上锁机制，所有阶段/章节自由访问
        chapters = []
        for ci, ch in enumerate(st["chapters"]):
            ch_tasks = ch.get("tasks", [])
            ch_solved = sum(1 for t in ch_tasks if tasks_state.get(t["task_id"], {}).get("solved"))
            ch_locked = False  # v1.1：取消上锁
            chapters.append({
                "chapter_id": ch["chapter_id"],
                "title": ch["title"],
                "task_count": len(ch_tasks),
                "solved": ch_solved,
                "locked": ch_locked,
                "has_hands_on": bool(ch.get("hands_on")),
                "hands_done": ch["chapter_id"] in hands,
            })
        stages_summary.append({
            "stage_id": st["stage_id"],
            "index": i,
            "title": st["title"],
            "subtitle": st.get("subtitle", ""),
            "emoji": st.get("emoji", "📘"),
            "estimated_days": st.get("estimated_days", 1),
            "task_count": len(stage_tasks),
            "solved": stage_solved,
            "locked": locked,
            "chapters": chapters,
        })

    schedule = plan.build_schedule(content.STAGES)
    total_days = len(schedule)
    day_index = min(max(1, plan.current_day_index()), total_days)
    today_entries = [e for e in schedule if e["day"] == day_index]

    earned = set(db.list_badges())
    badge_list = [dict(r, earned=r["id"] in earned) for r in badges.all_rules()]

    return {
        "xp": xp,
        "level": level_progress(xp),
        "streak": streak,
        "solved_total": solved_total,
        "total_tasks": len(all_tasks),
        "solved_by_type": solved_by_type,
        "hands_count": len(hands),
        "badges": badge_list,
        "stages": stages_summary,
        "plan": {
            "total_days": total_days,
            "day_index": day_index,
            "start_date": db.get("start_date"),
            "today": today_entries,
            "checkin_done": db.checkin_today(),
        },
        "tasks_state": tasks_state,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "BigDataLearn/1.0"

    def log_message(self, fmt, *args):
        pass

    # ---------- 基础工具 ----------
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def _file(self, rel):
        path = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not path.startswith(STATIC_DIR) or not os.path.isfile(path):
            self._json({"error": "not found"}, 404)
            return
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # ---------- GET ----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._file("index.html")
        elif path.startswith("/static/"):
            self._file(path[len("/static/"):])
        elif path == "/api/bootstrap":
            self._json({"app": content.META, "snapshot": build_snapshot()})
        elif path.startswith("/api/stage/"):
            sid = path[len("/api/stage/"):]
            stage = next((s for s in content.STAGES if s["stage_id"] == sid), None)
            if stage:
                self._json(stage)
            else:
                self._json({"error": "stage not found"}, 404)
        elif path == "/api/interview":
            iv_path = os.path.join(content.CONTENT_DIR, "interview.json")
            if os.path.exists(iv_path):
                with open(iv_path, encoding="utf-8") as f:
                    self._json(json.load(f))
            else:
                self._json({"title": "面试宝典", "categories": []})
        else:
            self._json({"error": "not found"}, 404)

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        if path == "/api/submit":
            self._json(self._submit(body))
        elif path == "/api/hands_on":
            self._json(self._hands_on(body))
        elif path == "/api/checkin":
            self._json(self._checkin())
        elif path == "/api/run_code":
            code = body.get("code", "")
            ok, (out, err) = checker.run_python(code)
            self._json({"ok": ok, "stdout": out, "stderr": err})
        elif path == "/api/run_sql":
            task = content.TASK_BY_ID.get(body.get("task_id", ""))
            if not task or task.get("type") != "sql":
                self._json({"error": "task not found"}, 404)
                return
            ok, data = checker.run_sql(task.get("setup", ""), body.get("sql", ""))
            if ok:
                self._json({"ok": True, "cols": data[0], "rows": data[1]})
            else:
                self._json({"ok": False, "error": data})
        elif path == "/api/reset":
            if body.get("confirm") == "RESET":
                db.reset_all()
                self._json({"ok": True})
            else:
                self._json({"error": "需要 confirm=RESET"}, 400)
        else:
            self._json({"error": "not found"}, 404)

    # ---------- 业务 ----------
    def _submit(self, body):
        task_id = body.get("task_id", "")
        task = content.TASK_BY_ID.get(task_id)
        if not task:
            return {"error": "task not found"}
        answer = body.get("answer")
        prev = db.get_task_state(task_id)
        already = bool(prev and prev["solved"])

        result = checker.grade(task, answer)
        attempts = (prev["attempts"] if prev else 0) + 1
        xp = 0
        if result["correct"]:
            if already:
                db.record_attempt(task_id, attempts)
            else:
                diff = max(1, min(5, task.get("difficulty", 1)))
                mult = ATTEMPT_MULT[min(attempts - 1, len(ATTEMPT_MULT) - 1)]
                xp = max(5, round(XP_BY_DIFF[diff] * mult))
                db.record_solve(task_id, attempts, xp)
                db.add_xp("task", task_id, xp)
                db.touch_active()
        else:
            db.record_attempt(task_id, attempts)

        new_badges = badges.refresh()
        return {
            "correct": result["correct"],
            "already": already,
            "attempts": attempts,
            "xp": xp,
            "feedback": result["feedback"],
            "expected_display": result.get("expected_display"),
            "analysis": result["analysis"],
            "reference": result.get("reference"),
            "enterprise_tip": result.get("enterprise_tip"),
            "new_badges": new_badges,
            "snapshot": build_snapshot(),
        }

    def _hands_on(self, body):
        chapter_id = body.get("chapter_id", "")
        found = any(ch["chapter_id"] == chapter_id for st in content.STAGES for ch in st["chapters"])
        if not found:
            return {"error": "chapter not found"}
        new = db.mark_hands_done(chapter_id)
        xp = 0
        if new:
            xp = HANDS_XP
            db.add_xp("hands", chapter_id, xp)
            db.touch_active()
        return {
            "done": True,
            "xp": xp,
            "new_badges": badges.refresh(),
            "snapshot": build_snapshot(),
        }

    def _checkin(self):
        new, streak = db.do_checkin()
        xp = CHECKIN_XP if new else 0
        return {
            "new": new,
            "xp": xp,
            "streak": streak,
            "new_badges": badges.refresh(),
            "snapshot": build_snapshot(),
        }


def main():
    db.init()
    port = DEFAULT_PORT
    httpd = None
    for p in range(port, port + 10):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            port = p
            break
        except OSError:
            continue
    if httpd is None:
        print("端口 %d~%d 均被占用，请关闭占用程序后重试" % (DEFAULT_PORT, DEFAULT_PORT + 9))
        sys.exit(1)
    url = "http://127.0.0.1:%d" % port
    print("=" * 62)
    print("  大数据学习闯关平台 已启动")
    print("  访问地址：%s" % url)
    print("  学习进度 / XP / 徽章 / 打卡 自动保存在本地 data 目录")
    print("  关闭本窗口即退出程序")
    print("=" * 62)
    if os.environ.get("DS_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
