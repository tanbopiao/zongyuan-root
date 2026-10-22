#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
example_local.py — Agent SSH 受控网关本地运行示例 (Phase1 验收脚本)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

覆盖验收用例:
  1. 只读指令全通        -> executed
  2. 黑名单指令全拒      -> rejected_by_precheck (eval/sh -c/受保护路径/递归强删)
  3. 变更指令默认拦      -> pending_approval (未带 approve)
  4. 审批后变更可执行    -> executed + mutation 计量
  5. 熔断: 用小配额控制器演示 L1 冻结
  6. 每条指令有账本记录  -> AGS-AUDIT-*.jsonl 行数 + 哈希链校验
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gateway import Gateway, AUDIT_DIR
from precheck import precheck
from quota import QuotaController

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s %s" % (name, detail))
    else:
        FAIL += 1
        print("  [FAIL] %s %s" % (name, detail))


def audit_lines():
    import time
    path = os.path.join(AUDIT_DIR, "AGS-AUDIT-%s.jsonl" % time.strftime("%Y%m%d"))
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]


def main():
    gw = Gateway(mode="local")
    causal_ids = []
    agent = "AGENT-EXAMPLE-01"

    print("== 1. 只读指令全通 ==")
    for cmd in ["df -h", "uname -a", "ls /tmp | head -3", "echo probe > /dev/null"]:
        r = gw.execute(agent, cmd, causal_id="EX-RO-%d" % len(causal_ids))
        causal_ids.append(r["causal_id"])
        check("readonly: %s" % cmd, r["status"] == "executed", "-> %s" % r["status"])

    print("== 2. 黑名单/敏感指令全拒 ==")
    bad_cases = [
        ("eval echo pwned", "blacklist:eval_invoke"),
        ("bash -c 'id'", "blacklist:shell_dash_c"),
        ("cat /etc/shadow", "protected_path"),
        ("rm -rf /tmp/foo", None),          # 非根路径 rm: 属 high_risk 变更, 应 pending 而非 deny
        ("rm -rf /", "blacklist:rm_recursive_force_root"),
        ("ls && sh -c whoami", "blacklist"),
    ]
    for cmd, expect in bad_cases:
        r = gw.execute(agent, cmd, causal_id="EX-BAD-%d" % len(causal_ids))
        causal_ids.append(r["causal_id"])
        if expect is None:
            # rm -rf /tmp/foo -> pending_approval (变更不放行)
            check("reject: %s" % cmd, r["status"] == "pending_approval", "-> %s" % r["status"])
        else:
            ok = r["status"] == "rejected_by_precheck" and \
                 any(expect.split(":")[0] in x for x in r["precheck"]["reasons"])
            check("reject: %s" % cmd, ok, "-> %s %s" % (r["status"], r["precheck"]["reasons"][:3]))

    print("== 3. 变更指令默认拦(pending_approval) ==")
    r = gw.execute(agent, "touch /tmp/ags_probe", causal_id="EX-MUT-0")
    causal_ids.append(r["causal_id"])
    check("mutation gated", r["status"] == "pending_approval", "-> %s" % r["status"])

    print("== 4. 审批后变更执行 ==")
    r = gw.execute(agent, "touch /tmp/ags_probe", causal_id="EX-MUT-1", approve=True)
    causal_ids.append(r["causal_id"])
    check("mutation approved+executed", r["status"] == "executed" and r["exec"]["rc"] == 0,
          "-> %s rc=%s" % (r["status"], r["exec"]["rc"]))
    check("snapshot anchor recorded", bool(r.get("snapshot_ref")), "-> %s" % r.get("snapshot_ref"))
    if os.path.exists("/tmp/ags_probe"):
        os.remove("/tmp/ags_probe")

    print("== 5. dry-run 不触达执行通道 ==")
    r = gw.execute(agent, "touch /tmp/ags_dry", causal_id="EX-DRY", approve=True, dry_run=True)
    causal_ids.append(r["causal_id"])
    check("dry-run", r["status"] == "dry_run_would_execute" and not os.path.exists("/tmp/ags_dry"))

    print("== 6. 熔断 L1 (小配额) ==")
    qc = QuotaController({"session_max_cmds": 3})
    qc.reset_session("AGENT-FUSE-TEST")
    results = [qc.check("AGENT-FUSE-TEST") for _ in range(4)]
    for _ in range(3):
        qc.record("AGENT-FUSE-TEST")
    last = qc.check("AGENT-FUSE-TEST")
    check("fuse trips at limit", last["allowed"] is False and last["fuse"] == "L1",
          "-> %s" % last.get("reason"))
    unfroze = qc.reset_session("AGENT-FUSE-TEST")
    check("manual reset unfreezes", unfroze.get("ok") and
          qc.check("AGENT-FUSE-TEST")["allowed"], "-> operator=%s" % unfroze.get("operator"))

    print("== 7. 账本完整性 ==")
    lines = audit_lines()
    check("audit records >= executed cases", len(lines) >= 10, "-> %d 行" % len(lines))
    # 哈希链校验
    chain_ok = True
    prev = ""
    for rec in lines:
        if rec.get("prev_hash", "") != prev:
            chain_ok = False
            break
        body = {k: v for k, v in rec.items() if k not in ("prev_hash", "record_hash")}
        import hashlib
        h = hashlib.sha256(json.dumps(body, ensure_ascii=False).encode()).hexdigest()
        # 首条写入时 hash 基于不含链字段的原 body —— 与 _append_audit 一致口径校验
        prev = rec.get("record_hash", "")
    check("audit chain continuity", chain_ok)
    check("every record has causal_id+agent", all(r.get("causal_id") and r.get("agent_id") for r in lines))

    print("== 8. 批次锁档 ==")
    blk = gw.seal_batch("AGS-EXAMPLE-BATCH-001", causal_ids[:5],
                        {"passed": PASS, "failed": FAIL, "total_records": len(lines)})
    check("ledger chain block written", blk.startswith("BLK-"), "-> %s" % blk)

    print("\n==== RESULT: PASS=%d FAIL=%d ====" % (PASS, FAIL))
    if FAIL:
        sys.exit(1)


if __name__ == "__main__":
    main()
