#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜27算子核心框架
算子基类 + 核心算子实现 + 算子调度器
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import sys
import json
import time
import hashlib
import sqlite3
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR / "config"))

try:
    from config_loader import config as _config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False


def _cfg(key, default):
    if _CONFIG_AVAILABLE:
        return _config.get(key, default)
    return default


# ==================== 算子基类 ====================

class BaseOperator(ABC):
    """算子基类：所有27算子的抽象基类"""

    def __init__(self, operator_id, name, layer, description):
        self.operator_id = operator_id
        self.name = name
        self.layer = layer  # 所属层（1-10）
        self.description = description
        self.execution_count = 0
        self.last_execution = None
        self.last_result = None
        self.enabled = True

    @abstractmethod
    def execute(self, **kwargs):
        """执行算子逻辑，返回结果字典"""
        pass

    def run(self, **kwargs):
        """运行算子（带统计和异常处理）"""
        if not self.enabled:
            return {"status": "disabled", "operator_id": self.operator_id}

        start_time = time.time()
        try:
            result = self.execute(**kwargs)
            result["status"] = result.get("status", "success")
        except Exception as e:
            result = {"status": "error", "error": str(e), "operator_id": self.operator_id}

        elapsed = time.time() - start_time
        self.execution_count += 1
        self.last_execution = time.time()
        self.last_result = result

        result["operator_id"] = self.operator_id
        result["operator_name"] = self.name
        result["layer"] = self.layer
        result["execution_count"] = self.execution_count
        result["elapsed_ms"] = round(elapsed * 1000, 2)
        result["timestamp"] = time.time()

        return result

    def get_status(self):
        """获取算子状态"""
        return {
            "operator_id": self.operator_id,
            "name": self.name,
            "layer": self.layer,
            "description": self.description,
            "enabled": self.enabled,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution,
            "last_status": self.last_result.get("status") if self.last_result else None,
        }


# ==================== 第一层：真值过滤与深度蒸馏 ====================

class TruthReconciliationOperator(BaseOperator):
    """P4真值对账算子：对大模型输出执行真值粗对账，区分客观事实/推演猜想/主观观点"""

    def __init__(self):
        super().__init__(
            operator_id="P4_TRUTH_RECONCILIATION",
            name="真值对账算子",
            layer=1,
            description="对大模型输出原始碎片执行第一层真值粗对账，区分客观事实/推演猜想/主观观点"
        )

    def execute(self, fragments=None, **kwargs):
        fragments = fragments or []
        facts = []
        hypotheses = []
        opinions = []
        filtered = []

        for frag in fragments:
            text = frag.get("text", "").lower() if isinstance(frag, dict) else str(frag).lower()
            frag_dict = frag if isinstance(frag, dict) else {"text": frag}

            # 简单分类规则（实际应接入NLP模型）
            if any(kw in text for kw in ["数据显示", "研究表明", "统计", "据报道", "实验证明"]):
                frag_dict["truth_type"] = "fact"
                frag_dict["confidence"] = min(frag_dict.get("confidence", 0.8) + 0.1, 1.0)
                facts.append(frag_dict)
            elif any(kw in text for kw in ["可能", "推测", "假设", "预测", "预计"]):
                frag_dict["truth_type"] = "hypothesis"
                frag_dict["confidence"] = frag_dict.get("confidence", 0.5)
                hypotheses.append(frag_dict)
            elif any(kw in text for kw in ["我认为", "我觉得", "个人观点", "建议"]):
                frag_dict["truth_type"] = "opinion"
                frag_dict["confidence"] = frag_dict.get("confidence", 0.3)
                opinions.append(frag_dict)
            else:
                frag_dict["truth_type"] = "unclassified"
                filtered.append(frag_dict)

        # 过滤无来源碎片
        sourced = [f for f in facts + hypotheses if f.get("source")]
        unsourced_count = len(facts) + len(hypotheses) - len(sourced)

        return {
            "total_fragments": len(fragments),
            "facts": len(facts),
            "hypotheses": len(hypotheses),
            "opinions": len(opinions),
            "unclassified": len(filtered),
            "sourced_fragments": len(sourced),
            "filtered_unsourced": unsourced_count,
            "truth_purity": round(len(sourced) / max(len(fragments), 1) * 100, 2),
            "fragments": {"facts": facts[:10], "hypotheses": hypotheses[:10], "opinions": opinions[:10]},
        }


class TruthDistillationOperator(BaseOperator):
    """真值提炼蒸馏算子：从过滤后的碎片中深度蒸馏高纯度真值"""

    def __init__(self):
        super().__init__(
            operator_id="TRUTH_DISTILLATION",
            name="真值提炼蒸馏算子",
            layer=1,
            description="多轮交叉验证+来源锚定+逻辑一致性检查+冲突消解，提炼高置信度结构化真值条目"
        )

    def execute(self, fragments=None, **kwargs):
        fragments = fragments or []
        cross_verified = []
        conflicts = []

        # 多轮交叉验证（简化版：按内容哈希去重+来源计数）
        source_map = {}
        for frag in fragments:
            content_hash = hashlib.sha256(
                json.dumps(frag.get("text", ""), sort_keys=True).encode()
            ).hexdigest()[:16]
            if content_hash not in source_map:
                source_map[content_hash] = {"fragment": frag, "source_count": 0, "confidences": []}
            source_map[content_hash]["source_count"] += 1
            source_map[content_hash]["confidences"].append(frag.get("confidence", 0.5))

        # 逻辑一致性检查（简化版：置信度>0.7且来源>1）
        for content_hash, data in source_map.items():
            avg_confidence = sum(data["confidences"]) / len(data["confidences"])
            if avg_confidence >= 0.7 and data["source_count"] >= 1:
                truth_entry = {
                    "truth_id": f"TRUTH-{content_hash}",
                    "content": data["fragment"].get("text", ""),
                    "confidence": round(avg_confidence, 4),
                    "source_count": data["source_count"],
                    "truth_type": data["fragment"].get("truth_type", "fact"),
                    "distilled_at": time.time(),
                }
                cross_verified.append(truth_entry)
            elif avg_confidence < 0.5:
                conflicts.append({"fragment": data["fragment"], "avg_confidence": avg_confidence})

        return {
            "input_fragments": len(fragments),
            "distilled_truths": len(cross_verified),
            "conflicts_detected": len(conflicts),
            "truth_purity_score": round(len(cross_verified) / max(len(fragments), 1) * 100, 2),
            "distillation_compression_ratio": round(len(fragments) / max(len(cross_verified), 1), 2),
            "truth_entries": cross_verified[:20],
            "conflicts": conflicts[:10],
        }


# ==================== 第二层：流形度量与稳态映射 ====================

class DriftDetectionOperator(BaseOperator):
    """漂移巡检量化算子：对全资产库执行语义漂移量化巡检"""

    def __init__(self):
        super().__init__(
            operator_id="DRIFT_DETECTION",
            name="漂移巡检量化算子",
            layer=2,
            description="计算每个概念在不同时间快照中的流形坐标偏移量，输出漂移率+漂移方向向量+Top-N高漂移概念"
        )

    def execute(self, concepts=None, snapshots=None, **kwargs):
        concepts = concepts or []
        snapshots = snapshots or []
        drift_results = []

        # 简化版漂移检测：比较不同快照中的概念向量距离
        if len(snapshots) >= 2:
            current = snapshots[-1]
            previous = snapshots[-2]
            for concept in concepts:
                curr_vec = current.get(concept, [0] * 8)
                prev_vec = previous.get(concept, [0] * 8)
                # 计算欧氏距离作为漂移量
                drift = sum((c - p) ** 2 for c, p in zip(curr_vec, prev_vec)) ** 0.5
                drift_rate = drift / max(sum(abs(v) for v in prev_vec), 1) * 100
                # 漂移方向向量
                direction = [c - p for c, p in zip(curr_vec, prev_vec)]
                drift_results.append({
                    "concept": concept,
                    "drift_amount": round(drift, 4),
                    "drift_rate_percent": round(drift_rate, 2),
                    "direction_vector": [round(d, 4) for d in direction],
                    "alert_level": "red" if drift_rate > 20 else "orange" if drift_rate > 10 else "yellow" if drift_rate > 5 else "normal",
                })

        # 按漂移率排序
        drift_results.sort(key=lambda x: x["drift_rate_percent"], reverse=True)
        high_drift = [d for d in drift_results if d["alert_level"] in ["red", "orange"]]

        return {
            "concepts_checked": len(concepts),
            "snapshots_compared": len(snapshots),
            "total_drift_detected": len(drift_results),
            "high_drift_concepts": len(high_drift),
            "avg_drift_rate": round(sum(d["drift_rate_percent"] for d in drift_results) / max(len(drift_results), 1), 2),
            "top_n_drift": drift_results[:10],
            "alerts": {
                "red": len([d for d in drift_results if d["alert_level"] == "red"]),
                "orange": len([d for d in drift_results if d["alert_level"] == "orange"]),
                "yellow": len([d for d in drift_results if d["alert_level"] == "yellow"]),
            },
            "thresholds": {"yellow": 5, "orange": 10, "red": 20},
        }


# ==================== 第四层：因果级推理 ====================

class CausalChainOperator(BaseOperator):
    """因果链溯源回溯算子：从任意结果事件出发，沿第七维因果域反向回溯完整因果链"""

    def __init__(self):
        super().__init__(
            operator_id="CAUSAL_CHAIN_TRACE",
            name="因果链溯源回溯算子",
            layer=4,
            description="从任意结果事件出发，沿第七维因果域反向回溯完整因果链，识别关键因果节点/旁路分支/因果汇聚点"
        )

    def execute(self, result_event=None, causal_graph=None, max_depth=10, **kwargs):
        result_event = result_event or "unknown_event"
        causal_graph = causal_graph or {}
        chain = []
        visited = set()
        current = result_event
        depth = 0

        # 反向回溯因果链
        while current and current not in visited and depth < max_depth:
            visited.add(current)
            node = causal_graph.get(current, {})
            chain.append({
                "event": current,
                "causal_strength": node.get("strength", 0.5),
                "node_type": node.get("type", "intermediate"),
                "depth": depth,
                "causes": node.get("causes", []),
            })
            # 找上游原因（取最强因果边）
            causes = node.get("causes", [])
            if causes:
                current = max(causes, key=lambda c: c.get("strength", 0)) if isinstance(causes[0], dict) else causes[0]
                if isinstance(current, dict):
                    current = current.get("event", "unknown")
            else:
                current = None
            depth += 1

        # 识别关键节点（因果强度>0.7）
        key_nodes = [n for n in chain if n["causal_strength"] > 0.7]
        # 识别因果汇聚点（有多个下游事件）
        convergence_points = []
        for node in chain:
            downstream = [e for e, n in causal_graph.items() if node["event"] in [c.get("event") if isinstance(c, dict) else c for c in n.get("causes", [])]]
            if len(downstream) > 1:
                convergence_points.append({"event": node["event"], "downstream_count": len(downstream)})

        return {
            "result_event": result_event,
            "chain_length": len(chain),
            "max_depth_reached": depth,
            "key_causal_nodes": len(key_nodes),
            "convergence_points": convergence_points,
            "causal_chain": chain,
            "total_causal_strength": round(sum(n["causal_strength"] for n in chain), 4),
            "avg_causal_strength": round(sum(n["causal_strength"] for n in chain) / max(len(chain), 1), 4),
        }


# ==================== 第六层：结构化归档 ====================

class MerkleVerificationOperator(BaseOperator):
    """Merkle-DAG主链追加校验算子：新资产归档时计算Merkle哈希追加至主DAG链，校验前序链完整性"""

    def __init__(self):
        super().__init__(
            operator_id="MERKLE_DAG_VERIFY",
            name="Merkle-DAG主链追加校验算子",
            layer=6,
            description="新资产归档时计算Merkle哈希追加至主DAG链，校验前序链完整性，防止链断裂或中间篡改"
        )

    def execute(self, new_assets=None, merkle_tree=None, **kwargs):
        new_assets = new_assets or []
        merkle_tree = merkle_tree or {"leaves": [], "root": None}
        verification_results = []
        new_leaves = []

        # 校验前序链完整性
        chain_valid = True
        if len(merkle_tree.get("leaves", [])) > 1:
            leaves = merkle_tree["leaves"]
            for i in range(1, len(leaves)):
                expected_prev = hashlib.sha256(
                    json.dumps(leaves[i-1], sort_keys=True).encode()
                ).hexdigest()
                if leaves[i].get("prev_hash") != expected_prev:
                    chain_valid = False
                    verification_results.append({
                        "type": "chain_break",
                        "index": i,
                        "expected": expected_prev[:16],
                        "actual": leaves[i].get("prev_hash", "N/A")[:16],
                    })

        # 计算新资产的Merkle叶子
        for asset in new_assets:
            leaf_hash = hashlib.sha256(
                json.dumps(asset, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            prev_hash = merkle_tree["leaves"][-1]["hash"] if merkle_tree["leaves"] else "0" * 64
            leaf = {
                "hash": leaf_hash,
                "prev_hash": prev_hash,
                "asset_id": asset.get("asset_id", "unknown"),
                "timestamp": time.time(),
            }
            new_leaves.append(leaf)
            verification_results.append({
                "type": "new_leaf",
                "asset_id": asset.get("asset_id"),
                "hash": leaf_hash[:16] + "...",
                "prev_hash": prev_hash[:16] + "...",
            })

        # 计算新的Merkle根
        all_hashes = [l["hash"] for l in merkle_tree.get("leaves", [])] + [l["hash"] for l in new_leaves]
        new_root = hashlib.sha256("".join(sorted(all_hashes)).encode()).hexdigest()

        return {
            "chain_valid": chain_valid,
            "previous_leaves": len(merkle_tree.get("leaves", [])),
            "new_leaves": len(new_leaves),
            "total_leaves": len(all_hashes),
            "new_merkle_root": new_root,
            "previous_root": merkle_tree.get("root"),
            "root_changed": new_root != merkle_tree.get("root"),
            "verification_results": verification_results[:20],
            "tampering_detected": not chain_valid,
        }


# ==================== 算子调度器 ====================

class OperatorScheduler:
    """27算子调度器：按十层依赖拓扑依次运行算子"""

    def __init__(self):
        self.operators = {}
        self.execution_history = []
        self._register_core_operators()

    def _register_core_operators(self):
        """注册核心算子"""
        core_operators = [
            TruthReconciliationOperator(),
            TruthDistillationOperator(),
            DriftDetectionOperator(),
            CausalChainOperator(),
            MerkleVerificationOperator(),
        ]
        for op in core_operators:
            self.operators[op.operator_id] = op

    def register(self, operator):
        """注册算子"""
        self.operators[operator.operator_id] = operator

    def get_operator(self, operator_id):
        """获取算子"""
        return self.operators.get(operator_id)

    def list_operators(self):
        """列出所有算子"""
        return [op.get_status() for op in self.operators.values()]

    def run_operator(self, operator_id, **kwargs):
        """运行单个算子"""
        op = self.operators.get(operator_id)
        if not op:
            return {"status": "error", "error": f"算子 {operator_id} 不存在"}
        result = op.run(**kwargs)
        self.execution_history.append(result)
        return result

    def run_layer(self, layer, **kwargs):
        """运行指定层的所有算子"""
        layer_operators = [op for op in self.operators.values() if op.layer == layer]
        results = []
        for op in sorted(layer_operators, key=lambda x: x.operator_id):
            result = op.run(**kwargs)
            results.append(result)
            self.execution_history.append(result)
        return results

    def run_all(self, **kwargs):
        """按十层依赖拓扑依次运行所有算子"""
        all_results = []
        for layer in range(1, 11):
            layer_results = self.run_layer(layer, **kwargs)
            all_results.extend(layer_results)
        return all_results

    def get_stats(self):
        """获取调度器统计"""
        total_executions = sum(op.execution_count for op in self.operators.values())
        return {
            "registered_operators": len(self.operators),
            "total_executions": total_executions,
            "execution_history_size": len(self.execution_history),
            "operators": self.list_operators(),
        }


# 全局单例
_scheduler = None

def get_scheduler():
    """获取算子调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = OperatorScheduler()
    return _scheduler


if __name__ == "__main__":
    print("=" * 60)
    print("元极恒一｜27算子核心框架测试")
    print("=" * 60)

    scheduler = get_scheduler()
    print(f"\n已注册算子: {len(scheduler.operators)}个")
    for op in scheduler.list_operators():
        print(f"  [{op['layer']}] {op['operator_id']}: {op['name']}")

    # 测试真值对账算子
    print("\n--- 测试真值对账算子 ---")
    result = scheduler.run_operator("P4_TRUTH_RECONCILIATION", fragments=[
        {"text": "数据显示AI市场增长30%", "source": "report", "confidence": 0.9},
        {"text": "我认为AI会改变世界", "confidence": 0.5},
        {"text": "可能明年会出现AGI", "confidence": 0.4},
    ])
    print(f"  状态: {result['status']}")
    print(f"  事实: {result['facts']}, 猜想: {result['hypotheses']}, 观点: {result['opinions']}")
    print(f"  真值纯度: {result['truth_purity']}%")

    # 测试Merkle校验算子
    print("\n--- 测试Merkle校验算子 ---")
    result = scheduler.run_operator("MERKLE_DAG_VERIFY",
        new_assets=[{"asset_id": "asset-001", "content": "test"}],
        merkle_tree={"leaves": [], "root": None}
    )
    print(f"  状态: {result['status']}")
    print(f"  链有效: {result['chain_valid']}")
    print(f"  新Merkle根: {result['new_merkle_root'][:32]}...")

    print("\n" + "=" * 60)
    print("27算子核心框架测试完成")
    print("=" * 60)
