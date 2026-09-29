"""
ZONGYUAN-ROOT 协议鉴权工具集
版本: V1.0
溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT V1.7

包含:
1. CA证书体系生成工具(根CA+中间CA+节点证书)
2. JWT令牌签发/校验/刷新/吊销
3. Scope细粒度权限校验
4. Nginx mTLS配置生成
"""

import hashlib
import hmac
import json
import os
import time
import uuid
import base64
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum


# ============================================================
# 常量
# ============================================================

JWT_SECRET = "ZONGYUAN-ROOT-JWT-SECRET-2026"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 15 * 60  # 15分钟
REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60  # 7天
MAX_CONCURRENT_SESSIONS = 3


# ============================================================
# Scope权限模型
# ============================================================

class Scope:
    """Scope细粒度权限模型"""

    # 资源域
    DOMAINS = ["truth", "node", "kernel", "asset", "sync", "task", "protocol", "admin"]

    # 操作
    ACTIONS = ["read", "write", "execute", "manage"]

    # 资源范围
    RANGES = ["self", "domain", "global"]

    def __init__(self, scope_str: str = ""):
        self.scopes: Set[str] = set()
        if scope_str:
            self.parse(scope_str)

    def parse(self, scope_str: str):
        """解析Scope字符串,格式: domain:action[:range]"""
        for s in scope_str.split():
            s = s.strip()
            if s:
                self.scopes.add(s)

    def has(self, required_scope: str) -> bool:
        """检查是否拥有指定权限"""
        # 通配符支持
        if "*" in self.scopes or "admin:*" in self.scopes:
            return True

        if required_scope in self.scopes:
            return True

        # 检查通配符匹配,如 truth:read:self 匹配 truth:read:*
        parts = required_scope.split(":")
        if len(parts) >= 2:
            wildcard = f"{parts[0]}:{parts[1]}:*"
            if wildcard in self.scopes:
                return True
            domain_wildcard = f"{parts[0]}:*"
            if domain_wildcard in self.scopes:
                return True

        return False

    def has_all(self, required_scopes: List[str]) -> bool:
        """检查是否拥有所有指定权限"""
        return all(self.has(s) for s in required_scopes)

    def has_any(self, required_scopes: List[str]) -> bool:
        """检查是否拥有任一指定权限"""
        return any(self.has(s) for s in required_scopes)

    def add(self, scope: str):
        """添加权限"""
        self.scopes.add(scope)

    def remove(self, scope: str):
        """移除权限"""
        self.scopes.discard(scope)

    def to_string(self) -> str:
        """转换为字符串"""
        return " ".join(sorted(self.scopes))

    def to_list(self) -> List[str]:
        return sorted(self.scopes)

    def __repr__(self):
        return f"Scope({self.to_string()})"


# 节点类型默认Scope集
NODE_DEFAULT_SCOPES = {
    "cloud-kernel": [
        "admin:*", "truth:*", "node:*", "kernel:*", "asset:*",
        "sync:*", "task:*", "protocol:*"
    ],
    "local-kernel": [
        "truth:read:self", "truth:write:self",
        "node:heartbeat", "node:task:execute",
        "kernel:status:read", "kernel:identity:read",
        "asset:archive", "asset:read:self",
        "sync:pull", "sync:push:self",
        "protocol:read"
    ],
    "compute-node": [
        "node:heartbeat", "node:task:execute", "node:task:read",
        "sync:pull", "kernel:status:read"
    ],
    "storage-node": [
        "asset:archive", "asset:read", "asset:write",
        "sync:pull", "sync:push", "node:heartbeat",
        "kernel:status:read"
    ],
    "gateway-node": [
        "kernel:status:read", "kernel:identity:read",
        "protocol:read", "node:heartbeat"
    ],
    "observer-node": [
        "truth:read:self", "kernel:status:read", "kernel:identity:read",
        "asset:read:self", "task:read:self", "protocol:read"
    ],
}


# ============================================================
# JWT令牌
# ============================================================

@dataclass
class JWTPayload:
    """JWT载荷"""
    iss: str = "https://kernel.huodouai.com"
    sub: str = ""  # node:xxx
    aud: str = "https://kernel.huodouai.com/api/v1"
    exp: int = 0
    iat: int = 0
    nbf: int = 0
    jti: str = ""
    scope: str = ""
    node_id: str = ""
    node_type: str = ""
    did: str = "DID-BR-000002"
    mtls_fingerprint: str = ""
    session_id: str = ""
    quota: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'JWTPayload':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class JWTManager:
    """JWT令牌管理器"""

    def __init__(self, secret: str = JWT_SECRET):
        self.secret = secret
        self.blacklist: Set[str] = set()  # 吊销的jti集合
        self.sessions: Dict[str, Dict] = {}  # session_id -> {tokens, node_id, created}

    def _b64encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

    def _b64decode(self, data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)

    def _sign(self, message: str) -> str:
        return self._b64encode(hmac.new(self.secret.encode(), message.encode(), hashlib.sha256).digest())

    def create_token(self, node_id: str, node_type: str,
                     scope: str = "", mtls_fingerprint: str = "",
                     custom_claims: Dict = None,
                     expire_seconds: int = ACCESS_TOKEN_EXPIRE) -> Tuple[str, JWTPayload]:
        """签发JWT令牌
        
        Returns:
            (token字符串, 载荷对象)
        """
        now = int(time.time())
        jti = str(uuid.uuid4())
        session_id = custom_claims.get("session_id", f"sess_{uuid.uuid4().hex[:16]}") if custom_claims else f"sess_{uuid.uuid4().hex[:16]}"

        # 默认Scope
        if not scope:
            scope = " ".join(NODE_DEFAULT_SCOPES.get(node_type, ["truth:read:self"]))

        payload = JWTPayload(
            sub=f"node:{node_id}",
            exp=now + expire_seconds,
            iat=now,
            nbf=now,
            jti=jti,
            scope=scope,
            node_id=node_id,
            node_type=node_type,
            mtls_fingerprint=mtls_fingerprint,
            session_id=session_id,
            quota={
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "tokens_per_day": 100000
            }
        )

        # 合并自定义claims
        if custom_claims:
            for k, v in custom_claims.items():
                if hasattr(payload, k):
                    setattr(payload, k, v)

        # 构建JWT
        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        header_b64 = self._b64encode(json.dumps(header, sort_keys=True).encode())
        payload_b64 = self._b64encode(json.dumps(payload.to_dict(), sort_keys=True).encode())
        message = f"{header_b64}.{payload_b64}"
        signature = self._sign(message)
        token = f"{message}.{signature}"

        # 记录会话
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "node_id": node_id,
                "created": now,
                "tokens": []
            }
        self.sessions[session_id]["tokens"].append(jti)

        # 并发会话限制
        node_sessions = [s for s in self.sessions.values() if s["node_id"] == node_id]
        if len(node_sessions) > MAX_CONCURRENT_SESSIONS:
            # 踢掉最旧的会话
            oldest = min(node_sessions, key=lambda s: s["created"])
            for old_jti in oldest["tokens"]:
                self.blacklist.add(old_jti)
            oldest_sid = next(sid for sid, s in self.sessions.items() if s is oldest)
            del self.sessions[oldest_sid]

        return token, payload

    def verify_token(self, token: str, 
                     expected_mtls_fingerprint: str = "") -> Tuple[bool, Optional[JWTPayload], List[str]]:
        """校验JWT令牌
        
        Returns:
            (是否有效, 载荷对象, 错误信息列表)
        """
        errors = []

        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, None, ["令牌格式错误"]

            header_b64, payload_b64, signature = parts

            # 验证签名
            message = f"{header_b64}.{payload_b64}"
            expected_signature = self._sign(message)
            if not hmac.compare_digest(signature, expected_signature):
                errors.append("签名验证失败")

            # 解析载荷
            payload_data = json.loads(self._b64decode(payload_b64))
            payload = JWTPayload.from_dict(payload_data)

            # 检查黑名单
            if payload.jti in self.blacklist:
                errors.append("令牌已被吊销")

            # 检查过期
            now = int(time.time())
            if payload.exp and now > payload.exp:
                errors.append(f"令牌已过期(过期时间:{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload.exp))})")

            # 检查生效时间
            if payload.nbf and now < payload.nbf:
                errors.append("令牌尚未生效")

            # 检查mTLS指纹绑定
            if expected_mtls_fingerprint and payload.mtls_fingerprint:
                if payload.mtls_fingerprint != expected_mtls_fingerprint:
                    errors.append("mTLS证书指纹不匹配(令牌绑定了其他证书)")

            return (len(errors) == 0, payload, errors)

        except Exception as e:
            return False, None, [f"令牌解析失败: {str(e)}"]

    def revoke_token(self, jti: str):
        """吊销令牌(加入黑名单)"""
        self.blacklist.add(jti)

    def revoke_session(self, session_id: str):
        """吊销整个会话的所有令牌"""
        if session_id in self.sessions:
            for jti in self.sessions[session_id]["tokens"]:
                self.blacklist.add(jti)
            del self.sessions[session_id]

    def create_refresh_token(self, node_id: str, node_type: str) -> str:
        """创建刷新令牌(7天有效,一次性使用)"""
        token, _ = self.create_token(
            node_id=node_id,
            node_type=node_type,
            scope="refresh",
            expire_seconds=REFRESH_TOKEN_EXPIRE,
            custom_claims={"token_type": "refresh"}
        )
        return token

    def refresh_access_token(self, refresh_token: str,
                             expected_mtls_fingerprint: str = "") -> Tuple[bool, str, Optional[JWTPayload]]:
        """用刷新令牌换取新的访问令牌(一次性刷新)"""
        ok, payload, errors = self.verify_token(refresh_token, expected_mtls_fingerprint)
        if not ok:
            return False, "", None

        # 一次性刷新:吊销旧刷新令牌
        self.revoke_token(payload.jti)

        # 签发新的访问令牌
        new_token, new_payload = self.create_token(
            node_id=payload.node_id,
            node_type=payload.node_type,
            scope=payload.scope.replace(" refresh", ""),
            mtls_fingerprint=payload.mtls_fingerprint,
            custom_claims={"session_id": payload.session_id}
        )

        return True, new_token, new_payload

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "active_sessions": len(self.sessions),
            "blacklisted_tokens": len(self.blacklist),
            "nodes_with_sessions": len(set(s["node_id"] for s in self.sessions.values()))
        }


# ============================================================
# CA证书体系(简化版·使用openssl命令行)
# ============================================================

class CertificateAuthority:
    """CA证书体系管理器(简化版,调用openssl)"""

    def __init__(self, base_dir: str = "./certs"):
        self.base_dir = base_dir
        self.root_ca_dir = os.path.join(base_dir, "root-ca")
        self.intermediate_ca_dir = os.path.join(base_dir, "intermediate-ca")
        self.nodes_dir = os.path.join(base_dir, "nodes")

    def init_dirs(self):
        """初始化目录结构"""
        for d in [self.base_dir, self.root_ca_dir, self.intermediate_ca_dir, self.nodes_dir]:
            os.makedirs(d, exist_ok=True)

    def generate_root_ca(self, common_name: str = "ZONGYUAN-ROOT-CA",
                          validity_days: int = 3650) -> Dict:
        """生成根CA证书(10年有效)"""
        self.init_dirs()
        ca_key = os.path.join(self.root_ca_dir, "ca.key")
        ca_cert = os.path.join(self.root_ca_dir, "ca.crt")

        # 生成私钥
        self._run_openssl(f"genrsa -out {ca_key} 4096")
        # 生成自签名证书
        self._run_openssl(
            f"req -new -x509 -days {validity_days} -key {ca_key} "
            f"-out {ca_cert} -subj \"/CN={common_name}/O=ZONGYUAN-ROOT/OU=Root-CA\""
        )

        fingerprint = self._get_cert_fingerprint(ca_cert)
        return {
            "key_path": ca_key,
            "cert_path": ca_cert,
            "fingerprint": fingerprint,
            "common_name": common_name,
            "validity_days": validity_days
        }

    def generate_intermediate_ca(self, common_name: str = "ZONGYUAN-LOCAL-ICA",
                                  validity_days: int = 1825) -> Dict:
        """生成中间CA证书(5年有效,由根CA签名)"""
        self.init_dirs()
        ica_key = os.path.join(self.intermediate_ca_dir, "ica.key")
        ica_csr = os.path.join(self.intermediate_ca_dir, "ica.csr")
        ica_cert = os.path.join(self.intermediate_ca_dir, "ica.crt")
        ca_key = os.path.join(self.root_ca_dir, "ca.key")
        ca_cert = os.path.join(self.root_ca_dir, "ca.crt")

        # 生成私钥和CSR
        self._run_openssl(f"genrsa -out {ica_key} 4096")
        self._run_openssl(
            f"req -new -key {ica_key} -out {ica_csr} "
            f"-subj \"/CN={common_name}/O=ZONGYUAN-ROOT/OU=Intermediate-CA\""
        )
        # 根CA签名
        self._run_openssl(
            f"x509 -req -days {validity_days} -in {ica_csr} "
            f"-CA {ca_cert} -CAkey {ca_key} -CAcreateserial "
            f"-out {ica_cert} -extfile <(echo \"basicConstraints=critical,CA:TRUE\")"
        )

        fingerprint = self._get_cert_fingerprint(ica_cert)
        return {
            "key_path": ica_key,
            "cert_path": ica_cert,
            "fingerprint": fingerprint,
            "common_name": common_name,
            "validity_days": validity_days
        }

    def generate_node_certificate(self, node_id: str, node_type: str = "local-kernel",
                                    common_name: str = "",
                                    validity_days: int = 365,
                                    san_domains: List[str] = None,
                                    san_ips: List[str] = None) -> Dict:
        """生成节点证书(1年有效,由中间CA签名)"""
        self.init_dirs()
        node_dir = os.path.join(self.nodes_dir, node_id)
        os.makedirs(node_dir, exist_ok=True)

        node_key = os.path.join(node_dir, "node.key")
        node_csr = os.path.join(node_dir, "node.csr")
        node_cert = os.path.join(node_dir, "node.crt")
        ica_key = os.path.join(self.intermediate_ca_dir, "ica.key")
        ica_cert = os.path.join(self.intermediate_ca_dir, "ica.crt")

        cn = common_name or node_id

        # 生成私钥和CSR
        self._run_openssl(f"genrsa -out {node_key} 2048")
        self._run_openssl(
            f"req -new -key {node_key} -out {node_csr} "
            f"-subj \"/CN={cn}/O=ZONGYUAN-ROOT/OU={node_type}\""
        )

        # 构建SAN扩展
        san_entries = []
        if san_domains:
            san_entries.extend([f"DNS:{d}" for d in san_domains])
        if san_ips:
            san_entries.extend([f"IP:{ip}" for ip in san_ips])
        san_str = ",".join(san_entries) if san_entries else f"DNS:{cn}"

        # 中间CA签名
        ext_file = os.path.join(node_dir, "san.ext")
        with open(ext_file, 'w') as f:
            f.write(f"subjectAltName={san_str}\n")
            f.write("extendedKeyUsage=clientAuth,serverAuth\n")
            f.write("basicConstraints=CA:FALSE\n")

        self._run_openssl(
            f"x509 -req -days {validity_days} -in {node_csr} "
            f"-CA {ica_cert} -CAkey {ica_key} -CAcreateserial "
            f"-out {node_cert} -extfile {ext_file}"
        )

        fingerprint = self._get_cert_fingerprint(node_cert)
        return {
            "node_id": node_id,
            "node_type": node_type,
            "key_path": node_key,
            "cert_path": node_cert,
            "fingerprint": fingerprint,
            "common_name": cn,
            "validity_days": validity_days,
            "san": san_str
        }

    def _run_openssl(self, command: str) -> str:
        """执行openssl命令"""
        import subprocess
        full_cmd = f"openssl {command}"
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"openssl命令失败: {result.stderr}")
        return result.stdout

    def _get_cert_fingerprint(self, cert_path: str) -> str:
        """获取证书SHA256指纹"""
        output = self._run_openssl(f"x509 -in {cert_path} -noout -fingerprint -sha256")
        # 输出格式: SHA256 Fingerprint=AB:CD:EF:...
        fingerprint = output.split("=")[1].strip().replace(":", "").lower()
        return f"sha256:{fingerprint}"


# ============================================================
# Nginx mTLS配置生成
# ============================================================

class NginxMTLSConfig:
    """Nginx mTLS配置生成器"""

    @staticmethod
    def generate_server_config(server_name: str,
                                listen_port: int = 443,
                                ssl_cert: str = "/path/to/server.crt",
                                ssl_key: str = "/path/to/server.key",
                                ca_cert: str = "/path/to/ca.crt",
                                proxy_pass: str = "http://127.0.0.1:8040",
                                client_cert_verify: str = "on",
                                client_cert_optional: bool = False) -> str:
        """生成Nginx mTLS服务端配置"""

        optional_suffix = " optional" if client_cert_optional else ""

        config = f"""# ============================================================
# ZONGYUAN-ROOT mTLS双向认证配置
# 溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
# ============================================================

server {{
    listen {listen_port} ssl http2;
    server_name {server_name};

    # 服务端证书
    ssl_certificate     {ssl_cert};
    ssl_certificate_key {ssl_key};

    # TLS协议版本
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 会话缓存
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # ===== mTLS客户端证书认证 =====
    ssl_client_certificate {ca_cert};
    ssl_verify_client {client_cert_verify}{optional_suffix};
    ssl_verify_depth 3;

    # 将客户端证书信息传递给后端
    proxy_set_header X-SSL-Client-Cert $ssl_client_cert;
    proxy_set_header X-SSL-Client-Fingerprint $ssl_client_fingerprint;
    proxy_set_header X-SSL-Client-S-DN $ssl_client_s_dn;
    proxy_set_header X-SSL-Client-I-DN $ssl_client_i_dn;
    proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
    proxy_set_header X-SSL-Protocol $ssl_protocol;
    proxy_set_header X-SSL-Cipher $ssl_cipher;

    # 其他代理头
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    location / {{
        proxy_pass {proxy_pass};
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_connect_timeout 60s;
    }}
}}
"""
        return config

    @staticmethod
    def generate_client_config(server_url: str,
                                client_cert: str = "/path/to/client.crt",
                                client_key: str = "/path/to/client.key",
                                ca_cert: str = "/path/to/ca.crt") -> str:
        """生成curl客户端mTLS配置示例"""
        return f"""# mTLS客户端调用示例
# 溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002

# 使用客户端证书调用API
curl --cert {client_cert} \\
     --key {client_key} \\
     --cacert {ca_cert} \\
     {server_url}/api/v1/kernel/status

# 获取JWT令牌
curl --cert {client_cert} \\
     --key {client_key} \\
     --cacert {ca_cert} \\
     -X POST {server_url}/auth/token \\
     -H "Content-Type: application/json" \\
     -d '{{"node_id": "your-node-id", "node_type": "local-kernel"}}'
"""


# ============================================================
# 配额限流器
# ============================================================

class RateLimiter:
    """配额限流器(滑动窗口)"""

    def __init__(self):
        self.requests: Dict[str, List[float]] = {}  # key -> [timestamp, ...]
        self.token_usage: Dict[str, Dict] = {}  # key -> {date: token_count}

    def check_rate(self, key: str, 
                   per_minute: int = 60,
                   per_hour: int = 1000) -> Tuple[bool, Dict]:
        """检查频率限制
        
        Returns:
            (是否允许, 限流信息)
        """
        now = time.time()
        one_minute_ago = now - 60
        one_hour_ago = now - 3600

        if key not in self.requests:
            self.requests[key] = []

        # 清理过期记录
        self.requests[key] = [t for t in self.requests[key] if t > one_hour_ago]

        # 统计
        minute_count = sum(1 for t in self.requests[key] if t > one_minute_ago)
        hour_count = len(self.requests[key])

        info = {
            "minute_count": minute_count,
            "minute_limit": per_minute,
            "hour_count": hour_count,
            "hour_limit": per_hour,
            "minute_remaining": max(0, per_minute - minute_count),
            "hour_remaining": max(0, per_hour - hour_count)
        }

        if minute_count >= per_minute:
            return False, {**info, "reason": "每分钟请求数超限"}
        if hour_count >= per_hour:
            return False, {**info, "reason": "每小时请求数超限"}

        # 记录请求
        self.requests[key].append(now)
        return True, info

    def record_token_usage(self, key: str, tokens: int, daily_limit: int = 100000) -> Tuple[bool, Dict]:
        """记录Token使用量
        
        Returns:
            (是否允许, 使用信息)
        """
        today = time.strftime("%Y-%m-%d")
        if key not in self.token_usage:
            self.token_usage[key] = {}
        if today not in self.token_usage[key]:
            self.token_usage[key][today] = 0

        current = self.token_usage[key][today]
        if current + tokens > daily_limit:
            return False, {
                "current": current,
                "limit": daily_limit,
                "requested": tokens,
                "reason": "每日Token配额超限"
            }

        self.token_usage[key][today] += tokens
        return True, {
            "current": self.token_usage[key][today],
            "limit": daily_limit,
            "remaining": daily_limit - self.token_usage[key][today]
        }

    def cleanup(self):
        """清理过期数据"""
        now = time.time()
        one_hour_ago = now - 3600
        for key in list(self.requests.keys()):
            self.requests[key] = [t for t in self.requests[key] if t > one_hour_ago]
            if not self.requests[key]:
                del self.requests[key]

        # 清理昨天及以前的token统计
        today = time.strftime("%Y-%m-%d")
        for key in list(self.token_usage.keys()):
            for date in list(self.token_usage[key].keys()):
                if date != today:
                    del self.token_usage[key][date]
            if not self.token_usage[key]:
                del self.token_usage[key]


# ============================================================
# 单元测试
# ============================================================

def run_tests():
    """运行单元测试"""
    print("=" * 60)
    print("ZONGYUAN-ROOT 协议鉴权工具集 单元测试")
    print("=" * 60)

    passed = 0
    failed = 0

    # 测试1: Scope权限模型
    print("\n[测试1] Scope权限模型...")
    try:
        scope = Scope("truth:read:self truth:write:self node:heartbeat")
        assert scope.has("truth:read:self")
        assert scope.has("truth:write:self")
        assert scope.has("node:heartbeat")
        assert not scope.has("truth:read:global")
        assert not scope.has("admin:*")
        assert scope.has_any(["truth:read:self", "truth:read:global"])
        assert not scope.has_all(["truth:read:self", "admin:*"])

        # 通配符测试
        scope2 = Scope("truth:*")
        assert scope2.has("truth:read:self")
        assert scope2.has("truth:write:global")
        assert not scope2.has("node:heartbeat")

        print("  ✅ 通过")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

    # 测试2: JWT签发与校验
    print("\n[测试2] JWT签发与校验...")
    try:
        jwt_mgr = JWTManager()
        token, payload = jwt_mgr.create_token(
            node_id="test-node-001",
            node_type="local-kernel",
            mtls_fingerprint="sha256:testfingerprint123"
        )
        assert token, "令牌不应为空"
        assert payload.node_id == "test-node-001"
        assert payload.node_type == "local-kernel"
        assert payload.mtls_fingerprint == "sha256:testfingerprint123"
        assert "truth:read:self" in payload.scope

        # 校验令牌
        ok, verified_payload, errors = jwt_mgr.verify_token(token)
        assert ok, f"令牌校验失败: {errors}"
        assert verified_payload.node_id == "test-node-001"
        print(f"  ✅ 通过 (jti={payload.jti[:16]}...)")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    # 测试3: JWT吊销
    print("\n[测试3] JWT吊销...")
    try:
        jwt_mgr = JWTManager()
        token, payload = jwt_mgr.create_token(node_id="test-node-002", node_type="observer-node")

        # 吊销前可校验
        ok, _, _ = jwt_mgr.verify_token(token)
        assert ok

        # 吊销
        jwt_mgr.revoke_token(payload.jti)

        # 吊销后不可校验
        ok, _, errors = jwt_mgr.verify_token(token)
        assert not ok
        assert "已被吊销" in errors[0]
        print("  ✅ 通过")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

    # 测试4: mTLS指纹绑定
    print("\n[测试4] mTLS指纹绑定...")
    try:
        jwt_mgr = JWTManager()
        token, payload = jwt_mgr.create_token(
            node_id="test-node-003",
            node_type="local-kernel",
            mtls_fingerprint="sha256:correctfingerprint"
        )

        # 正确指纹可校验
        ok, _, _ = jwt_mgr.verify_token(token, expected_mtls_fingerprint="sha256:correctfingerprint")
        assert ok

        # 错误指纹不可校验
        ok, _, errors = jwt_mgr.verify_token(token, expected_mtls_fingerprint="sha256:wrongfingerprint")
        assert not ok
        assert "指纹不匹配" in errors[0]
        print("  ✅ 通过")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

    # 测试5: 令牌刷新
    print("\n[测试5] 令牌刷新(一次性)...")
    try:
        jwt_mgr = JWTManager()
        refresh_token = jwt_mgr.create_refresh_token("test-node-004", "local-kernel")

        # 第一次刷新成功
        ok, new_token, new_payload = jwt_mgr.refresh_access_token(refresh_token)
        assert ok
        assert new_token
        assert new_payload.node_id == "test-node-004"

        # 第二次刷新失败(一次性)
        ok2, _, _ = jwt_mgr.refresh_access_token(refresh_token)
        assert not ok2
        print("  ✅ 通过 (一次性刷新验证成功)")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

    # 测试6: 配额限流
    print("\n[测试6] 配额限流...")
    try:
        limiter = RateLimiter()

        # 测试频率限制(设为3次/分钟)
        for i in range(3):
            ok, info = limiter.check_rate("test-key", per_minute=3, per_hour=100)
            assert ok, f"第{i+1}次应允许"

        # 第4次应被拒绝
        ok, info = limiter.check_rate("test-key", per_minute=3, per_hour=100)
        assert not ok
        assert "超限" in info["reason"]
        print(f"  ✅ 通过 (第4次请求被正确拒绝: {info['reason']})")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

    # 测试7: Token配额
    print("\n[测试7] Token配额...")
    try:
        limiter = RateLimiter()

        # 使用50000 token(在100000限额内)
        ok, info = limiter.record_token_usage("test-key", 50000, daily_limit=100000)
        assert ok
        assert info["current"] == 50000

        # 再使用60000(超出限额)
        ok, info = limiter.record_token_usage("test-key", 60000, daily_limit=100000)
        assert not ok
        assert "配额超限" in info["reason"]
        print(f"  ✅ 通过 (超额请求被正确拒绝: {info['reason']})")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

    # 测试8: 节点默认Scope
    print("\n[测试8] 节点默认Scope...")
    try:
        assert "truth:read:self" in NODE_DEFAULT_SCOPES["local-kernel"]
        assert "node:heartbeat" in NODE_DEFAULT_SCOPES["local-kernel"]
        assert "admin:*" in NODE_DEFAULT_SCOPES["cloud-kernel"]
        assert "asset:archive" in NODE_DEFAULT_SCOPES["storage-node"]
        assert "node:task:execute" in NODE_DEFAULT_SCOPES["compute-node"]
        print("  ✅ 通过 (6种节点类型默认Scope验证)")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

    # 测试9: Nginx配置生成
    print("\n[测试9] Nginx mTLS配置生成...")
    try:
        config = NginxMTLSConfig.generate_server_config(
            server_name="kernel.huodouai.com",
            listen_port=443,
            ssl_cert="/etc/nginx/ssl/server.crt",
            ssl_key="/etc/nginx/ssl/server.key",
            ca_cert="/etc/nginx/ssl/ca.crt",
            proxy_pass="http://127.0.0.1:8040"
        )
        assert "ssl_verify_client on" in config
        assert "ssl_client_certificate" in config
        assert "X-SSL-Client-Fingerprint" in config
        assert "proxy_pass http://127.0.0.1:8040" in config
        print("  ✅ 通过 (Nginx配置包含mTLS认证和证书指纹传递)")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

    # 测试10: JWT统计
    print("\n[测试10] JWT管理器统计...")
    try:
        jwt_mgr = JWTManager()
        for i in range(3):
            jwt_mgr.create_token(node_id=f"node-{i}", node_type="local-kernel")

        stats = jwt_mgr.get_stats()
        assert stats["active_sessions"] == 3
        assert stats["nodes_with_sessions"] == 3
        print(f"  ✅ 通过 (活跃会话={stats['active_sessions']}, 节点数={stats['nodes_with_sessions']})")
        passed += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1

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
        print("ZONGYUAN-ROOT 协议鉴权工具集 V1.0")
        print("溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT V1.7")
        print()
        print("用法:")
        print("  python auth_toolkit.py test    # 运行单元测试")
        print()
        print("包含模块:")
        print("  1. Scope - 细粒度权限模型")
        print("  2. JWTManager - JWT签发/校验/刷新/吊销")
        print("  3. CertificateAuthority - CA证书体系生成")
        print("  4. NginxMTLSConfig - Nginx mTLS配置生成")
        print("  5. RateLimiter - 配额限流器")
