#!/usr/bin/env python3
"""
八维世界模型引擎 V1.0
工程化落地：将抽象的八维宇宙模型转化为可计算、可查询、可推理的工程系统

八维定义：
  D1 空间维 (Space)     - 3D坐标/拓扑结构/地理分布
  D2 时间维 (Time)      - 时序/快照/历史轨迹/预测
  D3 因果维 (Causality) - 因果链/干预/反事实/奇点
  D4 能量维 (Energy)    - fitness/活跃度/价值密度/势能
  D5 信息维 (Information) - 真值/知识图谱/信息熵/置信度
  D6 意识维 (Consciousness) - 决策/意图/元认知/自反思
  D7 进化维 (Evolution) - 适应度/策略变更/层级跃迁/迭代
  D8 本源维 (Origin)    - 元公理/锚点/太初寂态/基准态

核心能力：
  1. 八维坐标映射 - 将每个实体/态元/真值映射到八维空间
  2. 维度耦合计算 - 计算维度间相关性和耦合强度
  3. 因果推理 - 基于D3因果维执行do-calculus干预模拟
  4. 趋势预测 - 基于D2时间维+D7进化维预测未来状态
  5. 世界模型快照 - 生成当前全域八维状态快照
  6. 异常检测 - 识别维度间不协调/漂移/断裂
"""

import json
import os
import sqlite3
import hashlib
from datetime import datetime
from collections import defaultdict
import math


class EightDimensionWorldModel:
    def __init__(self, kernel_path=None, kg_path=None, db_path=None):
        self.kernel_path = kernel_path or os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
        self.kg_path = kg_path or os.path.expanduser("~/.zongyuan_root/knowledge_graph/knowledge_graph.json")
        self.db_path = db_path or os.path.expanduser("~/.zongyuan_root/state_atoms.db")
        self.output_dir = os.path.expanduser("~/.zongyuan_root/world_model")
        os.makedirs(self.output_dir, exist_ok=True)

        # 八维定义
        self.dimensions = {
            "D1": {"name": "空间维", "en": "Space", "weight": 0.10},
            "D2": {"name": "时间维", "en": "Time", "weight": 0.12},
            "D3": {"name": "因果维", "en": "Causality", "weight": 0.15},
            "D4": {"name": "能量维", "en": "Energy", "weight": 0.13},
            "D5": {"name": "信息维", "en": "Information", "weight": 0.15},
            "D6": {"name": "意识维", "en": "Consciousness", "weight": 0.10},
            "D7": {"name": "进化维", "en": "Evolution", "weight": 0.15},
            "D8": {"name": "本源维", "en": "Origin", "weight": 0.10}
        }

    def load_data(self):
        """加载内核、知识图谱、态元库数据"""
        with open(self.kernel_path) as f:
            self.kernel = json.load(f)
        with open(self.kg_path) as f:
            self.kg = json.load(f)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM atoms")
        self.atoms = [dict(row) for row in c.fetchall()]
        conn.close()

        self.entities = self.kg.get("entities", [])
        self.relations = self.kg.get("relations", [])
        return self

    def map_to_dimensions(self):
        """将所有实体/态元映射到八维坐标"""
        mapped = []

        # 映射知识图谱实体
        for ent in self.entities:
            coords = self._calc_entity_coords(ent)
            mapped.append({
                "id": ent.get("id", ent.get("entity_id", "unknown")),
                "label": ent.get("label", "unknown"),
                "type": ent.get("type", "concept"),
                "source": "knowledge_graph",
                "coordinates": coords,
                "magnitude": self._calc_magnitude(coords)
            })

        # 映射态元
        for atom in self.atoms:
            coords = self._calc_atom_coords(atom)
            mapped.append({
                "id": atom.get("atom_id", "unknown"),
                "label": atom.get("content", "unknown")[:50],
                "type": atom.get("atom_type", "state_atom"),
                "source": "state_atom",
                "coordinates": coords,
                "magnitude": self._calc_magnitude(coords)
            })

        return mapped

    def _calc_entity_coords(self, entity):
        """计算知识图谱实体的八维坐标"""
        etype = entity.get("type", "concept")
        confidence = entity.get("confidence", 0.5)

        # D1 空间维 - 基于实体类型的拓扑位置
        space_map = {"concept": 0.3, "system": 0.7, "technology": 0.5, "protocol": 0.6,
                     "node": 0.8, "role": 0.4, "rule": 0.2, "dimension": 0.9,
                     "state": 0.5, "operator": 0.6, "framework": 0.55}
        d1 = space_map.get(etype, 0.5)

        # D2 时间维 - 基于创建时间/新鲜度
        created = entity.get("created_at", entity.get("timestamp", ""))
        if created:
            try:
                age_hours = (datetime.now() - datetime.fromisoformat(created)).total_seconds() / 3600
                d2 = max(0.1, min(1.0, 1.0 - age_hours / 168))  # 一周内衰减
            except:
                d2 = 0.5
        else:
            d2 = 0.5

        # D3 因果维 - 基于关系数量（入度=结果，出度=原因）
        eid = entity.get("id", entity.get("entity_id", ""))
        out_degree = sum(1 for r in self.relations if r.get("source") == eid or r.get("head") == eid)
        in_degree = sum(1 for r in self.relations if r.get("target") == eid or r.get("tail") == eid)
        d3 = min(1.0, (out_degree + in_degree) / 10)

        # D4 能量维 - 基于置信度和连接度
        d4 = min(1.0, confidence * 0.6 + (out_degree + in_degree) / 20 * 0.4)

        # D5 信息维 - 基于实体描述丰富度
        desc_len = len(str(entity.get("label", "")) + str(entity.get("description", "")))
        d5 = min(1.0, desc_len / 100)

        # D6 意识维 - 规则/决策类实体意识维高
        conscious_types = ["rule", "protocol", "decision", "operator"]
        d6 = 0.8 if etype in conscious_types else 0.3

        # D7 进化维 - 技术/框架类进化维高
        evolve_types = ["technology", "framework", "system", "operator"]
        d7 = 0.75 if etype in evolve_types else 0.4

        # D8 本源维 - 元规则/公理类本源维高
        origin_types = ["rule", "dimension", "concept"]
        d8 = 0.7 if etype in origin_types else 0.3

        return {"D1": round(d1, 3), "D2": round(d2, 3), "D3": round(d3, 3), "D4": round(d4, 3),
                "D5": round(d5, 3), "D6": round(d6, 3), "D7": round(d7, 3), "D8": round(d8, 3)}

    def _calc_atom_coords(self, atom):
        """计算态元的八维坐标"""
        fitness = atom.get("fitness_score", 0.5) or 0.5
        usage = atom.get("usage_frequency", 0) or 0
        atype = atom.get("atom_type", "unknown")
        stage = atom.get("lifecycle_stage", "unknown")

        # D1 空间维 - 态元在体系中的位置
        d1 = 0.5

        # D2 时间维 - 最近使用时间
        last_used = atom.get("last_used", "")
        if last_used:
            try:
                age_hours = (datetime.now() - datetime.fromisoformat(last_used)).total_seconds() / 3600
                d2 = max(0.1, min(1.0, 1.0 - age_hours / 72))
            except:
                d2 = 0.5
        else:
            d2 = 0.3

        # D3 因果维 - 态元间消息传递
        d3 = min(1.0, usage / 20)

        # D4 能量维 - fitness直接映射
        d4 = fitness

        # D5 信息维 - 内容长度
        content_len = len(str(atom.get("content", "")))
        d5 = min(1.0, content_len / 200)

        # D6 意识维 - 活跃态元意识维高
        d6 = 0.7 if stage == "active" else 0.4

        # D7 进化维 - fitness趋势
        low_streak = atom.get("low_fitness_streak", 0) or 0
        d7 = max(0.1, min(1.0, fitness - low_streak * 0.05))

        # D8 本源维 - 元法则/宪法类态元本源维高
        origin_keywords = ["元法则", "元公理", "宪法", "本源", "锚点"]
        content = str(atom.get("content", ""))
        d8 = 0.8 if any(k in content for k in origin_keywords) else 0.3

        return {"D1": round(d1, 3), "D2": round(d2, 3), "D3": round(d3, 3), "D4": round(d4, 3),
                "D5": round(d5, 3), "D6": round(d6, 3), "D7": round(d7, 3), "D8": round(d8, 3)}

    def _calc_magnitude(self, coords):
        """计算八维向量的模长"""
        return round(math.sqrt(sum(v ** 2 for v in coords.values())), 3)

    def calc_dimension_coupling(self, mapped):
        """计算维度间耦合强度（相关性矩阵）"""
        dims = list(self.dimensions.keys())
        n = len(mapped)
        if n < 2:
            return {"coupling_matrix": {}, "note": "insufficient_data"}

        # 计算每对维度的皮尔逊相关系数
        coupling = {}
        for i, d1 in enumerate(dims):
            for d2 in dims[i+1:]:
                x = [m["coordinates"][d1] for m in mapped]
                y = [m["coordinates"][d2] for m in mapped]
                corr = self._pearson(x, y)
                coupling[f"{d1}-{d2}"] = round(corr, 3)

        # 维度均值
        dim_means = {}
        for d in dims:
            dim_means[d] = round(sum(m["coordinates"][d] for m in mapped) / n, 3)

        return {
            "coupling_matrix": coupling,
            "dimension_means": dim_means,
            "strongest_coupling": max(coupling.items(), key=lambda x: abs(x[1])) if coupling else ("none", 0),
            "weakest_coupling": min(coupling.items(), key=lambda x: abs(x[1])) if coupling else ("none", 0)
        }

    def _pearson(self, x, y):
        """皮尔逊相关系数"""
        n = len(x)
        if n < 2:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
        dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
        if dx == 0 or dy == 0:
            return 0.0
        return num / (dx * dy)

    def causal_reasoning(self, mapped):
        """基于D3因果维执行因果推理"""
        # 找出高因果维实体（潜在原因节点）
        high_causal = sorted(mapped, key=lambda m: m["coordinates"]["D3"], reverse=True)[:5]
        # 找出高能量维实体（潜在结果节点）
        high_energy = sorted(mapped, key=lambda m: m["coordinates"]["D4"], reverse=True)[:5]

        # 因果链推断
        causal_chains = []
        for cause in high_causal[:3]:
            for effect in high_energy[:3]:
                if cause["id"] != effect["id"]:
                    # 检查知识图谱中是否有直接关系
                    has_relation = any(
                        (r.get("source") == cause["id"] and r.get("target") == effect["id"]) or
                        (r.get("head") == cause["id"] and r.get("tail") == effect["id"])
                        for r in self.relations
                    )
                    strength = round(cause["coordinates"]["D3"] * effect["coordinates"]["D4"], 3)
                    causal_chains.append({
                        "cause": cause["label"],
                        "effect": effect["label"],
                        "strength": strength,
                        "has_direct_relation": has_relation,
                        "inferred": not has_relation
                    })

        return {
            "top_cause_nodes": [{"id": c["id"], "label": c["label"], "d3": c["coordinates"]["D3"]} for c in high_causal],
            "top_effect_nodes": [{"id": e["id"], "label": e["label"], "d4": e["coordinates"]["D4"]} for e in high_energy],
            "inferred_chains": causal_chains[:6],
            "singularity_risk": self._calc_singularity_risk(mapped)
        }

    def _calc_singularity_risk(self, mapped):
        """计算奇点爆发概率（高D3+高D4+高D7聚集）"""
        high_all = [m for m in mapped
                    if m["coordinates"]["D3"] > 0.6
                    and m["coordinates"]["D4"] > 0.6
                    and m["coordinates"]["D7"] > 0.6]
        probability = min(1.0, len(high_all) / len(mapped) * 2) if mapped else 0
        level = "蓝" if probability < 0.2 else "黄" if probability < 0.4 else "橙" if probability < 0.6 else "红"
        return {"probability": round(probability, 3), "level": level, "high_risk_nodes": len(high_all)}

    def trend_prediction(self, mapped):
        """基于D2时间维+D7进化维预测趋势"""
        # 当前各维度均值
        dims = list(self.dimensions.keys())
        current = {d: round(sum(m["coordinates"][d] for m in mapped) / len(mapped), 3) for d in dims}

        # 简单线性外推（基于D2新鲜度加权）
        predicted = {}
        for d in dims:
            # 新鲜实体的维度值代表趋势方向
            fresh = [m for m in mapped if m["coordinates"]["D2"] > 0.6]
            if fresh:
                fresh_avg = sum(m["coordinates"][d] for m in fresh) / len(fresh)
                trend = (fresh_avg - current[d]) * 0.3  # 30%外推
                predicted[d] = round(current[d] + trend, 3)
            else:
                predicted[d] = current[d]

        return {
            "current_dimension_means": current,
            "predicted_next_cycle": predicted,
            "trend_direction": {d: "↑" if predicted[d] > current[d] else "↓" if predicted[d] < current[d] else "→"
                               for d in dims}
        }

    def anomaly_detection(self, mapped, coupling):
        """检测维度间不协调/漂移/断裂"""
        anomalies = []

        # 1. 低模长实体（边缘化）
        low_mag = [m for m in mapped if m["magnitude"] < 0.8]
        if len(low_mag) > len(mapped) * 0.3:
            anomalies.append({
                "type": "marginalization",
                "severity": "medium",
                "description": f"{len(low_mag)}个实体八维模长<0.8，存在边缘化风险",
                "affected_count": len(low_mag)
            })

        # 2. 维度均值偏差（某维度整体偏低）
        dim_means = coupling.get("dimension_means", {})
        for d, val in dim_means.items():
            if val < 0.3:
                anomalies.append({
                    "type": "dimension_deficit",
                    "severity": "high" if val < 0.2 else "medium",
                    "description": f"{self.dimensions[d]['name']}({d})均值={val}，维度发育不足",
                    "dimension": d,
                    "value": val
                })

        # 3. 强负耦合（维度间冲突）
        for pair, corr in coupling.get("coupling_matrix", {}).items():
            if corr < -0.5:
                anomalies.append({
                    "type": "dimension_conflict",
                    "severity": "high",
                    "description": f"{pair}维度强负相关({corr})，存在内在冲突",
                    "pair": pair,
                    "correlation": corr
                })

        # 4. 本源维过低（锚点缺失）
        origin_avg = dim_means.get("D8", 0.5)
        if origin_avg < 0.4:
            anomalies.append({
                "type": "anchor_drift",
                "severity": "high",
                "description": f"本源维均值={origin_avg}，体系锚点漂移风险",
                "dimension": "D8"
            })

        return anomalies

    def generate_snapshot(self):
        """生成八维世界模型完整快照"""
        print("=" * 50)
        print("八维世界模型引擎 V1.0")
        print("=" * 50)

        print("[1/6] 加载数据...")
        self.load_data()
        print(f"  内核: {self.kernel.get('version')} | 图谱: {len(self.entities)}实体/{len(self.relations)}关系 | 态元: {len(self.atoms)}")

        print("[2/6] 八维坐标映射...")
        mapped = self.map_to_dimensions()
        print(f"  映射完成: {len(mapped)}个对象")

        print("[3/6] 维度耦合计算...")
        coupling = self.calc_dimension_coupling(mapped)
        print(f"  最强耦合: {coupling['strongest_coupling']}")
        print(f"  最弱耦合: {coupling['weakest_coupling']}")

        print("[4/6] 因果推理...")
        causal = self.causal_reasoning(mapped)
        print(f"  奇点风险: {causal['singularity_risk']['level']}级 (概率{causal['singularity_risk']['probability']})")

        print("[5/6] 趋势预测...")
        trend = self.trend_prediction(mapped)
        print(f"  趋势方向: {trend['trend_direction']}")

        print("[6/6] 异常检测...")
        anomalies = self.anomaly_detection(mapped, coupling)
        print(f"  发现异常: {len(anomalies)}项")

        # 组装快照
        snapshot = {
            "snapshot_id": f"WM-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "did": "DID-BR-000002",
            "anchor": "Ω₀⊂⊙∞⊂Ω",
            "version": "V1.0",
            "dimensions": self.dimensions,
            "mapped_objects_count": len(mapped),
            "top_objects": sorted(mapped, key=lambda x: x["magnitude"], reverse=True)[:10],
            "dimension_coupling": coupling,
            "causal_reasoning": causal,
            "trend_prediction": trend,
            "anomalies": anomalies,
            "world_model_health": self._calc_health(coupling, anomalies)
        }

        # 保存快照
        snapshot_path = os.path.join(self.output_dir, f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        # 保存最新快照指针
        latest_path = os.path.join(self.output_dir, "latest_snapshot.json")
        with open(latest_path, "w") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        # 写入内核
        self.kernel["world_model"] = {
            "version": "V1.0",
            "status": "active",
            "last_snapshot": snapshot["snapshot_id"],
            "snapshot_path": snapshot_path,
            "mapped_objects": len(mapped),
            "health": snapshot["world_model_health"],
            "anomaly_count": len(anomalies),
            "updated_at": datetime.now().isoformat()
        }
        with open(self.kernel_path, "w") as f:
            json.dump(self.kernel, f, ensure_ascii=False, indent=2)

        print("=" * 50)
        print(f"世界模型快照生成完成: {snapshot['snapshot_id']}")
        print(f"健康度: {snapshot['world_model_health']['score']}/100")
        print(f"异常: {len(anomalies)}项")
        print(f"快照已保存: {snapshot_path}")
        print("=" * 50)

        return snapshot

    def _calc_health(self, coupling, anomalies):
        """计算世界模型健康度"""
        score = 100.0
        # 异常扣分
        for a in anomalies:
            score -= {"high": 10, "medium": 5, "low": 2}.get(a.get("severity", "low"), 2)
        # 维度均值偏差扣分
        dim_means = coupling.get("dimension_means", {})
        for d, val in dim_means.items():
            if val < 0.3:
                score -= 3
        # 强负耦合扣分
        for pair, corr in coupling.get("coupling_matrix", {}).items():
            if corr < -0.5:
                score -= 5
        score = max(0, round(score, 1))
        level = "excellent" if score >= 85 else "good" if score >= 70 else "fair" if score >= 50 else "critical"
        return {"score": score, "level": level, "anomaly_count": len(anomalies)}


if __name__ == "__main__":
    wm = EightDimensionWorldModel()
    wm.generate_snapshot()
