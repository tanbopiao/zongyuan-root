"""SSH远程运维工具集
支持：密钥/密码连接、命令执行、服务管理、日志查看、资源监控、部署执行
安全：命令白名单、危险命令拦截、操作审计、超时控制
"""
import paramiko, json, os, time, re, hashlib
from datetime import datetime
from cryptography.fernet import Fernet

# 危险命令黑名单（绝对禁止）
DANGEROUS_PATTERNS = [
    r'rm\s+-rf\s+/', r'mkfs', r'dd\s+if=', r':\(\)\s*\{',  # fork bomb
    r'>\s*/dev/sda', r'chmod\s+-R\s+777\s+/', r'shutdown',
    r'halt', r'poweroff', r'reboot\s',  # 允许reboot但需确认
    r'iptables\s+-F', r'cat\s+/etc/shadow',
]

# 允许的命令前缀（白名单）
ALLOWED_PREFIXES = [
    'systemctl', 'service', 'docker', 'docker-compose', 'nginx',
    'ls', 'cat', 'head', 'tail', 'grep', 'find', 'df', 'du',
    'free', 'top', 'ps', 'uptime', 'uname', 'hostname', 'ifconfig',
    'curl', 'wget', 'git', 'pip', 'pip3', 'python', 'python3',
    'node', 'npm', 'pm2', 'supervisorctl', 'journalctl',
    'mkdir', 'touch', 'chmod', 'chown', 'cp', 'mv',
    'echo', 'export', 'source', 'bash', 'sh',
    'lark-cli', 'nginx -t', 'nginx -s',
    'fuser', 'netstat', 'ss', 'lsof',
    'tar', 'zip', 'unzip', 'scp',
]


class LocalOps:
    """本地执行模式（管理自身服务器，无需SSH）"""
    def __init__(self):
        self.host = "127.0.0.1"
        self.audit_log = []
    
    def connect(self, timeout=15):
        return {"success": True, "host": "localhost", "mode": "local"}
    
    def _check_command(self, command):
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return False, f"危险命令被拦截: {pattern}"
        return True, ""
    
    def execute(self, command, timeout=60):
        import subprocess
        safe, reason = self._check_command(command)
        if not safe:
            result = {"success": False, "command": command, "error": reason, "timestamp": datetime.now().isoformat(), "mode": "local"}
            self.audit_log.append(result)
            return result
        try:
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            result = {
                "success": proc.returncode == 0,
                "command": command,
                "exit_code": proc.returncode,
                "output": proc.stdout[:5000],
                "error": proc.stderr[:2000] if proc.stderr else "",
                "timestamp": datetime.now().isoformat(),
                "mode": "local"
            }
            self.audit_log.append(result)
            return result
        except subprocess.TimeoutExpired:
            return {"success": False, "command": command, "error": "执行超时", "mode": "local"}
        except Exception as e:
            return {"success": False, "command": command, "error": str(e), "mode": "local"}
    
    def service_status(self, service_name):
        return self.execute(f"systemctl is-active {service_name}")
    def service_restart(self, service_name):
        return self.execute(f"systemctl restart {service_name} && systemctl is-active {service_name}")
    def service_logs(self, service_name, lines=50):
        return self.execute(f"journalctl -u {service_name} -n {lines} --no-pager")
    def resource_monitor(self):
        return self.execute("echo '=== CPU ===' && uptime && echo '=== MEMORY ===' && free -h && echo '=== DISK ===' && df -h / && echo '=== LOAD ===' && cat /proc/loadavg")
    def port_check(self, port):
        return self.execute(f"ss -tlnp | grep :{port} || echo '端口{port}未监听'")
    def close(self):
        pass

class SSHOps:
    def __init__(self, host, port=22, username='root', password=None, key_path=None, key_content=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.key_content = key_content
        self.client = None
        self.audit_log = []
    
    def connect(self, timeout=15):
        """建立SSH连接"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            if self.key_content:
                import io
                pkey = paramiko.RSAKey.from_private_key(io.StringIO(self.key_content))
                self.client.connect(self.host, port=self.port, username=self.username, pkey=pkey, timeout=timeout)
            elif self.key_path and os.path.exists(self.key_path):
                self.client.connect(self.host, port=self.port, username=self.username, key_filename=self.key_path, timeout=timeout)
            elif self.password:
                self.client.connect(self.host, port=self.port, username=self.username, password=self.password, timeout=timeout)
            else:
                return {"success": False, "error": "未提供认证方式（密码或密钥）"}
            return {"success": True, "host": self.host}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_command(self, command):
        """安全检查"""
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return False, f"危险命令被拦截: {pattern}"
        # 白名单检查（第一个命令必须在白名单中）
        first_cmd = command.strip().split()[0] if command.strip() else ""
        if first_cmd and not any(first_cmd.startswith(p) for p in ALLOWED_PREFIXES):
            # 允许管道和复合命令，但第一个命令必须安全
            return False, f"命令不在白名单中: {first_cmd}"
        return True, ""
    
    def execute(self, command, timeout=60):
        """执行命令"""
        if not self.client:
            conn = self.connect()
            if not conn["success"]:
                return conn
        
        safe, reason = self._check_command(command)
        if not safe:
            result = {"success": False, "command": command, "error": reason, "timestamp": datetime.now().isoformat()}
            self.audit_log.append(result)
            return result
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')
            result = {
                "success": exit_code == 0,
                "command": command,
                "exit_code": exit_code,
                "output": output[:5000],  # 限制输出长度
                "error": error[:2000] if error else "",
                "timestamp": datetime.now().isoformat()
            }
            self.audit_log.append(result)
            return result
        except Exception as e:
            result = {"success": False, "command": command, "error": str(e), "timestamp": datetime.now().isoformat()}
            self.audit_log.append(result)
            return result
    
    def service_status(self, service_name):
        """检查服务状态"""
        return self.execute(f"systemctl is-active {service_name}")
    
    def service_restart(self, service_name):
        """重启服务"""
        return self.execute(f"systemctl restart {service_name} && systemctl is-active {service_name}")
    
    def service_logs(self, service_name, lines=50):
        """查看服务日志"""
        return self.execute(f"journalctl -u {service_name} -n {lines} --no-pager")
    
    def resource_monitor(self):
        """资源监控"""
        cmd = "echo '=== CPU ===' && uptime && echo '=== MEMORY ===' && free -h && echo '=== DISK ===' && df -h / && echo '=== LOAD ===' && cat /proc/loadavg"
        return self.execute(cmd)
    
    def process_list(self, keyword=None):
        """进程列表"""
        cmd = f"ps aux | grep {keyword} | grep -v grep" if keyword else "ps aux --sort=-%mem | head -20"
        return self.execute(cmd)
    
    def port_check(self, port):
        """端口检查"""
        return self.execute(f"ss -tlnp | grep :{port} || echo '端口{port}未监听'")
    
    def disk_usage(self, path='/'):
        """磁盘使用"""
        return self.execute(f"du -sh {path} 2>/dev/null && df -h {path}")
    
    def deploy_script(self, script_content, script_name='deploy.sh'):
        """部署脚本执行"""
        upload = self.execute(f"cat > /tmp/{script_name} << 'SCRIPT_EOF'\n{script_content}\nSCRIPT_EOF")
        if not upload["success"]:
            return upload
        return self.execute(f"chmod +x /tmp/{script_name} && bash /tmp/{script_name}")
    
    def close(self):
        if self.client:
            self.client.close()

# 服务器凭据加密存储
class CredentialStore:
    def __init__(self, db_path):
        self.db_path = db_path
        self.key = self._get_or_create_key()
    
    def _get_or_create_key(self):
        key_file = self.db_path + '.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        os.chmod(key_file, 0o600)
        return key
    
    def encrypt(self, text):
        return Fernet(self.key).encrypt(text.encode()).decode()
    
    def decrypt(self, token):
        return Fernet(self.key).decrypt(token.encode()).decode()

print("  ✅ SSH运维工具模块创建完成")
