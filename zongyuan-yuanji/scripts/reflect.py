#!/usr/bin/env python3
import json, glob
# 自我反思：做完事自动复盘
tasks = glob.glob("/root/zongyuan-yuanji/var/tasks/*.json")
for f in tasks:
    d = json.load(open(f))
    if d.get("status") == "done" and "reflect" not in d:
        score = d.get("score",5)
        if score >= 8:
            d["reflect"] = "做得好，继续保持"
        elif score >= 6:
            d["reflect"] = "一般，下次优化"
        else:
            d["reflect"] = "差，需要改进"
        json.dump(d, open(f,"w"), ensure_ascii=False, indent=2)
        print(d["id"], d["reflect"])
