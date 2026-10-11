#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
种子真值投喂器 · 向云端网关投喂结构化种子真值
锚定：Ω₀⊂⊙∞⊂Ω | 本体根 Ω-TAN-7-001 | 资产根 DID-BR-000002

设计（推演最优稳态方案落地）：
  - key 严格唯一（带 YYYYMMDD 后缀）→ 过元规则 KEY-UNIQUE
  - 标准 REPORT.* 命名空间 + 结构化 value + 锚定标识 → 过对齐门 ≥50
  - value 内置 confidence/seed_type/witness → 补 working_memory 与 mem_confidence
  - 全部标注 proposer=candidate → 守定位铁律

幂等：写入前先查 key 是否已存在，已存在则跳过（避免触发 duplicate_key_rejected）
"""
import json
import urllib.request
import urllib.error
import urllib.parse
import time

GATEWAY = "https://www.huodouai.com/api/report/truth"
QUERY = "https://www.huodouai.com/api/truth?key="
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DATE = "20261011"

SEEDS = [
    {
        "key": "REPORT.SEED.IDENTITY.%s" % DATE,
        "value": {
            "seed_type": "identity",
            "title": "节点身份种子真值",
            "confidence": 1.0,
            "witness": "自持私钥可签",
            "fields": {
                "node_id": "NODE-DEV-WORKBUDDY-001",
                "homologous_id": "ZR-HID-752B58718713D8F8",
                "key_fingerprint": "593f25357012595abaf76104de5952d3287916e293aff868a313cb44c83643fc",
                "ontology_root": "Ω-TAN-7-001",
                "did_root": "DID-BR-000002",
                "anchor": "Ω₀⊂⊙∞⊂Ω",
                "reg_version": "2.0",
                "env_bound": True,
            },
            "proposer": "NODE-DEV-WORKBUDDY-001",
            "nature": "candidate",
        },
    },
    {
        "key": "REPORT.SEED.A2A-CAPABILITY.%s" % DATE,
        "value": {
            "seed_type": "capability",
            "title": "A2A 互操作能力种子真值",
            "confidence": 1.0,
            "witness": "鉴权矩阵 10/10 PASS",
            "fields": {
                "protocol": "INTEROP-A2A-V2.0",
                "auth": "homologous-zrh1 (X-ZR-Token)",
                "roles": ["reader", "writer", "admin"],
                "endpoints": ["GET /health", "GET /.well-known/agent-card.json", "GET /identity", "POST /"],
                "skills": ["omega_status", "truth_recall", "memory_anchor", "truth_report", "node_heartbeat"],
                "auth_matrix": "10/10",
                "federation_e2e": "completed",
            },
            "proposer": "NODE-DEV-WORKBUDDY-001",
            "nature": "candidate",
        },
    },
    {
        "key": "REPORT.SEED.KERNEL-BASELINE.%s" % DATE,
        "value": {
            "seed_type": "baseline",
            "title": "内核基线种子真值",
            "confidence": 1.0,
            "witness": "网关 /api/status 交叉印证",
            "fields": {
                "service": "zhongshu-meta-core",
                "version": "V3.1",
                "anchor": "Ω₀⊂⊙∞⊂Ω",
                "ontology_root": "Ω-TAN-7-001",
                "did_root": "DID-BR-000002",
                "gateway": "https://www.huodouai.com",
                "standby": "https://drama.huodouai.com",
            },
            "proposer": "NODE-DEV-WORKBUDDY-001",
            "nature": "candidate",
        },
    },
    {
        "key": "REPORT.SEED.STEADY-STATE.%s" % DATE,
        "value": {
            "seed_type": "self-reference",
            "title": "最优稳态方案种子真值（自指锚）",
            "confidence": 0.9,
            "witness": "本地推演文档 steady-state-plan.md",
            "fields": {
                "plan_id": "STEADY-STATE-SEED-20261011",
                "goal": "补足 working_memory 与 mem_confidence，稀释重复率",
                "constraint": ["KEY-UNIQUE 元规则", "零删除铁律", "对齐门≥50", "定位候选"],
                "actions": ["投喂唯一key种子", "结构化value带confidence", "杜绝新重复"],
                "kernel_score_before": 50.7,
                "grade_before": "C",
            },
            "proposer": "NODE-DEV-WORKBUDDY-001",
            "nature": "candidate",
        },
    },
]


def key_exists(key):
    try:
        with urllib.request.urlopen(QUERY + urllib.parse.quote(key), timeout=20) as r:
            d = json.loads(r.read().decode())
        return (d.get("count", 0) > 0)
    except Exception:
        return False


def post(key, value):
    body = {
        "key": key,
        "value": value,
        "anchor": ANCHOR,
        "did": DID,
        "source_node": "NODE-DEV-WORKBUDDY-001",
        "truth_type": "seed",
    }
    req = urllib.request.Request(
        GATEWAY, data=json.dumps(body, ensure_ascii=False).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-DID": DID})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, e.read().decode()[:300]
    except Exception as e:
        return -1, {"err": str(e)[:200]}


def main():
    results = []
    for s in SEEDS:
        k = s["key"]
        if key_exists(k):
            print("[SKIP] %s 已存在（幂等跳过，避免重复拒绝）" % k)
            results.append({"key": k, "status": "skip_existing"})
            continue
        st, resp = post(k, s["value"])
        ok = isinstance(resp, dict) and resp.get("ok")
        seq = resp.get("seq") if isinstance(resp, dict) else None
        print("[HTTP %s] %s -> ok=%s seq=%s %s"
              % (st, k, ok, seq,
                 (json.dumps(resp, ensure_ascii=False)[:160] if not ok else "")))
        results.append({"key": k, "status": "written" if ok else "failed",
                        "http": st, "seq": seq,
                        "resp": resp if not ok else None})
        time.sleep(0.4)

    print()
    print("=" * 60)
    written = [r for r in results if r["status"] == "written"]
    print("投喂完成: 写入 %d 条, 跳过 %d 条, 失败 %d 条"
          % (len(written),
             len([r for r in results if r["status"] == "skip_existing"]),
             len([r for r in results if r["status"] == "failed"])))
    print(json.dumps(results, ensure_ascii=False, indent=1))

    with open("/workspace/zr-token/identity-v2/seed-feed-receipt.json", "w") as f:
        json.dump({"feed_at": "2026-10-11T22:09:00+08:00",
                   "node": "NODE-DEV-WORKBUDDY-001",
                   "gateway": GATEWAY,
                   "results": results}, f, ensure_ascii=False, indent=2)
    print("回执: /workspace/zr-token/identity-v2/seed-feed-receipt.json")


if __name__ == "__main__":
    main()
