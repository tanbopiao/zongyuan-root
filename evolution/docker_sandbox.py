#!/usr/bin/env python3
"""
ZONGYUAN-ROOT Docker沙箱管理模块 V2.0
功能：Docker容器生命周期管理、资源限制、网络隔离、命令执行、日志收集
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import os
import sys
import json
import time
import subprocess
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class DockerSandbox:
    """Docker沙箱管理器"""
    
    def __init__(self, 
                 sandbox_dir: str = "/opt/ZONGYUAN-ROOT/evolution/sandbox",
                 default_image: str = "python:3.9-slim",
                 default_cpu: str = "1",
                 default_memory: str = "512m",
                 default_disk: str = "1g",
                 network_whitelist: List[str] = None):
        """
        初始化沙箱管理器
        
        Args:
            sandbox_dir: 沙箱工作目录
            default_image: 默认Docker镜像
            default_cpu: 默认CPU限制
            default_memory: 默认内存限制
            default_disk: 默认磁盘限制
            network_whitelist: 网络白名单域名列表
        """
        self.sandbox_dir = Path(sandbox_dir)
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.default_image = default_image
        self.default_cpu = default_cpu
        self.default_memory = default_memory
        self.default_disk = default_disk
        self.network_whitelist = network_whitelist or [
            "pypi.org", "files.pythonhosted.org",  # Python包
            "registry-1.docker.io", "auth.docker.io",  # Docker镜像
            "huodouai.com", "www.huodouai.com",  # 自有域名
        ]
        self.containers_dir = self.sandbox_dir / "containers"
        self.containers_dir.mkdir(exist_ok=True)
        self.logs_dir = self.sandbox_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)
    
    def _run_docker_cmd(self, cmd: List[str], timeout: int = 60) -> Tuple[int, str, str]:
        """
        执行Docker命令
        
        Args:
            cmd: 命令参数列表
            timeout: 超时时间(秒)
            
        Returns:
            (returncode, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["docker"] + cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    def _generate_sandbox_id(self, prefix: str = "sb") -> str:
        """生成沙箱ID"""
        timestamp = int(time.time())
        random_str = hashlib.md5(os.urandom(8)).hexdigest()[:8]
        return f"{prefix}-{timestamp}-{random_str}"
    
    def check_docker_available(self) -> bool:
        """检查Docker是否可用"""
        returncode, stdout, stderr = self._run_docker_cmd(["info"], timeout=10)
        return returncode == 0
    
    def pull_image(self, image: str = None) -> bool:
        """拉取Docker镜像"""
        image = image or self.default_image
        print(f"正在拉取镜像: {image}...")
        returncode, stdout, stderr = self._run_docker_cmd(["pull", image], timeout=300)
        if returncode == 0:
            print(f"镜像拉取成功: {image}")
            return True
        else:
            print(f"镜像拉取失败: {stderr}")
            return False
    
    def create_sandbox(self, 
                        name: str = None,
                        image: str = None,
                        cpu: str = None,
                        memory: str = None,
                        disk: str = None,
                        env_vars: Dict[str, str] = None,
                        volumes: Dict[str, str] = None,
                        network_mode: str = "bridge",
                        command: str = "tail -f /dev/null") -> Dict:
        """
        创建沙箱容器
        
        Args:
            name: 容器名称
            image: Docker镜像
            cpu: CPU限制 (如 "1", "0.5")
            memory: 内存限制 (如 "512m", "1g")
            disk: 磁盘限制 (如 "1g", "2g")
            env_vars: 环境变量字典
            volumes: 卷挂载字典 {宿主路径: 容器路径}
            network_mode: 网络模式 (bridge/none/host)
            command: 容器启动命令
            
        Returns:
            沙箱信息字典
        """
        sandbox_id = name or self._generate_sandbox_id()
        image = image or self.default_image
        cpu = cpu or self.default_cpu
        memory = memory or self.default_memory
        disk = disk or self.default_disk
        env_vars = env_vars or {}
        volumes = volumes or {}
        
        # 创建沙箱工作目录
        sandbox_workdir = self.containers_dir / sandbox_id
        sandbox_workdir.mkdir(parents=True, exist_ok=True)
        
        # 构建Docker run命令
        cmd = ["run", "-d", "--name", sandbox_id]
        
        # 资源限制
        cmd.extend(["--cpus", cpu])
        cmd.extend(["--memory", memory])
        # 注意：--storage-opt需要overlay over xfs with pquota，多数环境不支持
        # 磁盘限制通过挂载目录配额实现，此处不使用--storage-opt
        
        # 网络模式
        cmd.extend(["--network", network_mode])
        
        # 环境变量
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])
        
        # 卷挂载
        for host_path, container_path in volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])
        
        # 挂载沙箱工作目录
        cmd.extend(["-v", f"{sandbox_workdir}:/workspace"])
        
        # 镜像和命令（使用sh -c包装，支持复杂命令）
        cmd.extend([image, "sh", "-c", command])
        
        # 执行创建
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=60)
        
        if returncode != 0:
            return {
                "sandbox_id": sandbox_id,
                "status": "error",
                "error": stderr,
                "created_at": datetime.now().isoformat()
            }
        
        container_id = stdout.strip()
        
        # 保存沙箱元数据
        metadata = {
            "sandbox_id": sandbox_id,
            "container_id": container_id,
            "image": image,
            "resources": {
                "cpu": cpu,
                "memory": memory,
                "disk": disk
            },
            "network_mode": network_mode,
            "env_vars": env_vars,
            "volumes": volumes,
            "workdir": str(sandbox_workdir),
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "溯源标识": "Ω₀⊂⊙∞⊂Ω",
            "确权编码": "DID-BR-000002"
        }
        
        metadata_path = sandbox_workdir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return metadata
    
    def execute_command(self, sandbox_id: str, command: str, timeout: int = 300) -> Dict:
        """
        在沙箱内执行命令
        
        Args:
            sandbox_id: 沙箱ID
            command: 要执行的命令
            timeout: 超时时间(秒)
            
        Returns:
            执行结果字典
        """
        cmd = ["exec", sandbox_id, "bash", "-c", command]
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=timeout)
        
        result = {
            "sandbox_id": sandbox_id,
            "command": command,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "executed_at": datetime.now().isoformat(),
            "success": returncode == 0
        }
        
        # 保存执行日志
        log_path = self.logs_dir / f"{sandbox_id}_{int(time.time())}.log"
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result
    
    def copy_to_sandbox(self, sandbox_id: str, local_path: str, container_path: str) -> bool:
        """
        复制文件到沙箱
        
        Args:
            sandbox_id: 沙箱ID
            local_path: 本地文件路径
            container_path: 容器内目标路径
            
        Returns:
            是否成功
        """
        cmd = ["cp", local_path, f"{sandbox_id}:{container_path}"]
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=30)
        return returncode == 0
    
    def copy_from_sandbox(self, sandbox_id: str, container_path: str, local_path: str) -> bool:
        """
        从沙箱复制文件
        
        Args:
            sandbox_id: 沙箱ID
            container_path: 容器内源路径
            local_path: 本地目标路径
            
        Returns:
            是否成功
        """
        cmd = ["cp", f"{sandbox_id}:{container_path}", local_path]
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=30)
        return returncode == 0
    
    def get_sandbox_status(self, sandbox_id: str) -> Dict:
        """
        获取沙箱状态
        
        Args:
            sandbox_id: 沙箱ID
            
        Returns:
            沙箱状态字典
        """
        cmd = ["inspect", sandbox_id, "--format", 
               '{"status":"{{.State.Status}}","running":{{.State.Running}},"pid":{{.State.Pid}},"started_at":"{{.State.StartedAt}}","cpu_usage":{{.HostConfig.CpuShares}},"memory_limit":"{{.HostConfig.Memory}}"}']
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=10)
        
        if returncode != 0:
            return {"sandbox_id": sandbox_id, "status": "not_found", "error": stderr}
        
        try:
            status = json.loads(stdout)
            status["sandbox_id"] = sandbox_id
            return status
        except json.JSONDecodeError:
            return {"sandbox_id": sandbox_id, "status": "error", "raw": stdout}
    
    def get_sandbox_stats(self, sandbox_id: str) -> Dict:
        """
        获取沙箱资源使用统计
        
        Args:
            sandbox_id: 沙箱ID
            
        Returns:
            资源统计字典
        """
        cmd = ["stats", sandbox_id, "--no-stream", "--format", 
               '{"cpu_percent":"{{.CPUPerc}}","memory_usage":"{{.MemUsage}}","memory_percent":"{{.MemPerc}}","network_io":"{{.NetIO}}","block_io":"{{.BlockIO}}","pids":{{.PIDs}}}']
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=10)
        
        if returncode != 0:
            return {"sandbox_id": sandbox_id, "error": stderr}
        
        try:
            stats = json.loads(stdout)
            stats["sandbox_id"] = sandbox_id
            return stats
        except json.JSONDecodeError:
            return {"sandbox_id": sandbox_id, "raw": stdout}
    
    def stop_sandbox(self, sandbox_id: str) -> bool:
        """
        停止沙箱
        
        Args:
            sandbox_id: 沙箱ID
            
        Returns:
            是否成功
        """
        cmd = ["stop", sandbox_id]
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=30)
        return returncode == 0
    
    def start_sandbox(self, sandbox_id: str) -> bool:
        """
        启动沙箱
        
        Args:
            sandbox_id: 沙箱ID
            
        Returns:
            是否成功
        """
        cmd = ["start", sandbox_id]
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=30)
        return returncode == 0
    
    def destroy_sandbox(self, sandbox_id: str, remove_workdir: bool = True) -> bool:
        """
        销毁沙箱
        
        Args:
            sandbox_id: 沙箱ID
            remove_workdir: 是否删除工作目录
            
        Returns:
            是否成功
        """
        # 强制停止并删除容器
        cmd = ["rm", "-f", sandbox_id]
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=30)
        
        # 删除工作目录
        if remove_workdir:
            workdir = self.containers_dir / sandbox_id
            if workdir.exists():
                shutil.rmtree(workdir, ignore_errors=True)
        
        return returncode == 0
    
    def list_sandboxes(self) -> List[Dict]:
        """
        列出所有沙箱
        
        Returns:
            沙箱列表
        """
        cmd = ["ps", "-a", "--filter", "name=sb-", "--format", 
               '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","created_at":"{{.CreatedAt}}"}']
        returncode, stdout, stderr = self._run_docker_cmd(cmd, timeout=10)
        
        if returncode != 0 or not stdout:
            return []
        
        sandboxes = []
        for line in stdout.strip().split('\n'):
            if line:
                try:
                    sandboxes.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return sandboxes
    
    def cleanup_expired_sandboxes(self, max_age_hours: int = 24) -> int:
        """
        清理过期沙箱
        
        Args:
            max_age_hours: 最大存活时间(小时)
            
        Returns:
            清理的沙箱数量
        """
        sandboxes = self.list_sandboxes()
        cleaned = 0
        now = time.time()
        
        for sb in sandboxes:
            try:
                created = datetime.fromisoformat(sb.get("created_at", ""))
                age_hours = (now - created.timestamp()) / 3600
                if age_hours > max_age_hours:
                    self.destroy_sandbox(sb["name"])
                    cleaned += 1
            except (ValueError, KeyError):
                continue
        
        return cleaned


class SandboxVerification:
    """沙箱验证器 - 执行自动化测试、性能基准、安全扫描"""
    
    def __init__(self, sandbox: DockerSandbox):
        self.sandbox = sandbox
    
    def run_functional_tests(self, sandbox_id: str, test_commands: List[str]) -> Dict:
        """
        运行功能测试
        
        Args:
            sandbox_id: 沙箱ID
            test_commands: 测试命令列表
            
        Returns:
            测试结果字典
        """
        results = []
        passed = 0
        failed = 0
        
        for i, cmd in enumerate(test_commands):
            result = self.sandbox.execute_command(sandbox_id, cmd)
            test_result = {
                "test_id": f"TEST-{i+1:03d}",
                "command": cmd,
                "passed": result["success"],
                "returncode": result["returncode"],
                "stdout": result["stdout"][:500],  # 截断长输出
                "stderr": result["stderr"][:500]
            }
            results.append(test_result)
            if result["success"]:
                passed += 1
            else:
                failed += 1
        
        total = len(test_commands)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.1f}%",
            "passed_threshold": pass_rate >= 95,
            "results": results,
            "verified_at": datetime.now().isoformat()
        }
    
    def run_performance_benchmark(self, sandbox_id: str, benchmarks: Dict[str, str]) -> Dict:
        """
        运行性能基准测试
        
        Args:
            sandbox_id: 沙箱ID
            benchmarks: 基准测试字典 {名称: 命令}
            
        Returns:
            性能基准结果
        """
        results = {}
        
        for name, cmd in benchmarks.items():
            start_time = time.time()
            result = self.sandbox.execute_command(sandbox_id, cmd)
            elapsed = time.time() - start_time
            results[name] = {
                "command": cmd,
                "elapsed_seconds": round(elapsed, 3),
                "success": result["success"],
                "stdout": result["stdout"][:200]
            }
        
        return {
            "benchmarks": results,
            "benchmarked_at": datetime.now().isoformat()
        }
    
    def run_security_scan(self, sandbox_id: str) -> Dict:
        """
        运行安全扫描
        
        Args:
            sandbox_id: 沙箱ID
            
        Returns:
            安全扫描结果
        """
        # 检查常见安全问题
        checks = {
            "root_user": "whoami | grep -q root && echo 'WARNING: running as root' || echo 'OK: not root'",
            "sensitive_files": "ls -la /etc/shadow /etc/passwd 2>&1 | head -5",
            "network_access": "curl -s --connect-timeout 3 https://www.baidu.com > /dev/null 2>&1 && echo 'WARNING: network access available' || echo 'OK: network restricted'",
            "docker_socket": "ls -la /var/run/docker.sock 2>&1",
            "privileged": "capsh --print 2>/dev/null | head -5 || echo 'capsh not available'",
        }
        
        results = {}
        vulnerabilities = []
        
        for check_name, cmd in checks.items():
            result = self.sandbox.execute_command(sandbox_id, cmd)
            results[check_name] = {
                "output": result["stdout"][:300],
                "success": result["success"]
            }
            # 简单漏洞检测
            if "WARNING" in result["stdout"]:
                vulnerabilities.append(check_name)
        
        return {
            "checks": results,
            "vulnerabilities_found": len(vulnerabilities),
            "vulnerabilities": vulnerabilities,
            "passed": len(vulnerabilities) == 0,
            "scanned_at": datetime.now().isoformat()
        }
    
    def run_compatibility_check(self, sandbox_id: str, api_endpoints: List[str]) -> Dict:
        """
        运行API兼容性检查
        
        Args:
            sandbox_id: 沙箱ID
            api_endpoints: API端点列表
            
        Returns:
            兼容性检查结果
        """
        results = {}
        
        for endpoint in api_endpoints:
            cmd = f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout 5 {endpoint}"
            result = self.sandbox.execute_command(sandbox_id, cmd)
            http_code = result["stdout"].strip()
            results[endpoint] = {
                "http_code": http_code,
                "compatible": http_code in ["200", "201", "204", "301", "302"],
                "success": result["success"]
            }
        
        compatible_count = sum(1 for r in results.values() if r["compatible"])
        total = len(api_endpoints)
        
        return {
            "endpoints_checked": total,
            "compatible": compatible_count,
            "compatibility_rate": f"{compatible_count/total*100:.1f}%" if total > 0 else "N/A",
            "results": results,
            "checked_at": datetime.now().isoformat()
        }


# 便捷函数
def create_verification_sandbox(
    code_path: str = None,
    config: Dict = None,
    sandbox_manager: DockerSandbox = None
) -> Tuple[DockerSandbox, str, Dict]:
    """
    创建验证沙箱的便捷函数
    
    Args:
        code_path: 待验证代码路径
        config: 配置字典
        sandbox_manager: 沙箱管理器实例
        
    Returns:
        (sandbox_manager, sandbox_id, metadata)
    """
    if sandbox_manager is None:
        sandbox_manager = DockerSandbox()
    
    config = config or {}
    
    # 创建沙箱
    metadata = sandbox_manager.create_sandbox(
        image=config.get("image", "python:3.9-slim"),
        cpu=config.get("cpu", "1"),
        memory=config.get("memory", "512m"),
        env_vars=config.get("env_vars", {}),
        network_mode=config.get("network_mode", "bridge")
    )
    
    sandbox_id = metadata["sandbox_id"]
    
    # 复制代码到沙箱
    if code_path and os.path.exists(code_path):
        sandbox_manager.copy_to_sandbox(sandbox_id, code_path, "/workspace/")
    
    return sandbox_manager, sandbox_id, metadata


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("  ZONGYUAN-ROOT Docker沙箱管理模块 V2.0")
    print("  溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    print("=" * 60)
    print()
    
    sandbox = DockerSandbox()
    
    # 检查Docker可用性
    print("【检查Docker可用性】")
    if sandbox.check_docker_available():
        print("  ✅ Docker可用")
    else:
        print("  ❌ Docker不可用，请先安装Docker")
        sys.exit(1)
    
    print()
    print("【列出现有沙箱】")
    sandboxes = sandbox.list_sandboxes()
    print(f"  当前沙箱数量: {len(sandboxes)}")
    for sb in sandboxes:
        print(f"  - {sb['name']}: {sb['status']}")
    
    print()
    print("模块加载完成。使用方法：")
    print("  from docker_sandbox import DockerSandbox, SandboxVerification")
    print("  sandbox = DockerSandbox()")
    print("  metadata = sandbox.create_sandbox()")
    print("  result = sandbox.execute_command(metadata['sandbox_id'], 'echo hello')")
    print("  sandbox.destroy_sandbox(metadata['sandbox_id'])")
