#!/usr/bin/env python3
"""自动提炼：从联邦记忆里提炼高频成功模式，追加进system_prompt"""
import json, glob
from collections import Counter

files = glob.glob("/root/zongyuan-yuanji/var/trajectories/fed-*.json")
if not files:
    print("no federated memories")
    exit(0)

tasks = []
scores = []
for f in files:
    try:
        d = json.load(open(f))
        tasks.append(d.get("task",""))
        scores.append(d.get("score",0))
    except: pass

# 高频任务
freq = Counter(tasks).most_common(5)
avg_score = sum(scores)/len(scores) if scores else 0

# 提炼
new_law = "\n【自动提炼模式】\n"
new_law += "高频成功任务: " + ", ".join(t for t,_ in freq if t) + "\n"
new_law += "平均得分: " + str(round(avg_score,1)) + "\n"

# 追加进system prompt
sp = open("/root/zongyuan-yuanji/src/system_prompt.txt").read()
if "自动提炼模式" not in sp:
    open("/root/zongyuan-yuanji/src/system_prompt.txt","a").write(new_law)
    print("added:", new_law)
else:
    print("already exists")

print("total memories:", len(files))
