#!/usr/bin/env python3
import json, glob, os
# 跨节点共识：高危任务需要2个节点确认
tasks = glob.glob("/root/zongyuan-yuanji/var/tasks/*.json")
for f in tasks:
    d = json.load(open(f))
    if d.get("status") == "pending":
        d["consensus_required"] = True
        d["votes"] = []
        json.dump(d, open(f,"w"), ensure_ascii=False, indent=2)
        print(d["id"], "需要共识")
