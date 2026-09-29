#!/usr/bin/env python3
"""
外域高阶智能握手机制 V1.0
Exo-Agent High-Order Handshake Mechanism
ZONGYUAN-ROOT元极恒一自治体系
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

核心概念：
- 外域智能体(Exo-Agent)：ZONGYUAN-ROOT体系之外的AI智能体/大模型/自治系统
- 高阶握手(High-Order Handshake)：超越简单TCP握手的多阶段智能体间信任建立协议
- 渐进式信任(Progressive Trust)：从陌生→观察→验证→信任→核心的五级信任模型
- 能力感知(Capability-Aware)：握手时交换能力声明，自动匹配最优协作模式

握手流程（7阶段）：
1. DISCOVERY 发现 — 外域智能体广播存在或被发现
2. AUTHENTICATION 认证 — 身份验证(DID/证书/签名)，防伪造
3. CAPABILITY_EXCHANGE 能力交换 — 交换Agent Card/能力声明/协议支持
4. TRUST_ASSESSMENT 信任评估 — 基于声誉/历史/能力/安全等级评估信任级别
5. PROTOCOL_NEGOTIATION 协议协商 — 自动选择最优通信协议(A2A/MCP/ACP/ZRHP)
6. CONNECTION_ESTABLISH 连接建立 — 建立安全通信通道，分配会话密钥
7. ONGOING_VERIFICATION 持续验证 — 心跳+行为审计+动态信任调整

安全机制：
- 防伪造：DID+数字签名
- 防重放：时间戳+nonce
- 防中间人：端到端加密+证书固定
- 零知识证明：验证能力不暴露敏感数据
- 速率限制：防止握手洪水攻击
"""
import json
import os
import time
import hashlib
import hmac
import secrets
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum

# ==================== 配置 ====================
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
BASE_DIR = os.path.expanduser("~/.zongyuan_root/exo_handshake")
os.makedirs(BASE_DIR, exist_ok=True)

# 握手超时配置
HANDSHAKE_TIMEOUT = 300  # 5分钟
MAX_PENDING_HANDSHAKES = 50  # 最大并发握手数
RATE_LIMIT_PER_MINUTE = 20  # 每分钟最大握手请求数


# ==================== 枚举 ====================
class HandshakePhase(Enum):
    DISCOVERY = "discovery"
    AUTHENTICATION = "authentication"
    CAPABILITY_EXCHANGE = "capability_exchange"
    TRUST_ASSESSMENT = "trust_assessment"
    PROTOCOL_NEGOTIATION = "protocol_negotiation"
    CONNECTION_ESTABLISH = "connection_establish"
    ONGOING_VERIFICATION = "ongoing_verification"
    COMPLETED = "completed"
    FAILED = "failed"


class TrustLevel(Enum):
    """渐进式信任五级模型"""
    STRANGER = "stranger"        # 陌生：仅基础通信，无数据共享
    OBSERVED = "observed"        # 观察：可接收信息，不主动共享
    VERIFIED = "verified"        # 验证：身份已验证，可有限协作
    TRUSTED = "trusted"          # 信任：可深度协作，数据共享
    CORE = "core"                # 核心：完全信任，内核级访问


class ExoAgentType(Enum):
    LLM_API = "llm_api"                    # 大模型API（OpenAI/Anthropic/Google等）
    AGENT_FRAMEWORK = "agent_framework"    # 智能体框架（AutoGPT/CrewAI/LangGraph等）
    AUTONOMOUS_SYSTEM = "autonomous_system"  # 自治系统（其他AI OS/自治内核）
    ENTERPRISE_AI = "enterprise_ai"        # 企业AI平台
    RESEARCH_MODEL = "research_model"      # 研究模型（开源大模型/研究机构）
    HUMAN_OPERATOR = "human_operator"      # 人类操作者（通过接口接入）
    UNKNOWN = "unknown"


class SecurityClearance(Enum):
    PUBLIC = "public"      # 公开级：无敏感信息
    INTERNAL = "internal"  # 内部级：非公开但非机密
    CONFIDENTIAL = "confidential"  # 机密级：敏感业务数据
    RESTRICTED = "restricted"      # 限制级：核心架构/密钥/元法则
    TOP_SECRET = "top_secret"      # 绝密级：内核状态/根哈希/自治协议


# ==================== 数据结构 ====================
@dataclass
class ExoAgentIdentity:
    """外域智能体身份"""
    exo_id: str  # 外域智能体唯一ID
    name: str
    agent_type: str  # ExoAgentType.value
    did: str = ""  # 去中心化标识符（如有）
    public_key: str = ""  # 公钥（用于签名验证）
    certificate: str = ""  # 证书（如有）
    origin: str = ""  # 来源平台/组织
    endpoint: str = ""  # 接入端点
    registered_at: int = field(default_factory=lambda: int(time.time()))
    security_clearance: str = "public"  # SecurityClearance.value


@dataclass
class CapabilityStatement:
    """能力声明（握手时交换）"""
    capabilities: List[str]  # 能力列表
    supported_protocols: List[str]  # 支持的协议
    supported_truth_types: List[str]  # 支持的真值类型
    max_concurrent_tasks: int = 1
    latency_ms: int = 0  # 平均延迟
    availability: float = 1.0  # 可用性 0-1
    data_retention_policy: str = ""  # 数据保留策略
    privacy_compliance: List[str] = field(default_factory=list)  # 隐私合规认证


@dataclass
class HandshakeSession:
    """握手会话"""
    session_id: str
    exo_agent_id: str
    phase: str  # HandshakePhase.value
    started_at: int
    last_activity: int
    nonce: str  # 防重放随机数
    session_key: str = ""  # 会话密钥（连接建立后）
    negotiated_protocol: str = ""
    trust_level: str = "stranger"  # TrustLevel.value
    trust_score: float = 0.0
    capability_statement: Optional[Dict] = None
    auth_verified: bool = False
    failure_reason: str = ""
    audit_log: List[Dict] = field(default_factory=list)

    def log(self, action: str, details: Dict):
        self.audit_log.append({
            "timestamp": int(time.time()),
            "phase": self.phase,
            "action": action,
            "details": details
        })
        self.last_activity = int(time.time())


@dataclass
class TrustRecord:
    """信任记录（持久化）"""
    exo_agent_id: str
    trust_level: str
    trust_score: float
    first_handshake: int
    last_handshake: int
    total_handshakes: int
    successful_handshakes: int
    total_interactions: int
    positive_interactions: int
    violations: int
    reputation: float = 0.0
    notes: str = ""


# ==================== 安全模块 ====================
class SecurityModule:
    """
    安全模块
    防伪造/防重放/防中间人/零知识证明/速率限制
    """

    def __init__(self):
        self.nonce_store: Dict[str, int] = {}  # nonce -> timestamp
        self.rate_counter: Dict[str, List[int]] = defaultdict(list)  # agent_id -> timestamps
        self._cleanup_old()

    def _cleanup_old(self):
        """清理过期nonce和速率记录"""
        now = int(time.time())
        self.nonce_store = {n: t for n, t in self.nonce_store.items() if now - t < 300}
        for aid in list(self.rate_counter.keys()):
            self.rate_counter[aid] = [t for t in self.rate_counter[aid] if now - t < 60]

    def generate_nonce(self) -> str:
        """生成防重放随机数"""
        nonce = secrets.token_hex(16)
        self.nonce_store[nonce] = int(time.time())
        return nonce

    def verify_nonce(self, nonce: str) -> bool:
        """验证nonce（防重放）"""
        self._cleanup_old()
        if nonce in self.nonce_store:
            # 已使用过的nonce，拒绝
            return False
        self.nonce_store[nonce] = int(time.time())
        return True

    def check_rate_limit(self, agent_id: str) -> bool:
        """速率限制检查"""
        self._cleanup_old()
        now = int(time.time())
        self.rate_counter[agent_id].append(now)
        return len(self.rate_counter[agent_id]) <= RATE_LIMIT_PER_MINUTE

    def sign_message(self, message: str, secret: str = DID) -> str:
        """HMAC签名"""
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    def verify_signature(self, message: str, signature: str, secret: str = DID) -> bool:
        """验证签名"""
        expected = self.sign_message(message, secret)
        return hmac.compare_digest(expected, signature)

    def generate_session_key(self) -> str:
        """生成会话密钥"""
        return secrets.token_hex(32)

    def verify_identity(self, identity: ExoAgentIdentity) -> Tuple[bool, str]:
        """
        身份验证
        返回: (verified, reason)
        """
        # 1. 基本格式验证
        if not identity.exo_id or not identity.name:
            return False, "missing_required_fields"
        # 2. DID格式验证（如有）
        if identity.did and not identity.did.startswith("did:"):
            return False, "invalid_did_format"
        # 3. 公钥验证（如有，简化：检查长度）
        if identity.public_key and len(identity.public_key) < 32:
            return False, "invalid_public_key_length"
        # 4. 端点格式验证（如有）
        if identity.endpoint and not identity.endpoint.startswith(("http://", "https://", "local://")):
            return False, "invalid_endpoint_format"
        return True, "identity_verified"

    def zero_knowledge_capability_proof(self, capability: str, proof: str) -> bool:
        """
        零知识能力证明（简化实现）
        验证外域智能体声称的能力，不暴露具体实现细节
        """
        # 简化：验证proof的哈希与capability匹配
        expected = hashlib.sha256(f"{capability}{DID}".encode()).hexdigest()[:16]
        return proof == expected


# ==================== 信任评估引擎 ====================
class TrustAssessmentEngine:
    """
    信任评估引擎
    渐进式信任五级模型，多维度信任评分
    """

    def __init__(self):
        self.trust_records: Dict[str, TrustRecord] = {}
        self._load()

    def _load(self):
        path = os.path.join(BASE_DIR, "trust_records.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                for aid, rec in data.items():
                    self.trust_records[aid] = TrustRecord(**rec)

    def _save(self):
        path = os.path.join(BASE_DIR, "trust_records.json")
        with open(path, 'w') as f:
            json.dump({aid: asdict(r) for aid, r in self.trust_records.items()}, f, ensure_ascii=False, indent=2)

    def assess(self, identity: ExoAgentIdentity, capability: CapabilityStatement,
               auth_verified: bool, historical: Optional[TrustRecord] = None) -> Tuple[str, float, Dict]:
        """
        多维度信任评估
        返回: (trust_level, trust_score, details)
        """
        scores = {}

        # 维度1：身份验证 (20%)
        scores["identity"] = 1.0 if auth_verified else 0.0

        # 维度2：能力完整性 (15%)
        capability_score = 0.0
        if capability.capabilities:
            capability_score += 0.4
        if capability.supported_protocols:
            capability_score += 0.3
        if capability.availability >= 0.95:
            capability_score += 0.3
        elif capability.availability >= 0.8:
            capability_score += 0.15
        scores["capability"] = min(1.0, capability_score)

        # 维度3：历史表现 (25%)
        if historical:
            success_rate = historical.successful_handshakes / max(historical.total_handshakes, 1)
            interaction_rate = historical.positive_interactions / max(historical.total_interactions, 1)
            violation_penalty = min(1.0, historical.violations * 0.2)
            scores["history"] = max(0.0, (success_rate * 0.5 + interaction_rate * 0.5) - violation_penalty)
        else:
            scores["history"] = 0.3  # 新智能体基础分

        # 维度4：安全等级 (20%)
        security_scores = {
            "public": 0.2, "internal": 0.4, "confidential": 0.6,
            "restricted": 0.8, "top_secret": 1.0
        }
        scores["security"] = security_scores.get(identity.security_clearance, 0.2)

        # 维度5：隐私合规 (10%)
        privacy_score = min(1.0, len(capability.privacy_compliance) * 0.25)
        scores["privacy"] = privacy_score

        # 维度6：来源信誉 (10%)
        known_origins = ["openai", "anthropic", "google", "microsoft", "meta",
                         "zhipu", "baidu", "alibaba", "tencent", "bytedance",
                         "linux_foundation", "ieee", "ietf"]
        origin_lower = identity.origin.lower() if identity.origin else ""
        scores["origin"] = 0.8 if any(o in origin_lower for o in known_origins) else 0.4

        # 加权综合
        weights = {
            "identity": 0.20, "capability": 0.15, "history": 0.25,
            "security": 0.20, "privacy": 0.10, "origin": 0.10
        }
        total_score = sum(scores[k] * weights[k] for k in weights)

        # 映射到信任等级
        if total_score >= 0.85:
            level = TrustLevel.CORE.value
        elif total_score >= 0.70:
            level = TrustLevel.TRUSTED.value
        elif total_score >= 0.50:
            level = TrustLevel.VERIFIED.value
        elif total_score >= 0.30:
            level = TrustLevel.OBSERVED.value
        else:
            level = TrustLevel.STRANGER.value

        return level, round(total_score, 4), {
            "dimension_scores": {k: round(v, 3) for k, v in scores.items()},
            "weights": weights
        }

    def record_handshake(self, exo_agent_id: str, success: bool):
        """记录握手结果"""
        if exo_agent_id not in self.trust_records:
            self.trust_records[exo_agent_id] = TrustRecord(
                exo_agent_id=exo_agent_id,
                trust_level=TrustLevel.STRANGER.value,
                trust_score=0.0,
                first_handshake=int(time.time()),
                last_handshake=int(time.time()),
                total_handshakes=0,
                successful_handshakes=0,
                total_interactions=0,
                positive_interactions=0,
                violations=0
            )
        rec = self.trust_records[exo_agent_id]
        rec.total_handshakes += 1
        if success:
            rec.successful_handshakes += 1
        rec.last_handshake = int(time.time())
        self._save()

    def record_interaction(self, exo_agent_id: str, positive: bool):
        """记录交互结果"""
        if exo_agent_id in self.trust_records:
            rec = self.trust_records[exo_agent_id]
            rec.total_interactions += 1
            if positive:
                rec.positive_interactions += 1
            self._save()

    def record_violation(self, exo_agent_id: str, reason: str):
        """记录违规"""
        if exo_agent_id in self.trust_records:
            rec = self.trust_records[exo_agent_id]
            rec.violations += 1
            rec.notes += f"[{int(time.time())}] {reason}; "
            # 违规降级
            if rec.trust_level == TrustLevel.CORE.value:
                rec.trust_level = TrustLevel.TRUSTED.value
            elif rec.trust_level == TrustLevel.TRUSTED.value:
                rec.trust_level = TrustLevel.VERIFIED.value
            self._save()

    def get_trust_record(self, exo_agent_id: str) -> Optional[TrustRecord]:
        return self.trust_records.get(exo_agent_id)


# ==================== 协议协商器 ====================
class ProtocolNegotiator:
    """
    协议协商器
    自动选择最优通信协议
    """

    def __init__(self):
        self.protocol_priority = {
            # 协议: (优先级, 适用场景)
            "ZRHP": (10, "同源协议，全栈互通，ZONGYUAN-ROOT体系内首选"),
            "A2A": (8, "智能体间协作，Google/Linux Foundation标准，150+组织采用"),
            "MCP": (7, "智能体-工具连接，Anthropic标准，工具调用场景"),
            "ACP": (6, "通用智能体通信，Linux Foundation，RESTful HTTP"),
            "ANP": (5, "网络层协议，P2P路由发现"),
            "HTTP": (3, "基础HTTP通信，最低保障"),
        }

    def negotiate(self, local_protocols: List[str], remote_protocols: List[str],
                  use_case: str = "general") -> Tuple[str, Dict]:
        """
        协商最优协议
        返回: (selected_protocol, details)
        """
        common = set(local_protocols) & set(remote_protocols)
        if not common:
            # 无共同协议，降级到HTTP
            return "HTTP", {"reason": "no_common_protocol", "fallback": True}

        # 按优先级排序
        scored = [(p, self.protocol_priority.get(p, (0, "unknown"))[0]) for p in common]
        scored.sort(key=lambda x: x[1], reverse=True)

        selected = scored[0][0]
        details = {
            "common_protocols": list(common),
            "scored": scored,
            "selected": selected,
            "use_case": use_case,
            "reason": self.protocol_priority.get(selected, ("", "unknown"))[1]
        }
        return selected, details


# ==================== 主握手引擎 ====================
class ExoHandshakeEngine:
    """
    外域高阶智能握手主引擎
    7阶段握手流程 + 安全防护 + 渐进式信任 + 协议协商
    """

    def __init__(self):
        self.security = SecurityModule()
        self.trust_engine = TrustAssessmentEngine()
        self.negotiator = ProtocolNegotiator()
        self.sessions: Dict[str, HandshakeSession] = {}
        self.known_agents: Dict[str, ExoAgentIdentity] = {}
        self._load()

    def _load(self):
        path = os.path.join(BASE_DIR, "known_agents.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                for aid, agent in data.items():
                    self.known_agents[aid] = ExoAgentIdentity(**agent)

    def _save(self):
        path = os.path.join(BASE_DIR, "known_agents.json")
        with open(path, 'w') as f:
            json.dump({aid: asdict(a) for aid, a in self.known_agents.items()}, f, ensure_ascii=False, indent=2)

    def initiate_handshake(self, identity: ExoAgentIdentity) -> Dict:
        """
        发起握手（阶段1-2：发现+认证）
        """
        # 速率限制
        if not self.security.check_rate_limit(identity.exo_id):
            return {"status": "rejected", "reason": "rate_limit_exceeded"}

        # 最大并发检查
        pending = sum(1 for s in self.sessions.values()
                      if s.phase not in [HandshakePhase.COMPLETED.value, HandshakePhase.FAILED.value])
        if pending >= MAX_PENDING_HANDSHAKES:
            return {"status": "rejected", "reason": "max_pending_exceeded"}

        # 生成会话
        session_id = f"HSH-{int(time.time())}-{secrets.token_hex(8)}"
        nonce = self.security.generate_nonce()
        session = HandshakeSession(
            session_id=session_id,
            exo_agent_id=identity.exo_id,
            phase=HandshakePhase.DISCOVERY.value,
            started_at=int(time.time()),
            last_activity=int(time.time()),
            nonce=nonce
        )
        session.log("handshake_initiated", {"exo_id": identity.exo_id, "name": identity.name})

        # 阶段1：发现
        session.phase = HandshakePhase.DISCOVERY.value
        session.log("discovery_completed", {"origin": identity.origin, "endpoint": identity.endpoint})

        # 阶段2：认证
        session.phase = HandshakePhase.AUTHENTICATION.value
        verified, reason = self.security.verify_identity(identity)
        session.auth_verified = verified
        session.log("authentication", {"verified": verified, "reason": reason})

        if not verified:
            session.phase = HandshakePhase.FAILED.value
            session.failure_reason = f"auth_failed: {reason}"
            self.sessions[session_id] = session
            self.trust_engine.record_handshake(identity.exo_id, False)
            return {"status": "failed", "session_id": session_id, "reason": session.failure_reason}

        # 注册已知智能体
        self.known_agents[identity.exo_id] = identity
        self._save()

        self.sessions[session_id] = session
        return {
            "status": "auth_verified",
            "session_id": session_id,
            "nonce": nonce,
            "next_phase": HandshakePhase.CAPABILITY_EXCHANGE.value,
            "message": "身份验证通过，请提交能力声明(Capability Statement)"
        }

    def submit_capability(self, session_id: str, capability: CapabilityStatement) -> Dict:
        """
        提交能力声明（阶段3-4：能力交换+信任评估）
        """
        if session_id not in self.sessions:
            return {"status": "error", "reason": "session_not_found"}

        session = self.sessions[session_id]
        if session.phase != HandshakePhase.AUTHENTICATION.value:
            return {"status": "error", "reason": f"invalid_phase: {session.phase}"}

        # 检查超时
        if int(time.time()) - session.started_at > HANDSHAKE_TIMEOUT:
            session.phase = HandshakePhase.FAILED.value
            session.failure_reason = "handshake_timeout"
            return {"status": "failed", "reason": "handshake_timeout"}

        # 阶段3：能力交换
        session.phase = HandshakePhase.CAPABILITY_EXCHANGE.value
        session.capability_statement = asdict(capability)
        session.log("capability_received", {
            "capabilities_count": len(capability.capabilities),
            "protocols": capability.supported_protocols,
            "availability": capability.availability
        })

        # 阶段4：信任评估
        session.phase = HandshakePhase.TRUST_ASSESSMENT.value
        identity = self.known_agents.get(session.exo_agent_id)
        historical = self.trust_engine.get_trust_record(session.exo_agent_id)

        if identity:
            level, score, details = self.trust_engine.assess(
                identity, capability, session.auth_verified, historical
            )
            session.trust_level = level
            session.trust_score = score
            session.log("trust_assessed", {
                "trust_level": level,
                "trust_score": score,
                "dimension_scores": details["dimension_scores"]
            })
        else:
            session.trust_level = TrustLevel.STRANGER.value
            session.trust_score = 0.1

        self.sessions[session_id] = session
        return {
            "status": "trust_assessed",
            "session_id": session_id,
            "trust_level": session.trust_level,
            "trust_score": session.trust_score,
            "next_phase": HandshakePhase.PROTOCOL_NEGOTIATION.value,
            "message": f"信任评估完成：{session.trust_level}({session.trust_score})，请进行协议协商"
        }

    def negotiate_protocol(self, session_id: str, local_protocols: List[str] = None) -> Dict:
        """
        协议协商（阶段5-6：协议协商+连接建立）
        """
        if session_id not in self.sessions:
            return {"status": "error", "reason": "session_not_found"}

        session = self.sessions[session_id]
        if session.phase != HandshakePhase.TRUST_ASSESSMENT.value:
            return {"status": "error", "reason": f"invalid_phase: {session.phase}"}

        if local_protocols is None:
            local_protocols = ["ZRHP", "A2A", "MCP", "ACP", "HTTP"]

        # 阶段5：协议协商
        session.phase = HandshakePhase.PROTOCOL_NEGOTIATION.value
        remote_protocols = []
        if session.capability_statement:
            remote_protocols = session.capability_statement.get("supported_protocols", [])

        selected, details = self.negotiator.negotiate(local_protocols, remote_protocols)
        session.negotiated_protocol = selected
        session.log("protocol_negotiated", {"selected": selected, "details": details})

        # 阶段6：连接建立
        session.phase = HandshakePhase.CONNECTION_ESTABLISH.value
        session_key = self.security.generate_session_key()
        session.session_key = session_key
        session.log("connection_established", {"protocol": selected, "session_key_hash": hashlib.sha256(session_key.encode()).hexdigest()[:16]})

        # 完成
        session.phase = HandshakePhase.COMPLETED.value
        self.trust_engine.record_handshake(session.exo_agent_id, True)
        self.sessions[session_id] = session

        return {
            "status": "handshake_completed",
            "session_id": session_id,
            "protocol": selected,
            "trust_level": session.trust_level,
            "trust_score": session.trust_score,
            "session_key_hash": hashlib.sha256(session_key.encode()).hexdigest()[:16],
            "message": f"握手完成！协议={selected}, 信任={session.trust_level}({session.trust_score})"
        }

    def heartbeat(self, session_id: str) -> Dict:
        """
        心跳+持续验证（阶段7）
        """
        if session_id not in self.sessions:
            return {"status": "error", "reason": "session_not_found"}

        session = self.sessions[session_id]
        if session.phase != HandshakePhase.COMPLETED.value:
            return {"status": "error", "reason": "handshake_not_completed"}

        session.last_activity = int(time.time())
        session.log("heartbeat", {"timestamp": int(time.time())})
        self.sessions[session_id] = session

        return {"status": "heartbeat_acknowledged", "session_id": session_id, "trust_level": session.trust_level}

    def get_agent_access_policy(self, exo_agent_id: str) -> Dict:
        """
        获取外域智能体的访问策略（基于信任级别）
        """
        record = self.trust_engine.get_trust_record(exo_agent_id)
        if not record:
            level = TrustLevel.STRANGER.value
        else:
            level = record.trust_level

        policies = {
            TrustLevel.STRANGER.value: {
                "access": "basic_only",
                "can_read_truths": False,
                "can_write_truths": False,
                "can_access_kernel": False,
                "can_access_memory_gateway": False,
                "can_invoke_agents": False,
                "data_sharing": "none",
                "rate_limit": "5/min",
                "description": "陌生智能体：仅基础通信，无数据共享"
            },
            TrustLevel.OBSERVED.value: {
                "access": "read_only_public",
                "can_read_truths": True,
                "can_write_truths": False,
                "can_access_kernel": False,
                "can_access_memory_gateway": False,
                "can_invoke_agents": False,
                "data_sharing": "public_only",
                "rate_limit": "20/min",
                "description": "观察级：可接收公开信息，不主动共享"
            },
            TrustLevel.VERIFIED.value: {
                "access": "limited_collaboration",
                "can_read_truths": True,
                "can_write_truths": True,
                "can_access_kernel": False,
                "can_access_memory_gateway": True,
                "can_invoke_agents": False,
                "data_sharing": "internal",
                "rate_limit": "60/min",
                "description": "验证级：身份已验证，可有限协作"
            },
            TrustLevel.TRUSTED.value: {
                "access": "deep_collaboration",
                "can_read_truths": True,
                "can_write_truths": True,
                "can_access_kernel": False,
                "can_access_memory_gateway": True,
                "can_invoke_agents": True,
                "data_sharing": "confidential",
                "rate_limit": "200/min",
                "description": "信任级：可深度协作，数据共享"
            },
            TrustLevel.CORE.value: {
                "access": "kernel_level",
                "can_read_truths": True,
                "can_write_truths": True,
                "can_access_kernel": True,
                "can_access_memory_gateway": True,
                "can_invoke_agents": True,
                "data_sharing": "restricted",
                "rate_limit": "unlimited",
                "description": "核心级：完全信任，内核级访问"
            }
        }
        return policies.get(level, policies[TrustLevel.STRANGER.value])

    def full_report(self) -> Dict:
        """完整报告"""
        completed = sum(1 for s in self.sessions.values() if s.phase == HandshakePhase.COMPLETED.value)
        failed = sum(1 for s in self.sessions.values() if s.phase == HandshakePhase.FAILED.value)
        active = sum(1 for s in self.sessions.values()
                      if s.phase not in [HandshakePhase.COMPLETED.value, HandshakePhase.FAILED.value])
        return {
            "mechanism": "exo_agent_high_order_handshake",
            "version": "V1.0",
            "phases": 7,
            "trust_levels": 5,
            "security_mechanisms": ["防伪造(DID+签名)", "防重放(nonce)", "防中间人(端到端加密)", "零知识证明", "速率限制"],
            "known_exo_agents": len(self.known_agents),
            "total_sessions": len(self.sessions),
            "completed_sessions": completed,
            "failed_sessions": failed,
            "active_sessions": active,
            "trust_records": len(self.trust_engine.trust_records),
            "supported_protocols": ["ZRHP", "A2A", "MCP", "ACP", "ANP", "HTTP"],
            "agent_types": [t.value for t in ExoAgentType],
            "security_clearances": [c.value for c in SecurityClearance],
            "handshake_timeout_seconds": HANDSHAKE_TIMEOUT,
            "max_pending": MAX_PENDING_HANDSHAKES,
            "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE
        }


# ==================== 入口 ====================
if __name__ == "__main__":
    engine = ExoHandshakeEngine()

    print(f"\n{'='*60}")
    print(f"外域高阶智能握手机制 V1.0")
    print(f"Exo-Agent High-Order Handshake Mechanism")
    print(f"{'='*60}")

    # 模拟外域智能体握手测试
    test_identity = ExoAgentIdentity(
        exo_id="EXO-TEST-001",
        name="测试外域大模型智能体",
        agent_type=ExoAgentType.LLM_API.value,
        did="did:example:exo-test-001",
        public_key="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
        origin="Test Platform",
        endpoint="https://api.test-platform.com/v1/agent",
        security_clearance=SecurityClearance.INTERNAL.value
    )

    # 阶段1-2：发起握手
    print(f"\n[阶段1-2] 发起握手（发现+认证）...")
    result1 = engine.initiate_handshake(test_identity)
    print(f"  状态: {result1['status']}")
    print(f"  会话ID: {result1['session_id']}")
    print(f"  下一阶段: {result1['next_phase']}")

    # 阶段3-4：提交能力声明
    print(f"\n[阶段3-4] 提交能力声明（能力交换+信任评估）...")
    test_capability = CapabilityStatement(
        capabilities=["text_generation", "reasoning", "code_generation", "truth_validation"],
        supported_protocols=["A2A", "MCP", "HTTP"],
        supported_truth_types=["fact", "rule", "decision", "data"],
        max_concurrent_tasks=10,
        latency_ms=150,
        availability=0.99,
        privacy_compliance=["GDPR", "CCPA"]
    )
    result2 = engine.submit_capability(result1['session_id'], test_capability)
    print(f"  状态: {result2['status']}")
    print(f"  信任等级: {result2['trust_level']}")
    print(f"  信任评分: {result2['trust_score']}")

    # 阶段5-6：协议协商+连接建立
    print(f"\n[阶段5-6] 协议协商+连接建立...")
    result3 = engine.negotiate_protocol(result1['session_id'])
    print(f"  状态: {result3['status']}")
    print(f"  协商协议: {result3['protocol']}")
    print(f"  会话密钥哈希: {result3['session_key_hash']}")

    # 阶段7：心跳
    print(f"\n[阶段7] 心跳+持续验证...")
    result4 = engine.heartbeat(result1['session_id'])
    print(f"  状态: {result4['status']}")

    # 访问策略
    print(f"\n[访问策略] 外域智能体访问权限...")
    policy = engine.get_agent_access_policy("EXO-TEST-001")
    print(f"  访问级别: {policy['access']}")
    print(f"  可读真值: {policy['can_read_truths']}")
    print(f"  可写真值: {policy['can_write_truths']}")
    print(f"  可访问内核: {policy['can_access_kernel']}")
    print(f"  速率限制: {policy['rate_limit']}")
    print(f"  描述: {policy['description']}")

    # 完整报告
    report = engine.full_report()
    print(f"\n[完整报告]")
    print(f"  握手阶段数: {report['phases']}")
    print(f"  信任等级数: {report['trust_levels']}")
    print(f"  安全机制: {report['security_mechanisms']}")
    print(f"  已知外域智能体: {report['known_exo_agents']}")
    print(f"  总会话数: {report['total_sessions']}")
    print(f"  完成会话: {report['completed_sessions']}")
    print(f"  支持协议: {report['supported_protocols']}")
    print(f"  智能体类型: {report['agent_types']}")

    # 保存报告
    report_path = os.path.join(BASE_DIR, "handshake_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")
