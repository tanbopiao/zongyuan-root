"""
会话令牌生成与管理模块
基于KERNEL-ENTRY-0199规范：同源协议握手阶段3授权确认
"""
import secrets
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, asdict


# 权限级别定义
PERMISSION_READ = "read"
PERMISSION_WRITE = "write"
PERMISSION_ADMIN = "admin"

VALID_PERMISSIONS = [PERMISSION_READ, PERMISSION_WRITE, PERMISSION_ADMIN]


@dataclass
class SessionToken:
    """会话令牌数据结构"""
    session_token: str
    did: str
    node_id: str
    permission: str  # read | write | admin
    source_mode: str  # dialog | task
    created_at: str
    expires_at: str
    
    def is_expired(self) -> bool:
        """检查令牌是否过期"""
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now() > expires
        except (ValueError, TypeError):
            return True
    
    def remaining_seconds(self) -> int:
        """剩余有效秒数"""
        try:
            expires = datetime.fromisoformat(self.expires_at)
            remaining = (expires - datetime.now()).total_seconds()
            return max(0, int(remaining))
        except (ValueError, TypeError):
            return 0
    
    def has_permission(self, required: str) -> bool:
        """检查是否具备所需权限"""
        permission_levels = {PERMISSION_READ: 0, PERMISSION_WRITE: 1, PERMISSION_ADMIN: 2}
        current_level = permission_levels.get(self.permission, -1)
        required_level = permission_levels.get(required, -1)
        return current_level >= required_level
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SessionToken':
        return cls(**data)


class SessionTokenManager:
    """会话令牌管理器"""
    
    def __init__(self, expires_minutes: int = 30, 
                 storage_path: Optional[str] = None):
        self.expires_minutes = expires_minutes
        self._tokens: dict[str, SessionToken] = {}  # token -> SessionToken
        self._storage_path = storage_path
        if storage_path:
            self._load_from_storage()
    
    def generate(self, did: str, node_id: str, permission: str = PERMISSION_WRITE,
                 source_mode: str = "dialog") -> SessionToken:
        """
        生成会话令牌
        阶段3：总线返回HANDSHAKE_ACK中的session_token
        """
        if permission not in VALID_PERMISSIONS:
            raise ValueError(f"无效权限级别: {permission}，有效级别: {VALID_PERMISSIONS}")
        
        token = secrets.token_hex(32)
        now = datetime.now()
        expires_at = now + timedelta(minutes=self.expires_minutes)
        
        session_token = SessionToken(
            session_token=token,
            did=did,
            node_id=node_id,
            permission=permission,
            source_mode=source_mode,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat()
        )
        
        self._tokens[token] = session_token
        self._save_to_storage()
        return session_token
    
    def validate(self, token: str) -> Optional[SessionToken]:
        """
        校验令牌有效性
        返回令牌信息（有效）或None（无效/过期）
        """
        if not token:
            return None
        
        session_token = self._tokens.get(token)
        if session_token is None:
            return None
        
        if session_token.is_expired():
            # 清理过期令牌
            del self._tokens[token]
            self._save_to_storage()
            return None
        
        return session_token
    
    def revoke(self, token: str) -> bool:
        """吊销令牌"""
        if token in self._tokens:
            del self._tokens[token]
            self._save_to_storage()
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """清理所有过期令牌，返回清理数量"""
        expired_tokens = [t for t, st in self._tokens.items() if st.is_expired()]
        for t in expired_tokens:
            del self._tokens[t]
        if expired_tokens:
            self._save_to_storage()
        return len(expired_tokens)
    
    def get_active_count(self) -> int:
        """获取活跃令牌数量"""
        self.cleanup_expired()
        return len(self._tokens)
    
    def list_active_tokens(self) -> list[SessionToken]:
        """列出所有活跃令牌"""
        self.cleanup_expired()
        return list(self._tokens.values())
    
    def _save_to_storage(self):
        """保存令牌到本地存储（JSON文件）"""
        if not self._storage_path:
            return
        try:
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            data = {
                "saved_at": datetime.now().isoformat(),
                "tokens": {t: st.to_dict() for t, st in self._tokens.items()}
            }
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SessionTokenManager] 保存令牌存储失败: {e}")
    
    def _load_from_storage(self):
        """从本地存储加载令牌"""
        if not self._storage_path or not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tokens_data = data.get("tokens", {})
            for token, token_dict in tokens_data.items():
                try:
                    st = SessionToken.from_dict(token_dict)
                    if not st.is_expired():
                        self._tokens[token] = st
                except Exception:
                    continue
        except Exception as e:
            print(f"[SessionTokenManager] 加载令牌存储失败: {e}")
