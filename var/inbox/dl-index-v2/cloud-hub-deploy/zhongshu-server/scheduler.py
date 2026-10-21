#!/usr/bin/env python3
"""scheduler.py · 云端中枢元内核 · 中枢调度 worker
职责：心跳握手(上行网关+下行任务表) + 定时锁档触发 + 真值积累
依赖：lark-cli（飞书 Base 共享大脑），可选
启动：python3 scheduler.py --interval 300
"""
import json, os, subprocess, sys, time

BASE = os.environ.get("ZR_BASE_TOKEN", "DgnMbLqZiaIUDKshqCrcD4DvnBg")
TASK_TABLE = os.environ.get("ZR_TASK_TABLE", "tblnVRjuf7P31cEP")
BLOCK_TABLE = os.environ.get("ZR_BLOCK_TABLE", "tbljp3z11UtiuWCF")
DID = "DID-BR-000002"
INTERVAL = int(sys.argv[sys.argv.index("--interval") + 1]) if "--interval" in sys.argv else 300


def lark(args):
    try:
        p = subprocess.run(["lark-cli", "base"] + args + ["--as", "user"], capture_output=True, text=True, timeout=60)
        return json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
    except Exception:
        return {}


def heartbeat_once():
    out = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": "alive", "did": DID}
    # 下行：读任务表 待开始/进行中 + 阻塞表
    try:
        t = lark(["+record-list", "--base-token", BASE, "--table-id", TASK_TABLE, "--limit", "100", "--offset", "0", "--format", "json"])
        data = t.get("data", {})
        rows = data.get("data", [])
        fields = data.get("fields", [])
        idx = {n: i for i, n in enumerate(fields)} if isinstance(fields, list) else {}
        st_i = idx.get("状态", -1)
        out["downstream"] = {
            "tasks": len(rows),
            "todo": sum(1 for r in rows if st_i >= 0 and isinstance(r, list) and st_i < len(r) and str(r[st_i]) in ("待开始", "进行中")),
        }
    except Exception as e:
        out["downstream_error"] = str(e)[:120]
    return out


def run_loop():
    print(f"中枢调度 worker 启动 · 间隔 {INTERVAL}s · DID {DID}", flush=True)
    while True:
        try:
            hb = heartbeat_once()
            print(json.dumps(hb, ensure_ascii=False), flush=True)
        except Exception as e:
            print("heartbeat_error:", str(e)[:160], flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    run_loop()
