#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 本地根内核与云端内核比对引擎（R007）

功能：
  1. 本地根内核：基于 all_truths.json 全量真值库
  2. 云端内核：从真值库中 cloud.*/kernel.*/SFMP.* 类条目提取云端状态
  3. 比对维度：真值数量差异、哈希一致性、key覆盖率、类别对齐
  4. 漂移检测与修复建议
  5. 生成比对报告

使用方式：
  python3 kernel_comparison.py             # 执行比对
  python3 kernel_comparison.py --report     # 查看最近比对报告
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set, Tuple

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
COMPARISON_DIR = EVOLUTION_DIR / "kernel_comparison"
COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = COMPARISON_DIR / "comparison.log"
REPORT_FILE = COMPARISON_DIR / "report.json"

SERVICES_DIR = WORKSPACE / "scripts" / "services"
sys.path.insert(0, str(SERVICES_DIR))

DID_TAG = "DID-BR-000002"
META_RULES_FILE = WORKSPACE / "persistence_root" / "datalake_snapshot" / "shared_brain" / "rules" / "meta_rules.json"


def log(level: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def compute_truth_hash(truth: Dict[str, Any]) -> str:
    """计算单条真值的哈希（用于一致性校验）。"""
    content = json.dumps({
        "seq": truth.get("seq"),
        "key": truth.get("key"),
        "value": truth.get("value"),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def load_local_kernel() -> Dict[str, Any]:
    """加载本地根内核。"""
    try:
        from autonomous_kernel import AutonomousKernel
        kernel = AutonomousKernel()
        stats = kernel.get_stats()
        return {
            "source": "local_root_kernel",
            "truth_count": stats["total"],
            "categories": stats["categories"],
            "top_categories": stats["top_categories"],
            "seq_range": stats["seq_range"],
            "truths": kernel.truths,
            "kernel_obj": kernel,
        }
    except Exception as e:
        log("ERROR", f"本地内核加载失败: {e}")
        return {"truth_count": 0, "truths": [], "categories": 0}


def extract_cloud_kernel_truths(truths: List[Dict[str, Any]]) -> Dict[str, Any]:
    """从真值库中提取云端内核相关条目。"""
    cloud_prefixes = ["cloud.", "kernel.", "SFMP.", "probe.cloudstatus"]
    cloud_truths = []
    for t in truths:
        key = t.get("key", "")
        if any(key.startswith(prefix) for prefix in cloud_prefixes):
            cloud_truths.append(t)

    # 按类别分组
    cloud_categories = {}
    for t in cloud_truths:
        key = t["key"]
        cat = key
        for sep in [".", "_", "-"]:
            if sep in key:
                cat = key.split(sep)[0]
                break
        cloud_categories.setdefault(cat, []).append(t)

    return {
        "source": "cloud_kernel_extracted",
        "truth_count": len(cloud_truths),
        "categories": len(cloud_categories),
        "top_categories": sorted(
            [(k, len(v)) for k, v in cloud_categories.items()],
            key=lambda x: -x[1]
        )[:10],
        "truths": cloud_truths,
    }


def compare_kernels(local: Dict[str, Any], cloud: Dict[str, Any]) -> Dict[str, Any]:
    """比对本地根内核与云端内核。"""

    # 1. 真值数量差异
    local_count = local["truth_count"]
    cloud_count = cloud["truth_count"]
    count_diff = local_count - cloud_count

    # 2. key 覆盖率
    local_keys: Set[str] = {t["key"] for t in local.get("truths", [])}
    cloud_keys: Set[str] = {t["key"] for t in cloud.get("truths", [])}

    # 云端独有的 key（本地缺失）
    cloud_only_keys = cloud_keys - local_keys
    # 本地独有的 key（云端缺失）
    local_only_keys = local_keys - cloud_keys
    # 共有 key
    common_keys = cloud_keys & local_keys

    # 3. 哈希一致性（共有 key 的哈希比对）
    hash_mismatches = []
    local_hash_map = {t["key"]: compute_truth_hash(t) for t in local.get("truths", []) if t["key"] in common_keys}
    cloud_hash_map = {t["key"]: compute_truth_hash(t) for t in cloud.get("truths", []) if t["key"] in common_keys}

    for key in common_keys:
        if local_hash_map.get(key) != cloud_hash_map.get(key):
            hash_mismatches.append({
                "key": key[:60],
                "local_hash": local_hash_map.get(key),
                "cloud_hash": cloud_hash_map.get(key),
            })

    # 4. 类别对齐
    local_cats = set()
    for t in local.get("truths", []):
        k = t["key"]
        for sep in [".", "_", "-"]:
            if sep in k:
                local_cats.add(k.split(sep)[0])
                break
        else:
            local_cats.add(k)

    cloud_cats = set(c for c, _ in cloud.get("top_categories", []))
    cats_local_only = local_cats - cloud_cats
    cats_cloud_only = cloud_cats - local_cats

    # 5. 漂移检测
    drift_detected = False
    drift_items = []
    if abs(count_diff) > local_count * 0.1:  # 差异超过10%
        drift_detected = True
        drift_items.append(f"真值数量差异 {count_diff}（{(count_diff/local_count*100):.1f}%）")
    if len(hash_mismatches) > 0:
        drift_detected = True
        drift_items.append(f"哈希不一致 {len(hash_mismatches)} 条")
    if len(cloud_only_keys) > 5:
        drift_detected = True
        drift_items.append(f"本地缺失 {len(cloud_only_keys)} 个云端 key")

    # 6. 修复建议
    repair_actions = []
    if cloud_only_keys:
        repair_actions.append(f"从云端同步 {len(cloud_only_keys)} 条缺失真值到本地")
    if hash_mismatches:
        repair_actions.append(f"重新校验 {len(hash_mismatches)} 条哈希不一致真值")
    if len(local_only_keys) > 10:
        repair_actions.append(f"推送 {len(local_only_keys)} 条本地独有真值到云端")

    return {
        "comparison_time": datetime.now().isoformat(),
        "local_kernel": {
            "source": local["source"] if "source" in local else "local_root_kernel",
            "truth_count": local_count,
            "categories": local.get("categories", 0),
        },
        "cloud_kernel": {
            "source": cloud["source"],
            "truth_count": cloud_count,
            "categories": cloud["categories"],
        },
        "metrics": {
            "count_diff": count_diff,
            "count_diff_pct": round(abs(count_diff) / max(1, local_count) * 100, 1),
            "common_keys": len(common_keys),
            "local_only_keys": len(local_only_keys),
            "cloud_only_keys": len(cloud_only_keys),
            "hash_mismatches": len(hash_mismatches),
            "key_coverage_pct": round(len(common_keys) / max(1, len(cloud_keys)) * 100, 1),
            "category_alignment": len(local_cats & cloud_cats),
            "cats_local_only": len(cats_local_only),
            "cats_cloud_only": len(cats_cloud_only),
        },
        "drift": {
            "detected": drift_detected,
            "items": drift_items,
        },
        "repair_actions": repair_actions,
        "hash_mismatches_sample": hash_mismatches[:5],
        "did_tag": DID_TAG,
    }


def main():
    show_report = "--report" in sys.argv

    if show_report:
        if REPORT_FILE.exists():
            print(REPORT_FILE.read_text(encoding="utf-8"))
        else:
            print("暂无比对报告，请先执行比对")
        return 0

    log("INFO", "=" * 50)
    log("INFO", "本地根内核与云端内核比对引擎启动 (R007)")
    log("INFO", "=" * 50)

    # 加载元法则
    if META_RULES_FILE.exists():
        rules = json.loads(META_RULES_FILE.read_text(encoding="utf-8"))
        r007 = next((r for r in rules.get("rules", []) if r["id"] == "R007"), None)
        if r007:
            log("INFO", f"元法则 R007 约束: {r007['checks']}")
    else:
        log("WARN", "元法则文件未找到")

    # 1. 加载本地根内核
    log("INFO", "加载本地根内核...")
    local = load_local_kernel()
    log("INFO", f"本地根内核: {local['truth_count']} 条真值, {local.get('categories', 0)} 个类别")

    # 2. 提取云端内核
    log("INFO", "提取云端内核条目...")
    cloud = extract_cloud_kernel_truths(local.get("truths", []))
    log("INFO", f"云端内核: {cloud['truth_count']} 条真值, {cloud['categories']} 个类别")

    # 3. 比对
    log("INFO", "执行比对...")
    report = compare_kernels(local, cloud)

    # 4. 输出结果
    m = report["metrics"]
    log("INFO", f"数量差异: {m['count_diff']} ({m['count_diff_pct']}%)")
    log("INFO", f"共有key: {m['common_keys']}, 本地独有: {m['local_only_keys']}, 云端独有: {m['cloud_only_keys']}")
    log("INFO", f"哈希不一致: {m['hash_mismatches']}, key覆盖率: {m['key_coverage_pct']}%")
    log("INFO", f"类别对齐: {m['category_alignment']}, 本地独有类别: {m['cats_local_only']}, 云端独有类别: {m['cats_cloud_only']}")

    if report["drift"]["detected"]:
        log("WARN", f"检测到漂移: {report['drift']['items']}")
    else:
        log("INFO", "无漂移检测")

    if report["repair_actions"]:
        log("INFO", f"修复建议: {report['repair_actions']}")

    # 5. 保存报告
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log("INFO", f"比对报告已保存: {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(0)
