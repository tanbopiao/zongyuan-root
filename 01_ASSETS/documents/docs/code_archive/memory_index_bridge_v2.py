#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 双轨记忆索引桥(术语词典增强版) (memory_index_bridge)
ZONGYUAN-ROOT 元极恒一自治体系 · 记忆闭环自动化 阶段2.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

目标：建立 云端记忆网关(truth_key) ↔ 本地M9账本(asset_id) 的统一双轨索引桥，
使两套语义同源但命名异构的体系首次可机器对账。

核心能力：
1. 三通道映射算法：Exact / Rule(前缀类别) / Semantic(文本相似)
2. 双轨索引桥 schema：bridge_id / truth_key / asset_id / mapping_method / confidence
3. 对账引擎：孤儿真值 / 本地独有资产 / 双轨已桥接 三维统计 + 漂移检测
4. 本地仿真模式：全内存运行，不触云，符合 AAB 双隔离
"""
import json
import re
import hashlib
from difflib import SequenceMatcher

# ============ 元信息 ============
BRIDGE_VERSION = "2.0.0"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

# ============ 1. 规则通道：类别映射表 ============
# 云端 truth_key 前缀 → 本地 meta_class / 语义词
TRUTH_KEY_CATEGORY_MAP = {
    "metalaw":   {"meta_class": "M9", "sem": ["元法", "公理", "law", "元规则"]},
    "lock":      {"meta_class": "M7", "sem": ["锁档", "快照", "lock"]},
    "deployment":{"meta_class": "M1", "sem": ["部署", "上线", "deploy"]},
    "service":   {"meta_class": "M1", "sem": ["服务", "网关", "service"]},
    "meta":      {"meta_class": "M4", "sem": ["元", "meta"]},
    "operator":  {"meta_class": "M1", "sem": ["算子", "operator"]},
    "architecture":{"meta_class":"M4", "sem": ["架构", "architecture"]},
    "achievement":{"meta_class":"M3", "sem": ["成果", "achievement"]},
    "audit":     {"meta_class": "M7", "sem": ["审计", "对账", "audit"]},
    "asset":     {"meta_class": "M7", "sem": ["资产", "asset"]},
    "resource":  {"meta_class": "M5", "sem": ["资源", "resource"]},
    "optimization":{"meta_class":"M1","sem": ["优化", "optim"]},
    "decision":  {"meta_class": "M2", "sem": ["决策", "decision"]},
    "monitoring": {"meta_class":"M1","sem": ["监控", "monitor"]},
    "local":     {"meta_class": "M5", "sem": ["本地", "local"]},
    "index":     {"meta_class": "M7", "sem": ["索引", "index"]},
    "nl2action": {"meta_class": "M1", "sem": ["指令", "nl", "action"]},
    "causal-engine":{"meta_class":"M6","sem": ["因果", "causal"]},
    "arbitration":{"meta_class":"M2","sem": ["仲裁", "arbit"]},
    "node":      {"meta_class": "M5", "sem": ["节点", "node"]},
    "assets":    {"meta_class": "M7", "sem": ["资产", "assets"]},
    "security":  {"meta_class": "M8", "sem": ["安全", "security"]},
    "status":    {"meta_class": "M5", "sem": ["状态", "status"]},
    "governance": {"meta_class":"M7","sem": ["治理", "govern"]},
    "identity":  {"meta_class": "M8", "sem": ["身份", "identity"]},
    "methodology":{"meta_class":"M4","sem": ["方法", "method"]},
    "test":      {"meta_class": "M1", "sem": ["测试", "test"]},
    "phase":     {"meta_class": "M5", "sem": ["阶段", "phase"]},
    "commercial": {"meta_class":"M3","sem": ["商业", "commercial"]},
    "strategy":  {"meta_class": "M2", "sem": ["策略", "strategy"]},
    "system":    {"meta_class": "M4", "sem": ["系统", "system"]},
    "protocol":  {"meta_class": "M9", "sem": ["协议", "protocol"]},
    "brand":     {"meta_class": "M4", "sem": ["品牌", "brand"]},
    "trace":     {"meta_class": "M4", "sem": ["溯源", "trace"]},
    "services":  {"meta_class": "M1", "sem": ["服务", "services"]},
    "product":   {"meta_class": "M3", "sem": ["产品", "product"]},
    "sync":      {"meta_class": "M7", "sem": ["同步", "sync"]},
    "sop":       {"meta_class": "M9", "sem": ["规程", "sop"]},
    "integration-test":{"meta_class":"M1","sem":["集成", "integration"]},
}

# 本地 KD-* 前缀 → 语义词
ASSET_PREFIX_SEM = {
    "KD-ALGO": ["算法", "架构", "算子", "部署", "服务", "对账", "映射"],
    "KD-THEO": ["理论", "体系", "方案", "文档", "协议", "机制", "架构"],
    "KD-KERN": ["内核", "锁档", "快照", "状态", "协议"],
    "KD-META": ["元", "架构", "体系", "公理"],
    "KD-AUTO": ["自治", "优化", "闭环", "进化", "成果"],
    "KD-PROD": ["产品", "成果", "商业", "网站", "资产"],
    "KD-INTE": ["集成", "测试", "接入", "对账"],
    "KD-INDEX":["索引", "资产", "目录", "清单", "台账"],
    "KD-DELIV":["交付", "成果", "产品", "发布"],
    "KD-INDU": ["行业", "知识"],
    "KD-MANIFEST":["清单", "清单", "索引", "资产"],
    "KD-ROOT": ["根", "内核", "协议"],
    "KD-OS":   ["系统", "操作系统", "内核"],
    "KD-ALGO-NEXUS": ["网关", "令牌", "Nexus", "部署"],
}

# 中英术语词典（P1 增强：truth_key body 词 → 中文语义锚点）
TERM_DICT = {
    "mechanism": ["机制", "机理"],
    "cloud": ["云", "云端", "云服务"],
    "loop": ["闭环", "循环"],
    "kernel": ["内核"],
    "execution": ["执行", "运行"],
    "gateway": ["网关", "入口"],
    "decision": ["决策"],
    "memory": ["记忆", "存储"],
    "api": ["接口", "api", "api服务"],
    "truth": ["真值", "真相"],
    "steady": ["稳态", "稳定"],
    "approval": ["审批", "审核"],
    "comm": ["通讯", "通信"],
    "proto": ["协议", "protocol"],
    "metalaw": ["元法", "公理", "元规则"],
    "evolution": ["进化", "演化", "自进化"],
    "local": ["本地"],
    "website": ["网站", "官网"],
    "health": ["健康", "体检", "状态"],
    "service": ["服务"],
    "meta": ["元", "元数据"],
    "closed": ["闭环", "关闭"],
    "platform": ["平台"],
    "unified": ["统一", "一体化"],
    "global": ["全域", "全局", "global"],
    "asset": ["资产"],
    "system": ["系统"],
    "index": ["索引", "目录"],
    "sop": ["规程", "流程", "sop"],
    "trace": ["溯源", "追踪"],
    "node": ["节点"],
    "nl2a": ["指令", "自然语言", "nl"],
    "integration": ["集成", "接入"],
    "deployed": ["部署", "上线"],
    "cross": ["跨", "交叉"],
    "session": ["会话", "窗口"],
    "snapshot": ["快照"],
    "baseline": ["基线", "基准"],
    "reconcile": ["对账", "归一", "对齐"],
    "semantic": ["语义"],
    "drift": ["漂移"],
    "fulltext": ["全文", "全量"],
    "transmutation": ["转译", "转化"],
    "operator": ["算子"],
    "scheduler": ["调度"],
    "arbitration": ["仲裁"],
    "identity": ["身份"],
    "security": ["安全"],
    "protocol": ["协议"],
    "governance": ["治理"],
    "manifest": ["清单", "索引"],
}

# ============ 2. 双轨索引桥 Schema ============
BRIDGE_SCHEMA = {
    "bridge_id": "str | BRIDGE-<n>",
    "truth_key": "str | 云端记忆网关键",
    "asset_id": "str | 本地账本资产ID",
    "mapping_method": "str | exact|rule|semantic",
    "confidence": "float | 0-1 置信度",
    "category": "str | 语义类别",
    "synced_at": "str | ISO时间",
}

# ============ 3. 映射算法 ============

def normalize_text(s: str) -> str:
    """文本归一：小写、去符号、去空白"""
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', s)
    return s


def extract_cloud_sem(tk: str) -> str:
    """提取云端 truth_key 语义词：取前缀后的主体 + 分段词"""
    parts = tk.split('.')
    head = parts[0]
    body = '.'.join(parts[1:]) if len(parts) > 1 else ''
    sem_words = re.split(r'[._-]', body)
    return head, ' '.join([w for w in sem_words if w])


def extract_asset_sem(asset_name: str) -> str:
    """提取账本资产名语义词（中文为主）"""
    if not asset_name:
        return ''
    return asset_name.lower()


def exact_match(cloud_key: str, assets) -> dict | None:
    """Exact 通道：truth_key 与 asset_name/asset_id 直接等价"""
    ck_norm = normalize_text(cloud_key)
    for a in assets:
        for field in ('asset_name', 'asset_id'):
            v = a.get(field, '')
            if v and normalize_text(v) == ck_norm:
                return {
                    "truth_key": cloud_key,
                    "asset_id": a["asset_id"],
                    "asset_name": a.get("asset_name", ""),
                    "mapping_method": "exact",
                    "confidence": 1.0,
                }
    return None


def rule_match(cloud_key: str, assets) -> dict | None:
    """Rule 通道：类别映射（truth_key 前缀 ↔ 本地 meta_class + 语义词）"""
    head, body_sem = extract_cloud_sem(cloud_key)
    cat = TRUTH_KEY_CATEGORY_MAP.get(head)
    if not cat:
        return None
    # 候选：同一 meta_class + 语义词包含度
    candidates = []
    for a in assets:
        if a.get('meta_class') != cat['meta_class']:
            continue
        an = normalize_text(a.get('asset_name', ''))
        # 计算 body 语义词与资产名交集
        score = 0.0
        for w in body_sem.split():
            if len(w) >= 3 and w in an:
                score += 0.4
        # 类别语义词命中
        for sw in cat['sem']:
            if normalize_text(sw) in an:
                score += 0.3
        if score > 0.3:
            candidates.append((score, a))
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    score, best = candidates[0]
    return {
        "truth_key": cloud_key,
        "asset_id": best["asset_id"],
        "asset_name": best.get("asset_name", ""),
        "mapping_method": "rule",
        "confidence": round(min(0.95, 0.4 + score), 3),
        "category": head,
    }


def semantic_match(cloud_key: str, assets) -> dict | None:
    """Semantic 通道 v2：术语词典 + 子串包含 + 前缀语义词 + 整串相似度"""
    head, body_sem = extract_cloud_sem(cloud_key)
    best_score = 0.0
    best = None
    for a in assets:
        an = a.get('asset_name', '')
        if not an:
            continue
        an_low = an.lower()
        # 1) 术语词典：body 词 → 中文锚点，命中资产名则加分
        dict_hit = 0.0
        for w in body_sem.split():
            wl = w.lower()
            if wl in TERM_DICT:
                for zw in TERM_DICT[wl]:
                    if zw.lower() in an_low:
                        dict_hit += 0.5
                        break
        # 2) 子串包含（英文词直配）
        substr_hit = 0.0
        for w in body_sem.split():
            wl = w.lower()
            if len(wl) >= 3 and wl in an_low:
                substr_hit += 0.4
        # 3) 前缀语义词（KD-* 类别）
        aid = a.get('asset_id', '')
        prefix_sem = []
        for p, sems in ASSET_PREFIX_SEM.items():
            if aid.startswith(p):
                prefix_sem = sems
                break
        cat_hit = 0.0
        for sw in prefix_sem:
            if sw.lower() in an_low:
                cat_hit += 0.2
        score = dict_hit + substr_hit + cat_hit
        # 4) 整串相似度弱补充
        sim = SequenceMatcher(None, body_sem, an).ratio()
        score = max(score, sim * 0.7)
        if score > best_score:
            best_score = score
            best = a
    if best and best_score >= 0.5:
        return {
            "truth_key": cloud_key,
            "asset_id": best["asset_id"],
            "asset_name": best.get("asset_name", ""),
            "mapping_method": "semantic",
            "confidence": round(min(0.95, 0.35 + best_score * 0.55), 3),
            "category": head,
        }
    return None


def build_bridge(cloud_keys: list, assets: list, thresh: float = 0.0) -> list:
    """三通道映射：exact > rule > semantic，取置信度最高的通道"""
    bridges = []
    used_assets = set()
    for ck in cloud_keys:
        m = exact_match(ck, assets)
        if m and m['asset_id'] not in used_assets:
            bridges.append(m)
            used_assets.add(m['asset_id'])
            continue
        m = rule_match(ck, assets)
        if m and m['asset_id'] not in used_assets and m['confidence'] >= thresh:
            bridges.append(m)
            used_assets.add(m['asset_id'])
            continue
        m = semantic_match(ck, assets)
        if m and m['asset_id'] not in used_assets and m['confidence'] >= thresh:
            bridges.append(m)
            used_assets.add(m['asset_id'])
    return bridges


# ============ 4. 对账引擎 ============
def reconcile(bridges: list, cloud_keys: set, assets: list) -> dict:
    bridged_keys = {b['truth_key'] for b in bridges}
    bridged_assets = {b['asset_id'] for b in bridges}
    orphan_truths = cloud_keys - bridged_keys
    local_only = {a['asset_id'] for a in assets} - bridged_assets
    return {
        "cloud_total": len(cloud_keys),
        "ledger_total": len(assets),
        "bridged": len(bridges),
        "bridge_rate": round(len(bridges) / len(cloud_keys) * 100, 1),
        "orphan_truths": len(orphan_truths),
        "local_only_assets": len(local_only),
        "drift_level": classify_drift(len(bridges) / max(1, len(cloud_keys))),
    }


def classify_drift(rate: float) -> str:
    """桥接率漂移等级：>80% GREEN / >60% YELLOW / >40% ORANGE / else RED"""
    if rate >= 0.8:
        return "GREEN"
    if rate >= 0.6:
        return "YELLOW"
    if rate >= 0.4:
        return "ORANGE"
    return "RED"


# ============ 5. 主入口（本地仿真） ============
if __name__ == "__main__":
    import sys
    ledger_path = "/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/locked/M9_global_ledger.json"
    cloud_path = "/tmp/cloud_truth_keys.txt"

    with open(ledger_path, encoding='utf-8') as f:
        ledger = json.load(f)
    assets = ledger.get('assets', [])
    with open(cloud_path, encoding='utf-8') as f:
        cloud_keys = [l.strip() for l in f if l.strip()]

    print(f"=== 双轨记忆索引桥 · 本地仿真 V{BRIDGE_VERSION} ===")
    print(f"DID: {DID} | {TRACE}")
    print(f"云端真值键: {len(cloud_keys)} | 本地账本资产: {len(assets)}")
    print()

    bridges = build_bridge(cloud_keys, assets)
    result = reconcile(bridges, set(cloud_keys), assets)
    print(f"桥接记录: {result['bridged']} | 桥接率: {result['bridge_rate']}% "
          f"| 漂移等级: {result['drift_level']}")
    print(f"孤儿真值(云端未桥接): {result['orphan_truths']} | "
          f"本地独有资产: {result['local_only_assets']}")
    print()
    print("=== 桥接样例(前15) ===")
    for b in bridges[:15]:
        print(f"  [{b['mapping_method']:<8} conf={b['confidence']:.2f}] "
              f"{b['truth_key'][:36]} → {b['asset_id']}")
    print()
    print("=== 方法分布 ===")
    from collections import Counter
    for m, n in Counter(b['mapping_method'] for b in bridges).most_common():
        print(f"  {m}: {n}")
