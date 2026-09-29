"""
ANCE 执行器
统一执行接口：SSH / 云API / 本地命令
"""
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Dict
from .planner import ExecutionStep, ExecutionDAG


@dataclass
class ExecutionResult:
    """执行结果"""
    step_id: str
    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration: float
    error: Optional[str] = None


class SSHExecutor:
    """SSH远程执行器"""

    def __init__(self, host: str, username: str = "root",
                 key_file: Optional[str] = None, password: Optional[str] = None,
                 port: int = 22, timeout: int = 30):
        self.host = host
        self.username = username
        self.key_file = key_file
        self.password = password
        self.port = port
        self.timeout = timeout

    def run(self, command: str) -> ExecutionResult:
        """通过SSH执行命令"""
        start = time.time()
        try:
            cmd = self._build_ssh_cmd(command)
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=self.timeout
            )
            return ExecutionResult(
                step_id="ssh",
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
                duration=time.time() - start,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                step_id="ssh", success=False, stdout="", stderr="TIMEOUT",
                return_code=-1, duration=time.time() - start, error="命令超时"
            )
        except Exception as e:
            return ExecutionResult(
                step_id="ssh", success=False, stdout="", stderr=str(e),
                return_code=-1, duration=time.time() - start, error=str(e)
            )

    def _build_ssh_cmd(self, command: str) -> str:
        base = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
        if self.key_file:
            base += f" -i {self.key_file}"
        if self.port != 22:
            base += f" -p {self.port}"
        return f"{base} {self.username}@{self.host} '{command}'"

    def test_connection(self) -> bool:
        """测试SSH连接"""
        result = self.run("echo CONNECTED")
        return result.success and "CONNECTED" in result.stdout


class LocalExecutor:
    """本地命令执行器"""

    def run(self, command: str, cwd: Optional[str] = None) -> ExecutionResult:
        start = time.time()
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=300, cwd=cwd
            )
            return ExecutionResult(
                step_id="local",
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
                duration=time.time() - start,
            )
        except Exception as e:
            return ExecutionResult(
                step_id="local", success=False, stdout="", stderr=str(e),
                return_code=-1, duration=time.time() - start, error=str(e)
            )


class Executor:
    """统一执行器"""

    def __init__(self, ssh_executor: Optional[SSHExecutor] = None):
        self.ssh = ssh_executor
        self.local = LocalExecutor()
        self.results: List[ExecutionResult] = []

    def execute_step(self, step: ExecutionStep) -> ExecutionResult:
        """执行单个步骤"""
        step.status = "running"
        all_stdout = []
        all_stderr = []
        success = True

        for cmd in step.commands:
            if self.ssh:
                result = self.ssh.run(cmd)
            else:
                result = self.local.run(cmd)

            all_stdout.append(result.stdout)
            all_stderr.append(result.stderr)

            if not result.success:
                success = False
                step.status = "failed"
                break

        if success:
            step.status = "success"

        final = ExecutionResult(
            step_id=step.step_id,
            success=success,
            stdout="\n".join(all_stdout),
            stderr="\n".join(all_stderr),
            return_code=0 if success else 1,
            duration=sum(r.duration for r in self.results[-len(step.commands):]) if self.results else 0,
        )
        self.results.append(final)
        return final

    def execute_dag(self, dag: ExecutionDAG, on_step_complete=None) -> List[ExecutionResult]:
        """执行整个DAG"""
        while not dag.is_complete() and not dag.has_failed():
            ready = dag.get_ready_steps()
            if not ready:
                break  # 死锁

            for step in ready:
                result = self.execute_step(step)
                if on_step_complete:
                    on_step_complete(step, result)

        return self.results

    def get_summary(self) -> Dict:
        return {
            "total": len(self.results),
            "success": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success),
            "total_duration": sum(r.duration for r in self.results),
        }
