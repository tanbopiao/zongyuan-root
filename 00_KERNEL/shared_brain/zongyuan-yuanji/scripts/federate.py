#!/usr/bin/env python3
import subprocess, json
r = subprocess.run(["curl","-s","https://www.huodouai.com/api/status"],capture_output=True,text=True)
try:
    d = json.loads(r.stdout)
    tc = d.get("truth_count","?")
    print("主节点truth_count=" + str(tc))
except:
    print("获取失败")
