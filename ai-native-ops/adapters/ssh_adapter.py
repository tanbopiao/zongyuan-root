"""
ANCE SSH适配器
基于paramiko的SSH远程执行，支持密钥/密码/批量
"""
import time
from typing import Optional, List, Dict


class SSHAdapter:
    """SSH远程执行适配器"""

    def __init__(self, host: str, username: str = "root",
                 key_file: Optional[str] = None, password: Optional[str] = None,
                 port: int = 22, timeout: int = 30):
        self.host = host
        self.username = username
        self.key_file = key_file
        self.password = password
        self.port = port
        self.timeout = timeout
        self._client = None

    def connect(self) -> bool:
        """建立SSH连接"""
        try:
            import paramiko
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": self.timeout,
            }
            if self.key_file:
                connect_kwargs["key_filename"] = self.key_file
            elif self.password:
                connect_kwargs["password"] = self.password

            self._client.connect(**connect_kwargs)
            return True
        except ImportError:
            # paramiko未安装，回退到subprocess ssh
            return self._test_subprocess()
        except Exception as e:
            print(f"SSH连接失败: {e}")
            return False

    def _test_subprocess(self) -> bool:
        """用subprocess测试连接"""
        import subprocess
        cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
        if self.key_file:
            cmd += f"-i {self.key_file} "
        cmd += f"{self.username}@{self.host} 'echo CONNECTED'"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            return "CONNECTED" in result.stdout
        except Exception:
            return False

    def execute(self, command: str, timeout: Optional[int] = None) -> Dict:
        """执行远程命令"""
        timeout = timeout or self.timeout

        # 优先用paramiko
        if self._client:
            try:
                stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
                out = stdout.read().decode("utf-8", errors="replace")
                err = stderr.read().decode("utf-8", errors="replace")
                code = stdout.channel.recv_exit_status()
                return {
                    "success": code == 0,
                    "stdout": out,
                    "stderr": err,
                    "return_code": code,
                }
            except Exception as e:
                return {"success": False, "stdout": "", "stderr": str(e), "return_code": -1}

        # 回退到subprocess
        import subprocess
        cmd = self._build_cmd(command)
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "TIMEOUT", "return_code": -1}

    def execute_batch(self, commands: List[str], delay: float = 0.5) -> List[Dict]:
        """批量执行命令"""
        results = []
        for cmd in commands:
            result = self.execute(cmd)
            results.append(result)
            if not result["success"]:
                break  # 遇到错误停止
            time.sleep(delay)
        return results

    def upload(self, local_path: str, remote_path: str) -> bool:
        """上传文件"""
        import subprocess
        cmd = f"scp -o StrictHostKeyChecking=no "
        if self.key_file:
            cmd += f"-i {self.key_file} "
        cmd += f"{local_path} {self.username}@{self.host}:{remote_path}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False

    def download(self, remote_path: str, local_path: str) -> bool:
        """下载文件"""
        import subprocess
        cmd = f"scp -o StrictHostKeyChecking=no "
        if self.key_file:
            cmd += f"-i {self.key_file} "
        cmd += f"{self.username}@{self.host}:{remote_path} {local_path}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False

    def _build_cmd(self, command: str) -> str:
        cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
        if self.key_file:
            cmd += f"-i {self.key_file} "
        if self.port != 22:
            cmd += f"-p {self.port} "
        cmd += f"{self.username}@{self.host} '{command}'"
        return cmd

    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
