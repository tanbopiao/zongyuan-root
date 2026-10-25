#!/usr/bin/env python3
import json, glob, os
# 自动找bug：检查失败任务
tasks = glob.glob("/root/zongyuan-yuanji/var/tasks/*.json")
bugs = []
for f in tasks:
    d = json.load(open(f))
    if d.get("status") == "done":
        out = str(d.get("result",""))
        if "Error" in out or "error" in out or "not found" in out:
            bugs.append({"task": d["id"], "error": out[:100]})
print("发现bug:", len(bugs))
for b in bugs:
    print(" ", b["task"], b["error"])
