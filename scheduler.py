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
        t = lark_guarded(["+record-list", "--base-token", BASE, "--table-id", TASK_TABLE, "--limit", "100", "--offset", "0", "--format", "json"])
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




def learn_first():
    """学习先行层(L4·META-LEARN-FIRST-001)：执行前先读体系元法则索引，未学习不执行主循环"""
    idx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "meta-laws-index.json")
    try:
        idx = json.load(open(idx_path, encoding="utf-8"))
        n = int(idx.get("count", 0))
        root = idx.get("root_sha", "")
        log = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "learned": True, "laws": n,
               "root_sha": root, "did": DID}
        if n <= 0:
            log["learned"] = False
            log["reason"] = "法则索引为空，禁止执行"
        print(json.dumps({"learn_first": log}, ensure_ascii=False), flush=True)
        return log["learned"]
    except Exception as e:
        print(json.dumps({"learn_first": {"learned": False, "reason": str(e)[:120]}}, ensure_ascii=False), flush=True)
        return False


def decision_gate(action: str, risk: str = "low"):
    """决策层(M1决策元法则)：低风险自动执行；高风险写动作 fail-closed 挂起需人工审批"""
    if risk == "low":
        return {"allow": True, "gate": "auto"}
    # 高风险：拒绝自动执行，记录审批待办
    print(json.dumps({"decision_gate": {"action": action, "risk": risk,
                                        "allow": False, "gate": "pending-approval",
                                        "rule": "P=0.3U-0.4R-0.3C risk-min-first"}}, ensure_ascii=False), flush=True)
    return {"allow": False, "gate": "pending-approval"}


def lark_guarded(args):
    """写操作守卫：所有 lark 写类命令先过决策门，未审批不执行"""
    write_kw = ("record-batch-update", "record-delete", "record-upsert", "field-create",
                "field-update", "record-batch-create", "view-create", "workflow")
    if any(w in args for w in write_kw):
        gate = decision_gate(" ".join(args[:3]), risk="high")
        if not gate["allow"]:
            return {"ok": False, "blocked": True, "gate": gate["gate"], "action": args[:3]}
    return lark(args)

def run_loop():
    print(f"中枢调度 worker 启动 · 间隔 {INTERVAL}s · DID {DID}", flush=True)
    # 学习先行：未通过法则学习校验则不进入主循环（fail-closed）
    learned = learn_first()
    if not learned:
        print(json.dumps({"fatal": "LEARN_FIRST_FAILED 未学习元法则，禁止执行调度"}, ensure_ascii=False), flush=True)
        sys.exit(2)
    while True:
        try:
            hb = heartbeat_once()
            print(json.dumps(hb, ensure_ascii=False), flush=True)
        except Exception as e:
            print("heartbeat_error:", str(e)[:160], flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    run_loop()
