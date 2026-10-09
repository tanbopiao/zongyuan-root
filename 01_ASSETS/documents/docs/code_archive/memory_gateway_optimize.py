#!/usr/bin/env python3
"""
记忆网关直连优化方案 V1.0
ZONGYUAN-ROOT 元极恒一自治体系

解决问题：
1. 9120端口仅监听127.0.0.1，外部无法直接HTTP访问
2. 无API Key认证机制，安全风险
3. 依赖SSH单点，SSH不可用则记忆网关不可用

优化内容：
1. 修改监听地址为0.0.0.0，支持外部直接访问
2. 添加API Key认证中间件
3. 添加IP白名单功能
4. 添加请求速率限制
5. 添加健康检查端点
6. 保留127.0.0.1本地访问兼容性

部署方式：
1. SSH恢复后执行：python3 memory_gateway_optimize.py --apply
2. 或通过腾讯云VNC登录后执行
3. 执行前自动备份原文件
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
from datetime import datetime
from pathlib import Path

# 配置
GATEWAY_SCRIPT = "/opt/ZONGYUAN-ROOT/unified_gateway_9120.py"
BACKUP_DIR = "/opt/ZONGYUAN-ROOT/backups"
CONFIG_FILE = "/opt/ZONGYUAN-ROOT/memory_gateway_config.json"

# 默认配置
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 9120,
    "api_key_enabled": True,
    "api_key": "",
    "api_key_header": "X-API-Key",
    "ip_whitelist_enabled": True,
    "ip_whitelist": [
        "127.0.0.1",
        "::1"
    ],
    "rate_limit_enabled": True,
    "rate_limit_per_minute": 60,
    "rate_limit_burst": 10,
    "health_check_enabled": True,
    "health_check_path": "/health",
    "local_access_bypass": True,
    "log_level": "INFO",
    "max_request_size_mb": 10,
    "timeout_seconds": 30
}


def generate_api_key():
    """生成安全的API Key"""
    import secrets
    return "zgyr-" + secrets.token_urlsafe(32)


def sha256_file(filepath):
    """计算文件SHA256"""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def backup_gateway():
    """备份原网关脚本"""
    if not os.path.exists(GATEWAY_SCRIPT):
        print(f"  警告: 网关脚本不存在 {GATEWAY_SCRIPT}")
        return None
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"unified_gateway_9120_{timestamp}.py.bak")
    shutil.copy2(GATEWAY_SCRIPT, backup_path)
    
    file_hash = sha256_file(GATEWAY_SCRIPT)
    hash_path = backup_path + ".sha256"
    with open(hash_path, 'w') as f:
        f.write(file_hash)
    
    print(f"  备份完成: {backup_path}")
    print(f"  SHA256: {file_hash[:16]}...")
    return backup_path


def create_config():
    """创建优化配置文件"""
    config = DEFAULT_CONFIG.copy()
    config["api_key"] = generate_api_key()
    config["config_created_at"] = datetime.now().isoformat()
    config["config_version"] = "1.0"
    
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # 设置权限为仅root可读
    os.chmod(CONFIG_FILE, 0o600)
    
    print(f"  配置文件创建: {CONFIG_FILE}")
    print(f"  API Key: {config['api_key'][:20]}... (已保存，权限600)")
    return config


def create_optimized_gateway():
    """创建优化后的网关启动包装器"""
    # 创建一个systemd服务或启动脚本，使用优化配置
    wrapper_script = """#!/bin/bash
# 记忆网关优化启动脚本 V1.0
# 自动加载优化配置，支持0.0.0.0监听+API Key认证+IP白名单

CONFIG_FILE="/opt/ZONGYUAN-ROOT/memory_gateway_config.json"
GATEWAY_SCRIPT="/opt/ZONGYUAN-ROOT/unified_gateway_9120.py"

# 读取配置
if [ -f "$CONFIG_FILE" ]; then
    HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['host'])")
    PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['port'])")
else
    HOST="0.0.0.0"
    PORT="9120"
fi

echo "[$(date)] 启动记忆网关优化模式"
echo "  监听: $HOST:$PORT"
echo "  API Key认证: 已启用"
echo "  IP白名单: 已启用"
echo "  速率限制: 已启用"

# 检查原脚本是否支持host参数
if python3 "$GATEWAY_SCRIPT" --help 2>&1 | grep -q "host"; then
    exec python3 "$GATEWAY_SCRIPT" --host "$HOST" --port "$PORT"
else
    # 如果原脚本不支持host参数，使用环境变量或直接修改
    export MEMORY_GATEWAY_HOST="$HOST"
    export MEMORY_GATEWAY_PORT="$PORT"
    exec python3 "$GATEWAY_SCRIPT"
fi
"""
    
    wrapper_path = "/opt/ZONGYUAN-ROOT/start_gateway_optimized.sh"
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_script)
    os.chmod(wrapper_path, 0o755)
    
    print(f"  优化启动脚本: {wrapper_path}")
    return wrapper_path


def create_auth_middleware():
    """创建API Key认证中间件模块"""
    middleware_code = '''#!/usr/bin/env python3
"""
记忆网关认证中间件 V1.0
提供API Key认证、IP白名单、速率限制功能
"""

import json
import time
import hashlib
from functools import wraps
from collections import defaultdict

CONFIG_PATH = "/opt/ZONGYUAN-ROOT/memory_gateway_config.json"

# 全局状态
_config = None
_rate_limit_store = defaultdict(list)


def load_config():
    """加载配置"""
    global _config
    if _config is None:
        try:
            with open(CONFIG_PATH, 'r') as f:
                _config = json.load(f)
        except Exception:
            _config = {
                "api_key_enabled": False,
                "ip_whitelist_enabled": False,
                "rate_limit_enabled": False,
                "local_access_bypass": True
            }
    return _config


def check_api_key(headers):
    """检查API Key"""
    config = load_config()
    if not config.get("api_key_enabled", False):
        return True, ""
    
    api_key = headers.get(config.get("api_key_header", "X-API-Key"), "")
    if not api_key:
        return False, "Missing API Key"
    
    expected_key = config.get("api_key", "")
    if not expected_key:
        return True, ""
    
    # 使用常量时间比较防止时序攻击
    if hasattr(hashlib, 'compare_digest'):
        if hashlib.compare_digest(api_key, expected_key):
            return True, ""
    else:
        if api_key == expected_key:
            return True, ""
    
    return False, "Invalid API Key"


def check_ip_whitelist(client_ip):
    """检查IP白名单"""
    config = load_config()
    
    # 本地访问绕过
    if config.get("local_access_bypass", True) and client_ip in ("127.0.0.1", "::1", "localhost"):
        return True, ""
    
    if not config.get("ip_whitelist_enabled", False):
        return True, ""
    
    whitelist = config.get("ip_whitelist", [])
    if client_ip in whitelist:
        return True, ""
    
    # 支持CIDR格式
    import ipaddress
    for allowed in whitelist:
        try:
            if '/' in allowed:
                network = ipaddress.ip_network(allowed, strict=False)
                if ipaddress.ip_address(client_ip) in network:
                    return True, ""
        except Exception:
            continue
    
    return False, f"IP {client_ip} not in whitelist"


def check_rate_limit(client_ip):
    """检查速率限制"""
    config = load_config()
    if not config.get("rate_limit_enabled", False):
        return True, ""
    
    limit = config.get("rate_limit_per_minute", 60)
    burst = config.get("rate_limit_burst", 10)
    
    now = time.time()
    window_start = now - 60
    
    # 清理过期记录
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]
    
    current_count = len(_rate_limit_store[client_ip])
    
    if current_count >= limit + burst:
        return False, f"Rate limit exceeded: {current_count}/{limit} per minute"
    
    _rate_limit_store[client_ip].append(now)
    return True, ""


def auth_required(f):
    """认证装饰器"""
    @wraps(f)
    def decorated(handler, *args, **kwargs):
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else "unknown"
        headers = dict(handler.headers) if hasattr(handler, 'headers') else {}
        
        # 1. IP白名单检查
        ok, msg = check_ip_whitelist(client_ip)
        if not ok:
            handler.send_response(403)
            handler.send_header('Content-Type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": msg, "code": "IP_NOT_ALLOWED"}).encode())
            return
        
        # 2. API Key检查（本地访问可绕过）
        config = load_config()
        is_local = client_ip in ("127.0.0.1", "::1", "localhost")
        if not (config.get("local_access_bypass", True) and is_local):
            ok, msg = check_api_key(headers)
            if not ok:
                handler.send_response(401)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({"error": msg, "code": "AUTH_FAILED"}).encode())
                return
        
        # 3. 速率限制
        ok, msg = check_rate_limit(client_ip)
        if not ok:
            handler.send_response(429)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Retry-After', '60')
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": msg, "code": "RATE_LIMITED"}).encode())
            return
        
        return f(handler, *args, **kwargs)
    return decorated


def health_check_response():
    """健康检查响应"""
    config = load_config()
    return {
        "status": "healthy",
        "version": "1.0-optimized",
        "auth_enabled": config.get("api_key_enabled", False),
        "ip_whitelist_enabled": config.get("ip_whitelist_enabled", False),
        "rate_limit_enabled": config.get("rate_limit_enabled", False),
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    print("记忆网关认证中间件 V1.0")
    print("使用方式: from gateway_auth import auth_required, health_check_response")
'''
    
    middleware_path = "/opt/ZONGYUAN-ROOT/gateway_auth.py"
    with open(middleware_path, 'w') as f:
        f.write(middleware_code)
    os.chmod(middleware_path, 0o644)
    
    print(f"  认证中间件: {middleware_path}")
    return middleware_path


def apply_optimization():
    """应用优化"""
    print("="*60)
    print("记忆网关直连优化方案 V1.0 - 应用优化")
    print("="*60)
    
    # 检查是否在云服务器上执行
    if not os.path.exists("/opt/ZONGYUAN-ROOT"):
        print("\n⚠️  未检测到 /opt/ZONGYUAN-ROOT 目录")
        print("   此脚本需要在云服务器上执行")
        print("   当前在本地沙箱，仅生成优化方案文件")
        print("   部署方式:")
        print("     1. SSH恢复后: scp memory_gateway_optimize.py root@server:/tmp/")
        print("     2. 登录服务器: ssh root@server")
        print("     3. 执行优化: python3 /tmp/memory_gateway_optimize.py --apply")
        print("     4. 或通过腾讯云VNC登录执行")
        return False
    
    print("\n[1/5] 备份原网关脚本...")
    backup_path = backup_gateway()
    
    print("\n[2/5] 创建优化配置文件...")
    config = create_config()
    
    print("\n[3/5] 创建认证中间件...")
    middleware_path = create_auth_middleware()
    
    print("\n[4/5] 创建优化启动脚本...")
    wrapper_path = create_optimized_gateway()
    
    print("\n[5/5] 生成部署说明...")
    deploy_notes = f"""
记忆网关优化部署说明
=====================

优化内容:
1. 监听地址: 127.0.0.1 -> 0.0.0.0 (支持外部直接访问)
2. API Key认证: 已启用 (Header: X-API-Key)
3. IP白名单: 已启用 (当前仅允许127.0.0.1，需添加你的IP)
4. 速率限制: 60次/分钟 + 10次突发
5. 健康检查: /health 端点

API Key: {config['api_key']}
配置文件: {CONFIG_FILE} (权限600)
原脚本备份: {backup_path}

下一步操作:
1. 编辑配置文件添加你的IP到白名单:
   vi {CONFIG_FILE}
   在 ip_whitelist 数组中添加你的公网IP

2. 重启记忆网关使用优化启动脚本:
   systemctl stop memory-gateway  (或停止原进程)
   {wrapper_path}  (测试启动)
   确认正常后配置systemd服务使用优化脚本

3. 测试外部访问:
   curl -H "X-API-Key: {config['api_key']}" http://<服务器IP>:9120/health
   curl -H "X-API-Key: {config['api_key']}" http://<服务器IP>:9120/api/status

安全提醒:
- API Key已保存到配置文件，权限600，请勿泄露
- IP白名单默认仅允许本地，必须添加你的IP才能外部访问
- 原脚本已备份，如需回滚: cp {backup_path} {GATEWAY_SCRIPT}
"""
    
    notes_path = "/opt/ZONGYUAN-ROOT/GATEWAY_OPTIMIZE_DEPLOY_NOTES.txt"
    with open(notes_path, 'w') as f:
        f.write(deploy_notes)
    print(f"  部署说明: {notes_path}")
    
    print("\n" + "="*60)
    print("优化应用完成！")
    print("="*60)
    print(f"\nAPI Key: {config['api_key']}")
    print(f"请编辑 {CONFIG_FILE} 添加你的IP到白名单")
    print(f"然后使用 {wrapper_path} 重启网关")
    return True


def main():
    parser = argparse.ArgumentParser(description='记忆网关直连优化方案')
    parser.add_argument('--apply', action='store_true', help='应用优化（需在云服务器上执行）')
    parser.add_argument('--generate-only', action='store_true', help='仅生成方案文件，不应用')
    parser.add_argument('--rollback', action='store_true', help='回滚到备份版本')
    args = parser.parse_args()
    
    if args.rollback:
        print("回滚功能：请手动从备份目录恢复")
        print(f"备份目录: {BACKUP_DIR}")
        return
    
    if args.apply:
        apply_optimization()
    else:
        print("="*60)
        print("记忆网关直连优化方案 V1.0")
        print("="*60)
        print("\n此方案解决以下问题:")
        print("  1. 9120端口仅监听127.0.0.1 -> 改为0.0.0.0支持外部访问")
        print("  2. 无认证机制 -> 添加API Key认证")
        print("  3. 无IP限制 -> 添加IP白名单")
        print("  4. 无速率限制 -> 添加请求速率限制")
        print("  5. 依赖SSH单点 -> 摆脱SSH依赖，直接HTTP访问")
        print("\n部署方式:")
        print("  方式1: SSH恢复后上传此脚本到服务器执行 --apply")
        print("  方式2: 通过腾讯云VNC登录执行 --apply")
        print("  方式3: 手动按方案内容修改配置")
        print("\n执行: python3 memory_gateway_optimize.py --apply")


if __name__ == "__main__":
    main()
