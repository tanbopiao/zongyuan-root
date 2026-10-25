#!/usr/bin/env python3
import json, glob, os, time
# 自动发现高价值任务，自动入队
templates = [
    {"name":"环境扫描","cmd":"df -h && free -m"},
    {"name":"系统巡检","cmd":"uptime && whoami"},
    {"name":"数据生成","cmd":"cd /mnt/workspace/OMEGA-BRAIN && python3 auto_gen_data.py"},
    {"name":"日志分析","cmd":"tail -20 /mnt/workspace/OMEGA-BRAIN/train.log 2>/dev/null || echo no log"},
]
for t in templates:
    tid = f"auto-{int(time.time())}"
    t["id"] = tid
    t["status"] = "pending"
    json.dump(t, open(f"/root/zongyuan-yuanji/var/tasks/{tid}.json","w"), ensure_ascii=False, indent=2)
    print("入队:", tid, t["name"])
