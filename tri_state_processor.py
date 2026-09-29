#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高秩序三态处理引擎 V1.0
ZONGYUAN-ROOT 全域资产逻辑态/信息态/能量态 三维治理

确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 协议: ZONGYUAN-ROOT

三态定义:
  逻辑态(Logic State): 元类归属、层级、域、关系、结构完整性
  信息态(Info State): 内容哈希、信息密度、真值置信度、信息熵
  能量态(Energy State): 活跃度、价值密度、进化势能、能量等级

使用:
  python3 tri_state_processor.py process
  python3 tri_state_processor.py report
"""

import json
import os
import sys
import hashlib
import time
import argparse
from datetime import datetime, timezone
from collections import Counter, defaultdict

WORKSPACE = "/home/user/.super_doubao/super-doubao-runtime/workspace"
MANIFEST_PATH = os.path.join(WORKSPACE, "UNIFIED_GLOBAL_LOCK_MANIFEST.json")
TRI_STATE_OUTPUT = os.path.join(WORKSPACE, "tri_state_analysis.json")
TRI_STATE_REPORT = os.path.join(WORKSPACE, "tri_state_report.json")

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
PROTOCOL = "ZONGYUAN-ROOT"

# 元类权重（能量态价值密度计算用）
METACLASS_WEIGHTS = {
    "M1": 0.95,  # 算法架构层 - 高价值
    "M2": 0.85,  # 数据模型层
    "M3": 0.80,  # 接口协议层
    "M4": 0.90,  # 理论体系层 - 高价值
    "M5": 0.75,  # 应用产线层
    "M6": 0.70,  # 运维治理层
    "M7": 0.80,  # 安全合规层
    "M8": 0.65,  # 业务逻辑层 - 量大
    "M9": 1.00,  # 元秩序层 - 最高价值
}

# 元类关键词映射（用于补全unknown元类）
METACLASS_KEYWORDS = {
    "M1": ["架构", "引擎", "算法", "系统", "设计", "拓扑", "内核", "DAG", "多链", "协议栈", "技术底座"],
    "M2": ["数据结构", "Schema", "模型", "字段", "表结构", "数据模型"],
    "M3": ["接口", "API", "协议", "规范", "标准", "CLI", "连接器"],
    "M4": ["白皮书", "理论", "体系", "哲学", "公理", "范式", "定理", "研究", "分析报告"],
    "M5": ["产品", "应用", "方案", "产线", "落地", "实施"],
    "M6": ["运维", "治理", "监控", "巡检", "SOP", "操作手册", "作业指导"],
    "M7": ["安全", "合规", "风险", "法律", "合同审查", "隐私", "防护"],
    "M8": ["业务", "流程", "商业", "订单", "客户", "报价", "合同", "工单", "交付", "市场"],
    "M9": ["元秩序", "锁档", "确权", "哈希", "eFuse", "内核快照", "自治", "元极恒一", "ZONGYUAN-ROOT", "全域锁档", "回执"],
}

# 域分类
DOMAIN_KEYWORDS = {
    "KERNEL": ["内核", "ZONGYUAN", "元极恒一", "自治", "元秩序", "锁档", "eFuse", "Merkle", "DAG", "多链"],
    "COMMERCIAL": ["商业", "订单", "客户", "报价", "合同", "交付", "市场", "定价", "收款", "商机", "线索"],
    "TECH": ["架构", "引擎", "算法", "系统", "技术", "代码", "脚本", "API", "数据", "模型"],
    "THEORY": ["白皮书", "理论", "哲学", "公理", "范式", "定理", "研究", "真值", "因果"],
    "DRAMA": ["短剧", "分镜", "昆仑洞天", "女娲", "九天玄女", "剧本", "关键帧", "角色"],
    "LEGAL": ["法律", "合规", "风险", "合同审查", "隐私", "安全"],
    "OPERATIONS": ["运维", "监控", "巡检", "SOP", "操作", "工单"],
    "ASSET": ["资产", "归档", "台账", "索引", "清单"],
}


def classify_metaclass(name: str, asset_type: str) -> str:
    """基于名称和类型推断元类"""
    name_lower = name.lower()
    # 优先匹配高优先级元类
    for mc in ["M9", "M4", "M1", "M7", "M3", "M2", "M5", "M6", "M8"]:
        for kw in METACLASS_KEYWORDS.get(mc, []):
            if kw.lower() in name_lower:
                return mc
    # 基于类型兜底
    if "folder" in asset_type:
        return "M9"  # 文件夹归为元秩序/资产组织
    if "bitable" in asset_type or "sheet" in asset_type:
        return "M8"  # 表格归为业务数据
    if "slides" in asset_type:
        return "M4"  # 演示归为理论/展示
    return "M8"  # 默认业务逻辑层


def classify_domain(name: str) -> str:
    """基于名称推断域归属"""
    name_lower = name.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return domain
    return "GENERAL"


def calc_logic_state(asset: dict, aid: str) -> dict:
    """计算逻辑态"""
    name = asset.get("name", "")
    asset_type = asset.get("asset_type", "")
    meta_class = asset.get("meta_class", "")
    meta_class_name = asset.get("meta_class_name", "")
    hierarchy_level = asset.get("hierarchy_level", "")
    domain = asset.get("domain", "")
    rev_count = asset.get("rev_count", 0)

    # 补全元类
    if not meta_class or meta_class == "unknown":
        meta_class = classify_metaclass(name, asset_type)
        meta_class_inferred = True
    else:
        meta_class_inferred = False

    # 补全域
    if not domain:
        domain = classify_domain(name)
        domain_inferred = True
    else:
        domain_inferred = False

    # 补全层级
    if not hierarchy_level:
        if meta_class == "M9":
            hierarchy_level = "L0-ROOT"
        elif meta_class in ("M1", "M4"):
            hierarchy_level = "L1-CORE"
        elif meta_class in ("M2", "M3", "M7"):
            hierarchy_level = "L2-FOUNDATION"
        elif meta_class in ("M5", "M6", "M8"):
            hierarchy_level = "L3-APPLICATION"
        else:
            hierarchy_level = "L4-INSTANCE"
        hierarchy_inferred = True
    else:
        hierarchy_inferred = False

    # 逻辑完整性评分（0-100）
    completeness = 100
    if meta_class_inferred: completeness -= 10
    if domain_inferred: completeness -= 5
    if hierarchy_inferred: completeness -= 5
    if rev_count == 0: completeness -= 5
    completeness = max(0, completeness)

    return {
        "meta_class": meta_class,
        "meta_class_name": meta_class_name or _metaclass_name(meta_class),
        "meta_class_inferred": meta_class_inferred,
        "domain": domain,
        "domain_inferred": domain_inferred,
        "hierarchy_level": hierarchy_level,
        "hierarchy_inferred": hierarchy_inferred,
        "rev_count": rev_count,
        "logic_completeness": completeness,
        "logic_grade": _grade(completeness),
    }


def _metaclass_name(mc: str) -> str:
    names = {
        "M1": "算法架构层", "M2": "数据模型层", "M3": "接口协议层",
        "M4": "理论体系层", "M5": "应用产线层", "M6": "运维治理层",
        "M7": "安全合规层", "M8": "业务逻辑层", "M9": "元秩序层",
    }
    return names.get(mc, "未知")


def calc_info_state(asset: dict, aid: str) -> dict:
    """计算信息态"""
    content_hash = asset.get("content_hash", "")
    content_size = asset.get("content_size", 0)
    content_type = asset.get("content_type", "")
    hash_confidence = asset.get("hash_confidence", 0)
    hash_type = asset.get("hash_type", "")
    asset_hash = asset.get("asset_hash", "")
    name = asset.get("name", "")

    has_content_hash = bool(content_hash and len(str(content_hash)) > 10)
    has_asset_hash = bool(asset_hash and len(str(asset_hash)) > 10)

    # 信息密度评分（0-100）：基于内容大小和类型
    if content_size and content_size > 0:
        # 对数归一化：1KB=20, 10KB=40, 100KB=60, 1MB=80, 10MB+=100
        import math
        density = min(100, 20 + 20 * math.log10(max(1, content_size / 1024)))
    else:
        density = 30  # 无内容大小的默认低分

    # 真值置信度
    if isinstance(hash_confidence, (int, float)):
        confidence = float(hash_confidence)
    elif hash_confidence:
        confidence = 80.0
    else:
        confidence = 50.0

    # 信息完整性
    info_completeness = 100
    if not has_content_hash: info_completeness -= 20
    if not has_asset_hash: info_completeness -= 10
    if not content_size: info_completeness -= 10
    if confidence < 70: info_completeness -= 10
    info_completeness = max(0, info_completeness)

    # 信息独特性（基于名称哈希的伪熵）
    name_hash = hashlib.sha256(name.encode('utf-8')).hexdigest()
    uniqueness = int(name_hash[:2], 16) / 255 * 100  # 0-100伪随机分布

    return {
        "has_content_hash": has_content_hash,
        "has_asset_hash": has_asset_hash,
        "content_size": content_size or 0,
        "content_type": content_type,
        "hash_confidence": confidence,
        "hash_type": hash_type,
        "information_density": round(density, 1),
        "information_completeness": info_completeness,
        "information_uniqueness": round(uniqueness, 1),
        "info_grade": _grade(info_completeness),
    }


def calc_energy_state(asset: dict, logic: dict, info: dict, aid: str) -> dict:
    """计算能量态"""
    meta_class = logic["meta_class"]
    rev_count = logic.get("rev_count", 0)
    mtime = asset.get("mtime", "")
    locked_at = asset.get("locked_at", "")
    deleted = asset.get("deleted", False)
    name = asset.get("name", "")

    # 元类权重
    mc_weight = METACLASS_WEIGHTS.get(meta_class, 0.5)

    # 活跃度评分（0-100）：基于修订次数和时间新鲜度
    activity = min(100, rev_count * 15)
    # 时间新鲜度加成
    if mtime:
        try:
            mtime_ts = int(mtime) if str(mtime).isdigit() else 0
            if mtime_ts > 0:
                age_days = (time.time() - mtime_ts) / 86400
                freshness = max(0, 100 - age_days * 2)
                activity = (activity + freshness) / 2
        except:
            pass

    # 价值密度 = 元类权重 × 信息密度 × 活跃度 / 100
    value_density = mc_weight * info["information_density"] * max(10, activity) / 100
    value_density = min(100, value_density)

    # 进化势能：核心资产（M9/M1/M4）+ 高活跃度 + 被引用
    evolution_potential = 0
    if meta_class in ("M9", "M1", "M4"):
        evolution_potential += 30
    if activity > 50:
        evolution_potential += 20
    if info["information_completeness"] > 80:
        evolution_potential += 20
    if rev_count >= 2:
        evolution_potential += 15
    if not deleted:
        evolution_potential += 15
    evolution_potential = min(100, evolution_potential)

    # 综合能量评分
    energy_score = (activity * 0.3 + value_density * 0.4 + evolution_potential * 0.3)

    # 能量等级
    if energy_score >= 80:
        energy_level = "S"
    elif energy_score >= 60:
        energy_level = "A"
    elif energy_score >= 40:
        energy_level = "B"
    elif energy_score >= 20:
        energy_level = "C"
    else:
        energy_level = "D"

    return {
        "activity_score": round(activity, 1),
        "value_density": round(value_density, 1),
        "evolution_potential": round(evolution_potential, 1),
        "energy_score": round(energy_score, 1),
        "energy_level": energy_level,
        "is_deleted": deleted,
    }


def _grade(score: float) -> str:
    if score >= 90: return "S"
    if score >= 75: return "A"
    if score >= 60: return "B"
    if score >= 40: return "C"
    return "D"


def process_all_assets():
    """执行全域三态处理"""
    start_time = time.time()
    print("=" * 70)
    print("高秩序三态处理引擎 V1.0")
    print("逻辑态 / 信息态 / 能量态 三维治理")
    print("=" * 70)

    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    assets = manifest.get("assets", {})
    total = len(assets)
    print(f"\n加载资产总数: {total}")

    tri_state_results = {}
    stats = {
        "logic": {"metaclass": Counter(), "domain": Counter(), "hierarchy": Counter(), "grade": Counter(), "inferred_metaclass": 0},
        "info": {"grade": Counter(), "has_content_hash": 0, "completeness_dist": Counter()},
        "energy": {"level": Counter(), "deleted": 0, "active": 0},
        "tri_state_grade": Counter(),
    }

    processed = 0
    for aid, asset in assets.items():
        if not isinstance(asset, dict):
            continue

        logic = calc_logic_state(asset, aid)
        info = calc_info_state(asset, aid)
        energy = calc_energy_state(asset, logic, info, aid)

        # 综合三态等级
        tri_score = (logic["logic_completeness"] + info["information_completeness"] + energy["energy_score"]) / 3
        tri_grade = _grade(tri_score)

        tri_state_results[aid] = {
            "asset_id": aid,
            "name": asset.get("name", ""),
            "asset_type": asset.get("asset_type", ""),
            "logic_state": logic,
            "information_state": info,
            "energy_state": energy,
            "tri_state_score": round(tri_score, 1),
            "tri_state_grade": tri_grade,
        }

        # 统计
        stats["logic"]["metaclass"][logic["meta_class"]] += 1
        stats["logic"]["domain"][logic["domain"]] += 1
        stats["logic"]["hierarchy"][logic["hierarchy_level"]] += 1
        stats["logic"]["grade"][logic["logic_grade"]] += 1
        if logic["meta_class_inferred"]:
            stats["logic"]["inferred_metaclass"] += 1

        stats["info"]["grade"][info["info_grade"]] += 1
        if info["has_content_hash"]:
            stats["info"]["has_content_hash"] += 1

        stats["energy"]["level"][energy["energy_level"]] += 1
        if energy["is_deleted"]:
            stats["energy"]["deleted"] += 1
        else:
            stats["energy"]["active"] += 1

        stats["tri_state_grade"][tri_grade] += 1

        processed += 1
        if processed % 2000 == 0:
            print(f"  已处理 {processed}/{total}...")

    elapsed = time.time() - start_time

    # 保存详细结果
    output = {
        "process_id": f"TRISTATE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "did": DID,
        "trace_mark": TRACE_MARK,
        "engine_version": "V1.0",
        "total_assets": total,
        "processed": processed,
        "elapsed_seconds": round(elapsed, 2),
        "statistics": {
            "logic_state": {
                "metaclass_distribution": dict(stats["logic"]["metaclass"]),
                "domain_distribution": dict(stats["logic"]["domain"]),
                "hierarchy_distribution": dict(stats["logic"]["hierarchy"]),
                "grade_distribution": dict(stats["logic"]["grade"]),
                "inferred_metaclass_count": stats["logic"]["inferred_metaclass"],
            },
            "information_state": {
                "grade_distribution": dict(stats["info"]["grade"]),
                "has_content_hash": stats["info"]["has_content_hash"],
                "content_hash_coverage": round(stats["info"]["has_content_hash"] / total * 100, 1),
            },
            "energy_state": {
                "level_distribution": dict(stats["energy"]["level"]),
                "active_count": stats["energy"]["active"],
                "deleted_count": stats["energy"]["deleted"],
            },
            "tri_state_grade_distribution": dict(stats["tri_state_grade"]),
        },
        "assets": tri_state_results,
    }

    with open(TRI_STATE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 生成精简报告
    report = _generate_report(output)
    with open(TRI_STATE_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 70}")
    print(f"三态处理完成 | 处理: {processed} | 耗时: {elapsed:.1f}s")
    print(f"{'=' * 70}")
    print(f"\n=== 逻辑态分布 ===")
    for mc, c in sorted(stats["logic"]["metaclass"].items()):
        print(f"  {mc}({_metaclass_name(mc)}): {c} ({c/total*100:.1f}%)")
    print(f"  元类补全: {stats['logic']['inferred_metaclass']} 个")
    print(f"\n=== 信息态分布 ===")
    for g, c in sorted(stats["info"]["grade"].items()):
        print(f"  {g}级: {c} ({c/total*100:.1f}%)")
    print(f"  内容哈希覆盖: {stats['info']['has_content_hash']}/{total} ({stats['info']['has_content_hash']/total*100:.1f}%)")
    print(f"\n=== 能量态分布 ===")
    for lvl, c in sorted(stats["energy"]["level"].items()):
        print(f"  {lvl}级: {c} ({c/total*100:.1f}%)")
    print(f"  活跃: {stats['energy']['active']} | 已删除: {stats['energy']['deleted']}")
    print(f"\n=== 三态综合等级 ===")
    for g, c in sorted(stats["tri_state_grade"].items()):
        print(f"  {g}级: {c} ({c/total*100:.1f}%)")
    print(f"\n详细结果: {TRI_STATE_OUTPUT}")
    print(f"精简报告: {TRI_STATE_REPORT}")
    return output


def _generate_report(output: dict) -> dict:
    """生成精简报告"""
    stats = output["statistics"]
    # 找出S级和A级资产
    s_assets = []
    a_assets = []
    for aid, data in output["assets"].items():
        if data["tri_state_grade"] == "S":
            s_assets.append({"id": aid, "name": data["name"][:50], "score": data["tri_state_score"], "energy": data["energy_state"]["energy_level"]})
        elif data["tri_state_grade"] == "A":
            a_assets.append({"id": aid, "name": data["name"][:50], "score": data["tri_state_score"], "energy": data["energy_state"]["energy_level"]})

    s_assets.sort(key=lambda x: -x["score"])
    a_assets.sort(key=lambda x: -x["score"])

    return {
        "report_id": output["process_id"],
        "timestamp": output["timestamp"],
        "total_assets": output["total_assets"],
        "elapsed_seconds": output["elapsed_seconds"],
        "summary": {
            "logic": stats["logic_state"],
            "information": stats["information_state"],
            "energy": stats["energy_state"],
            "tri_state_grade": stats["tri_state_grade_distribution"],
        },
        "top_s_assets": s_assets[:20],
        "top_a_assets": a_assets[:20],
        "recommendations": _generate_recommendations(stats),
    }


def _generate_recommendations(stats: dict) -> list:
    """生成治理建议"""
    recs = []
    logic = stats["logic_state"]
    info = stats["information_state"]
    energy = stats["energy_state"]

    if logic["inferred_metaclass_count"] > 0:
        recs.append(f"补全了{logic['inferred_metaclass_count']}个资产的元类归属，建议人工复核高价值资产的元类标注")

    ch_coverage = info["content_hash_coverage"]
    if ch_coverage < 100:
        recs.append(f"内容哈希覆盖率{ch_coverage}%，建议对缺失内容哈希的资产执行D2-T1全量内容哈希覆盖任务")

    d_count = energy["level_distribution"].get("D", 0)
    if d_count > 100:
        recs.append(f"D级低能量资产{d_count}个，建议评估是否归档或清理，释放索引空间")

    s_count = energy["level_distribution"].get("S", 0)
    if s_count > 0:
        recs.append(f"S级高能量资产{s_count}个，建议优先保护、高频备份、纳入核心资产白名单")

    recs.append("建议将三态标注结果写入资产清单，作为后续资产调度、进化优先级、价值评估的基础数据")
    return recs


def main():
    parser = argparse.ArgumentParser(description="高秩序三态处理引擎 V1.0")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("process", help="执行全域三态处理")
    subparsers.add_parser("report", help="查看处理报告")
    args = parser.parse_args()

    if args.command == "process":
        process_all_assets()
    elif args.command == "report":
        if os.path.exists(TRI_STATE_REPORT):
            with open(TRI_STATE_REPORT) as f:
                print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
        else:
            print("报告不存在，请先执行 process")
    else:
        process_all_assets()


if __name__ == "__main__":
    main()
