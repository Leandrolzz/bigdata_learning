# -*- coding: utf-8 -*-
"""内容补丁工具：向已有阶段 JSON 追加 任务 / 速记卡(QA/术语) / 新章节 / 阶段字段
用法：python tools/content_tools.py apply <补丁JSON路径...>
补丁格式：
{
  "file": "s01_python",                          # 阶段文件名（可带 .json）
  "stage_fields": {"estimated_days": 18},        # 可选：更新阶段字段
  "patches": [                                   # 可选：按章节追加
    {
      "chapter_id": "s01c01",
      "add_tasks": [ {任务对象(与 _SCHEMA.md 任务规范一致)} ],
      "hints": { "s01c01t03": "重写后的引导性提示（不给答案）" },
      "qa": [ {"q": "问题", "a": "标准答案"} ],
      "glossary": [ {"term": "术语", "desc": "解释"} ]
    }
  ],
  "new_chapters": [ {完整章节对象} ]             # 可选：追加新章节
}
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE, "content")


def apply_patch(path):
    patch = json.load(open(path, encoding="utf-8"))
    fname = patch["file"] if patch["file"].endswith(".json") else patch["file"] + ".json"
    fpath = os.path.join(CONTENT_DIR, fname)
    stage = json.load(open(fpath, encoding="utf-8"))
    for p in patch.get("patches", []):
        cid = p.get("chapter_id")
        if cid:
            ch = next((c for c in stage["chapters"] if c["chapter_id"] == cid), None)
            if not ch:
                raise SystemExit("❌ 章节不存在: %s（文件 %s）" % (cid, fname))
            tasks = p.get("add_tasks")
            if tasks:
                ch.setdefault("tasks", []).extend(tasks)
            kps = p.get("kps")
            if kps:
                ch["kps"] = kps
            hints = p.get("hints")
            if hints:
                for tid, newh in hints.items():
                    t = next((x for x in ch.get("tasks", []) if x["task_id"] == tid), None)
                    if t is None:
                        raise SystemExit("❌ 任务不存在: %s（文件 %s）" % (tid, fname))
                    t["hint"] = newh
            qa = p.get("qa")
            if qa:
                ch.setdefault("qa", []).extend(qa)
            gl = p.get("glossary")
            if gl:
                ch.setdefault("glossary", []).extend(gl)
    for newch in patch.get("new_chapters", []):
        stage["chapters"].append(newch)
    for k, v in (patch.get("stage_fields") or {}).items():
        stage[k] = v
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(stage, f, ensure_ascii=False, indent=2)
    # 二次读回校验
    json.load(open(fpath, encoding="utf-8"))
    print("✅ 已应用补丁 -> %s（章节 %s）" % (fname, "、".join(p.get("chapter_id", "?") for p in patch.get("patches", [])) or "新章节"))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "apply":
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[2:]:
        apply_patch(p)
    print("全部补丁应用完成")
