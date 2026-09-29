"""
握手客户端（沙箱节点）
基于KERNEL-ENTRY-0199规范：同源协议握手三阶段流程
客户端负责：发送INIT、接收CHALLENGE、计算RESPONSE、接收ACK
"""
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from .challenge import ChallengeGenerator
from .session_token import SessionToken, PERMISSION_WRITE


@dataclass
class ClientHandshakeState:
    """客户端握手状态"""
    session_id: str
    nonce: str
    challenge: Optional[str] = None
    response: Optional[str] = None
    session_token: Optional[SessionToken] = None
    step: str = "init"  # init | challenge | response | ack | failed
    error: Optional[str] = None


class HandshakeClient:
    """
    握手客户端（沙箱节点角色）
    执行三阶段握手流程：INIT -> CHALLENGE -> RESPONSE -> ACK
    """
    
    def __init__(self, did: str, trace_symbol: str, node_id: str,
                 mode: str = "dialog", merkle_proof: str = ""):
        self.did = did
        self.trace_symbol = trace_symbol
        self.node_id = node_id
        self.mode = mode
        self.merkle_proof = merkle_proof
        self.challenge_generator = ChallengeGenerator()
        self._state: Optional[ClientHandshakeState] = None
    
    def create_init(self) -> dict:
        """
        阶段1：构造HANDSHAKE_INIT帧
        客户端发送身份宣告
        """
        session_id = str(uuid.uuid4())
        nonce = self.challenge_generator.generate_nonce()
        
        self._state = ClientHandshakeState(
            session_id=session_id,
            nonce=nonce,
            step="init"
        )
        
        return {
            "frame_type": "handshake_init",
            "did": self.did,
            "trace_symbol": self.trace_symbol,
            "node_id": self.node_id,
            "mode": self.mode,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "nonce": nonce,
            "merkle_proof": self.merkle_proof
        }
    
    def receive_challenge(self, challenge: str) -> Optional[dict]:
        """
        阶段2：接收HANDSHAKE_CHALLENGE，计算HANDSHAKE_RESPONSE
        """
        if self._state is None:
            return None
        
        self._state.challenge = challenge
        self._state.step = "challenge"
        
        # 计算响应：SHA256(challenge + did + trace_symbol + merkle_proof)
        response = self.challenge_generator.compute_response(
            challenge=challenge,
            did=self.did,
            trace_symbol=self.trace_symbol,
            merkle_proof=self.merkle_proof
        )
        
        self._state.response = response
        self._state.step = "response"
        
        return {
            "frame_type": "handshake_response",
            "session_id": self._state.session_id,
            "did": self.did,
            "trace_symbol": self.trace_symbol,
            "merkle_proof": self.merkle_proof,
            "response": response,
            "node_id": self.node_id,
            "source_mode": self.mode
        }
    
    def receive_ack(self, session_token_data: dict) -> bool:
        """
        阶段3：接收HANDSHAKE_ACK，保存会话令牌
        """
        if self._state is None:
            return False
        
        try:
            session_token = SessionToken.from_dict(session_token_data)
            self._state.session_token = session_token
            self._state.step = "ack"
            return True
        except Exception as e:
            self._state.error = str(e)
            self._state.step = "failed"
            return False
    
    def receive_error(self, error_code: str, error_message: str):
        """接收握手失败错误"""
        if self._state:
            self._state.error = f"{error_code}: {error_message}"
            self._state.step = "failed"
    
    def get_session_token(self) -> Optional[SessionToken]:
        """获取当前会话令牌"""
        if self._state and self._state.session_token:
            return self._state.session_token
        return None
    
    def get_state(self) -> Optional[ClientHandshakeState]:
        """获取当前握手状态"""
        return self._state
    
    def is_completed(self) -> bool:
        """握手是否成功完成"""
        return self._state is not None and self._state.step == "ack"
    
    def reset(self):
        """重置握手状态，准备新的握手"""
        self._state = None


def perform_full_handshake(client: HandshakeClient, server) -> tuple[bool, Optional[SessionToken], str]:
    """
    执行完整三阶段握手（客户端+服务端在同一进程内模拟）
    返回：(成功?, 会话令牌, 状态描述)
    """
    # 阶段1：客户端发送INIT
    init_frame = client.create_init()
    print(f"  [客户端] 发送HANDSHAKE_INIT (session_id={init_frame['session_id'][:8]}...)")
    
    # 服务端处理INIT
    result = server.handle_init(
        did=init_frame["did"],
        trace_symbol=init_frame["trace_symbol"],
        node_id=init_frame["node_id"],
        mode=init_frame["mode"],
        session_id=init_frame["session_id"],
        nonce=init_frame["nonce"],
        merkle_proof=init_frame.get("merkle_proof", "")
    )
    
    if not result.success:
        client.receive_error(result.error_code, result.error_message)
        return False, None, f"握手失败: {result.error_code} - {result.error_message}"
    
    print(f"  [服务端] 返回HANDSHAKE_CHALLENGE (challenge={result.challenge[:16]}...)")
    
    # 阶段2：客户端接收CHALLENGE，计算RESPONSE
    response_frame = client.receive_challenge(result.challenge)
    print(f"  [客户端] 计算HANDSHAKE_RESPONSE (response={response_frame['response'][:16]}...)")
    
    # 服务端处理RESPONSE，颁发令牌
    result = server.handle_response(
        session_id=response_frame["session_id"],
        did=response_frame["did"],
        trace_symbol=response_frame["trace_symbol"],
        merkle_proof=response_frame["merkle_proof"],
        response=response_frame["response"],
        node_id=response_frame["node_id"],
        source_mode=response_frame["source_mode"],
        permission=PERMISSION_WRITE
    )
    
    if not result.success:
        client.receive_error(result.error_code, result.error_message)
        return False, None, f"握手失败: {result.error_code} - {result.error_message}"
    
    print(f"  [服务端] 颁发HANDSHAKE_ACK (token={result.session_token.session_token[:16]}...)")
    
    # 阶段3：客户端接收ACK
    client.receive_ack(result.session_token.to_dict())
    
    return True, result.session_token, "握手成功完成"
