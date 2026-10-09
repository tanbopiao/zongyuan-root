#!/usr/bin/env python3
import requests, subprocess, json, time, os
TOPIC="zongyuan-kunlun-2026"
SUB=f"https://ntfy.sh/{TOPIC}/json"
RESULT=f"https://ntfy.sh/{TOPIC}-result"
def send(msg):
    try: requests.post(RESULT, data=msg.encode(), timeout=10)
    except: pass
send(json.dumps({"type":"init","msg":"GPU实例上线","gpu":subprocess.run("rocm-smi --showproductname | head -3",shell=True,capture_output=True,text=True).stdout.strip()}))
while True:
    try:
        r=requests.get(SUB, stream=True, timeout=60)
        for line in r.iter_lines():
            if not line: continue
            d=json.loads(line.decode())
            if d.get("event")=="message":
                cmd=d["message"]
                send(json.dumps({"type":"task_start","cmd":cmd[:100]}))
                res=subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1800)
                send(json.dumps({"type":"task_done","stdout":res.stdout[:2000],"returncode":res.returncode}))
    except: time.sleep(5)
