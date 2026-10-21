#!/usr/bin/env python3
import json, glob, os
# 真实多节点投票：高危任务需要2个节点确认
nodes = glob.glob("/root/zongyuan-yuanji/var/nodes/*.json")
print("在线节点:", len(nodes))
tasks = glob.glob("/root/zongyuan-yuanji/var/tasks/*.json")
for f in tasks:
    d = json.load(open(f))
    if d.get("consensus_required") and d.get("status") == "pending":
        votes = d.get("votes",[])
        if len(votes) >= 2:
            d["consensus_passed"] = True
            json.dump(d, open(f,"w"), ensure_ascii=False, indent=2)
            print(d["id"], "共识通过")
        else:
            print(d["id"], "需要", 2-len(votes), "票")
