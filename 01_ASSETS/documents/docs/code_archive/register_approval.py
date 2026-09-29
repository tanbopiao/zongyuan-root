#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
register_approval.py — 审批登记总线: 本地发起审批后,把 instance_code 写入云端记忆网关
通过 ssh 在云端执行登记(记忆网关仅在云端127.0.0.1:9120)。
云端 command_router 轮询时自动认领并执行(高危指令闭环)

用法: python3 register_approval.py <instance_code> <func_name> <action_label> <command_text>
"""
import json, subprocess, sys

CLOUD_HOST = "123.207.202.158"
CLOUD_KEY = "~/.ssh/id_ed25519"
REGISTER_KEY = "ops.approval.register"

# 在云端执行的登记脚本(记忆网关在云端本地)
CLOUD_SCRIPT = r'''
import json, urllib.request, time, sys
MEMORY_GW = "http://127.0.0.1:9120"
REGISTER_KEY = "ops.approval.register"

def read_existing():
    try:
        req = urllib.request.Request(f"{MEMORY_GW}/api/truth/{REGISTER_KEY}")
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.load(r)
        if d.get("status") == "ok":
            v = d.get("truth", {}).get("truth_value", "[]")
            return json.loads(v) if isinstance(v, str) else v
    except Exception:
        pass
    return []

code, func, label, text = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
entries = read_existing()
entries = [e for e in entries if e.get("instance_code") != code]
entries.append({
    "instance_code": code,
    "func_name": func,
    "action_label": label,
    "command_text": text,
    "created_ts": time.time(),
    "source_msg_id": "local-auto-register"
})
payload = json.dumps({"key": REGISTER_KEY, "value": json.dumps(entries, ensure_ascii=False), "category": "ops"}).encode()
req = urllib.request.Request(f"{MEMORY_GW}/api/truth/upsert", data=payload,
                             headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=10) as r:
    resp = json.load(r)
if resp.get("status") == "ok":
    print(f"REGISTERED {code} {label}")
else:
    print(f"FAIL {resp}")
'''

def main():
    if len(sys.argv) < 5:
        print("用法: python3 register_approval.py <instance_code> <func_name> <action_label> <command_text>")
        sys.exit(1)
    ic, func, label, text = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    ssh_cmd = [
        "ssh", "-i", CLOUD_KEY, "-o", "BatchMode=yes", "-o", "ConnectTimeout=12",
        f"root@{CLOUD_HOST}", "python3", "-c", CLOUD_SCRIPT, ic, func, label, text
    ]
    try:
        r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=40)
        out = r.stdout.strip()
        if "REGISTERED" in out:
            print(f"✅ 已登记审批到云端认领总线: {ic} ({label})")
            return 0
        print(f"❌ 登记失败:\n{out}\n{r.stderr.strip()[:300]}")
        return 1
    except Exception as e:
        print(f"❌ ssh登记异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
