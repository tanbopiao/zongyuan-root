#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""认知→心智自动链路 V0.1：think 建议 → 提案 → 契约 → task_inbox
基底组件：让大脑输出直接进入心智闭环（全自动无人值守）
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | BASE-V1.0
"""
import os, json, time, glob, subprocess

ZK = "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
ZR = "/home/user/ZONGYUAN-ROOT"
INBOX = os.path.join(ZR, "task_inbox")
PROPS = os.path.join(ZR, "var/brain-proposals")

def run_advisor(goal, provider="zhipu"):
    r = subprocess.run(
        ["python3", f"{ZK}/scripts/cognitive_advisor.py", goal, "--provider", provider],
        capture_output=True, text=True, timeout=40, cwd=ZK)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"verdict": "parse_fail", "raw": r.stdout[:200]}

def to_proposal(adv):
    now = time.strftime("%Y%m%d_%H%M%S")
    a = adv.get("advice", {})
    proposal = {
        "brain": "Ω-Brainμ-Advisor-Pipeline", "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "read_only": True, "provider": adv.get("provider"), "model": adv.get("model"),
        "proposals": [{
            "type": "improve", "priority": "P2", "p_value": 0.6,
            "title": "认知建议", "evidence": f"provider={adv.get('provider')} model={adv.get('model')}",
            "suggest": json.dumps(a, ensure_ascii=False)[:500],
        }],
    }
    p = os.path.join(PROPS, f"advisor-proposal-{now}.json")
    json.dump(proposal, open(p, "w"), ensure_ascii=False, indent=2)
    return p

def to_contract(proposal_path):
    task_id = f"T-BRAIN-{int(time.time())}"
    contract = {
        "contract_version": "CONTRACT-OP-V1.0", "did": "DID-BR-000002",
        "ontology_signature": "Ω₀⊂⊙∞⊂Ω",
        "contract_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_id": task_id,
        "operator_list": [{"op_id": "OP-BRAIN-AUDIT-001", "params": {}, "timeout": 120}],
        "scheduling_policy": {"mode": "serial", "continue_on_fail": False},
        "memo": "认知建议自动入心智闭环",
    }
    c = os.path.join(INBOX, task_id + ".json")
    json.dump(contract, open(c, "w"), ensure_ascii=False, indent=2)
    return c

if __name__ == "__main__":
    import sys
    goal = sys.argv[1] if len(sys.argv) > 1 else "给出当前内核下一步的一个低风险优化建议，JSON格式"
    adv = run_advisor(goal)
    print("认知:", adv.get("verdict"), "|", adv.get("provider"), "|", adv.get("model"))
    if adv.get("verdict") == "ok":
        p = to_proposal(adv)
        c = to_contract(p)
        print(f"提案: {p}")
        print(f"契约: {c}")
        print("链路: 大脑→提案→契约→inbox 完成 ✓")
    else:
        print("认知不可用:", adv.get("reason", ""))
