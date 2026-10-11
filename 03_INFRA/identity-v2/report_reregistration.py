#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投递「节点身份与 A2A 重新注册」候选报告到云端审核队列 + 网关候选记录。
性质：候选（本节点 NODE-DEV-WORKBUDDY-001 为同源测试节点，非中枢，无裁决权）
铁律：前缀 NODE-DEV-WORKBUDDY-001.PROPOSAL.*；不发布无前缀的中枢级 key
"""
import json
import urllib.request
import urllib.error

GATEWAY = "https://www.huodouai.com/api/report/truth"
QUEUE = "https://www.huodouai.com/a2a/external/truth"

registration = json.load(open("/workspace/zr-token/identity-v2/identity-registration.json"))
ledger = json.load(open("/workspace/zr-token/identity-v2/a2a-ledger-v2.json"))

record = {
    "action": "node_identity_re_registration",
    "proposer": "NODE-DEV-WORKBUDDY-001",
    "proposal_status": "候选待裁决",
    "node_nature": "同源测试节点（非主中枢，无裁决权）",
    "trigger": "沙箱环境重建（container_id 变更），按当前环境配置重新注册身份与 A2A",
    "new_identity": {
        "homologous_id": registration["homologous_id"],
        "key_fingerprint": registration["key_fingerprint"],
        "public_salt": registration["public_salt"],
        "salt_env_bound": True,
        "salt_bound_tail": registration["env_binding"]["salt_bound_tail"],
    },
    "prev_identity": {
        "homologous_id": registration["prev_identity"]["homologous_id"],
        "status": "superseded-by-env-rebuild",
        "note": "旧 salt/口令未落环境，不可复原；旧记录保留不删除",
    },
    "env_binding": {
        "container_id": registration["env_binding"]["container_id"],
        "env_fingerprint": registration["env_binding"]["env_fingerprint"],
    },
    "verification": ledger["verification"],
    "fixes_applied": ledger["fixes_applied"],
    "ask": "请中枢裁决：①新身份 ZR-HID-752B58718713D8F8 是否登记入对端表；②旧身份记录保留或标注；③是否需要统一信任根对齐",
    "authority": "candidate-only",
    "ts": "2026-10-11T21:57:00+08:00",
}

def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return -1, str(e)[:200]

print("=" * 60)
print("1) 网关候选记录（PROPOSAL 前缀）")
gw_body = {
    "key": "NODE-DEV-WORKBUDDY-001.PROPOSAL.RE-REGISTRATION-V2",
    "value": record,
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "source_node": "NODE-DEV-WORKBUDDY-001",
    "truth_type": "proposal",
}
s1, r1 = post(GATEWAY, gw_body)
print("[HTTP %s] %s" % (s1, r1[:400]))

print()
print("2) 云端 A2A 审核队列")
q_body = {
    "key": "NODE-DEV-WORKBUDDY-001.PROPOSAL.RE-REGISTRATION-V2",
    "value": record,
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "source_node": "NODE-DEV-WORKBUDDY-001",
    "truth_type": "proposal",
}
s2, r2 = post(QUEUE, q_body)
print("[HTTP %s] %s" % (s2, r2[:400]))

print()
print("=" * 60)
print(json.dumps({"gateway": {"status": s1}, "queue": {"status": s2, "body": r2}}, ensure_ascii=False))
