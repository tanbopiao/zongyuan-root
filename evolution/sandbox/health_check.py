#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 沙箱健康检查脚本
功能：容器健康检查，验证沙箱环境是否正常运行
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path


def check_python() -> bool:
    """检查Python环境"""
    try:
        result = subprocess.run(
            ['python3', '--version'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def check_workspace() -> bool:
    """检查工作目录"""
    try:
        workspace = Path('/workspace')
        return workspace.exists() and workspace.is_dir()
    except Exception:
        return False


def check_network() -> bool:
    """检查网络（可选，沙箱可能限制网络）"""
    try:
        result = subprocess.run(
            ['curl', '-s', '--connect-timeout', '3', 'https://www.baidu.com'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False  # 网络受限是正常的


def check_disk_space() -> bool:
    """检查磁盘空间"""
    try:
        result = subprocess.run(
            ['df', '-h', '/workspace'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                usage = int(parts[4].replace('%', ''))
                return usage < 90
        return True
    except Exception:
        return True


def check_memory() -> bool:
    """检查内存"""
    try:
        result = subprocess.run(
            ['free', '-m'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                total = int(parts[1])
                available = int(parts[6]) if len(parts) > 6 else int(parts[3])
                return available > total * 0.1  # 至少10%可用
        return True
    except Exception:
        return True


def main():
    """主函数"""
    checks = {
        'python': check_python(),
        'workspace': check_workspace(),
        'disk_space': check_disk_space(),
        'memory': check_memory(),
    }
    
    # 网络检查是可选的
    checks['network'] = check_network()
    
    all_passed = all([
        checks['python'],
        checks['workspace'],
        checks['disk_space'],
        checks['memory'],
    ])
    
    health_status = {
        'status': 'healthy' if all_passed else 'unhealthy',
        'checks': checks,
        'checked_at': datetime.now().isoformat(),
        'container_id': os.environ.get('HOSTNAME', 'unknown'),
        '溯源标识': 'Ω₀⊂⊙∞⊂Ω',
        '确权编码': 'DID-BR-000002'
    }
    
    # 输出健康状态
    print(json.dumps(health_status, ensure_ascii=False, indent=2))
    
    # 返回退出码
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
