#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fleet_review 联邦文件评审门 CLI ｜ W-07 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
用法:
  fleet_review.py list                        → 列出 PENDING_REVIEW 文件提案
  fleet_review.py approve <pid> <reviewer>    → 人工评审通过
  fleet_review.py reject <pid> <reviewer> <reason>  → 人工评审拒绝
"""
import subprocess, sys, json

CLOUD = "zongyuan-cloud"
REMOTE = "/opt/ZONGYUAN-ROOT/scripts/fleet_review_apply.py"

def run(action, *args):
    cmd = f"python3 {REMOTE} {action}"
    for a in args:
        cmd += " '" + str(a).replace("'", "'\\''") + "'"
    try:
        out = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
                              CLOUD, cmd], capture_output=True, text=True, timeout=40)
        if out.returncode != 0:
            print(json.dumps({"error": "cloud call failed", "stderr": out.stderr[:300]}, ensure_ascii=False))
            sys.exit(1)
        print(out.stdout.strip())
    except Exception as e:
        print(json.dumps({"error": str(e)[:200]}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        run("list")
    elif sys.argv[1] == "approve" and len(sys.argv) >= 4:
        run("approve", sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "reject" and len(sys.argv) >= 4:
        run("reject", sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "unspecified")
    else:
        print("用法: fleet_review.py list | approve <pid> <reviewer> | reject <pid> <reviewer> <reason>")
