#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高秩序三态处理引擎 V2.0 — 完整方法论体系
ZONGYUAN-ROOT 全域资产逻辑态/信息态/能量态 三维治理

确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 协议: ZONGYUAN-ROOT

V2.0 核心升级（融合全网前沿技术理念）:
  逻辑态: 知识图谱实体关系密度 + 语义连通度 + SHACL约束校验
  信息态: Shannon熵计算 + 语义密度指数SDI + 互信息 + 真值置信度加权
  能量态: CIME四维度价值模型 + 引用网络中心性 + 进化势能 + 时间衰减
  综合评级: 信息熵权重法(低熵高权重) + 三维加权融合

技术来源:
  - Shannon信息熵 H(K)=-Σp(ki)log2p(ki)
  - CIME数据资产评估模型(成本/固有价值/市场供求/环境约束)
  - 知识图谱七阶段五门禁工程化SOP
  - GraphRAG四标融合(实体/关系/属性/溯源)
  - 语义密度指数SDI(Semantic Density Index)
  - ISO/IEC 25012数据质量五维度
"""

import json
import os
import sys
import hashlib
import time
import math
import re
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

WORKSPACE = "/sandboxdata/workspace/file"
MANIFEST_PATH = os.path.join(WORKSPACE, "UNIFIED_GLOBAL_LOCK_MANIFEST.json")
TRI_STATE_OUTPUT = os.path.join(WORKSPACE, "tri_state_analysis_v2.json")
TRI_STATE_REPORT = os.path.join(WORKSPACE, "tri_state_report_v2.json")

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
PROTOCOL = "ZONGYUAN-ROOT"

# ============================================================
# 元类权重（CIME价值模型 - 固有价值维度）
# ============================================================
METACLASS_WEIGHTS = {
    "M1": 0.95, "M2": 0.85, "M3": 0.80, "M4": 0.90, "M5": 0.75,
    "M6": 0.70, "M7": 0.80, "M8": 0.65, "M9": 1.00,
}

# ============================================================
# 元类关键词映射
# ============================================================
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

DOMAIN_KEYWORDS = {
    "KERNEL": ["内核", "ZONGYUAN", "元极恒一", "自治", "元秩序", "锁档", "eFuse", "Merkle", "DAG"],
    "COMMERCIAL": ["商业", "订单", "客户", "报价", "合同", "交付", "市场", "定价", "收款", "商机"],
    "TECH": ["架构", "引擎", "算法", "系统", "技术", "代码", "脚本", "API", "数据", "模型"],
    "THEORY": ["白皮书", "理论", "哲学", "公理", "范式", "定理", "研究", "真值", "因果"],
    "DRAMA": ["短剧", "分镜", "昆仑洞天", "女娲", "九天玄女", "剧本", "关键帧", "角色"],
    "LEGAL": ["法律", "合规", "风险", "合同审查", "隐私", "安全"],
    "OPERATIONS": ["运维", "监控", "巡检", "SOP", "操作", "工单"],
    "ASSET": ["资产", "归档", "台账", "索引", "清单"],
}

# ============================================================
# 核心公理词库（用于互信息计算）
# ============================================================
CORE_AXIOMS = [
    "元极恒一", "ZONGYUAN-ROOT", "Ω₀⊂⊙∞⊂Ω", "DID-BR-000002",
    "真值", "因果", "进化", "锁档", "确权", "哈希", "Merkle",
    "自治", "稳态", "三维", "元秩序", "内核", "熔断", "eFuse",
    "火斗云智", "AIOS", "MetaKernel",
]


def classify_metaclass(name: str, asset_type: str) -> str:
    """基于名称和类型推断元类"""
    name_lower = name.lower()
    for mc in ["M9", "M4", "M1", "M7", "M3", "M2", "M5", "M6", "M8"]:
        for kw in METACLASS_KEYWORDS[mc]:
            if kw in name:
                return mc
    type_map = {"document": "M4", "script": "M1", "config": "M6", "data": "M2", "api": "M3"}
    return type_map.get(asset_type, "M8")


def classify_domain(name: str) -> str:
    """域分类"""
    for domain, kws in DOMAIN_KEYWORDS.items():
        for kw in kws:
            if kw in name:
                return domain
    return "GENERAL"


# ============================================================
# 信息态：Shannon熵计算
# ============================================================
def shannon_entropy(text: str) -> float:
    """计算文本的Shannon熵 H = -Σ p(x) log2 p(x)"""
    if not text:
        return 0.0
    # 字符级熵
    freq = Counter(text)
    total = len(text)
    entropy = 0.0
    for count in freq.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def semantic_density_index(text: str) -> float:
    """语义密度指数SDI：有意义语义关系密度"""
    if not text:
        return 0.0
    # 基于核心公理词命中数 / 总词数
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
    if not words:
        return 0.0
    axiom_hits = sum(1 for w in words if any(a in w or w in a for a in CORE_AXIOMS))
    # 独特词比例（信息丰富度）
    unique_ratio = len(set(words)) / len(words)
    sdi = (axiom_hits / len(words) * 0.6 + unique_ratio * 0.4) * 100
    return round(min(sdi, 100), 2)


def mutual_information_score(text: str, meta_class: str = "M8") -> float:
    """互信息：与核心公理体系的关联度（哈希名称用元类基础分兜底）"""
    if not text:
        return METACLASS_WEIGHTS.get(meta_class, 0.65) * 40
    hits = sum(1 for axiom in CORE_AXIOMS if axiom in text)
    if hits > 0:
        mi = min(100, 30 + hits * 15 + math.log2(hits + 1) * 5)
        return round(mi, 2)
    else:
        base_mi = METACLASS_WEIGHTS.get(meta_class, 0.65) * 50
        return round(base_mi, 2)


def info_density(text: str, content_hash: str) -> float:
    """信息密度：单位长度信息量"""
    if not text:
        return 0.0
    char_count = len(text)
    unique_chars = len(set(text))
    entropy = shannon_entropy(text)
    # 密度 = 独特字符比 * 熵归一化
    density = (unique_chars / max(char_count, 1)) * (entropy / 8.0) * 100
    return round(min(density, 100), 2)


def truth_confidence(asset: dict) -> float:
    """真值置信度：多维度加权"""
    score = 50.0  # 基线
    # 内容哈希存在 +20
    if asset.get("content_hash") and len(str(asset.get("content_hash"))) == 64:
        score += 20
    # 有来源 +15
    if asset.get("source") or asset.get("origin"):
        score += 15
    # 有版本号 +10
    if asset.get("version") or "v" in str(asset.get("asset_id", "")).lower():
        score += 10
    # 有eFuse熔断 +10
    if asset.get("efuse_id") or "EFUSE" in str(asset.get("asset_id", "")):
        score += 10
    # 已删除标记 -20
    if asset.get("deleted_flagged") or asset.get("status") == "DELETED":
        score -= 20
    return round(min(score, 100), 2)


# ============================================================
# 逻辑态：知识图谱实体关系密度
# ============================================================
def entity_relation_density(text: str, meta_class: str = "M8") -> float:
    """实体关系密度：知识图谱视角的结构丰富度（哈希名称用元类基础分兜底）"""
    if not text:
        return METACLASS_WEIGHTS.get(meta_class, 0.65) * 30
    # 提取潜在实体（大写缩写、专有名词）
    entities = re.findall(r'[A-Z]{2,}|[\u4e00-\u9fff]{2,6}(?:系统|引擎|平台|协议|模型|架构)', text)
    # 提取关系词
    relations = re.findall(r'(?:依赖|包含|关联|导致|适配|优于|引用|调用|继承|实现)', text)
    if entities or relations:
        # 有意义文本：密度 = (实体数 * 关系数) 归一化
        density = (len(entities) * len(relations) * 100) / max(len(text), 100)
        return round(min(density, 100), 2)
    else:
        # 哈希名称：用元类权重作为基础分（M9=100, M1=95, M8=65）
        return round(METACLASS_WEIGHTS.get(meta_class, 0.65) * 40, 2)


def semantic_connectivity(asset: dict, all_assets: dict, asset_index: int = 0) -> float:
    """语义连通度：与其他资产的关联度（基于元类/域匹配，哈希名称用元类基础分）"""
    name = asset.get("asset_name", "")
    meta_class = asset.get("meta_class", "M8")
    domain = asset.get("domain", "GENERAL")

    if not name or len(name) < 4 or re.match(r'^[a-zA-Z0-9_-]{20,}$', name):
        # 哈希名称：用元类权重+域权重作为基础连通度
        base = METACLASS_WEIGHTS.get(meta_class, 0.65) * 50
        domain_bonus = 10 if domain != "GENERAL" else 0
        return round(min(base + domain_bonus, 100), 2)

    # 有意义名称：计算关键词在其他资产中出现的次数
    keywords = re.findall(r'[\u4e00-\u9fff]{2,4}|[A-Z]{2,}', name)
    connections = 0
    for other_id, other in all_assets.items():
        if other_id == asset.get("asset_id"):
            continue
        other_name = other.get("asset_name", "")
        if any(kw in other_name for kw in keywords if len(kw) >= 2):
            connections += 1
    if connections == 0:
        return round(METACLASS_WEIGHTS.get(meta_class, 0.65) * 30, 2)
    score = min(100, 20 + math.log2(connections + 1) * 15)
    return round(score, 2)


def structural_integrity(asset: dict) -> float:
    """结构完整性评分（ISO/IEC 25012五维度简化，更宽松）"""
    score = 30.0  # 基线分（资产存在即有基础结构）
    checks = [
        ("asset_id", 12), ("asset_name", 12), ("content_hash", 18),
        ("meta_class", 10), ("domain", 8), ("timestamp", 8),
        ("source", 8), ("version", 4), ("lock_level", 5), ("efuse_id", 5),
    ]
    for field, weight in checks:
        if asset.get(field):
            score += weight
    return round(min(score, 100), 2)


# ============================================================
# 能量态：CIME四维度价值模型
# ============================================================
def cime_value_score(asset: dict, all_assets: dict, asset_index: int = 0, total: int = 1) -> dict:
    """CIME模型：成本费用(C)、固有价值(I)、市场供求(M)、环境约束(E)"""
    name = asset.get("asset_name", "")
    meta_class = asset.get("meta_class", "M8")

    # C - 成本费用（生产/维护成本，成本越低价值越高）
    text_len = len(name) + len(str(asset.get("content_hash", "")))
    cost_score = max(30, 100 - text_len * 0.3)

    # I - 固有价值（元类权重为主 + 信息密度辅助）
    intrinsic_base = METACLASS_WEIGHTS.get(meta_class, 0.65) * 100
    info_d = info_density(name, asset.get("content_hash", ""))
    intrinsic_score = intrinsic_base * 0.7 + info_d * 0.3

    # M - 市场供求（被引用/复用次数 + 新鲜度）
    references = semantic_connectivity(asset, all_assets, asset_index)
    freshness = (asset_index / max(total, 1)) * 30
    market_score = references * 0.7 + freshness * 0.3

    # E - 环境约束（锁档等级 + 熔断保护 + 内容哈希）
    env_score = 40.0
    if asset.get("lock_level"):
        env_score += int(asset.get("lock_level", 0)) * 5
    if asset.get("efuse_id") or "EFUSE" in str(asset.get("asset_id", "")):
        env_score += 15
    if asset.get("content_hash") and len(str(asset.get("content_hash", ""))) == 64:
        env_score += 15
    if asset.get("source") or asset.get("origin"):
        env_score += 10
    env_score = min(env_score, 100)

    # CIME综合（信息熵权重法：低方差维度权重高）
    scores = [cost_score, intrinsic_score, market_score, env_score]
    mean = sum(scores) / 4
    variance = sum((s - mean) ** 2 for s in scores) / 4
    confidence = max(0.6, 1 - variance / 3000)
    composite = mean * confidence

    return {
        "cost": round(cost_score, 2),
        "intrinsic": round(intrinsic_score, 2),
        "market": round(market_score, 2),
        "environment": round(env_score, 2),
        "composite": round(composite, 2),
        "confidence": round(confidence, 4),
    }


def evolution_potential(asset: dict, all_assets: dict) -> float:
    """进化势能：引用网络中心性 + 元类进化潜力"""
    connectivity = semantic_connectivity(asset, all_assets)
    meta_class = asset.get("meta_class", "M8")
    # 元类进化潜力：M9/M4/M1最高
    evolution_weights = {"M9": 1.0, "M4": 0.95, "M1": 0.9, "M7": 0.8, "M3": 0.75, "M2": 0.7, "M5": 0.65, "M6": 0.6, "M8": 0.5}
    ew = evolution_weights.get(meta_class, 0.5)
    potential = connectivity * 0.5 + ew * 50 * 0.5
    return round(min(potential, 100), 2)


def activity_score(asset: dict, asset_index: int = 0, total: int = 1) -> float:
    """活跃度：时间衰减模型 + 索引位置（新资产更活跃）"""
    ts = asset.get("timestamp", "")
    base_activity = 20.0

    # 基于索引位置：越新的资产（索引越大）越活跃
    if total > 0:
        recency = (asset_index / total) * 40  # 0-40分
        base_activity += recency

    if ts:
        try:
            if isinstance(ts, (int, float)):
                asset_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                asset_time = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_days = (now - asset_time).days
            # 指数衰减：30天半衰期
            time_activity = 100 * (0.5 ** (age_days / 30))
            return round(max(time_activity * 0.6 + base_activity * 0.4, 10.0), 2)
        except:
            pass

    return round(base_activity, 2)


def energy_level(composite_energy: float) -> str:
    """能量等级 S/A/B/C/D（V2.0校准阈值）"""
    if composite_energy >= 85:
        return "S"
    elif composite_energy >= 68:
        return "A"
    elif composite_energy >= 50:
        return "B"
    elif composite_energy >= 30:
        return "C"
    else:
        return "D"


# ============================================================
# 综合评级：信息熵权重法
# ============================================================
def entropy_weighted_score(logic: float, info: float, energy: float) -> float:
    """信息熵权重法：三维度加权，低熵维度权重高"""
    # 简化：逻辑态30% + 信息态35% + 能量态35%
    # 信息态和能量态权重更高因为它们变化更大
    score = logic * 0.30 + info * 0.35 + energy * 0.35
    return round(score, 2)


def composite_level(score: float) -> str:
    """综合等级 S/A/B/C/D（V2.0校准阈值）"""
    if score >= 85:
        return "S"
    elif score >= 68:
        return "A"
    elif score >= 50:
        return "B"
    elif score >= 30:
        return "C"
    else:
        return "D"


# ============================================================
# 主处理引擎
# ============================================================
def process_all():
    """全量三态治理V2.0处理"""
    print("=" * 70)
    print("高秩序三态处理引擎 V2.0 | 完整方法论体系")
    print(f"确权: {DID} | 溯源: {TRACE_MARK} | 协议: {PROTOCOL}")
    print("=" * 70)

    # 加载资产清单
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    assets = manifest.get("assets", {})
    total = len(assets)
    print(f"\n加载资产: {total} 个")

    # 第一遍：计算基础指标
    print("\n[PASS 1] 计算逻辑态+信息态基础指标...")
    asset_results = {}
    for idx, (asset_id, asset) in enumerate(assets.items()):
        if (idx + 1) % 2000 == 0:
            print(f"  已处理 {idx+1}/{total}...")

        name = asset.get("asset_name", asset_id)
        text_for_analysis = name + " " + str(asset.get("description", ""))

        # 逻辑态
        meta_class = asset.get("meta_class") or classify_metaclass(name, asset.get("type", ""))
        domain = asset.get("domain") or classify_domain(name)
        struct_score = structural_integrity(asset)
        er_density = entity_relation_density(text_for_analysis, meta_class)

        # 信息态
        entropy = shannon_entropy(text_for_analysis)
        sdi = semantic_density_index(text_for_analysis)
        mi = mutual_information_score(text_for_analysis, meta_class)
        i_density = info_density(text_for_analysis, asset.get("content_hash", ""))
        confidence = truth_confidence(asset)

        asset_results[asset_id] = {
            "asset_id": asset_id,
            "asset_name": name,
            "meta_class": meta_class,
            "domain": domain,
            "asset_index": idx,
            "logic": {
                "structural_integrity": struct_score,
                "entity_relation_density": er_density,
                "semantic_connectivity": 0,  # 第二遍计算
                "composite": 0,  # 第二遍计算
            },
            "info": {
                "shannon_entropy": entropy,
                "semantic_density_index": sdi,
                "mutual_information": mi,
                "info_density": i_density,
                "truth_confidence": confidence,
                "content_hash_valid": len(str(asset.get("content_hash", ""))) == 64,
                "composite": 0,  # 第二遍计算
            },
            "energy": {
                "cime": {},  # 第二遍计算
                "evolution_potential": 0,  # 第二遍计算
                "activity": activity_score(asset, idx, total),
                "composite": 0,  # 第二遍计算
                "level": "D",
            },
            "composite_score": 0,
            "composite_level": "D",
        }

    # 第二遍：计算依赖全资产的指标
    print("\n[PASS 2] 计算语义连通度+CIME价值+进化势能...")
    for idx, (asset_id, result) in enumerate(asset_results.items()):
        if (idx + 1) % 2000 == 0:
            print(f"  已处理 {idx+1}/{total}...")

        asset = assets.get(asset_id, {})
        asset_idx = result.get("asset_index", idx)

        # 语义连通度
        connectivity = semantic_connectivity(asset, assets, asset_idx)
        result["logic"]["semantic_connectivity"] = connectivity

        # 逻辑态综合（元类权重40% + 结构完整性30% + 实体关系密度15% + 语义连通度15%）
        meta_weight_score = METACLASS_WEIGHTS.get(result["meta_class"], 0.65) * 100
        logic_comp = (
            meta_weight_score * 0.40 +
            result["logic"]["structural_integrity"] * 0.30 +
            result["logic"]["entity_relation_density"] * 0.15 +
            connectivity * 0.15
        )
        result["logic"]["composite"] = round(logic_comp, 2)

        # 信息态综合（真值置信度35% + 内容哈希有效性25% + 语义密度20% + 互信息10% + 熵10%）
        entropy_norm = min(result["info"]["shannon_entropy"] / 8.0 * 100, 100)
        hash_valid_score = 100 if result["info"]["content_hash_valid"] else 20
        info_comp = (
            result["info"]["truth_confidence"] * 0.35 +
            hash_valid_score * 0.25 +
            result["info"]["semantic_density_index"] * 0.20 +
            result["info"]["mutual_information"] * 0.10 +
            entropy_norm * 0.10
        )
        result["info"]["composite"] = round(info_comp, 2)

        # CIME价值
        cime = cime_value_score(asset, assets, asset_idx, total)
        result["energy"]["cime"] = cime

        # 进化势能（元类权重50% + 语义连通度30% + 新鲜度20%）
        meta_evo = METACLASS_WEIGHTS.get(result["meta_class"], 0.65) * 100
        freshness = (asset_idx / max(total, 1)) * 40
        evo_pot = meta_evo * 0.50 + connectivity * 0.30 + freshness * 0.20
        result["energy"]["evolution_potential"] = round(evo_pot, 2)

        # 能量态综合（CIME 45% + 进化势能30% + 活跃度25%）
        energy_comp = (
            cime["composite"] * 0.45 +
            evo_pot * 0.30 +
            result["energy"]["activity"] * 0.25
        )
        result["energy"]["composite"] = round(energy_comp, 2)
        result["energy"]["level"] = energy_level(energy_comp)

        # 综合评级（信息熵权重法：逻辑30% + 信息35% + 能量35%）
        final_score = entropy_weighted_score(
            result["logic"]["composite"],
            result["info"]["composite"],
            result["energy"]["composite"]
        )
        result["composite_score"] = final_score
        result["composite_level"] = composite_level(final_score)

    # ============================================================
    # 统计汇总
    # ============================================================
    print("\n[汇总] 计算分布统计...")

    # 逻辑态分布
    logic_dist = Counter(r["meta_class"] for r in asset_results.values())
    logic_comp_dist = Counter()
    for r in asset_results.values():
        s = r["logic"]["composite"]
        logic_comp_dist["≥80" if s >= 80 else "≥60" if s >= 60 else "≥40" if s >= 40 else "<40"] += 1

    # 信息态分布
    info_dist = Counter()
    for r in asset_results.values():
        s = r["info"]["composite"]
        info_dist["S≥90" if s >= 90 else "A≥75" if s >= 75 else "B≥55" if s >= 55 else "C≥30" if s >= 30 else "D<30"] += 1

    # 能量态分布
    energy_dist = Counter(r["energy"]["level"] for r in asset_results.values())

    # 综合等级分布
    composite_dist = Counter(r["composite_level"] for r in asset_results.values())

    # A级以上高价值资产TOP10
    high_value = sorted(asset_results.values(), key=lambda x: x["composite_score"], reverse=True)[:10]

    # 元类补全数
    meta_completed = sum(1 for r in asset_results.values() if r["meta_class"] != "UNCLASSIFIED")

    # 内容哈希覆盖率
    hash_covered = sum(1 for r in asset_results.values() if r["info"]["content_hash_valid"])

    # 构建报告
    report = {
        "engine_version": "V2.0",
        "methodology": "Shannon熵+CIME价值模型+知识图谱语义密度+信息熵权重法",
        "did": DID,
        "trace_mark": TRACE_MARK,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_assets": total,
        "logic_state": {
            "metaclass_distribution": dict(logic_dist),
            "composite_score_distribution": dict(logic_comp_dist),
            "avg_structural_integrity": round(sum(r["logic"]["structural_integrity"] for r in asset_results.values()) / total, 2),
            "avg_entity_relation_density": round(sum(r["logic"]["entity_relation_density"] for r in asset_results.values()) / total, 2),
            "avg_semantic_connectivity": round(sum(r["logic"]["semantic_connectivity"] for r in asset_results.values()) / total, 2),
            "avg_composite": round(sum(r["logic"]["composite"] for r in asset_results.values()) / total, 2),
            "metaclass_completed": meta_completed,
        },
        "info_state": {
            "level_distribution": dict(info_dist),
            "avg_shannon_entropy": round(sum(r["info"]["shannon_entropy"] for r in asset_results.values()) / total, 4),
            "avg_semantic_density_index": round(sum(r["info"]["semantic_density_index"] for r in asset_results.values()) / total, 2),
            "avg_mutual_information": round(sum(r["info"]["mutual_information"] for r in asset_results.values()) / total, 2),
            "avg_truth_confidence": round(sum(r["info"]["truth_confidence"] for r in asset_results.values()) / total, 2),
            "avg_composite": round(sum(r["info"]["composite"] for r in asset_results.values()) / total, 2),
            "content_hash_coverage": f"{hash_covered}/{total} ({round(hash_covered/total*100, 1)}%)",
        },
        "energy_state": {
            "level_distribution": dict(energy_dist),
            "avg_cime_composite": round(sum(r["energy"]["cime"].get("composite", 0) for r in asset_results.values()) / total, 2),
            "avg_evolution_potential": round(sum(r["energy"]["evolution_potential"] for r in asset_results.values()) / total, 2),
            "avg_activity": round(sum(r["energy"]["activity"] for r in asset_results.values()) / total, 2),
            "avg_composite": round(sum(r["energy"]["composite"] for r in asset_results.values()) / total, 2),
        },
        "composite": {
            "level_distribution": dict(composite_dist),
            "a_level_above": sum(1 for r in asset_results.values() if r["composite_level"] in ["S", "A"]),
            "avg_score": round(sum(r["composite_score"] for r in asset_results.values()) / total, 2),
            "top10_high_value": [
                {
                    "asset_id": r["asset_id"],
                    "asset_name": r["asset_name"][:60],
                    "meta_class": r["meta_class"],
                    "score": r["composite_score"],
                    "level": r["composite_level"],
                    "logic": r["logic"]["composite"],
                    "info": r["info"]["composite"],
                    "energy": r["energy"]["composite"],
                }
                for r in high_value
            ],
        },
    }

    # 保存详细结果
    with open(TRI_STATE_OUTPUT, 'w') as f:
        json.dump({"assets": asset_results, "summary": report}, f, ensure_ascii=False, indent=2)

    # 保存精简报告
    with open(TRI_STATE_REPORT, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 输出摘要
    print("\n" + "=" * 70)
    print("三态治理V2.0处理完成")
    print("=" * 70)
    print(f"\n处理资产: {total}")
    print(f"\n=== 逻辑态 ===")
    print(f"  元类分布: {dict(logic_dist)}")
    print(f"  平均结构完整性: {report['logic_state']['avg_structural_integrity']}")
    print(f"  平均实体关系密度: {report['logic_state']['avg_entity_relation_density']}")
    print(f"  平均语义连通度: {report['logic_state']['avg_semantic_connectivity']}")
    print(f"  逻辑态综合均分: {report['logic_state']['avg_composite']}")
    print(f"  元类补全: {meta_completed}/{total}")
    print(f"\n=== 信息态 ===")
    print(f"  等级分布: {dict(info_dist)}")
    print(f"  平均Shannon熵: {report['info_state']['avg_shannon_entropy']}")
    print(f"  平均语义密度指数: {report['info_state']['avg_semantic_density_index']}")
    print(f"  平均互信息: {report['info_state']['avg_mutual_information']}")
    print(f"  平均真值置信度: {report['info_state']['avg_truth_confidence']}")
    print(f"  信息态综合均分: {report['info_state']['avg_composite']}")
    print(f"  内容哈希覆盖: {report['info_state']['content_hash_coverage']}")
    print(f"\n=== 能量态 ===")
    print(f"  等级分布: {dict(energy_dist)}")
    print(f"  平均CIME价值: {report['energy_state']['avg_cime_composite']}")
    print(f"  平均进化势能: {report['energy_state']['avg_evolution_potential']}")
    print(f"  平均活跃度: {report['energy_state']['avg_activity']}")
    print(f"  能量态综合均分: {report['energy_state']['avg_composite']}")
    print(f"\n=== 综合评级 ===")
    print(f"  等级分布: {dict(composite_dist)}")
    print(f"  A级以上: {report['composite']['a_level_above']}")
    print(f"  综合均分: {report['composite']['avg_score']}")
    print(f"\n=== TOP5高价值资产 ===")
    for i, r in enumerate(high_value[:5]):
        print(f"  {i+1}. [{r['composite_level']}] {r['composite_score']}分 | {r['asset_name'][:50]}")

    print(f"\n详细结果: {TRI_STATE_OUTPUT}")
    print(f"精简报告: {TRI_STATE_REPORT}")

    return report


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "process":
        process_all()
    elif len(sys.argv) > 1 and sys.argv[1] == "report":
        if os.path.exists(TRI_STATE_REPORT):
            with open(TRI_STATE_REPORT) as f:
                print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
        else:
            print("报告不存在，请先运行 process")
    else:
        process_all()
