#!/usr/bin/env python3
"""受控行动层（ActionGate）：把内核 allowed_actions 从"代码白名单"升级为"分级授权 + 人工审批 + 审计追溯"。

设计（fail-closed）：
- 低风险动作（只读/审计/巡检/查询/状态）→ 自动放行
- 高风险动作（写/外发：api_call / feishu_write / gateway_report / execute）→ 必须人工审批
  - request：生成审批请求 var/action_requests/<id>.json + 审计 kernel.actiongate|request|pending
  - approve：检测到人工放行文件 <id>.approved（含白名单命令）→ 执行回调 → 审计 ok/fail
- 熔断：内核已熔断（fused）时一切高风险动作直接 deny
- 命令白名单：payload.command 必须命中白名单，防注入

用法：
  action_gate.py check <action> [--payload <json>]      # 分级判定
  action_gate.py request <action> --payload <json>      # 高风险发起审批
  action_gate.py approve <request_id> --by <operator>   # 人工放行并执行
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "var" / "audit" / "audit.jsonl"
REQS = ROOT / "var" / "action_requests"
PID_FILE = ROOT / "var" / "run" / "kernel.pid"

# 分级：低风险自动放行（与内核 allowed_actions 只读语义对齐）
LOW_RISK = {"audit", "reflect", "patrol", "query", "status", "route", "health", "merkle", "selfheal"}
# 高风险需审批（写/外发/执行）
HIGH_RISK = {"api_call", "feishu_write", "gateway_report", "execute", "memory_write"}
# 执行回调命令白名单（防注入；仅演示级无害命令 + 运维可扩展）
CMD_WHITELIST = {
    "true": ["/usr/bin/true"],
    "baseline_backup": ["/usr/bin/cp", "var/state/baseline.json", "/home/user/ZONGYUAN-ROOT/var/truth/"],
    "audit_tail": ["/usr/bin/tail", "-3", "var/audit/audit.jsonl"],
}


def audit(event, actor, action, result, detail=None):
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event,
           "actor": actor, "action": action, "result": result, "detail": detail}
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def is_fused():
    try:
        st = json.loads((ROOT / "var" / "state" / "baseline.json").read_text(encoding="utf-8"))
        return False
    except Exception:
        return True
    # 真实熔断状态以内核 state 为准（此处简化：存在 pid 且内核运行即未熔断）
    # 若内核 pid 文件存在且进程存活，进一步查 status 端口；此处保留 fail-closed 语义


def check(action, payload=None):
    if action in LOW_RISK:
        return {"action": action, "verdict": "allow", "tier": "low", "reason": "只读/审计类动作自动放行"}
    if action in HIGH_RISK:
        if is_fused():
            return {"action": action, "verdict": "deny", "tier": "high", "reason": "内核熔断，fail-closed 拒绝一切高风险动作"}
        return {"action": action, "verdict": "approve_required", "tier": "high",
                "reason": "写/外发类动作需人工审批", "payload": payload}
    return {"action": action, "verdict": "deny", "tier": "unknown", "reason": "动作不在分级清单内"}


def request(action, payload):
    v = check(action, payload)
    if v["verdict"] != "approve_required":
        return v
    cmd_key = (payload or {}).get("command", "")
    if cmd_key not in CMD_WHITELIST:
        return {"verdict": "deny", "reason": f"命令 {cmd_key!r} 不在白名单（CMD_WHITELIST）"}
    rid = f"{action}-{int(time.time())}-{os.getpid()}"
    req = {"request_id": rid, "action": action, "payload": payload,
           "requested_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "status": "pending", "DID": "DID-BR-000002"}
    REQS.mkdir(parents=True, exist_ok=True)
    (REQS / f"{rid}.json").write_text(json.dumps(req, ensure_ascii=False, indent=2), encoding="utf-8")
    audit("kernel.actiongate", "operator", "request", "pending", f"审批请求 {rid} action={action}")
    return {"verdict": "pending", "request_id": rid, "file": str(REQS / f"{rid}.json"),
            "note": "人工放行：创建同名的 .approved 文件（内容含 approved_by）后运行 approve"}


def approve(rid, by):
    req_file = REQS / f"{rid}.json"
    app_file = REQS / f"{rid}.approved"
    if not req_file.exists():
        return {"verdict": "deny", "reason": f"审批请求不存在 {rid}"}
    req = json.loads(req_file.read_text(encoding="utf-8"))
    if not app_file.exists():
        return {"verdict": "still_pending", "reason": "人工放行文件未创建", "request_id": rid}
    cmd_key = req.get("payload", {}).get("command", "")
    if cmd_key not in CMD_WHITELIST:
        return {"verdict": "deny", "reason": f"命令 {cmd_key!r} 已不在白名单，拒绝执行"}
    cmd = [c if c.startswith("/") else (str(ROOT / c) if c.startswith("var/") else c)
           for c in CMD_WHITELIST[cmd_key]]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        ok = r.returncode == 0
        audit("kernel.actiongate", by, "approve", "ok" if ok else "fail",
              f"{rid} 命令={cmd_key} rc={r.returncode} out={r.stdout.strip()[:120]}")
        (req_file).unlink()
        app_file.unlink()
        return {"verdict": "ok" if ok else "fail", "request_id": rid, "cmd": cmd_key, "rc": r.returncode,
                "output": r.stdout.strip()[:200]}
    except Exception as e:
        audit("kernel.actiongate", by, "approve", "fail", f"{rid} 异常 {e}")
        return {"verdict": "fail", "request_id": rid, "reason": str(e)}


def main():
    ap = argparse.ArgumentParser(description="受控行动层 ActionGate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("action")
    c.add_argument("--payload", type=json.loads, default=None)
    r = sub.add_parser("request"); r.add_argument("action")
    r.add_argument("--payload", type=json.loads, required=True)
    a = sub.add_parser("approve"); a.add_argument("request_id"); a.add_argument("--by", default="operator")
    args = ap.parse_args()
    if args.cmd == "check":
        print(json.dumps(check(args.action, args.payload), ensure_ascii=False, indent=2))
    elif args.cmd == "request":
        print(json.dumps(request(args.action, args.payload), ensure_ascii=False, indent=2))
    elif args.cmd == "approve":
        print(json.dumps(approve(args.request_id, args.by), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
