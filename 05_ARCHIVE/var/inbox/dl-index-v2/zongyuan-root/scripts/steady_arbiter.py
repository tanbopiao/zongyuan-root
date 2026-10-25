#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地×云端最优稳态方案仲裁执行器（META-STEADY-ARBITRATION-001）
用法:
  python3 steady_arbiter.py --compare '<local-json>' '<cloud-json>'
方案JSON: {"id","source","target","U","R","C","semantics"}
USI = 0.3U − 0.4R − 0.3C
裁决: |Δ|<5 等效云端优先；cloud>local+5 采纳云端；local>cloud+5 提名本地交云端复核(拒绝则升级)
留痕: var/arbitration/steady-<ts>.json + 审计 + 网关上报
"""
import json, os, sys, io, datetime

ZR = "/home/user/ZONGYUAN-ROOT"
HIST = f"{ZR}/var/arbitration"
KERNEL_AUDIT = "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl"

def usi(p):
    return round(0.3 * p["U"] - 0.4 * p["R"] - 0.3 * p["C"], 2)

def arbitrate(local, cloud):
    lu, cu = usi(local), usi(cloud)
    delta = round(lu - cu, 2)
    if abs(delta) < 5:
        verdict, reason = "equivalent_cloud_priority", "|Δ|<5 等效，云端优先（OMG-5 兜底防震荡）"
    elif cu > lu + 5:
        verdict, reason = "cloud_superior", "云端 USI 显著更高，采纳云端（全局信息优先）"
    elif lu > cu + 5:
        verdict, reason = "local_superior_propose_review", "本地 USI 显著更高，提名本地方案交云端 Omega 复核；拒绝则升级 L2/L3"
    result = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S"),
              "rule": "META-STEADY-ARBITRATION-001",
              "target": local.get("target"),
              "local": {**local, "usi": lu}, "cloud": {**cloud, "usi": cu},
              "delta_usi": delta, "verdict": verdict, "reason": reason}
    os.makedirs(HIST, exist_ok=True)
    with io.open(f"{HIST}/steady-{result['ts']}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "event": "kernel.truth", "actor": "operator", "action": "steady-arbitration",
           "result": "ok", "detail": f"target={local.get('target')} local_USI={lu} cloud_USI={cu} Δ={delta} → {verdict}"}
    with io.open(KERNEL_AUDIT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[仲裁] target={local.get('target')}")
    print(f"  本地 USI={lu}（U{local['U']}/R{local['R']}/C{local['C']}）｜ 云端 USI={cu}（U{cloud['U']}/R{cloud['R']}/C{cloud['C']}）｜ Δ={delta}")
    print(f"[裁决] {verdict}｜{reason}")
    print(f"[留痕] var/arbitration/steady-{result['ts']}.json")
    return result

if __name__ == "__main__":
    if "--compare" in sys.argv:
        i = sys.argv.index("--compare")
        arbitrate(json.loads(sys.argv[i + 1]), json.loads(sys.argv[i + 2]))
    else:
        print(__doc__)
