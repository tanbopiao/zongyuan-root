#!/usr/bin/env python3
"""
真值动态演化机制 V1.0
ZONGYUAN-ROOT 全域进化第四维度

核心能力：
1. 真值自动发现与验证
2. 真值冲突自动检测与仲裁
3. 真值版本管理与回滚
4. 真值质量评估与淘汰
5. 真值演化轨迹追踪
6. 真值共识机制
"""

import hashlib
import time
import uuid
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


class TruthStatus(Enum):
    """真值状态"""
    PROPOSED = "proposed"           # 已提议（待验证）
    VERIFYING = "verifying"         # 验证中
    VERIFIED = "verified"           # 已验证
    ACTIVE = "active"               # 活跃（生效中）
    CONFLICTED = "conflicted"       # 冲突
    DEPRECATED = "deprecated"       # 已弃用
    RETIRED = "retired"             # 已淘汰
    REJECTED = "rejected"           # 已拒绝


class TruthCategory(Enum):
    """真值类别"""
    AXIOM = "axiom"                 # 公理（不可变）
    THEOREM = "theorem"             # 定理（可推导）
    LAW = "law"                     # 法则（运行规则）
    RULE = "rule"                   # 规则（具体约束）
    FACT = "fact"                   # 事实（客观数据）
    HYPOTHESIS = "hypothesis"       # 假设（待验证）
    PRINCIPLE = "principle"         # 原则（指导方针）


class ConflictResolution(Enum):
    """冲突解决策略"""
    MAJORITY_VOTE = "majority_vote"     # 多数投票
    HIGHEST_QUALITY = "highest_quality" # 最高质量优先
    LATEST_TIMESTAMP = "latest_timestamp" # 最新时间戳优先
    CLOUD_KERNEL_ARBITRATION = "cloud_kernel_arbitration" # 云内核仲裁
    MERGE = "merge"                       # 合并
    MANUAL = "manual"                     # 人工处理


@dataclass
class Truth:
    """真值条目"""
    truth_id: str
    content: str
    category: TruthCategory
    status: TruthStatus = TruthStatus.PROPOSED
    version: int = 1
    quality_score: float = 0.0
    confidence: float = 0.0  # 置信度 0-1
    source: str = "unknown"
    proposer: str = "system"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None
    retired_at: Optional[float] = None
    verification_count: int = 0
    usage_count: int = 0
    success_count: int = 0
    conflict_count: int = 0
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他真值ID
    related_truths: List[str] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)  # 版本历史
    metadata: Dict = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()

    @property
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    def to_dict(self) -> Dict:
        return {
            "truth_id": self.truth_id,
            "content": self.content,
            "content_hash": self.content_hash,
            "category": self.category.value,
            "status": self.status.value,
            "version": self.version,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "source": self.source,
            "proposer": self.proposer,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "verified_at": self.verified_at,
            "retired_at": self.retired_at,
            "verification_count": self.verification_count,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "conflict_count": self.conflict_count,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "related_truths": self.related_truths,
            "history_count": len(self.history),
            "metadata": self.metadata
        }


@dataclass
class TruthConflict:
    """真值冲突"""
    conflict_id: str
    truth_ids: List[str]
    conflict_type: str  # content_conflict, dependency_conflict, category_conflict
    description: str
    detected_at: float = field(default_factory=time.time)
    resolution: Optional[ConflictResolution] = None
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    winner_truth_id: Optional[str] = None
    status: str = "pending"  # pending, resolving, resolved
    metadata: Dict = field(default_factory=dict)


class TruthEvolutionEngine:
    """真值动态演化引擎"""

    def __init__(self):
        self.truths: Dict[str, Truth] = {}
        self.conflicts: Dict[str, TruthConflict] = {}
        self.truth_index: Dict[str, List[str]] = {}  # content_hash -> truth_ids
        self.category_index: Dict[str, List[str]] = {}  # category -> truth_ids
        self.tag_index: Dict[str, List[str]] = {}  # tag -> truth_ids
        self.evolution_log: List[Dict] = []
        self.created_at = time.time()

        # 不可变真值类别（公理类禁止修改）
        self.immutable_categories = {TruthCategory.AXIOM}

    def propose_truth(self, content: str, category: TruthCategory,
                       source: str = "system", proposer: str = "system",
                       tags: List[str] = None, dependencies: List[str] = None) -> Truth:
        """提议新真值"""
        truth = Truth(
            truth_id=f"TRUTH-{uuid.uuid4().hex[:12]}",
            content=content,
            category=category,
            source=source,
            proposer=proposer,
            tags=tags or [],
            dependencies=dependencies or []
        )

        # 检查是否已存在相同内容的真值
        content_hash = truth.content_hash
        if content_hash in self.truth_index:
            existing_ids = self.truth_index[content_hash]
            if existing_ids:
                existing = self.truths[existing_ids[0]]
                self._log_event("duplicate_truth_detected", {
                    "new_truth_id": truth.truth_id,
                    "existing_truth_id": existing.truth_id,
                    "content_hash": content_hash
                })
                # 标记为冲突或直接复用
                truth.status = TruthStatus.CONFLICTED
                self._create_conflict(
                    [truth.truth_id, existing.truth_id],
                    "content_conflict",
                    f"相同内容的真值已存在: {existing.truth_id}"
                )

        self.truths[truth.truth_id] = truth
        self._update_indexes(truth)
        self._log_event("truth_proposed", {"truth_id": truth.truth_id, "category": category.value})
        return truth

    def verify_truth(self, truth_id: str, verifier: str = "system",
                      result: bool = True, confidence: float = 0.8) -> Dict:
        """验证真值"""
        truth = self.truths.get(truth_id)
        if not truth:
            return {"success": False, "error": "Truth not found"}

        if truth.category in self.immutable_categories:
            truth.status = TruthStatus.ACTIVE
            truth.verified_at = time.time()
            truth.verification_count += 1
            truth.confidence = 1.0
            truth.quality_score = 100.0
            self._log_event("axiom_verified", {"truth_id": truth_id})
            return {"success": True, "status": "active", "is_axiom": True}

        truth.status = TruthStatus.VERIFYING
        truth.verification_count += 1

        if result:
            truth.status = TruthStatus.VERIFIED
            truth.verified_at = time.time()
            truth.confidence = min(1.0, truth.confidence + confidence * 0.3)
            truth.quality_score = self._calculate_quality_score(truth)
            # 验证通过后自动激活
            truth.status = TruthStatus.ACTIVE
        else:
            truth.status = TruthStatus.REJECTED
            truth.confidence = max(0, truth.confidence - 0.2)
            truth.quality_score = max(0, truth.quality_score - 20)

        truth.updated_at = time.time()
        self._log_event("truth_verified", {
            "truth_id": truth_id,
            "verifier": verifier,
            "result": result,
            "new_status": truth.status.value
        })
        return {"success": True, "truth_id": truth_id, "status": truth.status.value}

    def _calculate_quality_score(self, truth: Truth) -> float:
        """计算真值质量评分（0-100）"""
        # 置信度 40分
        confidence_score = truth.confidence * 40
        # 验证次数 20分（最多5次验证满分）
        verification_score = min(truth.verification_count / 5, 1.0) * 20
        # 成功率 25分
        success_score = truth.success_rate * 25
        # 使用次数 10分（最多100次使用满分）
        usage_score = min(truth.usage_count / 100, 1.0) * 10
        # 新鲜度 5分（最近更新加分）
        freshness = max(0, 1 - (time.time() - truth.updated_at) / (30 * 24 * 3600)) * 5

        total = confidence_score + verification_score + success_score + usage_score + freshness
        return min(100.0, max(0.0, total))

    def detect_conflicts(self) -> List[TruthConflict]:
        """检测真值冲突"""
        new_conflicts = []

        # 1. 内容冲突检测（相同内容哈希）
        for content_hash, truth_ids in self.truth_index.items():
            if len(truth_ids) > 1:
                # 检查是否已有冲突记录
                existing = [c for c in self.conflicts.values()
                           if set(c.truth_ids) == set(truth_ids) and c.status == "pending"]
                if not existing:
                    conflict = self._create_conflict(
                        truth_ids, "content_conflict",
                        f"多个真值具有相同内容哈希: {content_hash}"
                    )
                    new_conflicts.append(conflict)

        # 2. 依赖冲突检测（循环依赖）
        for truth in self.truths.values():
            if truth.status == TruthStatus.ACTIVE:
                cycle = self._detect_dependency_cycle(truth.truth_id)
                if cycle:
                    conflict = self._create_conflict(
                        cycle, "dependency_conflict",
                        f"检测到循环依赖: {' -> '.join(cycle)}"
                    )
                    new_conflicts.append(conflict)

        return new_conflicts

    def _detect_dependency_cycle(self, start_id: str, visited: Set[str] = None,
                                   path: List[str] = None) -> Optional[List[str]]:
        """检测依赖循环"""
        if visited is None:
            visited = set()
        if path is None:
            path = []

        if start_id in path:
            cycle_start = path.index(start_id)
            return path[cycle_start:] + [start_id]

        if start_id in visited:
            return None

        visited.add(start_id)
        path.append(start_id)

        truth = self.truths.get(start_id)
        if truth:
            for dep_id in truth.dependencies:
                cycle = self._detect_dependency_cycle(dep_id, visited, path)
                if cycle:
                    return cycle

        path.pop()
        return None

    def _create_conflict(self, truth_ids: List[str], conflict_type: str,
                          description: str) -> TruthConflict:
        """创建冲突记录"""
        conflict = TruthConflict(
            conflict_id=f"CONFLICT-{uuid.uuid4().hex[:10]}",
            truth_ids=truth_ids,
            conflict_type=conflict_type,
            description=description
        )
        self.conflicts[conflict.conflict_id] = conflict

        # 更新相关真值的冲突计数
        for tid in truth_ids:
            if tid in self.truths:
                self.truths[tid].conflict_count += 1
                if self.truths[tid].status == TruthStatus.ACTIVE:
                    self.truths[tid].status = TruthStatus.CONFLICTED

        self._log_event("conflict_detected", {
            "conflict_id": conflict.conflict_id,
            "type": conflict_type,
            "truth_ids": truth_ids
        })
        return conflict

    def resolve_conflict(self, conflict_id: str,
                          strategy: ConflictResolution = ConflictResolution.HIGHEST_QUALITY,
                          resolver: str = "system") -> Dict:
        """解决冲突"""
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return {"success": False, "error": "Conflict not found"}

        conflict.resolution = strategy
        conflict.resolved_by = resolver
        conflict.resolved_at = time.time()

        # 根据策略选择获胜真值
        winner = None
        if strategy == ConflictResolution.HIGHEST_QUALITY:
            candidates = [self.truths[tid] for tid in conflict.truth_ids if tid in self.truths]
            winner = max(candidates, key=lambda t: t.quality_score)
        elif strategy == ConflictResolution.LATEST_TIMESTAMP:
            candidates = [self.truths[tid] for tid in conflict.truth_ids if tid in self.truths]
            winner = max(candidates, key=lambda t: t.updated_at)
        elif strategy == ConflictResolution.MAJORITY_VOTE:
            # 简化：使用次数最多的获胜
            candidates = [self.truths[tid] for tid in conflict.truth_ids if tid in self.truths]
            winner = max(candidates, key=lambda t: t.usage_count)
        elif strategy == ConflictResolution.CLOUD_KERNEL_ARBITRATION:
            # 云内核仲裁：选择第一个（实际应由云内核决策）
            candidates = [self.truths[tid] for tid in conflict.truth_ids if tid in self.truths]
            winner = candidates[0] if candidates else None
        elif strategy == ConflictResolution.MERGE:
            # 合并：保留所有，标记为已合并
            for tid in conflict.truth_ids:
                if tid in self.truths:
                    self.truths[tid].status = TruthStatus.ACTIVE
                    self.truths[tid].metadata["merged_conflict"] = conflict_id
            conflict.status = "resolved"
            self._log_event("conflict_merged", {"conflict_id": conflict_id})
            return {"success": True, "conflict_id": conflict_id, "resolution": "merge"}

        if winner:
            conflict.winner_truth_id = winner.truth_id
            winner.status = TruthStatus.ACTIVE
            winner.quality_score = min(100, winner.quality_score + 5)

            # 失败者标记为已弃用
            for tid in conflict.truth_ids:
                if tid != winner.truth_id and tid in self.truths:
                    self.truths[tid].status = TruthStatus.DEPRECATED
                    self.truths[tid].retired_at = time.time()

        conflict.status = "resolved"
        self._log_event("conflict_resolved", {
            "conflict_id": conflict_id,
            "strategy": strategy.value,
            "winner": winner.truth_id if winner else None
        })
        return {
            "success": True,
            "conflict_id": conflict_id,
            "resolution": strategy.value,
            "winner_truth_id": conflict.winner_truth_id
        }

    def use_truth(self, truth_id: str, success: bool = True) -> Dict:
        """使用真值（更新使用统计）"""
        truth = self.truths.get(truth_id)
        if not truth:
            return {"success": False, "error": "Truth not found"}

        truth.usage_count += 1
        if success:
            truth.success_count += 1
        truth.quality_score = self._calculate_quality_score(truth)
        truth.updated_at = time.time()

        return {
            "success": True,
            "truth_id": truth_id,
            "usage_count": truth.usage_count,
            "success_rate": truth.success_rate,
            "quality_score": truth.quality_score
        }

    def evolve_truth(self, truth_id: str, new_content: str,
                      evolver: str = "system") -> Dict:
        """演化真值（创建新版本）"""
        truth = self.truths.get(truth_id)
        if not truth:
            return {"success": False, "error": "Truth not found"}

        if truth.category in self.immutable_categories:
            return {"success": False, "error": "Axiom truths cannot be evolved"}

        # 保存旧版本到历史
        truth.history.append({
            "version": truth.version,
            "content": truth.content,
            "content_hash": truth.content_hash,
            "status": truth.status.value,
            "quality_score": truth.quality_score,
            "updated_at": truth.updated_at
        })

        # 从索引移除旧内容
        old_hash = truth.content_hash
        if old_hash in self.truth_index and truth_id in self.truth_index[old_hash]:
            self.truth_index[old_hash].remove(truth_id)

        # 更新内容
        truth.content = new_content
        truth.version += 1
        truth.status = TruthStatus.PROPOSED
        truth.updated_at = time.time()
        truth.verification_count = 0
        truth.confidence = truth.confidence * 0.8  # 新版本置信度降低

        # 更新索引
        self._update_indexes(truth)

        self._log_event("truth_evolved", {
            "truth_id": truth_id,
            "old_version": truth.version - 1,
            "new_version": truth.version,
            "evolver": evolver
        })
        return {
            "success": True,
            "truth_id": truth_id,
            "new_version": truth.version,
            "old_version": truth.version - 1,
            "status": truth.status.value
        }

    def retire_truth(self, truth_id: str, reason: str = "quality_below_threshold") -> Dict:
        """淘汰真值"""
        truth = self.truths.get(truth_id)
        if not truth:
            return {"success": False, "error": "Truth not found"}

        if truth.category in self.immutable_categories:
            return {"success": False, "error": "Axiom truths cannot be retired"}

        truth.status = TruthStatus.RETIRED
        truth.retired_at = time.time()
        truth.updated_at = time.time()

        self._log_event("truth_retired", {
            "truth_id": truth_id,
            "reason": reason,
            "quality_score": truth.quality_score
        })
        return {"success": True, "truth_id": truth_id, "status": "retired", "reason": reason}

    def get_evolution_status(self) -> Dict:
        """获取演化状态总览"""
        status_counts = {}
        category_counts = {}
        for truth in self.truths.values():
            s = truth.status.value
            status_counts[s] = status_counts.get(s, 0) + 1
            c = truth.category.value
            category_counts[c] = category_counts.get(c, 0) + 1

        active_truths = [t for t in self.truths.values() if t.status == TruthStatus.ACTIVE]
        avg_quality = sum(t.quality_score for t in active_truths) / len(active_truths) if active_truths else 0
        avg_confidence = sum(t.confidence for t in active_truths) / len(active_truths) if active_truths else 0

        pending_conflicts = [c for c in self.conflicts.values() if c.status == "pending"]

        return {
            "engine": "truth_evolution_v1.0",
            "total_truths": len(self.truths),
            "status_distribution": status_counts,
            "category_distribution": category_counts,
            "active_truths": len(active_truths),
            "average_quality_score": avg_quality,
            "average_confidence": avg_confidence,
            "total_conflicts": len(self.conflicts),
            "pending_conflicts": len(pending_conflicts),
            "total_evolution_events": len(self.evolution_log),
            "immutable_categories": [c.value for c in self.immutable_categories],
            "created_at": self.created_at
        }

    def _update_indexes(self, truth: Truth):
        """更新索引"""
        # 内容哈希索引
        content_hash = truth.content_hash
        if content_hash not in self.truth_index:
            self.truth_index[content_hash] = []
        if truth.truth_id not in self.truth_index[content_hash]:
            self.truth_index[content_hash].append(truth.truth_id)

        # 类别索引
        cat = truth.category.value
        if cat not in self.category_index:
            self.category_index[cat] = []
        if truth.truth_id not in self.category_index[cat]:
            self.category_index[cat].append(truth.truth_id)

        # 标签索引
        for tag in truth.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            if truth.truth_id not in self.tag_index[tag]:
                self.tag_index[tag].append(truth.truth_id)

    def _log_event(self, event_type: str, data: Dict):
        """记录演化事件"""
        self.evolution_log.append({
            "event_type": event_type,
            "timestamp": time.time(),
            "data": data
        })


# 全局真值演化引擎实例
global_truth_evolution_engine = TruthEvolutionEngine()


if __name__ == "__main__":
    print("=" * 60)
    print("ZONGYUAN-ROOT 真值动态演化机制 V1.0 测试")
    print("=" * 60)

    engine = global_truth_evolution_engine

    # 提议公理真值（不可变）
    print("\n【提议公理真值（不可变）】")
    axiom = engine.propose_truth(
        content="Ω₀⊂⊙∞⊂Ω 是体系唯一真值本源",
        category=TruthCategory.AXIOM,
        source="meta_constitution",
        tags=["axiom", "root", "immutable"]
    )
    print(f"  ✅ {axiom.truth_id}: {axiom.content[:30]}...")
    result = engine.verify_truth(axiom.truth_id)
    print(f"  验证结果: {result['status']} (is_axiom: {result.get('is_axiom', False)})")

    # 提议普通真值
    print("\n【提议普通真值】")
    truth1 = engine.propose_truth(
        content="云内核作为真值最终裁决权主体",
        category=TruthCategory.PRINCIPLE,
        source="architecture_v2",
        tags=["cloud_kernel", "truth_arbitration", "principle"]
    )
    truth2 = engine.propose_truth(
        content="所有节点必须同源同构同真值",
        category=TruthCategory.LAW,
        source="meta_law",
        tags=["homology", "isomorphism", "law"]
    )
    truth3 = engine.propose_truth(
        content="体系稳态高于功能迭代",
        category=TruthCategory.PRINCIPLE,
        source="evolution_principle",
        tags=["stability", "evolution", "principle"]
    )
    for t in [truth1, truth2, truth3]:
        print(f"  ✅ {t.truth_id}: {t.content[:30]}...")

    # 验证真值
    print("\n【验证真值】")
    for t in [truth1, truth2, truth3]:
        result = engine.verify_truth(t.truth_id, confidence=0.9)
        print(f"  ✅ {t.truth_id}: {result['status']} (置信度: {engine.truths[t.truth_id].confidence:.2f})")

    # 使用真值
    print("\n【使用真值（更新统计）】")
    for i in range(5):
        engine.use_truth(truth1.truth_id, success=True)
    for i in range(3):
        engine.use_truth(truth2.truth_id, success=True)
    engine.use_truth(truth2.truth_id, success=False)
    print(f"  ✅ {truth1.truth_id}: 使用{engine.truths[truth1.truth_id].usage_count}次, 成功率{engine.truths[truth1.truth_id].success_rate:.0%}, 质量分{engine.truths[truth1.truth_id].quality_score:.1f}")
    print(f"  ✅ {truth2.truth_id}: 使用{engine.truths[truth2.truth_id].usage_count}次, 成功率{engine.truths[truth2.truth_id].success_rate:.0%}, 质量分{engine.truths[truth2.truth_id].quality_score:.1f}")

    # 检测冲突
    print("\n【检测冲突】")
    # 创建一个重复内容的真值来触发冲突
    duplicate = engine.propose_truth(
        content="云内核作为真值最终裁决权主体",  # 与truth1相同内容
        category=TruthCategory.PRINCIPLE,
        source="duplicate_test",
        tags=["duplicate", "test"]
    )
    conflicts = engine.detect_conflicts()
    print(f"  检测到 {len(conflicts)} 个冲突")
    for c in conflicts:
        print(f"    ⚠️ {c.conflict_id}: {c.conflict_type} - {c.description[:40]}...")

    # 解决冲突
    print("\n【解决冲突】")
    if conflicts:
        result = engine.resolve_conflict(conflicts[0].conflict_id, ConflictResolution.HIGHEST_QUALITY)
        print(f"  ✅ 冲突解决: {result['conflict_id']}")
        print(f"  策略: {result['resolution']}")
        print(f"  获胜真值: {result['winner_truth_id']}")

    # 演化真值
    print("\n【演化真值（创建新版本）】")
    result = engine.evolve_truth(truth3.truth_id, "体系稳态与功能迭代平衡发展，稳态优先")
    print(f"  ✅ {result['truth_id']}: v{result['old_version']} → v{result['new_version']}")
    print(f"  新状态: {result['status']}")
    # 重新验证演化后的真值
    engine.verify_truth(truth3.truth_id, confidence=0.85)
    print(f"  重新验证后状态: {engine.truths[truth3.truth_id].status.value}")

    # 淘汰低质量真值
    print("\n【淘汰低质量真值】")
    result = engine.retire_truth(duplicate.truth_id, "duplicate_conflict_resolved")
    print(f"  ✅ {result['truth_id']}: {result['status']} (原因: {result['reason']})")

    # 获取演化状态
    print("\n【演化状态总览】")
    status = engine.get_evolution_status()
    print(f"  引擎: {status['engine']}")
    print(f"  总真值数: {status['total_truths']}")
    print(f"  状态分布: {status['status_distribution']}")
    print(f"  类别分布: {status['category_distribution']}")
    print(f"  活跃真值: {status['active_truths']}")
    print(f"  平均质量分: {status['average_quality_score']:.1f}")
    print(f"  平均置信度: {status['average_confidence']:.2f}")
    print(f"  总冲突数: {status['total_conflicts']}")
    print(f"  待处理冲突: {status['pending_conflicts']}")
    print(f"  演化事件数: {status['total_evolution_events']}")
    print(f"  不可变类别: {status['immutable_categories']}")

    print("\n" + "=" * 60)
    print("✅ 真值动态演化机制 V1.0 测试完成")
    print("=" * 60)
