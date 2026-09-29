#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 沙箱工具集
功能：沙箱内自动化测试、性能基准、安全扫描工具
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import os
import sys
import json
import time
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class SandboxTools:
    """沙箱工具集"""
    
    def __init__(self, workspace: str = "/workspace"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(exist_ok=True)
        self.results_dir = self.workspace / ".sandbox_results"
        self.results_dir.mkdir(exist_ok=True)
    
    def run_command(self, command: str, timeout: int = 60) -> Dict:
        """执行命令并返回结果"""
        start_time = time.time()
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout
            )
            elapsed = time.time() - start_time
            return {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "elapsed_seconds": round(elapsed, 3),
                "success": result.returncode == 0,
                "executed_at": datetime.now().isoformat()
            }
        except subprocess.TimeoutExpired:
            return {
                "command": command,
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out",
                "elapsed_seconds": timeout,
                "success": False,
                "executed_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "command": command,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "elapsed_seconds": 0,
                "success": False,
                "executed_at": datetime.now().isoformat()
            }
    
    def run_pytest(self, test_dir: str = None, coverage: bool = True) -> Dict:
        """运行pytest测试"""
        test_dir = test_dir or str(self.workspace)
        cmd = f"cd {test_dir} && python3 -m pytest "
        if coverage:
            cmd += "--cov=. --cov-report=json "
        cmd += "--tb=short -v"
        
        result = self.run_command(cmd, timeout=300)
        
        # 解析覆盖率
        coverage_data = {}
        if coverage:
            coverage_file = Path(test_dir) / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
        
        return {
            "test_result": result,
            "coverage": coverage_data,
            "test_dir": test_dir
        }
    
    def run_linting(self, target: str = None) -> Dict:
        """运行代码检查（flake8 + black + mypy）"""
        target = target or str(self.workspace)
        results = {}
        
        # flake8
        results['flake8'] = self.run_command(
            f"flake8 {target} --max-line-length=120 --statistics", timeout=60
        )
        
        # black
        results['black'] = self.run_command(
            f"black {target} --check --diff", timeout=60
        )
        
        # mypy
        results['mypy'] = self.run_command(
            f"mypy {target} --ignore-missing-imports", timeout=120
        )
        
        return results
    
    def run_performance_benchmark(self, benchmarks: Dict[str, str] = None) -> Dict:
        """运行性能基准测试"""
        benchmarks = benchmarks or {
            "cpu_python_loop": "python3 -c \"import time; s=time.time(); [i**2 for i in range(1000000)]; print(f'{time.time()-s:.3f}')\"",
            "memory_allocation": "python3 -c \"import time; s=time.time(); x=[i for i in range(1000000)]; print(f'{time.time()-s:.3f}')\"",
            "io_write": "python3 -c \"import time; s=time.time(); open('/tmp/test_io.txt','w').write('x'*10000000); print(f'{time.time()-s:.3f}')\"",
            "io_read": "python3 -c \"import time; s=time.time(); open('/tmp/test_io.txt','r').read(); print(f'{time.time()-s:.3f}')\"",
        }
        
        results = {}
        for name, cmd in benchmarks.items():
            result = self.run_command(cmd, timeout=60)
            results[name] = {
                "elapsed_seconds": result['elapsed_seconds'],
                "output": result['stdout'].strip(),
                "success": result['success']
            }
        
        return results
    
    def run_security_scan(self) -> Dict:
        """运行安全扫描"""
        results = {}
        
        # 检查是否以root运行
        results['root_check'] = {
            "running_as_root": os.geteuid() == 0,
            "current_user": os.environ.get('USER', 'unknown'),
            "warning": "Running as root is not recommended" if os.geteuid() == 0 else "OK"
        }
        
        # 检查敏感文件
        sensitive_files = ['/etc/shadow', '/etc/passwd', '/root/.ssh/id_rsa']
        results['sensitive_files'] = {}
        for f in sensitive_files:
            results['sensitive_files'][f] = {
                "exists": os.path.exists(f),
                "readable": os.access(f, os.R_OK)
            }
        
        # 检查网络访问
        results['network_access'] = self.run_command(
            "curl -s --connect-timeout 3 https://www.baidu.com > /dev/null 2>&1 && echo 'network_accessible' || echo 'network_restricted'",
            timeout=10
        )
        
        # 检查Docker socket
        results['docker_socket'] = {
            "exists": os.path.exists('/var/run/docker.sock'),
            "warning": "Docker socket accessible - potential privilege escalation risk" if os.path.exists('/var/run/docker.sock') else "OK"
        }
        
        return results
    
    def calculate_file_hash(self, filepath: str) -> str:
        """计算文件SHA256哈希"""
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def generate_verification_report(self, 
                                      test_results: Dict = None,
                                      lint_results: Dict = None,
                                      perf_results: Dict = None,
                                      security_results: Dict = None) -> Dict:
        """生成综合验证报告"""
        report = {
            "report_id": f"VER-{int(time.time())}",
            "generated_at": datetime.now().isoformat(),
            "workspace": str(self.workspace),
            "test_results": test_results or {},
            "lint_results": lint_results or {},
            "performance_results": perf_results or {},
            "security_results": security_results or {},
            "overall_status": "pending",
            "溯源标识": "Ω₀⊂⊙∞⊂Ω",
            "确权编码": "DID-BR-000002"
        }
        
        # 计算综合状态
        all_passed = True
        if test_results and not test_results.get('test_result', {}).get('success', True):
            all_passed = False
        if security_results:
            if security_results.get('root_check', {}).get('running_as_root'):
                all_passed = False
        
        report['overall_status'] = 'passed' if all_passed else 'failed'
        
        # 保存报告
        report_file = self.results_dir / f"report_{report['report_id']}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report


if __name__ == "__main__":
    print("=" * 60)
    print("  ZONGYUAN-ROOT 沙箱工具集")
    print("  溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    print("=" * 60)
    print()
    
    tools = SandboxTools()
    
    # 运行性能基准
    print("【性能基准测试】")
    perf = tools.run_performance_benchmark()
    for name, result in perf.items():
        print(f"  {name}: {result['elapsed_seconds']}s - {result['output']}")
    print()
    
    # 运行安全扫描
    print("【安全扫描】")
    security = tools.run_security_scan()
    print(f"  Root用户: {security['root_check']['running_as_root']}")
    print(f"  当前用户: {security['root_check']['current_user']}")
    print(f"  网络访问: {security['network_access']['stdout']}")
    print(f"  Docker Socket: {security['docker_socket']['exists']}")
    print()
    
    print("沙箱工具集加载完成。")
