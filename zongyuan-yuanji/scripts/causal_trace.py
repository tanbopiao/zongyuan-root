#!/usr/bin/env python3
import json, glob
# 因果追溯：每个决策为什么做
tasks = glob.glob("/root/zongyuan-yuanji/var/tasks/*.json")
for f in tasks:
    d = json.load(open(f))
    if "why" not in d:
        d["why"] = "自动调度：需要执行此任务"
        d["trace"] = {"cause":"auto_discover","effect":"task created"}
        json.dump(d, open(f,"w"), ensure_ascii=False, indent=2)
        print(d["id"], "因果已记录")
