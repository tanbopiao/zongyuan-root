"""
握手服务端（总线代理）
基于KERNEL-ENTRY-0199规范：同源协议握手三阶段流程
服务端负责：接收INIT、生成CHALLENGE、校验RESPONSE、返回ACK
"""
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from .challenge import ChallengeGenerator, ChallengeContext, ChallengeExpiredError
from .session_token import SessionTokenManager, SessionToken, PERMISSION_WRITE


# 握手失败错误码
HANDSHAKE_ERRORS = {
    "invalid_did": "DID不在同源节点白名单",
    "invalid_trace": "溯源标识不匹配",
    "challenge_expired": "挑战超时未响应",
    "response_mismatch": "响应哈希校验失败",
    "merkle_invalid": "Merkle凭证校验失败",
    "nonce_reused": "nonce重复使用（重放攻击）",
    "invalid_nonce": "nonce无效"
}


@dataclass
class HandshakeResult:
    """握手结果"""
    success: bool
    session_token: Optional[SessionToken] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    challenge: Optional[str] = None
    step: str = "init"  # init | challenge | response | ack | failed


class HandshakeServer:
    """
    握手服务端（总线代理角色）
    管理三阶段握手流程：INIT -> CHALLENGE -> RESPONSE -> ACK
    """
    
    def __init__(self, did: str, trace_symbol: str,
                 challenge_expires_seconds: int = 30,
                 session_token_expires_minutes: int = 30,
                 token_storage_path: Optional[str] = None,
                 allowed_dids: Optional[list[str]] = None):
        self.did = did
        self.trace_symbol = trace_symbol
        self.challenge_generator = ChallengeGenerator()
        self.token_manager = SessionTokenManager(
            expires_minutes=session_token_expires_minutes,
            storage_path=token_storage_path
        )
        self.challenge_expires_seconds = challenge_expires_seconds
        self.allowed_dids = allowed_dids or [did]  # 默认只允许自身DID
        
        # 活跃的挑战上下文（按会话ID索引）
        self._active_challenges: dict[str, ChallengeContext] = {}
    
    def handle_init(self, did: str, trace_symbol: str, node_id: str,
                    mode: str, session_id: str, nonce: str,
                    merkle_proof: str = "") -> HandshakeResult:
        """
        阶段1：处理HANDSHAKE_INIT
        客户端发送身份宣告，服务端校验并返回挑战
        """
        # 校验DID
        if did not in self.allowed_dids:
            return HandshakeResult(
                success=False, error_code="invalid_did",
                error_message=HANDSHAKE_ERRORS["invalid_did"],
                step="failed"
            )
        
        # 校验溯源标识
        if trace_symbol != self.trace_symbol:
            return HandshakeResult(
                success=False, error_code="invalid_trace",
                error_message=HANDSHAKE_ERRORS["invalid_trace"],
                step="failed"
            )
        
        # 校验nonce（防重放）
        if not nonce:
            return HandshakeResult(
                success=False, error_code="invalid_nonce",
                error_message=HANDSHAKE_ERRORS["invalid_nonce"],
                step="failed"
            )
        if not self.challenge_generator.register_nonce(nonce):
            return HandshakeResult(
                success=False, error_code="nonce_reused",
                error_message=HANDSHAKE_ERRORS["nonce_reused"],
                step="failed"
            )
        
        # 生成挑战
        challenge = self.challenge_generator.generate_challenge(did, nonce)
        challenge_context = ChallengeContext(
            challenge=challenge,
            did=did,
            nonce=nonce,
            expires_in_seconds=self.challenge_expires_seconds
        )
        
        # 保存挑战上下文（按session_id索引）
        self._active_challenges[session_id] = challenge_context
        
        return HandshakeResult(
            success=True,
            challenge=challenge,
            step="challenge"
        )
    
    def handle_response(self, session_id: str, did: str,
                        trace_symbol: str, merkle_proof: str,
                        response: str, node_id: str = "",
                        source_mode: str = "dialog",
                        permission: str = PERMISSION_WRITE) -> HandshakeResult:
        """
        阶段2-3：处理HANDSHAKE_RESPONSE，返回HANDSHAKE_ACK
        客户端发送挑战响应，服务端校验并颁发会话令牌
        """
        # 查找挑战上下文
        challenge_context = self._active_challenges.get(session_id)
        if challenge_context is None:
            return HandshakeResult(
                success=False, error_code="challenge_expired",
                error_message="未找到有效的挑战上下文（可能已过期或不存在）",
                step="failed"
            )
        
        # 检查挑战是否过期
        if challenge_context.is_expired():
            del self._active_challenges[session_id]
            return HandshakeResult(
                success=False, error_code="challenge_expired",
                error_message=HANDSHAKE_ERRORS["challenge_expired"],
                step="failed"
            )
        
        # 标记挑战已使用
        challenge_context.used = True
        
        # 校验响应
        is_valid = self.challenge_generator.verify_response(
            challenge=challenge_context.challenge,
            did=did,
            trace_symbol=trace_symbol,
            merkle_proof=merkle_proof,
            response=response
        )
        
        if not is_valid:
            del self._active_challenges[session_id]
            return HandshakeResult(
                success=False, error_code="response_mismatch",
                error_message=HANDSHAKE_ERRORS["response_mismatch"],
                step="failed"
            )
        
        # 校验通过，颁发会话令牌
        session_token = self.token_manager.generate(
            did=did,
            node_id=node_id,
            permission=permission,
            source_mode=source_mode
        )
        
        # 清理挑战上下文
        del self._active_challenges[session_id]
        
        return HandshakeResult(
            success=True,
            session_token=session_token,
            step="ack"
        )
    
    def validate_token(self, token: str) -> Optional[SessionToken]:
        """校验会话令牌有效性（供真值总线等模块调用）"""
        return self.token_manager.validate(token)
    
    def cleanup_expired_challenges(self) -> int:
        """清理过期的挑战上下文，返回清理数量"""
        expired = [sid for sid, ctx in self._active_challenges.items() if ctx.is_expired()]
        for sid in expired:
            del self._active_challenges[sid]
        return len(expired)
    
    def get_status(self) -> dict:
        """获取服务端状态"""
        return {
            "did": self.did,
            "trace_symbol": self.trace_symbol,
            "active_challenges": len(self._active_challenges),
            "active_tokens": self.token_manager.get_active_count(),
            "allowed_dids": self.allowed_dids
        }
