#!/usr/bin/env python3
# 实时自治状态
import subprocess, json, time
r = subprocess.run(["free","-m"],capture_output=True,text=True).stdout
mem = int(r.split("\n")[1].split()[2])
r2 = subprocess.run(["df","-h","/"],capture_output=True,text=True).stdout
disk = r2.split("\n")[1].split()[4]
r3 = subprocess.run(["uptime"],capture_output=True,text=True).stdout
load = r3.split("load average:")[1].strip()
print(json.dumps({"mem":mem,"disk":disk,"load":load,"ts":int(time.time())}))
