#!/usr/bin/env python3
import json, glob
tasks = glob.glob("/root/zongyuan-yuanji/var/tasks/*.json")
for f in tasks:
    d = json.load(open(f))
    if d.get("status") == "done" and "score" not in d:
        score = 8 if d.get("result") else 5
        d["score"] = score
        json.dump(d, open(f,"w"), ensure_ascii=False, indent=2)
        print(d["id"], "score:", score)
