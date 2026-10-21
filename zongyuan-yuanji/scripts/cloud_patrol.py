#!/usr/bin/env python3
"""云端自动巡检：健康检查+内存+模型可用性"""
import json, time, subprocess, requests, urllib3
urllib3.disable_warnings()
from pathlib import Path

LOG = Path("/home/user/ZONGYUAN-ROOT/var/patrol-log.jsonl")
LOG.parent.mkdir(parents=True, exist_ok=True)

def patrol():
    ts = int(time.time())
    # wrapper健康
    try:
        r = requests.get("https://127.0.0.1:18080/health", verify=False, timeout=5)
        wrapper_ok = r.json().get("ok", False)
    except:
        wrapper_ok = False
    
    # 内存
    r = subprocess.run(["free","-m"], capture_output=True, text=True)
    mem_avail = int(r.stdout.split("\n")[1].split()[6])
    
    # 模型测试
    try:
        r = requests.post("https://127.0.0.1:18080/v1/chat/completions",
            headers={"Authorization":"Bearer ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70","Content-Type":"application/json"},
            json={"model":"router","messages":[{"role":"user","content":"hi"}],"max_tokens":5},
            verify=False, timeout=15)
        model_ok = "choices" in r.json()
    except:
        model_ok = False
    
    status = "HEALTHY" if (wrapper_ok and mem_avail > 500) else "WARNING"
    if not wrapper_ok: status = "CRITICAL"
    
    entry = {"ts":ts,"time":time.strftime("%Y-%m-%d %H:%M:%S"),
             "wrapper":wrapper_ok,"mem_avail_mb":mem_avail,"model":model_ok,"status":status}
    with open(LOG,"a") as f:
        f.write(json.dumps(entry,ensure_ascii=False)+"\n")
    print(f"[{entry['time']}] wrapper={wrapper_ok} mem={mem_avail}M model={model_ok} → {status}")
    return entry

if __name__ == "__main__":
    patrol()
