#!/usr/bin/env python3
"""evolve.py — 自治进化提炼引擎

从任务台账 + 联邦记忆池 + 锁档清单中自动提取：
  1. 新任务范式 (paradigm)
  2. Badcase 规则 (rule)
  3. 新流水线 SOP (sop)
  4. 资产模板 (template)

输出到 /zongyuan-yuanji/var/evolve/ 目录。
"""

import json
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/zongyuan-yuanji")
TASKS = ROOT / "var" / "tasks"
SFMP = ROOT / "var" / "sfmp"
OUT = ROOT / "var" / "evolve"
OUT.mkdir(parents=True, exist_ok=True)

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"


def load_tasks():
    tasks = []
    for f in sorted(TASKS.glob("*.json")):
        try:
            tasks.append(json.loads(f.read_text()))
        except Exception:
            pass
    return tasks


# 从 name/cmd/result 字段推断任务类型
TYPE_PATTERNS = [
    (re.compile(r"扫描|scan|audit|巡检|patrol"), "inspection"),
    (re.compile(r"同步|sync|mirror|备份|backup"), "sync"),
    (re.compile(r"训练|train|微调|finetune|lora"), "training"),
    (re.compile(r"上报|report|truth|真值"), "truth_report"),
    (re.compile(r"共识|consensus|vote|投票"), "consensus"),
    (re.compile(r"记忆|memory|记忆库"), "memory"),
    (re.compile(r"部署|deploy|发布|publish"), "deploy"),
    (re.compile(r"节点|node|接入|bootstrap|admission"), "node_admission"),
    (re.compile(r"提取|extract|提炼|distill|seed"), "extract"),
    (re.compile(r"修复|fix|修复|recovery"), "fix"),
    (re.compile(r"监控|monitor|heartbeat|心跳"), "monitor"),
    (re.compile(r"归档|archive|归档"), "archive"),
    (re.compile(r"生成|generate|create|build"), "generate"),
]


def infer_type(task):
    """从 name/cmd/result 推断任务类型"""
    text = " ".join([
        str(task.get("name", "")),
        str(task.get("cmd", "")),
        str(task.get("result", "")),
        str(task.get("why", "")),
    ])
    for pat, ttype in TYPE_PATTERNS:
        if pat.search(text):
            return ttype
    return task.get("type", "unknown")


def extract_paradigms(tasks):
    """从任务中提取范式：按 type+status 分组，归纳共同模式"""
    paradigms = {}
    for t in tasks:
        ttype = infer_type(t)
        status = t.get("status", "unknown")
        key = f"{ttype}.{status}"
        paradigms.setdefault(key, {"type": ttype, "status": status, "count": 0, "sample_ids": []})
        paradigms[key]["count"] += 1
        if len(paradigms[key]["sample_ids"]) < 3:
            paradigms[key]["sample_ids"].append(t.get("id", "?"))
    return paradigms


def extract_badcase_rules(tasks):
    """从失败任务中提取 Badcase 规则"""
    rules = []
    seen = set()
    for t in tasks:
        if t.get("status") not in ("failed", "rejected", "error"):
            continue
        reason = t.get("reason", t.get("error", ""))
        result = str(t.get("result", ""))
        trigger = reason or result
        if not trigger:
            continue
        sig = _sha256(trigger)[:16]
        if sig in seen:
            continue
        seen.add(sig)
        rules.append({
            "rule_id": f"BADCASE-{sig}",
            "trigger": trigger[:200],
            "source_task": t.get("id", "?"),
            "type": infer_type(t),
            "extracted_at": _now(),
            "action": "reject_or_fix",
        })
    return rules


def extract_sops(tasks):
    """从成功任务中提取 SOP"""
    sops = {}
    for t in tasks:
        if t.get("status") != "done":
            continue
        ttype = infer_type(t)
        sops.setdefault(ttype, {"type": ttype, "count": 0, "sample_ids": []})
        sops[ttype]["count"] += 1
        if len(sops[ttype]["sample_ids"]) < 3:
            sops[ttype]["sample_ids"].append(t.get("id", "?"))
    return sops


def main():
    print("=" * 64)
    print("  evolve.py — 自治进化提炼引擎")
    print(f"  {ANCHOR} | {DID} | {_now()}")
    print("=" * 64)

    tasks = load_tasks()
    print(f"\n[输入] 任务台账: {len(tasks)} 条")

    paradigms = extract_paradigms(tasks)
    badcases = extract_badcase_rules(tasks)
    sops = extract_sops(tasks)

    print(f"[输出] 任务范式: {len(paradigms)} 类")
    for k, v in sorted(paradigms.items()):
        print(f"  {k}: {v['count']} 条")

    print(f"[输出] Badcase 规则: {len(badcases)} 条")
    for r in badcases:
        print(f"  {r['rule_id']}: {r['trigger'][:60]}...")

    print(f"[输出] 流水线 SOP: {len(sops)} 类")
    for k, v in sorted(sops.items()):
        print(f"  {k}: {v['count']} 条")

    # 写出
    out = {
        "generated_at": _now(),
        "anchor": ANCHOR,
        "did": DID,
        "source_tasks": len(tasks),
        "paradigms": paradigms,
        "badcase_rules": badcases,
        "sops": sops,
    }
    (OUT / "evolve.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    (OUT / "badcase_rules.json").write_text(
        json.dumps(badcases, ensure_ascii=False, indent=2))
    (OUT / "sop_registry.json").write_text(
        json.dumps(sops, ensure_ascii=False, indent=2))

    print(f"\n✓ 已写入: {OUT}/")
    print(f"  evolve.json      — 全量提炼结果")
    print(f"  badcase_rules.json — Badcase 规则库")
    print(f"  sop_registry.json  — 流水线 SOP 注册表")


if __name__ == "__main__":
    main()