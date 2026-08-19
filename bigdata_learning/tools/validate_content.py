# -*- coding: utf-8 -*-
"""内容校验脚本
用法：python tools/validate_content.py
检查所有 content/*.json 是否符合 _SCHEMA.md 规范，并预执行 SQL 期望语句、Python 参考答案。
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE, "content")

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def check_sql(task):
    setup = task.get("setup", "")
    q = task.get("expected_sql", "")
    if not q:
        err("%s: sql 任务缺少 expected_sql" % task["task_id"])
        return None
    try:
        conn = sqlite3.connect(":memory:")
        if setup:
            conn.executescript(setup)
        cur = conn.execute(q)
        rows = cur.fetchall()
        conn.close()
        return len(rows)
    except Exception as e:
        err("%s: expected_sql 执行失败 -> %s" % (task["task_id"], e))
        return None


def check_python(task):
    ref = task.get("reference")
    if not ref:
        err("%s: python 任务缺少 reference（标准答案代码）" % task["task_id"])
        return
    if "input(" in ref:
        err("%s: reference 中不能使用 input()" % task["task_id"])
        return
    reqs = task.get("requires") or []
    missing = []
    for mod in reqs:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        warn("%s: 需要第三方库 %s（本机未安装），跳过 reference 运行验证"
             % (task["task_id"], "、".join(missing)))
        return
    try:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, "-c", ref], capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace", cwd=tempfile.gettempdir(), env=env,
        )
    except subprocess.TimeoutExpired:
        err("%s: reference 运行超时" % task["task_id"])
        return
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()
        err("%s: reference 运行报错 -> %s" % (task["task_id"], tail[-1] if tail else "?"))
        return
    out = "\n".join(l.strip() for l in proc.stdout.strip().splitlines())
    exp = task.get("expected_output")
    if exp is not None and str(exp).strip() != "":
        exp_n = "\n".join(l.strip() for l in str(exp).strip().splitlines())
        if out != exp_n:
            err(
                "%s: reference 输出与 expected_output 不一致\n    参考输出: %r\n    期望输出: %r"
                % (task["task_id"], out[:150], exp_n[:150])
            )


def main():
    meta = json.load(open(os.path.join(CONTENT_DIR, "meta.json"), encoding="utf-8"))
    seen_chapters = set()
    seen_tasks = set()
    total_tasks = 0
    by_type = {}
    plan_days = 0
    est_days = 0
    for sid in meta["stages"]:
        path = os.path.join(CONTENT_DIR, sid + ".json")
        if not os.path.exists(path):
            err("缺少内容文件: %s" % path)
            continue
        stage = json.load(open(path, encoding="utf-8"))
        if stage.get("stage_id") != sid:
            err("%s: stage_id 必须与文件名一致（%s）" % (sid, stage.get("stage_id")))
        est_days += int(stage.get("estimated_days", 1))
        chapters = stage.get("chapters", [])
        if not chapters:
            err("%s: 没有章节" % sid)
        for ch in chapters:
            cid = ch.get("chapter_id", "")
            if not cid:
                err("%s: 章节缺少 chapter_id" % sid)
            elif cid in seen_chapters:
                err("chapter_id 重复: %s" % cid)
            seen_chapters.add(cid)
            for f in ("title", "theory"):
                if f not in ch:
                    err("%s: 缺少字段 %s" % (cid or "?", f))
            theory = ch.get("theory", [])
            if sum(1 for b in theory if b.get("type") == "text") < 2:
                warn("%s: 文字块少于 2 个" % cid)
            if not any(b.get("type") == "code" for b in theory):
                warn("%s: 理论缺少 code 块" % cid)
            if not any(b.get("type") == "enterprise" for b in theory):
                warn("%s: 理论缺少 enterprise 企业视角块" % cid)
            if not ch.get("hands_on"):
                warn("%s: 缺少 hands_on 动手实践" % cid)
            if not ch.get("goal"):
                warn("%s: 缺少 goal 学习目标" % cid)
            if not ch.get("kps"):
                warn("%s: 缺少 kps 知识点清单（v1.2 要求）" % cid)
            plan_days += max(1, int(ch.get("plan_days", 1)))
            br = ch.get("plan_breakdown", {})
            total_min = sum(int(br.get(k, 0)) for k in ("theory_min", "tasks_min", "hands_on_min", "review_min"))
            if not br:
                warn("%s: 无 plan_breakdown（将使用默认 40/50/20/10）" % cid)
            elif total_min < 90 or total_min > 150:
                warn("%s: plan_breakdown 合计 %d 分钟，建议约 120" % (cid, total_min))
            tasks = ch.get("tasks", [])
            if not tasks:
                err("%s: 没有任务" % cid)
            if len(tasks) > 4:
                warn("%s: 任务数 %d（建议 2~3 个）" % (cid, len(tasks)))
            for t in tasks:
                tid = t.get("task_id", "")
                if not tid:
                    err("%s: 任务缺少 task_id" % cid)
                elif tid in seen_tasks:
                    err("task_id 重复: %s" % tid)
                seen_tasks.add(tid)
                total_tasks += 1
                typ = t.get("type", "?")
                by_type[typ] = by_type.get(typ, 0) + 1
                for f in ("title", "question", "analysis"):
                    if f not in t:
                        err("%s: 缺少字段 %s" % (tid, f))
                d = t.get("difficulty", 1)
                if not isinstance(d, int) or not 1 <= d <= 5:
                    err("%s: difficulty 必须为 1~5 整数" % tid)
                if typ == "choice":
                    opts = t.get("options", [])
                    correct = [o for o in opts if o.get("correct")]
                    if len(correct) != 1:
                        err("%s: choice 必须有且仅有一个正确选项" % tid)
                    for o in opts:
                        if not o.get("explain"):
                            warn("%s: 选项缺少 explain" % tid)
                elif typ == "multi":
                    opts = t.get("options", [])
                    correct = [o for o in opts if o.get("correct")]
                    if len(correct) < 2:
                        err("%s: multi 至少 2 个正确选项" % tid)
                    if not opts:
                        err("%s: multi 缺少 options" % tid)
                elif typ == "fill":
                    if not t.get("answer"):
                        err("%s: fill 缺少 answer 数组" % tid)
                    if not t.get("hint"):
                        warn("%s: fill 缺少 hint" % tid)
                elif typ == "order":
                    steps = t.get("steps", [])
                    co = t.get("correct_order", [])
                    if sorted(co) != list(range(len(steps))):
                        err("%s: correct_order 必须是 steps 索引的排列" % tid)
                    if not steps:
                        err("%s: order 缺少 steps" % tid)
                    if not t.get("order_explain"):
                        warn("%s: order 缺少 order_explain" % tid)
                elif typ == "sql":
                    check_sql(t)
                    if not t.get("setup"):
                        warn("%s: sql 缺少 setup（测试表数据）" % tid)
                elif typ == "python":
                    if not t.get("code_context"):
                        warn("%s: python 缺少 code_context" % tid)
                    check_python(t)
                else:
                    err("%s: 未知任务类型 %s" % (tid, typ))

    print("阶段数: %d  章节数: %d  总任务数: %d" % (len(meta["stages"]), len(seen_chapters), total_tasks))
    print("任务类型分布: %s" % json.dumps(by_type, ensure_ascii=False))
    print("按 plan_days 计划总天数: %d   阶段声明天数合计: %d" % (plan_days, est_days))
    if errors:
        print("\n❌ 发现 %d 个错误:" % len(errors))
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("\n✅ 校验通过（%d 条警告）" % len(warnings))
    for w in warnings[:25]:
        print("  ⚠", w)
    if len(warnings) > 25:
        print("  ... 还有 %d 条警告" % (len(warnings) - 25))


if __name__ == "__main__":
    main()
