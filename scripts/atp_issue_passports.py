#!/usr/bin/env python3
"""ATP Phase1 实务: 给体系已知 Agent 节点签发第一张数字身份证。

节点清单依据(仓内实据): HANDSHAKE-NODE-DEV-DOUBAO-WORK-001.json、
政务报告主/开发节点声明、云端心跳 HEARTBEAT.node.ZR-CLOUD-HUB (seq28580)、
云端 auto_reporter_v1 锁档 source (seq28576-28578)、steady_evolve_bootstrap.sh。
trust_tier 为按节点职责的初始分配(ATP 2.1: 由管理员分配, 可重签调整)。
护照库 var/atp/passport.db(state, 不入Git); 签发清单(公钥指纹)入Git。
"""
import hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atp_passport import IdentityIssuer, TRUST_TIERS

NODES = [
    {"node": "hub-central-agent",           "tier": "T4", "caps": ["truth.anchor", "model.pool.dispatch", "asset.lock", "meta_rule.execute"], "note": "主节点: 全域真值锚定/多模型调度/资产锁档(身份卡权限)"},
    {"node": "NODE-DEV-DOUBAO-WORK-001",    "tier": "T2", "caps": ["repo.write", "truth.report", "doc.archive"], "note": "开发节点: 仓仓推进/真值上报(source_node实据)"},
    {"node": "NODE-MI-V5-001",              "tier": "T2", "caps": ["repo.write", "truth.report"], "note": "v5并行节点(握手rebase吸收其commit实据)"},
    {"node": "ZR-CLOUD-HUB-123.207.202.158", "tier": "T3", "caps": ["truth.consume", "heartbeat", "auto_reporter_v1.lock", "evolution.route"], "note": "云端中枢: 心跳/消费/自动锁档(HEARTBEAT+LEDGER实据)"},
    {"node": "auto_reporter_v1",             "tier": "T2", "caps": ["ledger.append", "truth.report"], "note": "云端自动上报器(锁档事件source实据)"},
    {"node": "steady_evolve-worker",         "tier": "T1", "caps": ["heartbeat", "task.poll"], "note": "进化心跳worker: 只读轮询+心跳"},
]

def main():
    os.makedirs("var/atp", exist_ok=True)
    iss = IdentityIssuer("var/atp/passport.db")
    issued, failed = [], []
    for n in NODES:
        did = f"did:firev5:zongyuan:{n['node']}"
        try:
            row = iss.get(did)
            issued.append({**n, "agent_did": did, "action": "exists",
                           "pub_fp": hashlib.sha256(row["pub_key"].encode()).hexdigest()[:16],
                           "expires_at": row["expires_at"]})
        except ValueError:
            r = iss.register("zongyuan", n["node"], n["caps"], n["tier"],
                             workload_uri=f"node://{n['node']}")
            row = iss.get(r["agent_did"])
            issued.append({**n, "agent_did": did, "action": "issued",
                           "pub_fp": hashlib.sha256(row["pub_key"].encode()).hexdigest()[:16],
                           "expires_at": r["expires_at"]})
        print(f"  [PASS] {n['tier']} {did}")
    assert iss.audit_verify(), "audit链断裂"
    print("  [PASS] audit 链重放校验通过")
    reg = {"registry": "atp_passport_registry_v1", "issued_at": int(time.time()),
           "issuer": "did:firev5:issuer", "count": len(issued),
           "entries": issued, "secret_policy": "私钥/库不入Git(var/atp/, 600); 此清单仅公钥指纹"}
    with open("var/atp/passport_registry.json", "w") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    print(f"  [PASS] 签发清单落盘 var/atp/passport_registry.json ({len(issued)}节点)")
    n_iss = sum(1 for e in issued if e["action"] == "issued")
    print(f"passport_issue: {n_iss} issued, {len(issued)-n_iss} existed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
