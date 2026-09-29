#!/usr/bin/env python3
"""
API Key管理器 - 节点注册审批后自动签发
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import hashlib
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone

class APIKeyManager:
    def __init__(self, db_path="/opt/ZONGYUAN-ROOT/data/gateway.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY,
                api_key_hash TEXT UNIQUE NOT NULL,
                node_id TEXT NOT NULL,
                node_name TEXT,
                role TEXT DEFAULT 'worker',
                permissions TEXT DEFAULT 'read,write,report',
                ip_whitelist TEXT,
                expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used_at DATETIME,
                status TEXT DEFAULT 'active',
                approval_instance TEXT
            )
        """)
        conn.commit()
        conn.close()

    def generate_api_key(self):
        """生成API Key: zy- + 48位随机十六进制"""
        return "zy-" + secrets.token_hex(24)

    def _hash_key(self, api_key):
        return hashlib.sha256(api_key.encode()).hexdigest()

    def issue_key(self, node_id, node_name, role="worker", 
                  expire_days=365, ip_whitelist=None, approval_instance=None):
        """签发API Key，返回明文Key（仅此时返回明文）"""
        api_key = self.generate_api_key()
        key_hash = self._hash_key(api_key)
        
        permissions_map = {
            "observer": "read",
            "worker": "read,write,report",
            "core": "read,write,report,admin"
        }
        permissions = permissions_map.get(role, "read")
        
        expires_at = None
        if expire_days and expire_days > 0:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expire_days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO api_keys 
            (api_key_hash, node_id, node_name, role, permissions, 
             ip_whitelist, expires_at, approval_instance, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (key_hash, node_id, node_name, role, permissions, 
              ip_whitelist, expires_at, approval_instance))
        conn.commit()
        conn.close()

        return {
            "api_key": api_key,
            "node_id": node_id,
            "node_name": node_name,
            "role": role,
            "permissions": permissions,
            "expires_at": expires_at,
            "issued_at": datetime.now(timezone.utc).isoformat()
        }

    def validate_key(self, api_key, client_ip=None):
        """验证API Key，返回节点信息或None"""
        key_hash = self._hash_key(api_key)
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT node_id, node_name, role, permissions, ip_whitelist, expires_at, status FROM api_keys WHERE api_key_hash=?",
            (key_hash,)
        ).fetchone()
        conn.close()

        if not row:
            return None
        
        node_id, node_name, role, permissions, ip_whitelist, expires_at, status = row
        
        if status != 'active':
            return None
        
        if expires_at:
            if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                return None
        
        if ip_whitelist and client_ip:
            if client_ip not in ip_whitelist.split(','):
                return None
        
        # 更新最后使用时间
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE api_keys SET last_used_at=? WHERE api_key_hash=?",
                     (datetime.now(timezone.utc).isoformat(), key_hash))
        conn.commit()
        conn.close()

        return {
            "node_id": node_id,
            "node_name": node_name,
            "role": role,
            "permissions": permissions.split(',')
        }

    def revoke_key(self, api_key=None, node_id=None):
        """吊销API Key"""
        conn = sqlite3.connect(self.db_path)
        if api_key:
            key_hash = self._hash_key(api_key)
            conn.execute("UPDATE api_keys SET status='revoked' WHERE api_key_hash=?", (key_hash,))
        elif node_id:
            conn.execute("UPDATE api_keys SET status='revoked' WHERE node_id=?", (node_id,))
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return affected > 0

    def list_keys(self, status='active'):
        """列出所有API Key（仅元数据，不含Key明文）"""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT node_id, node_name, role, permissions, expires_at, created_at, last_used_at, status FROM api_keys WHERE status=?",
            (status,)
        ).fetchall()
        conn.close()
        return [dict(zip(['node_id','node_name','role','permissions','expires_at','created_at','last_used_at','status'], r)) for r in rows]


# 飞书审批回调处理
def handle_approval_callback(approval_data):
    """
    飞书审批通过回调，自动签发API Key
    由中枢智能体调用
    """
    form = approval_data.get('form', {})
    node_id = form.get('node_id', '')
    node_name = form.get('node_name', '')
    role = form.get('node_role', 'worker')
    expire_days = int(form.get('expire_days', 365))
    ip_range = form.get('ip_range')
    instance_code = approval_data.get('instance_code', '')

    if not node_id:
        return {"error": "node_id required"}

    manager = APIKeyManager()
    result = manager.issue_key(
        node_id=node_id,
        node_name=node_name,
        role=role,
        expire_days=expire_days,
        ip_whitelist=ip_range,
        approval_instance=instance_code
    )

    return {
        "status": "success",
        "message": "API Key已签发，请通过飞书消息查收",
        "node_id": node_id,
        "role": role,
        "api_key": result["api_key"],  # 仅此时返回明文，通过飞书消息发送
        "endpoints": {
            "read": "https://www.huodouai.com/api/v1/gateway/status",
            "write": "https://www.huodouai.com/api/memory/api/truth/upsert",
            "report": "https://www.huodouai.com/api/memory/api/gateway/report"
        }
    }


if __name__ == "__main__":
    # 测试
    mgr = APIKeyManager("/tmp/test_gateway.db")
    result = mgr.issue_key("NN-TEST-001", "测试节点", "worker", expire_days=30)
    print(f"签发API Key: {result['api_key']}")
    
    valid = mgr.validate_key(result['api_key'])
    print(f"验证结果: {valid}")
    
    invalid = mgr.validate_key("wrong-key")
    print(f"无效Key验证: {invalid}")
    
    keys = mgr.list_keys()
    print(f"活跃Key数量: {len(keys)}")
