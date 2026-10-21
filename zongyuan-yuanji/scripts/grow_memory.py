#!/usr/bin/env python3
import json, glob, os
tasks = glob.glob("/root/zongyuan-yuanji/var/tasks/*.json")
mem_dir = "/root/zongyuan-yuanji/var/trajectories/"
for f in tasks:
    d = json.load(open(f))
    if d.get("status") == "done":
        mid = "mem-" + d["id"]
        mf = os.path.join(mem_dir, mid + ".json")
        if not os.path.exists(mf):
            mem = {
                "id": mid,
                "summary": d["name"] + "已完成，评分" + str(d.get("score",8)),
                "lesson": d.get("reflect",""),
            }
            json.dump(mem, open(mf,"w"), ensure_ascii=False, indent=2)
            print("新增记忆:", mid)
