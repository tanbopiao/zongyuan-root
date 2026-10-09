"""
AIOS自治服务API客户端
用于用户态程序调用高权限服务API
"""
import requests
import json
from typing import Dict, Any, Optional, List

class AISOServiceClient:
    """AIOS自治服务客户端"""
    
    def __init__(self, base_url="http://127.0.0.1:9150", timeout=30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/health",
                timeout=self.timeout
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/status",
                timeout=self.timeout
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_command(self, command: str, timeout: int = 300,
                       need_backup: bool = False,
                       operation_type: str = "generic",
                       targets: List[str] = None) -> Dict[str, Any]:
        """执行命令（通过高权限服务）"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/execute",
                json={
                    "command": command,
                    "timeout": timeout,
                    "need_backup": need_backup,
                    "operation_type": operation_type,
                    "targets": targets or []
                },
                timeout=timeout + 10
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def backup(self, operation_type: str, targets: List[str]) -> Dict[str, Any]:
        """执行备份"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/backup",
                json={
                    "operation_type": operation_type,
                    "targets": targets
                },
                timeout=60
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def rollback(self, backup_id: str) -> Dict[str, Any]:
        """执行回滚"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/rollback",
                json={"backup_id": backup_id},
                timeout=60
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def backup_registry(self, key_path: str) -> Dict[str, Any]:
        """备份注册表"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/registry/backup",
                json={"key_path": key_path},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def restore_registry(self, reg_file: str) -> Dict[str, Any]:
        """恢复注册表"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/registry/restore",
                json={"reg_file": reg_file},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def control_service(self, service_name: str, action: str = "status") -> Dict[str, Any]:
        """控制服务"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/service/control",
                json={
                    "service_name": service_name,
                    "action": action
                },
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

# 单例
_client = None

def get_service_client() -> AISOServiceClient:
    """获取服务客户端单例"""
    global _client
    if _client is None:
        _client = AISOServiceClient()
    return _client

if __name__ == "__main__":
    # 测试
    client = get_service_client()
    print("=" * 50)
    print("AIOS自治服务客户端测试")
    print("=" * 50)
    
    health = client.health_check()
    print(f"\n健康检查: {json.dumps(health, indent=2, ensure_ascii=False)}")
    
    status = client.get_status()
    print(f"\n服务状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
