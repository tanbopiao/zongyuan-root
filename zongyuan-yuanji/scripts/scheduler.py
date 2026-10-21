#!/usr/bin/env python3
import json, glob
tasks = [json.load(open(f)) for f in glob.glob("/root/zongyuan-yuanji/var/tasks/*.json") if "pending" in open(f).read()]
nodes = [json.load(open(f)) for f in glob.glob("/root/zongyuan-yuanji/var/nodes/*.json")]
print("待执行任务:", len(tasks), "在线节点:", len(nodes))
for t in tasks:
    if "gpu" in t["name"].lower():
        assignee = "GPU节点"
    else:
        assignee = "CPU节点"
    tid = t["id"]
    print(" ", tid, "->", assignee)
