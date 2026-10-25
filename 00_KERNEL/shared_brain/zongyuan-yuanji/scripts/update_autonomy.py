#!/usr/bin/env python3
import subprocess, json
r = subprocess.run(["free","-m"],capture_output=True,text=True).stdout
mem = int(r.split("\n")[1].split()[2])
r2 = subprocess.run(["df","-h","/"],capture_output=True,text=True).stdout
disk = r2.split("\n")[1].split()[4]
r3 = subprocess.run(["uptime"],capture_output=True,text=True).stdout
load = r3.split("load average:")[1].strip()
kernels = []
for p in [18080,18082,18083,18084,18085,18086,18087,18088,18089,18090,18091,18092,18093,18094]:
    r = subprocess.run(["curl","-sk",f"https://127.0.0.1:{p}/health","--max-time","1"],capture_output=True,text=True)
    kernels.append({"port":p,"ok":"ok" in r.stdout})
with open("/www/wwwroot/huodouai.com/autonomy-data.json","w") as f:
    json.dump({"mem":mem,"disk":disk,"load":load,"kernels":kernels},f)
