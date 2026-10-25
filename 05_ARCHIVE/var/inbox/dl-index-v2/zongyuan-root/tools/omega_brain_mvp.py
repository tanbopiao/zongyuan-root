#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ω-Brainμ 最小心智原型 V0.1
职责：读账本+审计 → 故障/事件聚类 → 产出演化提案（CONTRACT 提案草稿）
边界：只出提案，绝不直接改文件；心智受公理约束（只读复盘）
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | META-RULE-014
"""
import os, json, csv, time, re
from collections import Counter
from datetime import datetime

ZR = "/home/user/ZONGYUAN-ROOT"
ZK = "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
LEDGER = os.path.join(ZR, "HASH-LEDGER-MAIN.csv")
AUDIT = os.path.join(ZK, "var/audit/audit.jsonl")
OUT = os.path.join(ZR, "var/brain-proposals")
os.makedirs(OUT, exist_ok=True)

def read_ledger_tail(n=300):
    rows = []
    try:
        with open(LEDGER, encoding="utf-8") as f:
            for line in f.readlines()[-n:]:
                try: rows.append(csv.reader([line]).__next__())
                except Exception: pass
    except FileNotFoundError:
        return rows
    return rows

def read_audit_tail(n=300):
    evs = []
    try:
        with open(AUDIT, encoding="utf-8") as f:
            for line in f.readlines()[-n:]:
                try:
                    d = json.loads(line)
                    evs.append(d)
                except Exception: pass
    except FileNotFoundError:
        return evs
    return evs

def calc_p(u, r, c):
    """决策元法则 P=0.3U−0.4R−0.3C"""
    return round(0.3*u - 0.4*r - 0.3*c, 2)

def analyze():
    ledger = read_ledger_tail()
    audits = read_audit_tail()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. 事件聚类
    action_cnt = Counter(a.get("event", a.get("action", "?")) for a in audits)
    fail_cnt = Counter(a.get("action", "?") for a in audits if "fail" in str(a.get("result","")).lower() or "error" in str(a.get("result","")).lower())
    exit_codes = Counter(r[5] if len(r) > 5 else "?" for r in ledger)
    total_audit = len(audits)
    total_ledger = len(ledger)

    # 2. 提案生成（规则引擎，只读复盘）
    proposals = []
    # P1: 审计失败事件收敛
    if total_audit > 0 and sum(fail_cnt.values()) > 0:
        p = calc_p(0.8, 0.4, 0.2)
        proposals.append({
            "type": "fix", "priority": "P1" if p >= 0.5 else "P2",
            "p_value": p, "title": "审计失败事件收敛复盘",
            "evidence": f"近{total_audit}条审计中失败/异常 {sum(fail_cnt.values())} 条: {dict(fail_cnt.most_common(3))}",
            "suggest": "定位失败根因 → 修复链路 → 重跑验证 → 回写审计",
        })
    # P2: 真值上报健康度
    truth_ok = action_cnt.get("kernel.truth", 0) + action_cnt.get("operator", 0)
    p2 = calc_p(0.7, 0.3, 0.3)
    proposals.append({
        "type": "improve", "priority": "P2",
        "p_value": p2, "title": "真值上报通道健康度评估",
        "evidence": f"近{total_audit}条审计中 kernel.truth 事件 {truth_ok} 条",
        "suggest": "确认 X-DID 单头上报成功率高 → 失败自动重试 + 双通道兜底",
    })
    # P3: 账本追加合规
    non_zero = sum(1 for c in exit_codes.values() if c not in ("0", "?", ""))
    p3 = calc_p(0.6, 0.5, 0.1)
    proposals.append({
        "type": "optimize", "priority": "P3",
        "p_value": p3, "title": "账本退出码异常巡检",
        "evidence": f"账本尾部{total_ledger}行中非零退出码 {non_zero} 行",
        "suggest": "对非零退出码任务逐条归因 → 补齐 rollback 契约覆盖",
    })

    proposal = {
        "brain": "Ω-Brainμ-MVP-V0.1",
        "generated_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "did": "DID-BR-000002",
        "ontology": "Ω₀⊂⊙∞⊂Ω",
        "read_only": True,
        "inputs": {"audit_tail": total_audit, "ledger_tail": total_ledger},
        "proposals": proposals,
    }
    path = os.path.join(OUT, f"brain-proposal-{now}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(proposal, f, ensure_ascii=False, indent=2)
    return proposal, path

if __name__ == "__main__":
    prop, path = analyze()
    print(json.dumps(prop["proposals"], ensure_ascii=False, indent=1))
    print(f"\n提案已写入: {path}")
