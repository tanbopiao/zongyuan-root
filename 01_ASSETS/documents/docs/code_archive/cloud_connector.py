"""
火斗云智AIOS - 云端服务器连接工具库
统一封装SSH、记忆网关、FRP等连接方式
"""
import os
import sys
import json
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

@dataclass
class CloudConfig:
    """云端配置"""
    server_ip: str = "123.207.202.158"
    ssh_user: str = "root"
    ssh_port: int = 22
    ssh_key_path: str = ""
    gateway_url: str = "https://www.huodouai.com/api/report/truth"
    gateway_query_url: str = "https://www.huodouai.com/api/truth"
    frp_server_port: int = 7000
    frp_token: str = "ZONGYUAN-FRP-2026-SECRET"
    dynamic_ip_port: int = 9130
    dynamic_ip_token: str = "ZONGYUAN-DYNAMIC-IP-2026-SECRET-KEY"
    node_id: str = "local-windows-001"
    did: str = "DID-BR-000002"
    trace_mark: str = "Ω₀⊂⊙∞⊂Ω"

class CloudConnector:
    """云端连接器 - 统一管理所有云端连接"""
    
    def __init__(self, config: CloudConfig = None):
        self.config = config or CloudConfig()
        self._ssh_connected = False
        self._tunnels = []
        
        # 自动检测密钥路径
        if not self.config.ssh_key_path:
            possible_paths = [
                os.path.expanduser("~/.ssh/id_ed25519_zongyuan"),
                os.path.expanduser("~/.ssh/id_rsa"),
                "C:/Users/4906/.ssh/id_ed25519_zongyuan",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    self.config.ssh_key_path = path
                    break
    
    # ========== SSH连接 ==========
    
    def ssh_exec(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行远程命令"""
        cmd = [
            "ssh",
            "-i", self.config.ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={timeout}",
            f"{self.config.ssh_user}@{self.config.server_ip}",
            command
        ]
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "timeout", "stdout": "", "stderr": ""}
        except Exception as e:
            return {"success": False, "error": str(e), "stdout": "", "stderr": ""}
    
    def ssh_upload(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """上传文件到云端"""
        cmd = [
            "scp", "-i", self.config.ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            local_path,
            f"{self.config.ssh_user}@{self.config.server_ip}:{remote_path}"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return {"success": result.returncode == 0, "stderr": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def ssh_download(self, remote_path: str, local_path: str) -> Dict[str, Any]:
        """从云端下载文件"""
        cmd = [
            "scp", "-i", self.config.ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            f"{self.config.ssh_user}@{self.config.server_ip}:{remote_path}",
            local_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return {"success": result.returncode == 0, "stderr": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_ssh_connection(self) -> bool:
        """检查SSH连接"""
        result = self.ssh_exec("echo ok", timeout=10)
        return result.get("success", False)
    
    # ========== 记忆网关 ==========
    
    def report_truth(self, truth_key: str, truth_value: Any, 
                     truth_type: str = "data", category: str = "general") -> Dict[str, Any]:
        """上报真值到记忆网关"""
        payload = {
            "truth_key": truth_key,
            "truth_value": json.dumps(truth_value, ensure_ascii=False) if not isinstance(truth_value, str) else truth_value,
            "source_node": self.config.node_id,
            "truth_type": truth_type,
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "did": self.config.did,
            "trace_mark": self.config.trace_mark
        }
        
        try:
            response = requests.post(
                self.config.gateway_url,
                json=payload,
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def query_truth(self, truth_key: str) -> Dict[str, Any]:
        """查询真值"""
        try:
            response = requests.get(
                f"{self.config.gateway_query_url}/{truth_key}",
                timeout=15
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def batch_report(self, truths: Dict[str, Any]) -> Dict[str, Any]:
        """批量上报真值"""
        results = {}
        for key, value in truths.items():
            results[key] = self.report_truth(key, value)
        return results
    
    # ========== 端口转发 ==========
    
    def start_local_tunnel(self, local_port: int, remote_host: str, remote_port: int) -> bool:
        """启动本地端口转发（访问云端内部服务）"""
        cmd = [
            "ssh", "-i", self.config.ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-N", "-f",
            "-L", f"{local_port}:{remote_host}:{remote_port}",
            f"{self.config.ssh_user}@{self.config.server_ip}"
        ]
        try:
            subprocess.Popen(cmd)
            self._tunnels.append({"type": "local", "local_port": local_port})
            return True
        except Exception as e:
            print(f"隧道启动失败: {e}")
            return False
    
    def start_remote_tunnel(self, remote_port: int, local_host: str, local_port: int) -> bool:
        """启动远程端口转发（暴露本地服务到云端）"""
        cmd = [
            "ssh", "-i", self.config.ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-N", "-f",
            "-R", f"{remote_port}:{local_host}:{local_port}",
            f"{self.config.ssh_user}@{self.config.server_ip}"
        ]
        try:
            subprocess.Popen(cmd)
            self._tunnels.append({"type": "remote", "remote_port": remote_port})
            return True
        except Exception as e:
            print(f"隧道启动失败: {e}")
            return False
    
    # ========== 综合状态 ==========
    
    def get_full_status(self) -> Dict[str, Any]:
        """获取完整连接状态"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "server_ip": self.config.server_ip,
                "ssh_user": self.config.ssh_user,
                "ssh_key": self.config.ssh_key_path,
                "node_id": self.config.node_id
            },
            "ssh": {
                "key_exists": os.path.exists(self.config.ssh_key_path) if self.config.ssh_key_path else False,
                "connected": self.check_ssh_connection()
            },
            "gateway": {
                "url": self.config.gateway_url,
                "test": self.report_truth("TEST.CONNECTOR.STATUS", {"status": "ok"}, "data", "test")
            },
            "active_tunnels": len(self._tunnels)
        }
        return status

# 单例
_connector = None

def get_cloud_connector(config: CloudConfig = None) -> CloudConnector:
    """获取云端连接器单例"""
    global _connector
    if _connector is None:
        _connector = CloudConnector(config)
    return _connector

if __name__ == "__main__":
    # 测试
    connector = get_cloud_connector()
    print("=" * 50)
    print("火斗云智AIOS - 云端连接器测试")
    print("=" * 50)
    
    status = connector.get_full_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
