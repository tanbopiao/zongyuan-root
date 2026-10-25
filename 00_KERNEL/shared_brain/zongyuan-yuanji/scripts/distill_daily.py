#!/usr/bin/env python3
import json, os, glob
# 读轨迹，提炼高频模式
traj = glob.glob("/root/zongyuan-yuanji/var/trajectories/*.json")
print(f"轨迹数: {len(traj)}")
# 写法则
laws = []
for f in traj[:10]:
    d = json.load(open(f))
    laws.append({"id": os.path.basename(f), "pattern": d.get("summary","")[:100]})
json.dump(laws, open("/root/zongyuan-yuanji/var/laws/daily_laws.json","w"), ensure_ascii=False, indent=2)
print("done")
