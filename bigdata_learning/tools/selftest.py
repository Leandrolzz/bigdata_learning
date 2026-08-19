# -*- coding: utf-8 -*-
"""判题引擎自检脚本：python tools/selftest.py
不依赖课程内容文件，直接验证 checker 引擎的 6 种题型判题逻辑。
"""
import sys
import os
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import checker

FAILS = 0
def check(name, cond):
    global FAILS
    print(("✅ " if cond else "❌ ") + name)
    if not cond:
        FAILS += 1

# ---------- SQL ----------
sql_task = {
    "type": "sql",
    "setup": "CREATE TABLE users(id INTEGER, name TEXT, age INTEGER, gender TEXT);\n"
             "INSERT INTO users VALUES (1,'a',25,'M'),(2,'b',30,'F'),(3,'c',22,'M');",
    "expected_sql": "SELECT name, age FROM users WHERE gender='M' ORDER BY age DESC;",
    "analysis": "x",
}
r = checker.grade(sql_task, "SELECT name, age FROM users WHERE gender='M' ORDER BY age DESC;")
check("SQL 正确答案通过", r["correct"])
r = checker.grade(sql_task, "SELECT name, age FROM users WHERE gender='F';")
check("SQL 错误答案不通过", not r["correct"])
check("SQL 错误反馈含差异提示", any("缺" in f["text"] or "多出" in f["text"] or "行数不一致" in f["title"] for f in r["feedback"]))
check("SQL 错误反馈不含标准行值（答对才给答案）", not any(("'a'" in f["text"] or "'c'" in f["text"]) for f in r["feedback"]))
r = checker.grade(sql_task, "DELETE FROM users")
check("SQL 非 SELECT 被拦截", not r["correct"])
r = checker.grade(sql_task, "SELECT name FROM users")
check("SQL 列不匹配不通过", not r["correct"])

# 窗口函数（SQLite 支持）
win_task = {
    "type": "sql",
    "setup": "CREATE TABLE t(a TEXT, v INTEGER);\nINSERT INTO t VALUES ('x',1),('x',2),('y',5);",
    "expected_sql": "SELECT a, v, ROW_NUMBER() OVER (PARTITION BY a ORDER BY v DESC) AS rn FROM t ORDER BY a, rn;",
    "analysis": "x",
}
r = checker.grade(win_task, "SELECT a, v, ROW_NUMBER() OVER (PARTITION BY a ORDER BY v DESC) AS rn FROM t ORDER BY a, rn;")
check("SQL 窗口函数正确通过", r["correct"])

# ---------- Python ----------
py_task = {
    "type": "python",
    "expected_output": "Hello Big Data\nI will be a data engineer",
    "analysis": "x",
}
r = checker.grade(py_task, "print('Hello Big Data')\nprint('I will be a data engineer')")
check("Python 输出一致通过", r["correct"])
r = checker.grade(py_task, "print('Hello Big Data')")
check("Python 输出不一致不通过", not r["correct"])
check("Python 错误反馈含你的输出", any("你的输出" in f["title"] for f in r["feedback"]))
check("Python 错误反馈不含期望输出（答对才给答案）",
      not any("期望输出" in f["title"] or "期望输出" in f["text"] for f in r["feedback"]))
r = checker.grade(py_task, "print(1/0)")
check("Python 运行报错被捕获", not r["correct"] and ("报错" in r["feedback"][0]["title"] or "报错" in r["feedback"][0]["text"]))
r = checker.grade(py_task, "while True: pass")
check("Python 死循环超时被捕获", not r["correct"])

# ---------- 其他 ----------
check("fill 大小写/空格归一", checker.grade({"type": "fill", "answer": ["2", "2小时"], "analysis": ""}, "  2  ")["correct"])
check("fill 可接受答案数组", checker.grade({"type": "fill", "answer": ["DISTINCT", "distinct"], "analysis": ""}, "Distinct")["correct"])
check("multi 全选对", checker.grade({"type": "multi", "options": [{"correct": True}, {"correct": True}, {"correct": False}]}, ["0", "1"])["correct"])
check("multi 漏选不通过", not checker.grade({"type": "multi", "options": [{"correct": True}, {"correct": True}, {"correct": False}]}, ["0"])["correct"])
check("choice 正确", checker.grade({"type": "choice", "options": [{"correct": False}, {"correct": True}]}, "1")["correct"])
check("choice 错误", not checker.grade({"type": "choice", "options": [{"correct": False}, {"correct": True}]}, "0")["correct"])
check("order 正确", checker.grade({"type": "order", "steps": ["a", "b", "c"], "correct_order": [2, 0, 1]}, [2, 0, 1])["correct"])
check("order 错误", not checker.grade({"type": "order", "steps": ["a", "b", "c"], "correct_order": [2, 0, 1]}, [0, 1, 2])["correct"])

# ---------- 答错不泄题（答案只在答对/主动查看后展示） ----------
r = checker.grade({"type": "choice", "options": [{"correct": False, "explain": "错因A"}, {"correct": True, "explain": "正解B"}]}, "0")
check("choice 错误反馈不含正确选项", not any(f["title"].startswith("正确选项") for f in r["feedback"]))
r = checker.grade({"type": "multi", "options": [{"correct": True, "explain": "a"}, {"correct": True, "explain": "b"}, {"correct": False, "explain": "c"}]}, ["0"])
check("multi 漏选不展示正确项", not any("正确选项" in f["title"] for f in r["feedback"]))
r = checker.grade({"type": "fill", "answer": ["DISTINCT", "distinct"], "hint": "提示", "analysis": ""}, "abc")
check("fill 错误反馈不含可接受答案", not any("DISTINCT" in f["text"] for f in r["feedback"]))
r = checker.grade({"type": "order", "steps": ["a", "b", "c"], "correct_order": [2, 0, 1], "order_explain": "原因"}, [0, 1, 2])
check("order 错误反馈不含标准顺序", not any("标准顺序" in f["title"] or f["title"] == "原因" for f in r["feedback"]))

# ---------- requires 依赖检查 ----------
req_task = {"type": "python", "requires": ["pandas"], "expected_output": "3", "analysis": "x"}
r = checker.grade(req_task, "import pandas as pd\nprint(pd.Series([1, 2, 3]).size)")
check("requires 依赖已装时正常判题", r["correct"])
r = checker.grade({"type": "python", "requires": ["not_exist_mod_xyz"], "expected_output": "1", "analysis": "x"}, "print(1)")
check("requires 依赖缺失时给出安装提示", not r["correct"] and "pip install" in r["feedback"][0]["text"])

# ---------- 6 选项题目回归（曾因 "ABCD"[5] 崩溃/显示 undefined） ----------
opts6 = [{"correct": i == 4, "explain": "解释%d" % i} for i in range(6)]
r = checker.grade({"type": "choice", "options": opts6}, "4")
check("6 选项单选正确通过", r["correct"])
r = checker.grade({"type": "choice", "options": opts6}, "0")
check("6 选项单选错误不泄题", not r["correct"] and not any("正确选项" in f["title"] for f in r["feedback"]))
opts6m = [{"correct": i in (0, 5), "explain": "解释%d" % i} for i in range(6)]
r = checker.grade({"type": "multi", "options": opts6m}, ["0", "5"])
check("6 选项多选正确通过", r["correct"])
r = checker.grade({"type": "multi", "options": opts6m}, ["0"])
check("6 选项多选漏选不泄题", not r["correct"] and not any("正确选项" in f["title"] for f in r["feedback"]))

print()
if FAILS:
    print("❌ %d 项未通过" % FAILS)
    sys.exit(1)
print("✅ 判题引擎全部自检通过")
