# -*- coding: utf-8 -*-
"""端到端测试：python tools/e2e_test.py
启动本地服务器（自动找空闲端口），验证 bootstrap / 阶段内容 / 提交判题 / 打卡 / 动手实践 / 重置 全链路。
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def check(name, cond, extra=""):
    print(("✅ " if cond else "❌ ") + name + ("  " + str(extra) if extra else ""))
    if not cond:
        FAILS.append(name)


def http(method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_server(proc, base_port=8321, tries=20):
    """app.py 在 8321~8330 范围内自动选端口，扫描实际监听端口"""
    for _ in range(tries):
        if proc.poll() is not None:
            raise RuntimeError("服务器进程提前退出")
        for p in range(base_port, base_port + 10):
            try:
                http("GET", "http://127.0.0.1:%d/api/bootstrap" % p)
                return p
            except Exception:
                continue
        time.sleep(0.5)
    raise RuntimeError("服务器启动超时（未在 8321~8330 发现服务）")


def main():
    # 重要：e2e 只使用临时数据库，绝不影响真实学习进度
    env = dict(os.environ, DS_NO_BROWSER="1", DS_E2E_TMPDB="1")
    tmp_db = os.path.join(tempfile.gettempdir(), "dsh_e2e_learning.db")
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    proc = subprocess.Popen([sys.executable, "app.py"], cwd=BASE, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port = find_server(proc)
    except Exception as e:
        proc.kill()
        print("❌ 启动失败: %s" % e)
        sys.exit(1)
    print("✅ 服务器已启动，端口 %d（临时数据库模式）" % port)

    base = "http://127.0.0.1:%d" % port
    try:
        # 1. bootstrap
        boot = http("GET", base + "/api/bootstrap")
        snap = boot["snapshot"]
        check("bootstrap 返回阶段数=12", len(snap["stages"]) == 12, len(snap["stages"]))
        check("bootstrap 返回总任务数>700", snap["total_tasks"] > 700, snap["total_tasks"])
        check("计划总天数≈180", 150 <= snap["plan"]["total_days"] <= 200, snap["plan"]["total_days"])

        # 2. 阶段内容
        stage = http("GET", base + "/api/stage/s02_sql")
        check("阶段 s02_sql 可访问", stage["stage_id"] == "s02_sql")
        ch = stage["chapters"][0]
        sql_tasks = [t for c in stage["chapters"] for t in c.get("tasks", []) if t["type"] == "sql"]
        check("s02 有 SQL 任务", len(sql_tasks) > 0, len(sql_tasks))

        # 3. 提交一个正确答案（SQL）
        t = sql_tasks[0]
        res = http("POST", base + "/api/submit", {"task_id": t["task_id"], "answer": t["expected_sql"]})
        check("SQL 正确答案判定通过", res["correct"], res.get("feedback", [{}])[0].get("title"))
        check("SQL 正确获得 XP", res["xp"] > 0, res["xp"])

        # 4. 提交一个错误答案（SQL 语法错误）
        res = http("POST", base + "/api/submit", {"task_id": t["task_id"], "answer": "SELEC * FROM x"})
        check("SQL 错误答案不通过且已通过状态保留", not res["correct"] and res["already"])

        # 5. Python 任务（s01 找一个）
        s01 = http("GET", base + "/api/stage/s01_python")
        py_tasks = [t for c in s01["chapters"] for t in c.get("tasks", []) if t["type"] == "python"]
        pt = py_tasks[0]
        res = http("POST", base + "/api/submit", {"task_id": pt["task_id"], "answer": pt["reference"]})
        check("Python 参考答案通过", res["correct"], res.get("feedback", [{}])[0].get("title"))

        # 6. 打卡（今日可能已打过卡，接口应正常返回）
        res = http("POST", base + "/api/checkin", {})
        check("打卡接口正常（首次+10XP 或今日已打卡）",
              res["streak"] >= 1 and (res["new"] and res["xp"] == 10 or not res["new"] and res["xp"] == 0), res)

        # 7. 动手实践（选一个未完成的章节；若全部完成则接受 xp=0）
        snap = http("GET", base + "/api/bootstrap")["snapshot"]
        hand_ch = None
        for st in snap["stages"]:
            for c in st["chapters"]:
                if c.get("has_hands_on") and not c.get("hands_done"):
                    hand_ch = c["chapter_id"]
                    break
            if hand_ch:
                break
        hand_ch = hand_ch or "s01c01"
        res = http("POST", base + "/api/hands_on", {"chapter_id": hand_ch})
        check("动手实践接口正常（首次+40XP 或已完成）",
              res["done"] and res["xp"] in (0, 40), res["xp"])

        # 8. 进度持久化（重新 bootstrap 可见）
        snap2 = http("GET", base + "/api/bootstrap")["snapshot"]
        check("进度持久化（XP>0 且任务已记录）", snap2["xp"] > 0 and snap2["solved_total"] >= 2, snap2["xp"])

        # 9. 重置
        res = http("POST", base + "/api/reset", {"confirm": "RESET"})
        check("重置成功", res.get("ok") is True)
        snap3 = http("GET", base + "/api/bootstrap")["snapshot"]
        check("重置后进度清零", snap3["xp"] == 0 and snap3["solved_total"] == 0, snap3["xp"])
    finally:
        proc.kill()

    print()
    if FAILS:
        print("❌ 端到端测试 %d 项未通过" % len(FAILS))
        sys.exit(1)
    print("✅ 端到端测试全部通过")


if __name__ == "__main__":
    main()
