#!/usr/bin/env python3
"""
能力市场握手协议 V2.0 - 基础框架
ZONGYUAN-ROOT 全域进化第一阶段

核心能力：
1. 动态能力注册与发现
2. 能力质量评估与排序
3. 能力组合与协同
4. 能力演化与淘汰机制
5. 能力市场激励机制
"""

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class CapabilityStatus(Enum):
    """能力状态"""
    REGISTERED = "registered"        # 已注册
    VERIFIED = "verified"            # 已验证
    ACTIVE = "active"                # 活跃可用
    DEPRECATED = "deprecated"        # 已弃用
    RETIRED = "retired"              # 已淘汰


class CapabilityCategory(Enum):
    """能力类别"""
    COMPUTATION = "computation"      # 计算能力
    STORAGE = "storage"              # 存储能力
    NETWORK = "network"              # 网络能力
    INTELLIGENCE = "intelligence"    # 智能能力
    TRUTH = "truth"                  # 真值能力
    GOVERNANCE = "governance"        # 治理能力
    CREATION = "creation"            # 创作能力


@dataclass
class Capability:
    """能力描述"""
    capability_id: str
    name: str
    description: str
    category: CapabilityCategory
    version: str
    owner_node_id: str
    status: CapabilityStatus = CapabilityStatus.REGISTERED
    quality_score: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    registered_at: float = field(default_factory=time.time)
    last_used_at: Optional[float] = None
    capabilities: List[str] = field(default_factory=list)  # 依赖的其他能力
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def capability_hash(self) -> str:
        """计算能力哈希"""
        content = f"{self.capability_id}|{self.name}|{self.version}|{self.owner_node_id}"
        return hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "version": self.version,
            "owner_node_id": self.owner_node_id,
            "status": self.status.value,
            "quality_score": self.quality_score,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
            "registered_at": self.registered_at,
            "last_used_at": self.last_used_at,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "metadata": self.metadata,
            "capability_hash": self.capability_hash()
        }


@dataclass
class CapabilityMarket:
    """能力市场"""
    market_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capabilities: Dict[str, Capability] = field(default_factory=dict)
    node_capabilities: Dict[str, Set[str]] = field(default_factory=dict)  # node_id -> capability_ids
    usage_log: List[Dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def register_capability(self, capability: Capability) -> str:
        """注册能力"""
        self.capabilities[capability.capability_id] = capability

        # 记录节点拥有的能力
        if capability.owner_node_id not in self.node_capabilities:
            self.node_capabilities[capability.owner_node_id] = set()
        self.node_capabilities[capability.owner_node_id].add(capability.capability_id)

        return capability.capability_id

    def discover_capabilities(self, category: Optional[CapabilityCategory] = None,
                               min_quality: float = 0.0,
                               tags: Optional[List[str]] = None) -> List[Capability]:
        """发现能力"""
        results = []
        for cap in self.capabilities.values():
            if cap.status != CapabilityStatus.ACTIVE:
                continue
            if category and cap.category != category:
                continue
            if cap.quality_score < min_quality:
                continue
            if tags and not any(tag in cap.tags for tag in tags):
                continue
            results.append(cap)

        # 按质量分数排序
        results.sort(key=lambda x: x.quality_score, reverse=True)
        return results

    def get_node_capabilities(self, node_id: str) -> List[Capability]:
        """获取节点拥有的能力"""
        cap_ids = self.node_capabilities.get(node_id, set())
        return [self.capabilities[cid] for cid in cap_ids if cid in self.capabilities]

    def invoke_capability(self, capability_id: str, caller_node_id: str,
                          params: Dict) -> Dict:
        """调用能力（记录使用）"""
        if capability_id not in self.capabilities:
            return {"success": False, "error": "Capability not found"}

        cap = self.capabilities[capability_id]
        if cap.status != CapabilityStatus.ACTIVE:
            return {"success": False, "error": f"Capability is {cap.status.value}"}

        # 记录使用
        cap.usage_count += 1
        cap.last_used_at = time.time()

        usage_record = {
            "capability_id": capability_id,
            "caller_node_id": caller_node_id,
            "owner_node_id": cap.owner_node_id,
            "timestamp": time.time(),
            "params_hash": hashlib.sha256(str(params).encode()).hexdigest()
        }
        self.usage_log.append(usage_record)

        return {
            "success": True,
            "capability": cap.to_dict(),
            "invocation_id": str(uuid.uuid4()),
            "message": "Capability invoked successfully"
        }

    def update_quality_score(self, capability_id: str, success: bool,
                              response_time_ms: float) -> None:
        """更新能力质量分数"""
        if capability_id not in self.capabilities:
            return

        cap = self.capabilities[capability_id]

        # 更新成功率（指数移动平均）
        alpha = 0.1
        cap.success_rate = cap.success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha

        # 更新平均响应时间
        cap.avg_response_time_ms = cap.avg_response_time_ms * (1 - alpha) + response_time_ms * alpha

        # 计算综合质量分数（0-100）
        quality = (
            cap.success_rate * 50 +  # 成功率占50分
            min(1000 / max(cap.avg_response_time_ms, 1), 50) +  # 响应速度占50分
            min(cap.usage_count / 100, 10) * 0.5  # 使用量加成
        )
        cap.quality_score = min(quality, 100.0)

    def get_market_stats(self) -> Dict:
        """获取市场统计"""
        total = len(self.capabilities)
        active = sum(1 for c in self.capabilities.values() if c.status == CapabilityStatus.ACTIVE)
        categories = {}
        for cap in self.capabilities.values():
            cat = cap.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "market_id": self.market_id,
            "total_capabilities": total,
            "active_capabilities": active,
            "registered_nodes": len(self.node_capabilities),
            "total_invocations": len(self.usage_log),
            "categories": categories,
            "created_at": self.created_at
        }


@dataclass
class HandshakeV2:
    """握手协议V2.0 - 能力市场握手"""
    protocol_version: str = "2.0"
    market: CapabilityMarket = field(default_factory=CapabilityMarket)

    def handshake(self, node_id: str, node_capabilities: List[Dict],
                  state_hash: str, timestamp: int) -> Dict:
        """V2.0握手 - 包含能力市场协商"""
        # 1. 注册节点能力
        registered = []
        for cap_data in node_capabilities:
            cap = Capability(
                capability_id=cap_data.get("capability_id", str(uuid.uuid4())),
                name=cap_data.get("name", "unknown"),
                description=cap_data.get("description", ""),
                category=CapabilityCategory(cap_data.get("category", "computation")),
                version=cap_data.get("version", "1.0"),
                owner_node_id=node_id,
                status=CapabilityStatus.ACTIVE,
                tags=cap_data.get("tags", []),
                metadata=cap_data.get("metadata", {})
            )
            self.market.register_capability(cap)
            registered.append(cap.capability_id)

        # 2. 发现匹配能力（与节点能力互补的）
        node_cap_ids = set(registered)
        complementary = []
        for cap in self.market.discover_capabilities():
            if cap.capability_id not in node_cap_ids:
                complementary.append(cap.to_dict())

        # 3. 生成会话
        session_id = str(uuid.uuid4())

        return {
            "status": "handshake_established_v2",
            "protocol_version": self.protocol_version,
            "session_id": session_id,
            "node_id": node_id,
            "registered_capabilities": registered,
            "complementary_capabilities": complementary[:10],  # 返回前10个互补能力
            "market_stats": self.market.get_market_stats(),
            "state_hash": state_hash,
            "timestamp": timestamp,
            "heartbeat_interval": 30,
            "capability_market_endpoint": "/capability/market"
        }


# 全局能力市场实例
global_market = CapabilityMarket()

# 全局握手V2实例
global_handshake_v2 = HandshakeV2(market=global_market)


if __name__ == "__main__":
    # 测试能力市场
    print("=== 能力市场握手协议V2.0 测试 ===")

    # 注册测试能力
    test_cap = Capability(
        capability_id="CAP-TEST-001",
        name="测试计算能力",
        description="用于测试的计算能力",
        category=CapabilityCategory.COMPUTATION,
        version="1.0",
        owner_node_id="NODE-TEST-001",
        status=CapabilityStatus.ACTIVE,
        tags=["test", "computation"]
    )
    global_market.register_capability(test_cap)

    # 握手测试
    result = global_handshake_v2.handshake(
        node_id="NODE-TEST-002",
        node_capabilities=[{
            "name": "测试存储能力",
            "description": "用于测试的存储能力",
            "category": "storage",
            "version": "1.0",
            "tags": ["test", "storage"]
        }],
        state_hash="test_hash_123",
        timestamp=int(time.time())
    )

    print(f"握手状态: {result['status']}")
    print(f"协议版本: {result['protocol_version']}")
    print(f"会话ID: {result['session_id']}")
    print(f"注册能力数: {len(result['registered_capabilities'])}")
    print(f"互补能力数: {len(result['complementary_capabilities'])}")
    print(f"市场统计: {result['market_stats']}")
    print()
    print("=== 测试完成 ===")
