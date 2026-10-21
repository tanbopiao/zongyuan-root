#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain_quota 心智算力配额决策器 ｜ W-09 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
职责: 读 SYSTEM-STATE.json → 按稳态决策表动态调节 Ω-Brainμ 心智采样频率/优先级
      健康 ok       → 30s / normal / full（全速推理）
      warning      → 60s / low   / throttled（降载保稳）
      partial_lock/degraded → 300s / minimal / lowpower（最低功耗保守护）
输出: var/brain/brain-quota.json（决策结果）
审计: var/brain/brain-quota-ledger.jsonl（决策变更 append-only）
支持: --state <ok|warning|degraded> 手动注入测试（不改真实状态文件）
"""
import json, os, sys, time

ZR = os.environ.get("ZONGYUAN_ROOT", "/home/user/ZONGYUAN-ROOT")
STATE_FILE = os.path.join(ZR, "var", "SYSTEM-STATE.json")
QUOTA_FILE = os.path.join(ZR, "var", "brain", "brain-quota.json")
LEDGER = os.path.join(ZR, "var", "brain", "brain-quota-ledger.jsonl")

DECISION = {
    "ok":     {"sampling_interval_sec": 30,  "priority": "normal",  "mode": "full"},
    "warning": {"sampling_interval_sec": 60,  "priority": "low",     "mode": "throttled"},
    "degraded": {"sampling_interval_sec": 300, "priority": "minimal", "mode": "lowpower"},
}

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def read_state(inject):
    if inject:
        return {"health": inject, "source": "manual-inject"}
    if not os.path.exists(STATE_FILE):
        return {"health": "degraded", "source": "missing-state-file"}
    d = json.load(open(STATE_FILE, encoding="utf-8"))
    return {"health": d.get("health", "degraded"), "source": STATE_FILE}

def decide(state):
    health = state.get("health", "degraded")
    # 归一化：partial_lock/异常 → degraded；ok/warning 直映射
    if health in DECISION:
        pass
    elif health in ("partial_lock", "quota_full", "read_fail"):
        health = "degraded"
    else:
        health = "warning"
    base = DECISION[health]
    rec = {
        "decision_ts": now(),
        "system_health": state.get("health"),
        "sampling_interval_sec": base["sampling_interval_sec"],
        "priority": base["priority"],
        "mode": base["mode"],
        "source": state.get("source", ""),
        "rationale": f"Ω-Brainμ 心智算力按 SYSTEM-STATE={state.get('health')} 动态调节"
    }
    return rec

def main():
    inject = None
    if len(sys.argv) > 1 and sys.argv[1] == "--state":
        inject = sys.argv[2]
    state = read_state(inject)
    rec = decide(state)
    os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
    # 变更审计（append-only）：仅当与上次决策不同才记录
    changed = True
    if os.path.exists(QUOTA_FILE):
        old = json.load(open(QUOTA_FILE, encoding="utf-8"))
        changed = (old.get("mode") != rec["mode"]) or (old.get("sampling_interval_sec") != rec["sampling_interval_sec"])
    json.dump(rec, open(QUOTA_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if changed:
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({"quota": rec, "changed": changed}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
