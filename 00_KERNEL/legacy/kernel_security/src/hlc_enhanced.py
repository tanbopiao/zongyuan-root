"""
ZONGYUAN-ROOT HLC增强版哈希逻辑链
版本: V2.0 (增强版·身份绑定+数字签名+分布式验证)
溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT V1.7

核心增强:
1. HLC节点绑定完整身份认证信息(mTLS证书指纹+JWT jti+Scope)
2. 节点私钥数字签名,实现不可否认
3. 轻量级分布式验证(任意节点拿根哈希即可验证)
4. Merkle树批量验证
5. 单主多从同步框架
"""

import hashlib
import json
import os
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# ============================================================
# 常量定义
# ============================================================

GENESIS_HASH = "0" * 64  # 创世节点prev_hash
DEFAULT_STORAGE_DIR = "./hlc_data"
ANCHOR_FILENAME = "ANCHOR.json"
NODES_DIR = "nodes"
MERKLE_INDEX_FILENAME = "merkle_index.json"


# ============================================================
# 枚举类型
# ============================================================

class NodeType(Enum):
    """节点类型"""
    CLOUD_KERNEL = "cloud-kernel"
    LOCAL_KERNEL = "local-kernel"
    COMPUTE_NODE = "compute-node"
    STORAGE_NODE = "storage-node"
    GATEWAY_NODE = "gateway-node"
    OBSERVER_NODE = "observer-node"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PayloadType(Enum):
    """载荷类型"""
    TRUTH_ASSET = "truth_asset"
    PROTOCOL_REGISTER = "protocol_register"
    NODE_HEARTBEAT = "node_heartbeat"
    TASK_EXECUTION = "task_execution"
    CONFIG_CHANGE = "config_change"
    AUDIT_LOG = "audit_log"
    SNAPSHOT = "snapshot"
    MERGE_NODE = "merge_node"


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ActorInfo:
    """写入者身份信息(绑定mTLS+JWT+Scope)"""
    node_id: str  # 节点ID
    node_type: str  # 节点类型
    did: str = "DID-BR-000002"  # 去中心化标识符
    cert_fingerprint: str = ""  # mTLS证书指纹(SHA256)
    jwt_jti: str = ""  # JWT令牌唯一标识
    scope_used: str = ""  # 使用的Scope权限
    session_id: str = ""  # 会话ID

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ExecutionInfo:
    """执行信息(内核二次校验+沙箱执行)"""
    sandbox_id: str = ""  # 沙箱ID
    risk_level: str = RiskLevel.LOW.value  # 风险等级
    contract_check: str = "passed"  # 契约校验结果
    duration_ms: int = 0  # 执行耗时(毫秒)
    resource_usage: Dict = field(default_factory=lambda: {
        "cpu_ms": 0,
        "memory_kb": 0
    })

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Payload:
    """数据载荷"""
    type: str  # 载荷类型
    content_hash: str  # 内容哈希(SHA256)
    content_ref: str = ""  # 内容引用(路径/URL)
    metadata: Dict = field(default_factory=dict)  # 元数据

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class HLCNode:
    """HLC哈希链节点(增强版)"""
    node_id: str  # 节点唯一ID
    height: int  # 链高度
    prev_hash: str  # 前一个节点哈希
    timestamp: str  # ISO8601时间戳
    actor: ActorInfo  # 写入者身份信息
    payload: Payload  # 数据载荷
    execution: ExecutionInfo  # 执行信息
    this_hash: str = ""  # 本节点哈希
    signature: str = ""  # 数字签名(节点私钥)
    merkle_proof: Dict = field(default_factory=dict)  # Merkle证明

    def calculate_hash(self) -> str:
        """计算本节点哈希(排除this_hash和signature和merkle_proof)"""
        node_dict = {
            "node_id": self.node_id,
            "height": self.height,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "actor": self.actor.to_dict(),
            "payload": self.payload.to_dict(),
            "execution": self.execution.to_dict(),
        }
        json_str = json.dumps(node_dict, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    def verify_hash(self) -> bool:
        """验证本节点哈希完整性"""
        return self.calculate_hash() == self.this_hash

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "height": self.height,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "actor": self.actor.to_dict(),
            "payload": self.payload.to_dict(),
            "execution": self.execution.to_dict(),
            "this_hash": self.this_hash,
            "signature": self.signature,
            "merkle_proof": self.merkle_proof,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'HLCNode':
        return cls(
            node_id=data["node_id"],
            height=data["height"],
            prev_hash=data["prev_hash"],
            timestamp=data["timestamp"],
            actor=ActorInfo(**data["actor"]),
            payload=Payload(**data["payload"]),
            execution=ExecutionInfo(**data["execution"]),
            this_hash=data.get("this_hash", ""),
            signature=data.get("signature", ""),
            merkle_proof=data.get("merkle_proof", {}),
        )


@dataclass
class Anchor:
    """锚点文件(当前链状态)"""
    chain_id: str  # 链ID
    height: int  # 当前链高度
    root_hash: str  # Merkle根哈希
    tip_hash: str  # 链尖端节点哈希
    last_update: str  # 最后更新时间
    node_count: int  # 节点总数
    writer_node_id: str = ""  # 当前写入者节点ID(单主模式)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================
# Merkle树
# ============================================================

class MerkleTree:
    """Merkle树(用于批量验证)"""

    def __init__(self):
        self.leaves: List[str] = []
        self.tree: List[List[str]] = []

    def add_leaf(self, leaf_hash: str):
        """添加叶子节点"""
        self.leaves.append(leaf_hash)

    def build(self) -> str:
        """构建Merkle树,返回根哈希"""
        if not self.leaves:
            return hashlib.sha256(b"empty").hexdigest()

        self.tree = [self.leaves[:]]
        current_level = self.leaves[:]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            self.tree.append(next_level)
            current_level = next_level

        return current_level[0]

    def get_proof(self, index: int) -> Dict:
        """获取指定叶子节点的Merkle证明"""
        if not self.tree or index >= len(self.leaves):
            return {}

        proof = {
            "leaf_index": index,
            "leaf_hash": self.leaves[index],
            "path": []
        }

        current_index = index
        for level in range(len(self.tree) - 1):
            level_nodes = self.tree[level]
            is_left = current_index % 2 == 0
            sibling_index = current_index + 1 if is_left else current_index - 1

            if sibling_index < len(level_nodes):
                proof["path"].append({
                    "direction": "right" if is_left else "left",
                    "hash": level_nodes[sibling_index]
                })
            else:
                # 奇数节点时,最后一个节点被复制(自己和自己配对)
                # sibling就是当前节点自己
                proof["path"].append({
                    "direction": "right" if is_left else "left",
                    "hash": level_nodes[current_index]
                })

            current_index //= 2

        return proof

    @staticmethod
    def verify_proof(proof: Dict, root_hash: str) -> bool:
        """验证Merkle证明"""
        if not proof or "leaf_hash" not in proof or "path" not in proof:
            return False

        current_hash = proof["leaf_hash"]

        for step in proof["path"]:
            if step["direction"] == "right":
                combined = current_hash + step["hash"]
            else:
                combined = step["hash"] + current_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()

        return current_hash == root_hash


# ============================================================
# 数字签名(简化版·实际使用时替换为真实的RSA/ECDSA)
# ============================================================

class SignatureManager:
    """数字签名管理器(简化版)
    
    注意: 这是简化实现,生产环境应使用:
    - RSA-PSS / ECDSA / Ed25519
    - 私钥存储在TPM/HSM/Keychain中,不可导出
    - 证书链验证通过mTLS层完成
    """

    def __init__(self, private_key: str = "", public_key: str = ""):
        self.private_key = private_key or hashlib.sha256(b"default-private-key").hexdigest()
        self.public_key = public_key or hashlib.sha256(self.private_key.encode()).hexdigest()

    def sign(self, data_hash: str) -> str:
        """对数据哈希进行签名(简化版)"""
        combined = data_hash + self.private_key
        return hashlib.sha256(combined.encode()).hexdigest()

    def verify(self, data_hash: str, signature: str, public_key: str = "") -> bool:
        """验证签名(简化版)
        
        注意: 这是简化实现,生产环境应使用非对称加密(RSA-PSS/ECDSA/Ed25519)。
        简化版中,公钥由私钥派生,验证时需要用原始私钥重新计算签名。
        """
        # 简化验证: 用当前实例的私钥重新计算签名进行比对
        # (实际非对称加密中,验证只需要公钥,不需要私钥)
        expected = self.sign(data_hash)
        return expected == signature


# ============================================================
# HLC核心引擎
# ============================================================

class HLCEngine:
    """HLC哈希逻辑链核心引擎(增强版)"""

    def __init__(self, storage_dir: str = DEFAULT_STORAGE_DIR, 
                 node_id: str = "default-node",
                 node_type: str = NodeType.LOCAL_KERNEL.value,
                 signature_manager: Optional[SignatureManager] = None):
        self.storage_dir = storage_dir
        self.node_id = node_id
        self.node_type = node_type
        self.sig_manager = signature_manager or SignatureManager()
        
        self.merkle_tree = MerkleTree()
        self.anchor: Optional[Anchor] = None
        self.nodes: Dict[str, HLCNode] = {}
        
        self._init_storage()
        self._load_anchor()
        self._load_nodes()

    def _init_storage(self):
        """初始化存储目录"""
        os.makedirs(os.path.join(self.storage_dir, NODES_DIR), exist_ok=True)

    def _load_anchor(self):
        """加载锚点文件"""
        anchor_path = os.path.join(self.storage_dir, ANCHOR_FILENAME)
        if os.path.exists(anchor_path):
            with open(anchor_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.anchor = Anchor(**data)
        else:
            # 创建新链
            self.anchor = Anchor(
                chain_id=str(uuid.uuid4()),
                height=0,
                root_hash=GENESIS_HASH,
                tip_hash=GENESIS_HASH,
                last_update=self._now_iso(),
                node_count=0,
                writer_node_id=self.node_id,
            )
            self._save_anchor()

    def _save_anchor(self):
        """保存锚点文件(原子写入)"""
        anchor_path = os.path.join(self.storage_dir, ANCHOR_FILENAME)
        tmp_path = anchor_path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self.anchor.to_dict(), f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, anchor_path)  # 原子替换

    def _load_nodes(self):
        """加载所有节点"""
        nodes_dir = os.path.join(self.storage_dir, NODES_DIR)
        if not os.path.exists(nodes_dir):
            return

        for filename in os.listdir(nodes_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(nodes_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        node = HLCNode.from_dict(data)
                        self.nodes[node.node_id] = node
                        self.merkle_tree.add_leaf(node.this_hash)
                except Exception as e:
                    print(f"[WARN] 加载节点失败 {filename}: {e}")

        # 重建Merkle树
        if self.nodes:
            sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.height)
            self.merkle_tree = MerkleTree()
            for node in sorted_nodes:
                self.merkle_tree.add_leaf(node.this_hash)
            self.merkle_tree.build()

    def _save_node(self, node: HLCNode):
        """保存节点到文件"""
        nodes_dir = os.path.join(self.storage_dir, NODES_DIR)
        filename = f"node_{node.height:08d}_{node.node_id}.json"
        filepath = os.path.join(nodes_dir, filename)
        tmp_path = filepath + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(node.to_dict(), f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, filepath)

    @staticmethod
    def _now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def append_node(self, payload: Payload, 
                    actor: Optional[ActorInfo] = None,
                    execution: Optional[ExecutionInfo] = None,
                    cert_fingerprint: str = "",
                    jwt_jti: str = "",
                    scope_used: str = "") -> HLCNode:
        """追加新节点到链尾
        
        Args:
            payload: 数据载荷
            actor: 写入者身份信息(可选,默认使用当前节点)
            execution: 执行信息(可选)
            cert_fingerprint: mTLS证书指纹(可选)
            jwt_jti: JWT令牌ID(可选)
            scope_used: 使用的Scope(可选)
            
        Returns:
            新创建的HLC节点
        """
        # 构建身份信息
        if actor is None:
            actor = ActorInfo(
                node_id=self.node_id,
                node_type=self.node_type,
                cert_fingerprint=cert_fingerprint,
                jwt_jti=jwt_jti,
                scope_used=scope_used,
            )

        if execution is None:
            execution = ExecutionInfo()

        # 创建节点
        new_height = self.anchor.height + 1
        node = HLCNode(
            node_id=f"node_{new_height:08d}_{uuid.uuid4().hex[:8]}",
            height=new_height,
            prev_hash=self.anchor.tip_hash,
            timestamp=self._now_iso(),
            actor=actor,
            payload=payload,
            execution=execution,
        )

        # 计算哈希
        node.this_hash = node.calculate_hash()

        # 数字签名
        node.signature = self.sig_manager.sign(node.this_hash)

        # 保存节点
        self._save_node(node)
        self.nodes[node.node_id] = node

        # 更新Merkle树
        self.merkle_tree.add_leaf(node.this_hash)
        new_root = self.merkle_tree.build()

        # 生成Merkle证明
        node_index = len(self.merkle_tree.leaves) - 1
        node.merkle_proof = self.merkle_tree.get_proof(node_index)
        self._save_node(node)  # 重新保存(含merkle_proof)

        # 更新锚点
        self.anchor.height = new_height
        self.anchor.tip_hash = node.this_hash
        self.anchor.root_hash = new_root
        self.anchor.node_count = len(self.nodes)
        self.anchor.last_update = self._now_iso()
        self.anchor.writer_node_id = self.node_id
        self._save_anchor()

        return node

    def verify_node(self, node: HLCNode, 
                    verify_signature: bool = True,
                    verify_prev_chain: bool = True) -> Tuple[bool, List[str]]:
        """验证单个节点
        
        Returns:
            (是否通过, 错误信息列表)
        """
        errors = []

        # 1. 验证哈希完整性
        if not node.verify_hash():
            errors.append(f"节点哈希不匹配: 计算值={node.calculate_hash()[:16]}..., 存储值={node.this_hash[:16]}...")

        # 2. 验证数字签名
        if verify_signature and node.signature:
            # 注意: 实际验证需要从证书中获取公钥,这里简化
            if not self.sig_manager.verify(node.this_hash, node.signature):
                errors.append("数字签名验证失败")

        # 3. 验证prev链
        if verify_prev_chain and node.height > 1:
            # 查找前一个节点
            prev_node = self._find_node_by_hash(node.prev_hash)
            if prev_node is None:
                errors.append(f"前一个节点不存在: prev_hash={node.prev_hash[:16]}...")
            elif prev_node.height != node.height - 1:
                errors.append(f"prev链高度不连续: prev高度={prev_node.height}, 当前高度={node.height}")

        # 4. 验证时间戳合理性
        # (简化: 不检查未来时间,实际应检查)

        return (len(errors) == 0, errors)

    def _find_node_by_hash(self, node_hash: str) -> Optional[HLCNode]:
        """通过哈希查找节点"""
        for node in self.nodes.values():
            if node.this_hash == node_hash:
                return node
        return None

    def verify_full_chain(self) -> Tuple[bool, List[str]]:
        """验证整条链的完整性"""
        errors = []

        if not self.nodes:
            return (True, ["空链"])

        # 按高度排序
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.height)

        # 验证每个节点
        prev_hash = GENESIS_HASH
        for i, node in enumerate(sorted_nodes):
            ok, node_errors = self.verify_node(node, verify_prev_chain=False)
            if not ok:
                errors.extend([f"[高度{node.height}] {e}" for e in node_errors])

            # 验证prev链连续性
            if node.prev_hash != prev_hash:
                errors.append(f"[高度{node.height}] prev链断裂: 期望={prev_hash[:16]}..., 实际={node.prev_hash[:16]}...")

            prev_hash = node.this_hash

        # 验证Merkle根
        calculated_root = self.merkle_tree.build()
        if calculated_root != self.anchor.root_hash:
            errors.append(f"Merkle根不匹配: 计算值={calculated_root[:16]}..., 锚点值={self.anchor.root_hash[:16]}...")

        # 验证链尖端
        if sorted_nodes[-1].this_hash != self.anchor.tip_hash:
            errors.append(f"链尖端不匹配: 最后节点={sorted_nodes[-1].this_hash[:16]}..., 锚点={self.anchor.tip_hash[:16]}...")

        return (len(errors) == 0, errors)

    def get_node_by_height(self, height: int, refresh_merkle_proof: bool = True) -> Optional[HLCNode]:
        """按高度获取节点
        
        Args:
            height: 链高度
            refresh_merkle_proof: 是否刷新Merkle证明(树增长后旧证明会失效)
        """
        for node in self.nodes.values():
            if node.height == height:
                if refresh_merkle_proof:
                    # 用当前Merkle树重新生成证明
                    sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.height)
                    for idx, n in enumerate(sorted_nodes):
                        if n.node_id == node.node_id:
                            node.merkle_proof = self.merkle_tree.get_proof(idx)
                            break
                return node
        return None

    def get_latest_nodes(self, count: int = 10) -> List[HLCNode]:
        """获取最新的N个节点"""
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.height, reverse=True)
        return sorted_nodes[:count]

    def get_chain_stats(self) -> Dict:
        """获取链统计信息"""
        return {
            "chain_id": self.anchor.chain_id,
            "height": self.anchor.height,
            "node_count": self.anchor.node_count,
            "root_hash": self.anchor.root_hash,
            "tip_hash": self.anchor.tip_hash,
            "last_update": self.anchor.last_update,
            "writer_node_id": self.anchor.writer_node_id,
            "storage_dir": self.storage_dir,
        }


# ============================================================
# 轻量级分布式验证器
# ============================================================

class DistributedVerifier:
    """轻量级分布式验证器
    
    核心价值: 任意节点拿到 锚点根哈希 + 节点数据 + Merkle证明 
    即可独立验证节点的真实性和完整性,不需要信任任何中心化节点。
    """

    @staticmethod
    def verify_lightweight(node_data: Dict, 
                           merkle_proof: Dict,
                           anchor_root_hash: str,
                           public_key: str = "") -> Tuple[bool, List[str]]:
        """轻量级验证单个节点(不需要全链数据)
        
        Args:
            node_data: 节点数据字典
            merkle_proof: Merkle证明
            anchor_root_hash: 锚点根哈希(可从公开渠道获取)
            public_key: 写入者公钥(用于验证签名,可选)
            
        Returns:
            (是否通过, 错误信息列表)
        """
        errors = []

        try:
            node = HLCNode.from_dict(node_data)
        except Exception as e:
            return (False, [f"节点数据解析失败: {e}"])

        # 1. 验证节点哈希
        if not node.verify_hash():
            errors.append("节点哈希不匹配(数据被篡改)")

        # 2. 验证数字签名(如果提供了公钥)
        if public_key and node.signature:
            sig_manager = SignatureManager(public_key=public_key)
            if not sig_manager.verify(node.this_hash, node.signature, public_key):
                errors.append("数字签名验证失败(写入者身份不可信)")

        # 3. 验证Merkle证明(节点属于锚点根哈希声明的集合)
        if merkle_proof:
            if not MerkleTree.verify_proof(merkle_proof, anchor_root_hash):
                errors.append("Merkle证明验证失败(节点不在链中)")
        else:
            errors.append("缺少Merkle证明(无法验证节点是否在链中)")

        # 4. 验证身份信息(简化检查)
        if not node.actor.node_id:
            errors.append("缺少写入者节点ID")
        if not node.actor.cert_fingerprint:
            errors.append("缺少mTLS证书指纹(身份未绑定)")

        # 5. 验证时间戳(简化: 不检查未来时间)
        # (实际应检查时间戳是否在合理范围内)

        return (len(errors) == 0, errors)

    @staticmethod
    def verify_batch(nodes_with_proofs: List[Tuple[Dict, Dict]],
                     anchor_root_hash: str,
                     public_keys: Dict[str, str] = None) -> Dict:
        """批量验证多个节点
        
        Args:
            nodes_with_proofs: [(节点数据, Merkle证明), ...]
            anchor_root_hash: 锚点根哈希
            public_keys: {node_id: public_key} 公钥映射
            
        Returns:
            验证结果统计
        """
        results = {
            "total": len(nodes_with_proofs),
            "passed": 0,
            "failed": 0,
            "details": []
        }

        for i, (node_data, proof) in enumerate(nodes_with_proofs):
            node_id = node_data.get("actor", {}).get("node_id", "unknown")
            pub_key = (public_keys or {}).get(node_id, "")
            
            ok, errors = DistributedVerifier.verify_lightweight(
                node_data, proof, anchor_root_hash, pub_key
            )
            
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "index": i,
                "node_id": node_id,
                "height": node_data.get("height"),
                "passed": ok,
                "errors": errors
            })

        return results


# ============================================================
# 单主多从同步框架
# ============================================================

class MasterSlaveSync:
    """单主多从同步框架(方案A·最小可行分布式)
    
    主节点: 唯一Writer,持有写权限
    从节点: 只读+验证,定期从主节点拉取新节点
    """

    def __init__(self, engine: HLCEngine, role: str = "slave"):
        self.engine = engine
        self.role = role  # "master" or "slave"
        self.last_sync_height = engine.anchor.height

    def export_new_nodes(self, from_height: int = 0) -> List[Dict]:
        """主节点: 导出从指定高度开始的新节点(用于同步到从节点)"""
        if self.role != "master":
            raise PermissionError("只有主节点可以导出节点")

        new_nodes = []
        for node in self.engine.nodes.values():
            if node.height > from_height:
                new_nodes.append(node.to_dict())

        return sorted(new_nodes, key=lambda n: n["height"])

    def export_anchor(self) -> Dict:
        """主节点: 导出锚点状态"""
        return self.engine.anchor.to_dict()

    def import_nodes(self, nodes_data: List[Dict], 
                     anchor_data: Dict,
                     verify: bool = True) -> Tuple[int, List[str]]:
        """从节点: 导入主节点的新节点
        
        Args:
            nodes_data: 节点数据列表
            anchor_data: 锚点数据
            verify: 是否验证导入的节点
            
        Returns:
            (导入成功数量, 错误信息列表)
        """
        if self.role != "slave":
            raise PermissionError("只有从节点可以导入节点")

        errors = []
        imported = 0

        for node_data in sorted(nodes_data, key=lambda n: n["height"]):
            try:
                node = HLCNode.from_dict(node_data)

                # 验证节点
                if verify:
                    ok, node_errors = self.engine.verify_node(node, verify_prev_chain=True)
                    if not ok:
                        errors.extend([f"[高度{node.height}] 验证失败: {e}" for e in node_errors])
                        continue

                # 检查是否已存在
                if node.node_id in self.engine.nodes:
                    continue

                # 检查prev链是否连续
                if node.prev_hash != self.engine.anchor.tip_hash:
                    errors.append(f"[高度{node.height}] prev链不连续,跳过")
                    continue

                # 导入节点
                self.engine._save_node(node)
                self.engine.nodes[node.node_id] = node
                self.engine.merkle_tree.add_leaf(node.this_hash)

                # 更新锚点
                self.engine.anchor.height = node.height
                self.engine.anchor.tip_hash = node.this_hash
                self.engine.anchor.node_count = len(self.engine.nodes)
                self.engine.anchor.last_update = node.timestamp
                self.engine._save_anchor()

                imported += 1

            except Exception as e:
                errors.append(f"导入节点失败: {e}")

        # 重建Merkle树并验证根
        if self.engine.nodes:
            sorted_nodes = sorted(self.engine.nodes.values(), key=lambda n: n.height)
            self.engine.merkle_tree = MerkleTree()
            for n in sorted_nodes:
                self.engine.merkle_tree.add_leaf(n.this_hash)
            calculated_root = self.engine.merkle_tree.build()

            if calculated_root != anchor_data.get("root_hash"):
                errors.append(f"Merkle根不匹配(同步后): 计算={calculated_root[:16]}..., 主节点={anchor_data.get('root_hash', '')[:16]}...")

        self.last_sync_height = self.engine.anchor.height
        return (imported, errors)


# ============================================================
# 单元测试
# ============================================================

def run_tests():
    """运行单元测试"""
    print("=" * 60)
    print("ZONGYUAN-ROOT HLC增强版 单元测试")
    print("=" * 60)

    import tempfile
    import shutil

    test_dir = tempfile.mkdtemp(prefix="hlc_test_")
    passed = 0
    failed = 0

    try:
        # 测试1: 初始化引擎
        print("\n[测试1] 初始化HLC引擎...")
        engine = HLCEngine(storage_dir=test_dir, node_id="test-node-001")
        stats = engine.get_chain_stats()
        assert stats["height"] == 0, f"初始高度应为0,实际{stats['height']}"
        print("  ✅ 通过")
        passed += 1

        # 测试2: 追加节点
        print("\n[测试2] 追加节点...")
        payload = Payload(
            type=PayloadType.TRUTH_ASSET.value,
            content_hash=hashlib.sha256(b"test content").hexdigest(),
            content_ref="/truth/test/001",
            metadata={"test": "value"}
        )
        node = engine.append_node(
            payload=payload,
            cert_fingerprint="sha256:test_cert_fingerprint",
            jwt_jti="test_jwt_jti_001",
            scope_used="truth:write:self"
        )
        assert node.height == 1, f"高度应为1,实际{node.height}"
        assert node.actor.cert_fingerprint == "sha256:test_cert_fingerprint"
        assert node.signature != "", "签名不应为空"
        print(f"  ✅ 通过 (node_id={node.node_id}, hash={node.this_hash[:16]}...)")
        passed += 1

        # 测试3: 验证节点
        print("\n[测试3] 验证节点完整性...")
        ok, errors = engine.verify_node(node)
        assert ok, f"节点验证失败: {errors}"
        print("  ✅ 通过")
        passed += 1

        # 测试4: 追加多个节点
        print("\n[测试4] 追加多个节点...")
        for i in range(10):
            p = Payload(
                type=PayloadType.AUDIT_LOG.value,
                content_hash=hashlib.sha256(f"log_{i}".encode()).hexdigest(),
                content_ref=f"/log/{i}"
            )
            engine.append_node(p, cert_fingerprint="sha256:test_cert_fingerprint")
        stats = engine.get_chain_stats()
        assert stats["height"] == 11, f"高度应为11,实际{stats['height']}"
        print(f"  ✅ 通过 (当前高度={stats['height']})")
        passed += 1

        # 测试5: 全链验证
        print("\n[测试5] 全链完整性验证...")
        ok, errors = engine.verify_full_chain()
        assert ok, f"全链验证失败: {errors}"
        print("  ✅ 通过")
        passed += 1

        # 测试6: 轻量级分布式验证
        print("\n[测试6] 轻量级分布式验证...")
        test_node = engine.get_node_by_height(5)
        verifier = DistributedVerifier()
        ok, errors = verifier.verify_lightweight(
            node_data=test_node.to_dict(),
            merkle_proof=test_node.merkle_proof,
            anchor_root_hash=engine.anchor.root_hash
        )
        assert ok, f"轻量级验证失败: {errors}"
        print("  ✅ 通过 (任意节点可独立验证)")
        passed += 1

        # 测试7: 篡改检测
        print("\n[测试7] 篡改检测...")
        tampered_node = engine.get_node_by_height(3)
        tampered_data = tampered_node.to_dict()
        tampered_data["payload"]["metadata"]["test"] = "tampered"  # 篡改数据
        ok, errors = verifier.verify_lightweight(
            node_data=tampered_data,
            merkle_proof=tampered_node.merkle_proof,
            anchor_root_hash=engine.anchor.root_hash
        )
        assert not ok, "篡改后应验证失败"
        print(f"  ✅ 通过 (成功检测到篡改: {errors[0][:40]}...)")
        passed += 1

        # 测试8: 单主多从同步
        print("\n[测试8] 单主多从同步...")
        slave_dir = tempfile.mkdtemp(prefix="hlc_slave_")
        master_engine = engine
        slave_engine = HLCEngine(storage_dir=slave_dir, node_id="slave-node-001")
        
        master_sync = MasterSlaveSync(master_engine, role="master")
        slave_sync = MasterSlaveSync(slave_engine, role="slave")
        
        # 主节点导出
        new_nodes = master_sync.export_new_nodes(from_height=0)
        anchor_data = master_sync.export_anchor()
        
        # 从节点导入
        imported, errors = slave_sync.import_nodes(new_nodes, anchor_data, verify=True)
        assert imported == 11, f"应导入11个节点,实际{imported}"
        assert slave_engine.anchor.height == 11, f"从节点高度应为11"
        print(f"  ✅ 通过 (同步{imported}个节点,从节点高度={slave_engine.anchor.height})")
        passed += 1
        
        shutil.rmtree(slave_dir, ignore_errors=True)

        # 测试9: Merkle树验证
        print("\n[测试9] Merkle树验证...")
        for i in range(1, 12):
            node = engine.get_node_by_height(i)
            proof = node.merkle_proof
            assert MerkleTree.verify_proof(proof, engine.anchor.root_hash), f"高度{i}的Merkle证明验证失败"
        print("  ✅ 通过 (所有节点Merkle证明验证通过)")
        passed += 1

        # 测试10: 身份信息绑定
        print("\n[测试10] 身份信息绑定验证...")
        node = engine.get_node_by_height(1)
        assert node.actor.node_id == "test-node-001"
        assert node.actor.cert_fingerprint != ""
        assert node.actor.jwt_jti != ""
        assert node.actor.scope_used != ""
        assert node.signature != ""
        print("  ✅ 通过 (mTLS证书指纹+JWT jti+Scope+数字签名全部绑定)")
        passed += 1

    except AssertionError as e:
        print(f"  ❌ 断言失败: {e}")
        failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        print("ZONGYUAN-ROOT HLC增强版哈希逻辑链 V2.0")
        print("溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT V1.7")
        print()
        print("用法:")
        print("  python hlc_enhanced.py test    # 运行单元测试")
        print()
        print("核心能力:")
        print("  1. HLC节点绑定完整身份认证信息(mTLS+JWT+Scope)")
        print("  2. 节点私钥数字签名,实现不可否认")
        print("  3. 轻量级分布式验证(任意节点拿根哈希即可验证)")
        print("  4. Merkle树批量验证")
        print("  5. 单主多从同步框架")
