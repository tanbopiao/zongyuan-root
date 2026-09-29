#!/usr/bin/env python3
"""
元学习闭环引擎 V1.0
态元fitness进化 → 内核策略参数反哺机制

核心逻辑：
1. 从态元库读取fitness历史数据
2. 分析态元进化趋势（上升/下降/稳定）
3. 识别高fitness态元的共性特征 → 提炼成功策略
4. 识别低fitness态元的共性特征 → 提炼失败模式
5. 生成内核策略参数调整建议（阈值/权重/优先级）
6. 反哺到内核配置（kernel_state.json的meta_learning层）
7. 记录元学习日志，支持A/B测试对比
"""

import json
import os
import sqlite3
import hashlib
import shutil
from datetime import datetime
from collections import Counter, defaultdict


class MetaLearningLoop:
    def __init__(self, db_path=None, kernel_path=None):
        self.db_path = db_path or os.path.expanduser("~/.zongyuan_root/state_atoms.db")
        self.kernel_path = kernel_path or os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
        self.log_path = os.path.expanduser("~/.zongyuan_root/meta_learning/meta_learning_log.json")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def read_atoms(self):
        """读取所有态元数据"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM atoms")
        atoms = [dict(row) for row in c.fetchall()]
        conn.close()
        return atoms

    def analyze_fitness_trends(self, atoms):
        """分析态元fitness进化趋势"""
        high_fitness = [a for a in atoms if (a.get("fitness_score") or 0) >= 0.7]
        mid_fitness = [a for a in atoms if 0.5 <= (a.get("fitness_score") or 0) < 0.7]
        low_fitness = [a for a in atoms if (a.get("fitness_score") or 0) < 0.5]

        # 按类型统计fitness分布
        type_fitness = defaultdict(list)
        for a in atoms:
            atype = a.get("atom_type", "unknown")
            type_fitness[atype].append(a.get("fitness_score") or 0)

        type_avg = {}
        for atype, scores in type_fitness.items():
            type_avg[atype] = round(sum(scores) / len(scores), 3) if scores else 0

        # 高使用频率态元的fitness
        high_usage = [a for a in atoms if (a.get("usage_frequency") or 0) >= 10]
        high_usage_avg = round(sum(a.get("fitness_score", 0) or 0 for a in high_usage) / max(len(high_usage), 1), 3)

        return {
            "total_atoms": len(atoms),
            "high_fitness": len(high_fitness),
            "mid_fitness": len(mid_fitness),
            "low_fitness": len(low_fitness),
            "avg_fitness": round(sum(a.get("fitness_score", 0) or 0 for a in atoms) / max(len(atoms), 1), 3),
            "type_avg_fitness": type_avg,
            "high_usage_avg_fitness": high_usage_avg,
            "high_usage_count": len(high_usage)
        }

    def extract_success_strategies(self, atoms):
        """从高fitness态元提炼成功策略"""
        high = [a for a in atoms if (a.get("fitness_score") or 0) >= 0.7]
        if not high:
            return {"strategies": [], "common_types": []}

        # 高fitness态元的类型分布
        type_counts = Counter(a.get("atom_type", "unknown") for a in high)
        common_types = type_counts.most_common(5)

        # 高fitness态元的生命周期阶段
        stage_counts = Counter(a.get("lifecycle_stage", "unknown") for a in high)

        # 提炼策略
        strategies = []
        for atype, count in common_types:
            type_atoms = [a for a in high if a.get("atom_type") == atype]
            avg_usage = round(sum(a.get("usage_frequency", 0) or 0 for a in type_atoms) / len(type_atoms), 1)
            strategies.append({
                "atom_type": atype,
                "count": count,
                "avg_usage": avg_usage,
                "strategy": f"增加{atype}类型态元的资源分配，当前平均使用频率{avg_usage}",
                "confidence": round(count / len(high), 2)
            })

        return {
            "strategies": strategies,
            "common_types": common_types,
            "dominant_stage": stage_counts.most_common(1)[0] if stage_counts else ("unknown", 0)
        }

    def extract_failure_modes(self, atoms):
        """从低fitness态元提炼失败模式"""
        low = [a for a in atoms if (a.get("fitness_score") or 0) < 0.5]
        if not low:
            return {"failure_modes": [], "at_risk_types": []}

        type_counts = Counter(a.get("atom_type", "unknown") for a in low)
        at_risk = type_counts.most_common(3)

        failure_modes = []
        for atype, count in at_risk:
            type_atoms = [a for a in low if a.get("atom_type") == atype]
            avg_streak = round(sum(a.get("low_fitness_streak", 0) or 0 for a in type_atoms) / len(type_atoms), 1)
            failure_modes.append({
                "atom_type": atype,
                "count": count,
                "avg_low_streak": avg_streak,
                "failure_mode": f"{atype}类型态元持续低fitness，平均连续{avg_streak}轮，建议降低优先级或合并",
                "severity": "high" if avg_streak >= 3 else "medium"
            })

        return {
            "failure_modes": failure_modes,
            "at_risk_types": at_risk
        }

    def generate_policy_adjustments(self, trends, success, failure):
        """生成内核策略参数调整建议"""
        adjustments = []

        # 1. 态元类型权重调整
        type_avg = trends.get("type_avg_fitness", {})
        for atype, avg in sorted(type_avg.items(), key=lambda x: x[1], reverse=True):
            if avg >= 0.7:
                adjustments.append({
                    "parameter": f"atom_type_weight.{atype}",
                    "current": "default",
                    "proposed": "increase_20%",
                    "reason": f"{atype}类型平均fitness={avg}，高于阈值，建议增加资源权重",
                    "confidence": 0.8
                })
            elif avg < 0.5:
                adjustments.append({
                    "parameter": f"atom_type_weight.{atype}",
                    "current": "default",
                    "proposed": "decrease_30%",
                    "reason": f"{atype}类型平均fitness={avg}，低于阈值，建议降低资源权重",
                    "confidence": 0.75
                })

        # 2. 低fitness保护阈值调整
        low_count = trends.get("low_fitness", 0)
        if low_count > 3:
            adjustments.append({
                "parameter": "low_fitness_protection_threshold",
                "current": 0.5,
                "proposed": 0.45,
                "reason": f"低fitness态元{low_count}个偏多，适当降低保护阈值以增加选择压力",
                "confidence": 0.7
            })

        # 3. 高使用频率态元的fitness关联
        if trends.get("high_usage_avg_fitness", 0) < 0.6:
            adjustments.append({
                "parameter": "usage_fitness_correlation_check",
                "current": "not_monitored",
                "proposed": "enable_correlation_alert",
                "reason": f"高使用频率态元平均fitness={trends['high_usage_avg_fitness']}，使用与质量不匹配，需监控",
                "confidence": 0.85
            })

        # 4. 成功策略推广
        for s in success.get("strategies", []):
            if s.get("confidence", 0) >= 0.3:
                adjustments.append({
                    "parameter": f"promote_strategy.{s['atom_type']}",
                    "current": "not_promoted",
                    "proposed": "promote_to_template",
                    "reason": s["strategy"],
                    "confidence": s["confidence"]
                })

        # 5. 失败模式干预
        for f in failure.get("failure_modes", []):
            if f.get("severity") == "high":
                adjustments.append({
                    "parameter": f"intervene.{f['atom_type']}",
                    "current": "no_intervention",
                    "proposed": "merge_or_retire",
                    "reason": f["failure_mode"],
                    "confidence": 0.8
                })

        return adjustments

    def apply_to_kernel(self, adjustments, trends, success, failure):
        """将策略调整反哺到内核配置"""
        with open(self.kernel_path) as f:
            kernel = json.load(f)

        # 初始化meta_learning层
        if "meta_learning" not in kernel:
            kernel["meta_learning"] = {
                "version": "V1.0",
                "loop_status": "active",
                "last_update": datetime.now().isoformat(),
                "policy_adjustments": [],
                "fitness_trends": {},
                "success_strategies": [],
                "failure_modes": [],
                "total_iterations": 0,
                "improvement_rate": 0.0
            }

        ml = kernel["meta_learning"]
        ml["last_update"] = datetime.now().isoformat()
        ml["total_iterations"] = ml.get("total_iterations", 0) + 1
        ml["fitness_trends"] = trends
        ml["success_strategies"] = success.get("strategies", [])
        ml["failure_modes"] = failure.get("failure_modes", [])

        # 合并策略调整（保留最近20条）
        existing = ml.get("policy_adjustments", [])
        for adj in adjustments:
            adj["applied_at"] = datetime.now().isoformat()
            adj["iteration"] = ml["total_iterations"]
        ml["policy_adjustments"] = (existing + adjustments)[-20:]

        # 计算改进率（与上一轮对比）
        prev_avg = ml.get("prev_avg_fitness", trends["avg_fitness"])
        if prev_avg > 0:
            ml["improvement_rate"] = round((trends["avg_fitness"] - prev_avg) / prev_avg * 100, 2)
        ml["prev_avg_fitness"] = trends["avg_fitness"]

        # 应用高优先级调整到内核活跃参数
        high_priority = [a for a in adjustments if a.get("confidence", 0) >= 0.8]
        ml["applied_high_priority"] = len(high_priority)
        for adj in high_priority:
            param = adj["parameter"]
            if "atom_type_weight" in param:
                atype = param.split(".")[-1]
                if "active_atom_weights" not in kernel:
                    kernel["active_atom_weights"] = {}
                kernel["active_atom_weights"][atype] = adj["proposed"]

        with open(self.kernel_path, "w") as f:
            json.dump(kernel, f, ensure_ascii=False, indent=2)

        return ml

    def log_iteration(self, result):
        """记录元学习日志"""
        logs = []
        if os.path.exists(self.log_path):
            with open(self.log_path) as f:
                logs = json.load(f)
        logs.append(result)
        logs = logs[-100:]  # 保留最近100轮
        with open(self.log_path, "w") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def run(self):
        """执行一轮元学习闭环"""
        print("=" * 50)
        print("元学习闭环引擎 V1.0")
        print("=" * 50)

        # 1. 读取态元
        atoms = self.read_atoms()
        print(f"[1/6] 读取态元: {len(atoms)}个")

        # 2. 分析fitness趋势
        trends = self.analyze_fitness_trends(atoms)
        print(f"[2/6] fitness趋势: 平均{trends['avg_fitness']} | 高{trends['high_fitness']} 中{trends['mid_fitness']} 低{trends['low_fitness']}")

        # 3. 提炼成功策略
        success = self.extract_success_strategies(atoms)
        print(f"[3/6] 成功策略: {len(success['strategies'])}条 | 主导类型: {success.get('dominant_stage', ('?',0))[0]}")

        # 4. 提炼失败模式
        failure = self.extract_failure_modes(atoms)
        print(f"[4/6] 失败模式: {len(failure['failure_modes'])}个风险类型")

        # 5. 生成策略调整
        adjustments = self.generate_policy_adjustments(trends, success, failure)
        print(f"[5/6] 策略调整: {len(adjustments)}条建议")

        # 6. 反哺内核
        ml = self.apply_to_kernel(adjustments, trends, success, failure)
        print(f"[6/6] 反哺内核: 第{ml['total_iterations']}轮 | 改进率{ml['improvement_rate']}%")

        result = {
            "iteration": ml["total_iterations"],
            "timestamp": datetime.now().isoformat(),
            "trends": trends,
            "adjustments_count": len(adjustments),
            "high_priority_applied": ml.get("applied_high_priority", 0),
            "improvement_rate": ml["improvement_rate"],
            "status": "completed"
        }
        self.log_iteration(result)

        print("=" * 50)
        print(f"元学习闭环完成 | 改进率: {ml['improvement_rate']}%")
        print(f"高优先级调整已应用: {ml.get('applied_high_priority', 0)}条")
        print("=" * 50)

        return result


if __name__ == "__main__":
    loop = MetaLearningLoop()
    loop.run()
