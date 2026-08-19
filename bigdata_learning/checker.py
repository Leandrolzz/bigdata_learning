# -*- coding: utf-8 -*-
"""答案校验引擎：
- choice   单选（选项索引）
- multi    多选（选项索引数组）
- fill     填空（归一化字符串比对）
- order    排序（步骤索引数组）
- sql      SQL 语句（内存 SQLite 运行并比对结果集）
- python   Python 代码（子进程运行并比对 stdout）
纯标准库实现。
"""
import os
import re
import sqlite3
import subprocess
import sys
import tempfile


def norm_text(s):
    """答案归一化：小写、全角空格转半角、空白折叠"""
    s = str(s).strip().lower()
    s = s.replace("\u3000", " ")
    return re.sub(r"\s+", " ", s)


def norm_stdout(s):
    """stdout 归一化：逐行去首尾空白"""
    return "\n".join(line.strip() for line in s.strip().splitlines())


def _norm_cell(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def _rows_key(rows):
    return sorted(tuple(_norm_cell(c) for c in r) for r in rows)


def run_sql(setup_sql, query):
    """在内存 SQLite 中执行查询，返回 (ok, data)。data 为 (cols, rows) 或错误信息"""
    conn = sqlite3.connect(":memory:")
    try:
        if setup_sql:
            conn.executescript(setup_sql)
        if not query.strip().lower().startswith("select"):
            return False, "只能提交 SELECT 查询语句（闯关任务只考察查询）"
        cur = conn.execute(query)
        cols = [d[0] for d in (cur.description or [])]
        rows = [tuple(r) for r in cur.fetchall()]
        return True, (cols, rows)
    except Exception as e:
        return False, "SQL 执行出错：%s" % e
    finally:
        conn.close()


def run_python(code):
    """运行用户 Python 代码，返回 (ok, data)。data 为 (stdout, stderr) 或错误信息"""
    if not code.strip():
        return False, ("", "代码为空，请先编写代码再提交")
    try:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=15, cwd=tempfile.gettempdir(), env=env,
        )
    except subprocess.TimeoutExpired:
        return False, ("", "代码运行超时（15 秒）。可能是死循环，或代码中使用了 input() 等待输入")
    if proc.returncode != 0:
        err = proc.stderr.strip().splitlines()
        return False, ("", "\n".join(err[-4:]))
    return True, (proc.stdout, "")


def feedback(kind, title, text):
    return {"type": kind, "title": title, "text": text}


def letter(i):
    """选项字母标签：A、B、C……Z，超出 26 个用数字"""
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[i] if 0 <= i < 26 else str(i + 1)


def _check_requires(requires):
    """检查运行环境是否具备所需第三方库，返回 (ok, missing列表)"""
    missing = []
    for mod in requires or []:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    return (not missing), missing


def grade(task, answer):
    """校验答案，返回 {correct, feedback[], expected_display, analysis, reference, enterprise_tip}"""
    t = task["type"]
    res = {
        "correct": False,
        "feedback": [],
        "expected_display": None,
        "analysis": task.get("analysis", ""),
        "reference": task.get("reference", ""),
        "enterprise_tip": task.get("enterprise_tip", ""),
    }

    if t == "choice":
        opts = task["options"]
        right = [i for i, o in enumerate(opts) if o.get("correct")]
        idx = str(answer)
        res["correct"] = idx in [str(i) for i in right]
        if res["correct"]:
            res["feedback"].append(feedback("ok", "回答正确", "正确！结合下面的标准解题思路巩固理解。"))
        else:
            chosen = None
            if idx.isdigit() and int(idx) < len(opts):
                chosen = opts[int(idx)]
            res["feedback"].append(feedback(
                "error", "回答错误",
                "先不展示答案，再自己想想。答对后（或尝试 2 次后点「查看标准解题思路」）会给出完整解析。"))
            if chosen and chosen.get("explain"):
                res["feedback"].append(feedback("hint", "你选的选项", chosen["explain"]))
            res["feedback"].append(feedback(
                "hint", "思考方向",
                "逐个选项对照知识点排除：为什么它符合/不符合？把每个选项的理由写出来再选。"))

    elif t == "multi":
        opts = task["options"]
        right = {i for i, o in enumerate(opts) if o.get("correct")}
        try:
            user = {int(x) for x in (answer or [])}
        except (TypeError, ValueError):
            user = set()
        res["correct"] = user == right
        if res["correct"]:
            res["feedback"].append(feedback("ok", "回答正确", "全部选对！结合下面的标准解题思路巩固理解。"))
        else:
            missing = right - user
            extra = user - right
            if missing:
                res["feedback"].append(feedback(
                    "error", "有漏选",
                    "你还漏选了 %d 个正确选项（不展示具体是哪些，请再对照知识点想想）。" % len(missing)))
            if extra:
                res["feedback"].append(feedback("error", "有多选", "以下选项不应被选中："))
                for i in sorted(extra):
                    res["feedback"].append(feedback("hint", "你多选的选项 " + letter(i), opts[i].get("explain", "")))
            if not missing and not extra:
                res["feedback"].append(feedback("error", "未选择", "请先选择选项再提交。"))

    elif t == "fill":
        a = norm_text(answer)
        acc = [norm_text(x) for x in task.get("answer", [])]
        res["correct"] = a in acc
        if res["correct"]:
            res["feedback"].append(feedback("ok", "回答正确", "填空正确！结合下面的标准解题思路巩固理解。"))
        else:
            res["feedback"].append(feedback("error", "回答不正确", "提示：" + task.get("hint", "再读一遍知识点。")))

    elif t == "order":
        steps = task["steps"]
        co = task["correct_order"]
        try:
            user = [int(x) for x in (answer or [])]
        except (TypeError, ValueError):
            user = []
        res["correct"] = user == co
        if res["correct"]:
            res["feedback"].append(feedback("ok", "顺序正确", "完全正确！结合下面的标准解题思路理解为什么是这个顺序。"))
        else:
            res["feedback"].append(feedback(
                "error", "顺序不对",
                "你的顺序与标准流程不一致。标准顺序暂不展示，请再想想每步之间的依赖关系：哪一步必须先完成，后面才能进行？"))

    elif t == "sql":
        ok, exp = run_sql(task.get("setup", ""), task["expected_sql"])
        exp_cols, exp_rows = exp
        exp_key = _rows_key(exp_rows)
        res["expected_display"] = {
            "sql": task["expected_sql"],
            "cols": exp_cols,
            "rows": exp_rows[:8],
            "row_count": len(exp_rows),
        }
        ok2, user = run_sql(task.get("setup", ""), answer)
        if not ok2:
            res["feedback"].append(feedback("error", "SQL 执行失败", user))
            return res
        ucols, urows = user
        res["user_display"] = {"cols": ucols, "rows": urows[:15], "row_count": len(urows)}
        user_key = _rows_key(urows)
        if user_key == exp_key and len(urows) == len(exp_rows):
            res["correct"] = True
            res["feedback"].append(feedback("ok", "查询结果正确", "你的查询结果与标准结果完全一致（%d 行）。" % len(exp_rows)))
            if [c.lower() for c in ucols] != [c.lower() for c in exp_cols]:
                res["feedback"].append(feedback(
                    "hint", "小提醒",
                    "你的结果列名与标准答案不同（标准列：%s）。若使用了别名，建议与需求中的字段名保持一致。" % ", ".join(exp_cols)))
            return res
        if len(urows) != len(exp_rows):
            res["feedback"].append(feedback(
                "error", "行数不一致",
                "你的结果有 %d 行，期望 %d 行（标准结果暂不展示）。常见原因：WHERE/HAVING 条件写错、分组维度（GROUP BY）粒度不对、漏了 DISTINCT、连接条件导致数据翻倍。" % (len(urows), len(exp_rows))))
        n_missing = sum(1 for r in exp_rows if _rows_key([r])[0] not in user_key)
        n_extra = sum(1 for r in urows if _rows_key([r])[0] not in exp_key)
        if n_missing or n_extra:
            res["feedback"].append(feedback(
                "error", "结果内容有差异",
                "你的结果与期望结果不一致（期望有而你缺 %d 行、你多出 %d 行，标准行内容暂不展示）。请对照题目条件逐条检查：条件、分组、连接、取值。" % (n_missing, n_extra)))
        if not n_missing and not n_extra and len(urows) == len(exp_rows):
            res["feedback"].append(feedback("error", "行内容不匹配", "行数相同但内容不一致，请逐列检查取值是否正确。"))
        res["feedback"].append(feedback(
            "hint", "常见原因",
            "① JOIN ON 条件是否写对（关联键、过滤条件放 WHERE 还是 ON）；② 分组键粒度；③ NULL 值处理（= NULL 永远不成立，要用 IS NULL）；④ 条件边界（>= 还是 >）。"))

    elif t == "python":
        reqs = task.get("requires")
        if reqs:
            ok_req, missing = _check_requires(reqs)
            if not ok_req:
                res["feedback"].append(feedback(
                    "error", "缺少运行环境",
                    "本题需要 %s 模块。请在命令行执行：pip install %s 安装后重试。"
                    % ("、".join(missing), " ".join(missing))))
                return res
        ok, (out, err) = run_python(answer)
        if not ok:
            res["feedback"].append(feedback("error", "你的代码运行失败", "运行报错信息（最后几行）：\n" + err))
            return res
        expected = task.get("expected_output")
        if expected is None or str(expected).strip() == "":
            res["correct"] = True
            res["user_display"] = {"stdout": out}
            res["expected_display"] = {"stdout": out}
            res["feedback"].append(feedback("ok", "运行成功", "代码无报错运行通过。"))
            return res
        res["user_display"] = {"stdout": out}
        res["expected_display"] = {"stdout": str(expected)}
        if norm_stdout(out) == norm_stdout(str(expected)):
            res["correct"] = True
            res["feedback"].append(feedback("ok", "输出完全一致", "程序输出与期望输出一致，逻辑正确！"))
            return res
        o_lines = norm_stdout(out).splitlines()
        res["feedback"].append(feedback(
            "error", "输出与期望不一致",
            "标准答案暂不展示（答对后可见）。先对照题目要求检查你的输出，再按下面的思路排查："))
        res["feedback"].append(feedback("diff", "你的输出", "\n".join(o_lines[:10])))
        res["feedback"].append(feedback(
            "hint", "如何排查",
            "① 重新读题：到底要输出什么、几行、什么格式？② 检查边界情况（0、空列表、负数）；③ 检查是否多打印/少打印了内容（比如调试用的 print 没删）；④ 在代码里加 print() 打印中间变量来调试；⑤ 用「运行」按钮反复试，确认无误再提交。"))

    return res
