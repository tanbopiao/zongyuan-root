"""
挑战生成与响应校验模块
基于KERNEL-ENTRY-0199规范：同源协议握手三阶段流程
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional


class ChallengeGenerator:
    """挑战生成器"""
    
    def __init__(self, algorithm: str = "SHA256"):
        self.algorithm = algorithm
        self._used_nonces: dict[str, datetime] = {}  # nonce -> 使用时间
        self._nonce_ttl = timedelta(minutes=5)  # nonce缓存5分钟
    
    def generate_nonce(self) -> str:
        """生成随机nonce（防重放）"""
        return secrets.token_hex(16)
    
    def generate_challenge(self, did: str, nonce: str) -> str:
        """
        基于DID+nonce+时间戳生成挑战字符串
        阶段2：总线返回HANDSHAKE_CHALLENGE
        """
        timestamp = datetime.now().timestamp()
        raw = f"{did}:{nonce}:{timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def compute_response(self, challenge: str, did: str, 
                         trace_symbol: str, merkle_proof: str) -> str:
        """
        客户端计算响应：SHA256(challenge + did + trace_symbol + merkle_proof)
        阶段2：客户端计算HANDSHAKE_RESPONSE
        """
        raw = f"{challenge}:{did}:{trace_symbol}:{merkle_proof}"
        return hashlib.sha256(raw.encode()).hexdigest().upper()
    
    def verify_response(self, challenge: str, did: str, 
                        trace_symbol: str, merkle_proof: str,
                        response: str) -> bool:
        """
        服务端校验响应是否匹配
        阶段3：总线校验HANDSHAKE_RESPONSE
        """
        expected = self.compute_response(challenge, did, trace_symbol, merkle_proof)
        return expected == response.upper()
    
    def register_nonce(self, nonce: str) -> bool:
        """
        注册nonce，防止重放攻击
        返回True表示nonce可用（未使用过），False表示已使用
        """
        self._clean_expired_nonces()
        if nonce in self._used_nonces:
            return False
        self._used_nonces[nonce] = datetime.now()
        return True
    
    def _clean_expired_nonces(self):
        """清理过期的nonce缓存"""
        now = datetime.now()
        expired = [n for n, t in self._used_nonces.items() if now - t > self._nonce_ttl]
        for n in expired:
            del self._used_nonces[n]


class ChallengeExpiredError(Exception):
    """挑战超时异常"""
    pass


class ChallengeContext:
    """挑战上下文（服务端保存的挑战状态）"""
    
    def __init__(self, challenge: str, did: str, nonce: str,
                 expires_in_seconds: int = 30):
        self.challenge = challenge
        self.did = did
        self.nonce = nonce
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=expires_in_seconds)
        self.used = False
    
    def is_expired(self) -> bool:
        """检查挑战是否过期"""
        return datetime.now() > self.expires_at
    
    def remaining_seconds(self) -> int:
        """剩余有效秒数"""
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, int(remaining))
