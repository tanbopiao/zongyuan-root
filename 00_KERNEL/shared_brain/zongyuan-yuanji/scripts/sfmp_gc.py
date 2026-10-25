#!/usr/bin/env python3
"""SFMP垃圾回收：回收低置信度和长期pending的z单元"""
import json, glob, time, os

sfmp_dir = "/root/zongyuan-yuanji/var/sfmp"
files = glob.glob(sfmp_dir + "/z-*.json")
recycled = 0
admitted = 0
pending = 0

for f in files:
    try:
        d = json.load(open(f))
        conf = d.get("confidence_U", 0.5)
        status = d.get("status", "pending")
        age = time.time() - d.get("proposed_at", time.time())
        
        # 规则1：置信度<0.5 回收
        if conf < 0.5:
            d["status"] = "recycled_low_confidence"
            json.dump(d, open(f,"w"), ensure_ascii=False)
            recycled += 1
            continue
        
        # 规则2：pending超过7天 自动回收
        if "pending" in status and age > 7*86400:
            d["status"] = "recycled_stale"
            json.dump(d, open(f,"w"), ensure_ascii=False)
            recycled += 1
            continue
        
        if status == "admitted": admitted += 1
        elif "pending" in status: pending += 1
    except: pass

print(f"SFMP GC: 总{len(files)} | admitted={admitted} | pending={pending} | recycled={recycled}")
