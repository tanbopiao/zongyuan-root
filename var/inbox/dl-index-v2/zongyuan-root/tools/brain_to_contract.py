#!/usr/bin/env python3
"""Ω-Brainμ 提案 → CONTRACT-OP-V1.0 契约转化器（心智落地的最后一步）
从最新 brain-proposal 生成契约，写入 task_inbox 由调度器执行"""
import os, json, glob, time
ZR = "/home/user/ZONGYUAN-ROOT"
INBOX = os.path.join(ZR, "task_inbox")
props = sorted(glob.glob(os.path.join(ZR, "var/brain-proposals", "brain-proposal-*.json")))
if not props:
    print("无提案"); exit(1)
latest = props[-1]
prop = json.load(open(latest, encoding="utf-8"))
task_id = f"T-BRAIN-{int(time.time())}"
contract = {
    "contract_version": "CONTRACT-OP-V1.0",
    "did": "DID-BR-000002",
    "ontology_signature": "Ω₀⊂⊙∞⊂Ω",
    "contract_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "task_id": task_id,
    "operator_list": [{"op_id": "OP-BRAIN-AUDIT-001", "params": {}, "timeout": 120}],
    "scheduling_policy": {"mode": "serial", "continue_on_fail": False},
    "memo": f"Ω-Brainμ 提案自动转化：{len(prop['proposals'])} 条（{', '.join(p['type'] for p in prop['proposals'])})",
}
path = os.path.join(INBOX, task_id + ".json")
json.dump(contract, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"契约已写入: {path}")
