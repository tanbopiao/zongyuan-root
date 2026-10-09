#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0-真值生命周期管理引擎 (TRUTH-LIFECYCLE-001)
对全域锁档清单资产执行反熵分级：活跃/休眠/归档/淘汰候选
原则：哈希链不可变——不删除，仅标记生命周期状态；淘汰候选需人工确认
产出：truth_lifecycle_report.json + 分级统计
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
"""
import json, time, datetime, hashlib

MANIFEST = "/home/user/.super_doubao/super-doubao-runtime/workspace/UNIFIED_GLOBAL_LOCK_MANIFEST.json"
OUT = "/home/user/Doubao/chats/38437335960673794/health_snapshots/truth_lifecycle_report.json"

NOW = time.time()
DAY = 86400

# 元类能量权重（M9元秩序最高）
META_ENERGY = {"M9":5, "M4":4, "M1":4, "M5":3, "M3":3, "M2":3, "M7":3, "M6":2, "M8":2}

def days_ago(ts):
    try:
        return max(0, (NOW - float(ts)) / DAY)
    except:
        return None

def classify(a):
    meta = a.get("meta_class","M8")
    deleted = a.get("deleted", False)
    no_content = a.get("content_hash","") in ("LEGACY_NO_CONTENT_HASH","","NONE") or a.get("content_size",0)==0
    trust = a.get("event_trust_level") in (True,"TRUE","true")
    mtime = a.get("mtime")
    age = days_ago(mtime) if mtime else None
    meta_energy = META_ENERGY.get(meta,1)

    # 淘汰候选：已删除标记
    if deleted:
        return "ELIMINATED", 0
    # 归档：无内容 + 低价值 或 极旧
    if no_content and age is not None and age > 180:
        return "ARCHIVED", meta_energy
    if age is not None and age > 365:
        return "ARCHIVED", meta_energy
    # 休眠：180天内未更新但非高活跃
    if age is not None and age > 60:
        return "SLEEPING", meta_energy
    # 活跃：60天内更新或高价值
    if meta_energy >= 4 or trust:
        return "ACTIVE", meta_energy
    return "SLEEPING", meta_energy

def main():
    d = json.load(open(MANIFEST))
    assets = d["assets"]
    stats = {"ACTIVE":0,"SLEEPING":0,"ARCHIVED":0,"ELIMINATED":0}
    by_meta = {}
    samples = {"ACTIVE":[], "SLEEPING":[], "ARCHIVED":[], "ELIMINATED":[]}
    graded = 0
    for key, a in assets.items():
        cls, energy = classify(a)
        stats[cls] += 1
        graded += 1
        by_meta.setdefault(a.get("meta_class","?"), {}).setdefault(cls,0)
        by_meta[a.get("meta_class","?")][cls] += 1
        if len(samples[cls]) < 5:
            samples[cls].append({"id":key, "name":a.get("name","")[:40], "meta":a.get("meta_class"), "age_days":round(days_ago(a.get("mtime")) or 0,1)})

    total = sum(stats.values())
    report = {
        "report_id": "TRUTH-LIFECYCLE-001",
        "generated_at": datetime.datetime.now().isoformat(),
        "did": "DID-BR-000002", "omega": "Ω₀⊂⊙∞⊂Ω", "protocol": "ZONGYUAN-ROOT",
        "total_assets": total,
        "distribution": stats,
        "distribution_pct": {k: round(v/total*100,1) for k,v in stats.items()},
        "by_meta_class": by_meta,
        "entropy_verdict": (
            "反熵达标" if stats["ACTIVE"]>=total*0.4 and stats["ARCHIVED"]<=total*0.3
            else "需人工治理（归档/淘汰候选偏高或活跃不足）"
        ),
        "recommend": {
            "ACTIVE": "保留热存储+向量化检索",
            "SLEEPING": "降级存储，不参与高频检索",
            "ARCHIVED": "冷归档（保留哈希链），移出热区",
            "ELIMINATED": "淘汰候选，待人工确认后物理清理"
        },
        "samples": samples
    }
    with open(OUT,"w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    # 摘要
    print("=== P0 真值生命周期报告 ===")
    print(f"总资产: {total}")
    for k,v in stats.items():
        print(f"  {k}: {v} ({round(v/total*100,1)}%)")
    print("反熵判定:", report["entropy_verdict"])
    print("按元类分级:")
    for m,v in by_meta.items():
        print(f"  {m}: {v}")
    print("输出:", OUT)
    print("SHA256:", hashlib.sha256(open(OUT,'rb').read()).hexdigest())

if __name__ == "__main__":
    main()
