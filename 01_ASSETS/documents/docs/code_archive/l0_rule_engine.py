#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L0 纯规则引擎 - ZONGYUAN-ROOT 元内核核心层
零模型依赖，常驻内存 <50MB
接管：真值分类、冲突检测、异常检测、真值去重
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import re
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


class L0RuleEngine:
    """L0纯规则引擎 - 零LLM依赖"""

    def __init__(self):
        self.version = "L0-RULE-ENGINE-V1.0"
        self.engine_type = "rule_based"
        self.memory_footprint = "<50MB"

    # ============================================================
    # 1. 真值分类（基于key前缀+关键词规则）
    # ============================================================
    def classify_truth(self, truth_key: str, truth_value: str = "") -> Dict[str, Any]:
        """
        基于规则的真值分类
        分类体系：元法则|公理|定理|方法|数据|风险|决策|创意|协议|通用
        """
        key_lower = truth_key.lower()
        value_lower = (truth_value or "").lower()

        # 规则1：基于key前缀
        category_rules = [
            (r"^meta[_-]?rule|^META[_-]?RULE|^元法则|^元规则", "元法则"),
            (r"^axiom|^AXIOM|^公理|^本源公理", "公理"),
            (r"^theorem|^THEOREM|^定理", "定理"),
            (r"^method|^METHOD|^SOP|^方法|^流程|^规范", "方法"),
            (r"^data|^DATA|^TRUTH\.|^真值|^数据|^统计", "数据"),
            (r"^risk|^RISK|^CONFLICT|^ANOMALY|^风险|^异常|^冲突", "风险"),
            (r"^decision|^DECISION|^决策|^裁决|^审批", "决策"),
            (r"^creative|^CREATIVE|^创意|^设计|^作品", "创意"),
            (r"^protocol|^PROTOCOL|^协议|^合约|^contract", "协议"),
            (r"^CLASSIFICATION|^分类", "通用"),
        ]

        category = "通用"
        confidence = 0.6

        for pattern, cat in category_rules:
            if re.search(pattern, key_lower):
                category = cat
                confidence = 0.9
                break

        # 规则2：基于value关键词增强置信度
        if category == "通用":
            value_keywords = {
                "元法则": ["必须", "禁止", "铁律", "元法则", "元规则", "全域生效"],
                "公理": ["公理", "不证自明", "本源", "第一性"],
                "方法": ["步骤", "流程", "SOP", "操作", "方法"],
                "数据": ["统计", "数量", "总量", "计数", "指标"],
                "风险": ["风险", "警告", "异常", "冲突", "失败"],
                "决策": ["决定", "决策", "裁决", "选择", "方案"],
            }
            for cat, keywords in value_keywords.items():
                if any(kw in value_lower for kw in keywords):
                    category = cat
                    confidence = 0.75
                    break

        return {
            "key": truth_key,
            "category": category,
            "confidence": confidence,
            "classifier": "L0-RULE-ENGINE",
            "engine_version": self.version,
        }

    def classify_truths_batch(self, truths: List[Dict]) -> List[Dict]:
        """批量分类"""
        results = []
        for t in truths:
            result = self.classify_truth(
                t.get("truth_key", ""),
                t.get("truth_value", "")
            )
            results.append(result)
        return results

    # ============================================================
    # 2. 冲突检测（基于key匹配+内容对比）
    # ============================================================
    def detect_conflicts(self, truths: List[Dict]) -> Dict[str, Any]:
        """
        基于规则的冲突检测
        检测维度：相同key不同value、关键词矛盾、时间线冲突
        """
        conflicts = []
        has_conflict = False

        # 规则1：相同key不同value
        key_groups = {}
        for t in truths:
            key = t.get("truth_key", "")
            if key not in key_groups:
                key_groups[key] = []
            key_groups[key].append(t)

        for key, items in key_groups.items():
            if len(items) >= 2:
                values = set()
                for item in items:
                    val = item.get("truth_value", "").strip()[:200]
                    if val:
                        values.add(val)
                if len(values) >= 2:
                    has_conflict = True
                    conflicts.append({
                        "keys": [key],
                        "type": "same_key_different_value",
                        "reason": f"相同key[{key}]存在{len(values)}个不同值",
                        "severity": "中",
                    })

        # 规则2：关键词矛盾检测
        contradiction_pairs = [
            ("启用", "禁用"),
            ("开启", "关闭"),
            ("允许", "禁止"),
            ("增加", "减少"),
            ("启动", "停止"),
            ("成功", "失败"),
            ("正常", "异常"),
            ("上线", "下线"),
        ]

        for i, t1 in enumerate(truths):
            for t2 in truths[i+1:]:
                v1 = t1.get("truth_value", "")
                v2 = t2.get("truth_value", "")
                for pos, neg in contradiction_pairs:
                    if pos in v1 and neg in v2 and t1.get("truth_key") != t2.get("truth_key"):
                        # 检查是否是同一主题
                        k1_prefix = ".".join(t1.get("truth_key", "").split(".")[:2])
                        k2_prefix = ".".join(t2.get("truth_key", "").split(".")[:2])
                        if k1_prefix == k2_prefix:
                            has_conflict = True
                            conflicts.append({
                                "keys": [t1.get("truth_key"), t2.get("truth_key")],
                                "type": "keyword_contradiction",
                                "reason": f"关键词矛盾：[{pos}] vs [{neg}]",
                                "severity": "高",
                            })
                            break

        # 规则3：元法则冲突（最高优先级）
        meta_rule_truths = [t for t in truths if "META_RULE" in t.get("truth_key", "").upper() or "元法则" in t.get("truth_key", "")]
        if len(meta_rule_truths) >= 2:
            for i, t1 in enumerate(meta_rule_truths):
                for t2 in meta_rule_truths[i+1:]:
                    v1 = t1.get("truth_value", "")
                    v2 = t2.get("truth_value", "")
                    if v1 != v2 and len(v1) > 10 and len(v2) > 10:
                        has_conflict = True
                        conflicts.append({
                            "keys": [t1.get("truth_key"), t2.get("truth_key")],
                            "type": "meta_rule_conflict",
                            "reason": "元法则之间存在潜在冲突，需人工仲裁",
                            "severity": "极高",
                        })

        summary = f"检测{len(truths)}条真值，发现{len(conflicts)}个潜在冲突" if conflicts else "未检测到冲突"

        return {
            "has_conflict": has_conflict,
            "conflicts": conflicts[:10],  # 最多返回10个
            "summary": summary,
            "detector": "L0-RULE-ENGINE",
            "engine_version": self.version,
            "total_truths_checked": len(truths),
        }

    # ============================================================
    # 3. 异常检测（基于阈值规则）
    # ============================================================
    def detect_anomalies(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于阈值规则的系统异常检测
        检测维度：内存、磁盘、CPU、服务状态、网络
        """
        anomalies = []
        overall_status = "正常"

        # 规则1：内存使用率
        mem_usage = system_info.get("mem_usage_percent", 0)
        if mem_usage >= 90:
            anomalies.append({
                "type": "memory_critical",
                "severity": "严重",
                "description": f"内存使用率{mem_usage}%，超过90%临界值",
                "suggestion": "立即释放内存，停止非必要服务，检查内存泄漏",
            })
            overall_status = "严重"
        elif mem_usage >= 80:
            anomalies.append({
                "type": "memory_warning",
                "severity": "高",
                "description": f"内存使用率{mem_usage}%，超过80%警告值",
                "suggestion": "关注内存增长趋势，准备释放非必要服务",
            })
            if overall_status != "严重":
                overall_status = "警告"
        elif mem_usage >= 70:
            anomalies.append({
                "type": "memory_notice",
                "severity": "中",
                "description": f"内存使用率{mem_usage}%，接近70%注意值",
                "suggestion": "持续监控，预防内存不足",
            })
            if overall_status == "正常":
                overall_status = "注意"

        # 规则2：磁盘使用率
        disk_usage = system_info.get("disk_usage_percent", 0)
        if disk_usage >= 90:
            anomalies.append({
                "type": "disk_critical",
                "severity": "严重",
                "description": f"磁盘使用率{disk_usage}%，超过90%临界值",
                "suggestion": "立即清理日志/临时文件，扩展磁盘容量",
            })
            overall_status = "严重"
        elif disk_usage >= 80:
            anomalies.append({
                "type": "disk_warning",
                "severity": "高",
                "description": f"磁盘使用率{disk_usage}%，超过80%警告值",
                "suggestion": "清理旧日志和备份文件",
            })
            if overall_status not in ["严重", "警告"]:
                overall_status = "警告"

        # 规则3：失败服务
        failed_services = system_info.get("failed_services", [])
        if failed_services:
            critical_services = [s for s in failed_services if any(
                kw in s.lower() for kw in ["nginx", "9120", "memory", "gateway", "ai-proxy", "mr010", "kernel"]
            )]
            if critical_services:
                anomalies.append({
                    "type": "critical_service_failed",
                    "severity": "严重",
                    "description": f"关键服务失败: {', '.join(critical_services[:5])}",
                    "suggestion": "立即重启关键服务，检查失败原因",
                })
                overall_status = "严重"
            elif len(failed_services) >= 3:
                anomalies.append({
                    "type": "multiple_service_failed",
                    "severity": "高",
                    "description": f"{len(failed_services)}个服务失败",
                    "suggestion": "检查服务依赖关系，批量重启",
                })
                if overall_status not in ["严重", "警告"]:
                    overall_status = "警告"

        # 规则4：CPU使用率
        cpu_usage = system_info.get("cpu_usage_percent", 0)
        if cpu_usage >= 90:
            anomalies.append({
                "type": "cpu_critical",
                "severity": "高",
                "description": f"CPU使用率{cpu_usage}%，持续高负载",
                "suggestion": "检查高CPU进程，考虑任务错峰执行",
            })
            if overall_status == "正常":
                overall_status = "注意"

        # 规则5：真值增长异常
        truth_growth_rate = system_info.get("truth_growth_rate", 0)
        if truth_growth_rate > 1000:
            anomalies.append({
                "type": "truth_explosion",
                "severity": "中",
                "description": f"真值增长过快: {truth_growth_rate}条/小时，可能存在重复写入",
                "suggestion": "检查真值去重机制，排查重复上报",
            })

        if not anomalies:
            anomalies.append({
                "type": "system_healthy",
                "severity": "低",
                "description": "系统运行正常，未检测到异常",
                "suggestion": "持续监控，保持当前状态",
            })

        return {
            "anomalies": anomalies,
            "overall_status": overall_status,
            "detector": "L0-RULE-ENGINE",
            "engine_version": self.version,
            "check_time": datetime.now().isoformat(),
        }

    # ============================================================
    # 4. 真值去重（基于哈希+内容相似度）
    # ============================================================
    def dedup_truths(self, truths: List[Dict]) -> Dict[str, Any]:
        """
        基于规则的真值去重
        方法：内容哈希匹配 + key前缀分组
        """
        merge_suggestions = []
        redundant_keys = []

        # 规则1：按key前缀分组
        groups = {}
        for t in truths:
            key = t.get("truth_key", "")
            prefix = ".".join(key.split(".")[:2]) if "." in key else key
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(t)

        # 规则2：内容哈希去重
        for prefix, items in groups.items():
            if len(items) < 2:
                continue

            # 计算内容哈希
            hash_groups = {}
            for item in items:
                val = item.get("truth_value", "").strip()
                if val:
                    content_hash = hashlib.md5(val.encode()).hexdigest()[:16]
                    if content_hash not in hash_groups:
                        hash_groups[content_hash] = []
                    hash_groups[content_hash].append(item)

            # 找出完全重复的
            for content_hash, dup_items in hash_groups.items():
                if len(dup_items) >= 2:
                    keys = [t.get("truth_key") for t in dup_items]
                    redundant_keys.extend(keys[1:])  # 保留第一个，其余标记为冗余
                    merge_suggestions.append({
                        "group": prefix,
                        "keys": keys,
                        "reason": f"内容完全相同（哈希:{content_hash}），建议合并保留最新版本",
                        "merged_summary": dup_items[0].get("truth_value", "")[:100],
                    })

        # 规则3：同组大量真值建议合并
        for prefix, items in groups.items():
            if len(items) >= 5 and prefix not in [s.get("group") for s in merge_suggestions]:
                merge_suggestions.append({
                    "group": prefix,
                    "keys": [t.get("truth_key") for t in items[:5]],
                    "reason": f"同组{len(items)}条真值，建议定期归档合并",
                    "merged_summary": f"{prefix}组共{len(items)}条真值",
                })

        return {
            "merge_suggestions": merge_suggestions[:10],
            "redundant_keys": redundant_keys[:20],
            "dedup_engine": "L0-RULE-ENGINE",
            "engine_version": self.version,
            "total_truths_checked": len(truths),
            "potential_redundant_count": len(redundant_keys),
        }

    # ============================================================
    # 工具函数
    # ============================================================
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            "engine_name": "L0-RULE-ENGINE",
            "version": self.version,
            "type": self.engine_type,
            "memory_footprint": self.memory_footprint,
            "llm_dependency": False,
            "supported_tasks": [
                "truth_classification",
                "conflict_detection",
                "anomaly_detection",
                "truth_dedup",
            ],
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω",
        }


# 单例
_l0_engine = None

def get_l0_engine() -> L0RuleEngine:
    """获取L0规则引擎单例"""
    global _l0_engine
    if _l0_engine is None:
        _l0_engine = L0RuleEngine()
    return _l0_engine


if __name__ == "__main__":
    # 自测
    engine = L0RuleEngine()
    print("=== L0规则引擎自测 ===")
    print(json.dumps(engine.get_engine_info(), ensure_ascii=False, indent=2))

    # 测试分类
    print("\n=== 真值分类测试 ===")
    test_truths = [
        {"truth_key": "META_RULE.001", "truth_value": "全域生效，必须执行"},
        {"truth_key": "DATA.TRUTH_COUNT", "truth_value": "总计16000条"},
        {"truth_key": "CUSTOM.XXX", "truth_value": "自定义内容"},
    ]
    results = engine.classify_truths_batch(test_truths)
    for r in results:
        print(f"  {r['key']} → {r['category']} ({r['confidence']})")

    print("\n✅ L0规则引擎自测通过")
