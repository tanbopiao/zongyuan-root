#!/usr/bin/env python3
"""
手脚驱动层加固3 - 动作级权限矩阵 (Action RBAC)

提供:
  - 角色定义 (admin/operator/observer/system)
  - Action级别权限控制 (哪些角色可以执行哪些Action)
  - 敏感操作二次确认 (需要confirmation_token)
  - 操作审计 (谁在什么时间执行了什么Action)
  - 权限变更日志

权限矩阵原则:
  - admin: 全部权限（含敏感操作）
  - operator: 常规操作权限（不含全局锁档、进化循环、权限变更）
  - observer: 只读权限（仅查询类Action）
  - system: 系统内部调用（不受限制，但全部审计）
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class Role(Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    OBSERVER = "observer"
    SYSTEM = "system"


class SensitivityLevel(Enum):
    LOW = "low"           # 只读/查询
    MEDIUM = "medium"     # 常规修改
    HIGH = "high"         # 重要修改（快照、向量同步）
    CRITICAL = "critical" # 敏感操作（全局锁档、进化循环、权限变更）- 需二次确认


# 默认权限矩阵: action_name → 允许的角色集合
DEFAULT_PERMISSION_MATRIX: Dict[str, Set[str]] = {
    # 只读类 - 所有角色可执行
    'api_call': {Role.ADMIN, Role.OPERATOR, Role.OBSERVER, Role.SYSTEM},
    # 常规修改 - admin/operator/system
    'cas_write': {Role.ADMIN, Role.OPERATOR, Role.SYSTEM},
    'audit_write': {Role.ADMIN, Role.OPERATOR, Role.SYSTEM},
    'file_backup': {Role.ADMIN, Role.OPERATOR, Role.SYSTEM},
    # 重要修改 - admin/system
    'snapshot': {Role.ADMIN, Role.SYSTEM},
    'vector_sync': {Role.ADMIN, Role.SYSTEM},
    'tpc_snapshot': {Role.ADMIN, Role.SYSTEM},
    'tpc_cas_write': {Role.ADMIN, Role.SYSTEM},
    # 敏感操作 - 仅admin/system（需二次确认）
    'evolution_cycle': {Role.ADMIN, Role.SYSTEM},
}

# 敏感度分级: action_name → SensitivityLevel
DEFAULT_SENSITIVITY: Dict[str, SensitivityLevel] = {
    'api_call': SensitivityLevel.LOW,
    'cas_write': SensitivityLevel.MEDIUM,
    'audit_write': SensitivityLevel.LOW,
    'file_backup': SensitivityLevel.MEDIUM,
    'snapshot': SensitivityLevel.HIGH,
    'vector_sync': SensitivityLevel.HIGH,
    'tpc_snapshot': SensitivityLevel.HIGH,
    'tpc_cas_write': SensitivityLevel.MEDIUM,
    'evolution_cycle': SensitivityLevel.CRITICAL,
}

# 需要二次确认的敏感度阈值
CONFIRMATION_THRESHOLD = SensitivityLevel.CRITICAL


class ActionRBAC:
    """
    动作级权限控制器

    用法:
        rbac = ActionRBAC()
        result = rbac.check("evolution_cycle", "admin_user", Role.ADMIN)
        if result['allowed']:
            if result['need_confirmation']:
                token = rbac.generate_confirmation_token("evolution_cycle", "admin_user")
                result = rbac.confirm("evolution_cycle", "admin_user", token)
            # 执行
    """

    def __init__(self, matrix_file: str = None, audit_file: str = None):
        self.matrix_file = Path(matrix_file) if matrix_file else Path(__file__).parent.parent / 'executor' / 'rbac_matrix.json'
        self.audit_file = Path(audit_file) if audit_file else Path(__file__).parent.parent / 'executor' / 'rbac_audit.jsonl'
        self.matrix_file.parent.mkdir(parents=True, exist_ok=True)

        self.permission_matrix: Dict[str, Set[str]] = {k: set(v.value for v in roles)
                                                        for k, roles in DEFAULT_PERMISSION_MATRIX.items()}
        self.sensitivity: Dict[str, str] = {k: v.value for k, v in DEFAULT_SENSITIVITY.items()}
        self._pending_confirmations: Dict[str, dict] = {}  # token → {action, user, expires_at}
        self._load_matrix()

    def _load_matrix(self):
        if self.matrix_file.exists():
            try:
                with open(self.matrix_file) as f:
                    data = json.load(f)
                    self.permission_matrix = {k: set(v) for k, v in data.get('permissions', {}).items()}
                    self.sensitivity = data.get('sensitivity', self.sensitivity)
            except Exception:
                pass

    def _save_matrix(self):
        with open(self.matrix_file, 'w') as f:
            json.dump({
                'permissions': {k: list(v) for k, v in self.permission_matrix.items()},
                'sensitivity': self.sensitivity,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, f, indent=2)

    def _audit(self, action_name: str, user: str, role: str, allowed: bool,
               reason: str = "", need_confirmation: bool = False):
        """写入权限审计日志"""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': action_name,
            'user': user,
            'role': role,
            'allowed': allowed,
            'need_confirmation': need_confirmation,
            'reason': reason,
        }
        try:
            with open(self.audit_file, 'a') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception:
            pass

    def check(self, action_name: str, user: str, role: Role or str,
              confirmation_token: str = None) -> dict:
        """
        检查是否允许执行Action

        Returns:
            {
                'allowed': bool,
                'need_confirmation': bool,
                'reason': str,
                'sensitivity': str,
            }
        """
        role_str = role.value if isinstance(role, Role) else role

        # 检查Action是否在权限矩阵中
        if action_name not in self.permission_matrix:
            self._audit(action_name, user, role_str, False, "action not in permission matrix")
            return {'allowed': False, 'need_confirmation': False,
                    'reason': f"action '{action_name}' not registered in permission matrix",
                    'sensitivity': 'unknown'}

        # 检查角色权限
        allowed_roles = self.permission_matrix[action_name]
        if role_str not in allowed_roles:
            self._audit(action_name, user, role_str, False, f"role {role_str} not allowed")
            return {'allowed': False, 'need_confirmation': False,
                    'reason': f"role '{role_str}' does not have permission for '{action_name}'",
                    'sensitivity': self.sensitivity.get(action_name, 'unknown')}

        # 检查敏感度
        sensitivity = self.sensitivity.get(action_name, SensitivityLevel.LOW.value)
        need_confirmation = (sensitivity == CONFIRMATION_THRESHOLD.value)

        if need_confirmation:
            # 检查二次确认token
            if confirmation_token:
                confirmed = self._verify_confirmation(action_name, user, confirmation_token)
                if confirmed:
                    self._audit(action_name, user, role_str, True, "confirmed with token")
                    return {'allowed': True, 'need_confirmation': False,
                            'reason': "permission granted with confirmation",
                            'sensitivity': sensitivity}
                else:
                    self._audit(action_name, user, role_str, False, "invalid confirmation token")
                    return {'allowed': False, 'need_confirmation': True,
                            'reason': "invalid or expired confirmation token",
                            'sensitivity': sensitivity}
            else:
                self._audit(action_name, user, role_str, False, "needs confirmation", need_confirmation=True)
                return {'allowed': False, 'need_confirmation': True,
                        'reason': f"action '{action_name}' is CRITICAL, requires confirmation token",
                        'sensitivity': sensitivity}

        self._audit(action_name, user, role_str, True, "permission granted")
        return {'allowed': True, 'need_confirmation': False,
                'reason': "permission granted", 'sensitivity': sensitivity}

    def generate_confirmation_token(self, action_name: str, user: str, ttl_seconds: int = 300) -> str:
        """
        生成二次确认token（5分钟有效）

        Returns:
            confirmation_token
        """
        token = hashlib.sha256(f"{action_name}:{user}:{time.time()}:{os.urandom(8).hex()}".encode()).hexdigest()[:16]
        self._pending_confirmations[token] = {
            'action': action_name,
            'user': user,
            'expires_at': time.time() + ttl_seconds,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        return token

    def _verify_confirmation(self, action_name: str, user: str, token: str) -> bool:
        """验证二次确认token"""
        entry = self._pending_confirmations.get(token)
        if not entry:
            return False
        if entry['action'] != action_name or entry['user'] != user:
            return False
        if time.time() > entry['expires_at']:
            del self._pending_confirmations[token]
            return False
        # 一次性使用
        del self._pending_confirmations[token]
        return True

    def grant_permission(self, action_name: str, role: Role or str, granted_by: str = "admin"):
        """授予权限（仅admin可操作）"""
        role_str = role.value if isinstance(role, Role) else role
        if action_name not in self.permission_matrix:
            self.permission_matrix[action_name] = set()
        self.permission_matrix[action_name].add(role_str)
        self._save_matrix()
        self._audit(action_name, granted_by, Role.ADMIN.value, True, f"granted permission to {role_str}")

    def revoke_permission(self, action_name: str, role: Role or str, revoked_by: str = "admin"):
        """撤销权限"""
        role_str = role.value if isinstance(role, Role) else role
        if action_name in self.permission_matrix:
            self.permission_matrix[action_name].discard(role_str)
            self._save_matrix()
        self._audit(action_name, revoked_by, Role.ADMIN.value, True, f"revoked permission from {role_str}")

    def set_sensitivity(self, action_name: str, level: SensitivityLevel or str):
        """设置Action敏感度"""
        self.sensitivity[action_name] = level.value if isinstance(level, SensitivityLevel) else level
        self._save_matrix()

    def get_matrix(self) -> dict:
        """获取完整权限矩阵"""
        return {
            'permissions': {k: sorted(list(v)) for k, v in self.permission_matrix.items()},
            'sensitivity': self.sensitivity,
            'roles': [r.value for r in Role],
            'confirmation_threshold': CONFIRMATION_THRESHOLD.value,
        }

    def get_audit_log(self, limit: int = 100) -> List[dict]:
        """获取审计日志"""
        if not self.audit_file.exists():
            return []
        entries = []
        with open(self.audit_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        continue
        return entries[-limit:]


import os  # 放在末尾避免循环导入问题

# 全局单例
_global_rbac: Optional[ActionRBAC] = None

def get_global_rbac() -> ActionRBAC:
    global _global_rbac
    if _global_rbac is None:
        _global_rbac = ActionRBAC()
    return _global_rbac
