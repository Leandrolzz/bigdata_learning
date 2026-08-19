# -*- coding: utf-8 -*-
"""学习内容加载器：读取 content/*.json 并建立索引（纯标准库）"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, "content")

META = None
STAGES = []
TASKS = []
TASK_BY_ID = {}


def load():
    global META, STAGES, TASKS, TASK_BY_ID
    with open(os.path.join(CONTENT_DIR, "meta.json"), encoding="utf-8") as f:
        META = json.load(f)
    STAGES = []
    TASKS = []
    TASK_BY_ID = {}
    for sid in META["stages"]:
        with open(os.path.join(CONTENT_DIR, sid + ".json"), encoding="utf-8") as f:
            stage = json.load(f)
        STAGES.append(stage)
        for ch in stage.get("chapters", []):
            for t in ch.get("tasks", []):
                t["stage_id"] = stage["stage_id"]
                t["chapter_id"] = ch["chapter_id"]
                TASKS.append(t)
                TASK_BY_ID[t["task_id"]] = t
    return META, STAGES, TASKS


load()
