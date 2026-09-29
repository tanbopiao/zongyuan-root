#!/usr/bin/env python3
"""
元极恒一CI/CD自动化测试流水线 V1.0
功能：代码检查 → 单元测试 → 集成测试 → 仿真验证 → 报告生成
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    test_type: str  # lint/unit/integration/simulation
    status: str  # pass/fail/skip
    duration: float = 0.0
    details: str = ""
    error: str = ""


@dataclass
class CICDReport:
    """CI/CD报告"""
    pipeline_id: str
    started_at: float
    finished_at: float = 0.0
    results: List[TestResult] = field(default_factory=list)
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    overall_status: str = "running"
    
    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_tests += 1
        if result.status == "pass":
            self.passed += 1
        elif result.status == "fail":
            self.failed += 1
        else:
            self.skipped += 1
    
    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "started_at": datetime.fromtimestamp(self.started_at).isoformat(),
            "finished_at": datetime.fromtimestamp(self.finished_at).isoformat() if self.finished_at else None,
            "duration": self.finished_at - self.started_at if self.finished_at else 0,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "pass_rate": f"{self.passed/self.total_tests*100:.1f}%" if self.total_tests > 0 else "0%",
            "overall_status": self.overall_status,
            "results": [
                {
                    "test_name": r.test_name,
                    "test_type": r.test_type,
                    "status": r.status,
                    "duration": round(r.duration, 3),
                    "details": r.details,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


class CICDPipeline:
    """CI/CD流水线"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.pipeline_id = f"cicd-{int(time.time())}-{os.getpid()}"
        self.report = CICDReport(
            pipeline_id=self.pipeline_id,
            started_at=time.time(),
        )
    
    def run_lint(self) -> TestResult:
        """代码语法检查"""
        start = time.time()
        try:
            # 检查所有Python文件语法
            py_files = []
            for root, dirs, files in os.walk(self.project_root):
                # 跳过__pycache__和.venv
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'node_modules')]
                for f in files:
                    if f.endswith('.py'):
                        py_files.append(os.path.join(root, f))
            
            errors = []
            for py_file in py_files:
                try:
                    result = subprocess.run(
                        [sys.executable, '-m', 'py_compile', py_file],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode != 0:
                        errors.append(f"{py_file}: {result.stderr.strip()}")
                except Exception as e:
                    errors.append(f"{py_file}: {str(e)}")
            
            duration = time.time() - start
            if errors:
                return TestResult(
                    test_name="Python语法检查",
                    test_type="lint",
                    status="fail",
                    duration=duration,
                    details=f"检查{len(py_files)}个Python文件",
                    error="; ".join(errors[:5]),
                )
            return TestResult(
                test_name="Python语法检查",
                test_type="lint",
                status="pass",
                duration=duration,
                details=f"检查{len(py_files)}个Python文件，全部通过",
            )
        except Exception as e:
            return TestResult(
                test_name="Python语法检查",
                test_type="lint",
                status="fail",
                duration=time.time() - start,
                error=str(e),
            )
    
    def run_unit_tests(self) -> List[TestResult]:
        """单元测试（直接运行各引擎的__main__测试）"""
        results = []
        
        test_scripts = [
            ("物理仿真引擎V2.0", "mechanism_implementation/engines/physics_simulation_engine_v2.py"),
            ("数字孪生引擎V1.0", "mechanism_implementation/engines/digital_twin_engine_v1.py"),
            ("同源协议服务端", "mechanism_implementation/servers/homologous_protocol_server.py"),
        ]
        
        for name, script_path in test_scripts:
            start = time.time()
            full_path = os.path.join(self.project_root, script_path)
            if not os.path.exists(full_path):
                results.append(TestResult(
                    test_name=name,
                    test_type="unit",
                    status="skip",
                    duration=0,
                    details=f"文件不存在: {script_path}",
                ))
                continue
            
            try:
                result = subprocess.run(
                    [sys.executable, full_path],
                    capture_output=True, text=True, timeout=30,
                    cwd=os.path.dirname(full_path),
                )
                duration = time.time() - start
                if result.returncode == 0:
                    # 检查输出中是否有"测试全部通过"或"✅"
                    if "✅" in result.stdout or "测试全部通过" in result.stdout or "测试通过" in result.stdout:
                        results.append(TestResult(
                            test_name=name,
                            test_type="unit",
                            status="pass",
                            duration=duration,
                            details="自测通过",
                        ))
                    else:
                        results.append(TestResult(
                            test_name=name,
                            test_type="unit",
                            status="pass",
                            duration=duration,
                            details="运行成功（退出码0）",
                        ))
                else:
                    results.append(TestResult(
                        test_name=name,
                        test_type="unit",
                        status="fail",
                        duration=duration,
                        error=result.stderr[:200] if result.stderr else "未知错误",
                    ))
            except subprocess.TimeoutExpired:
                results.append(TestResult(
                    test_name=name,
                    test_type="unit",
                    status="fail",
                    duration=time.time() - start,
                    error="测试超时（30秒）",
                ))
            except Exception as e:
                results.append(TestResult(
                    test_name=name,
                    test_type="unit",
                    status="fail",
                    duration=time.time() - start,
                    error=str(e),
                ))
        
        return results
    
    def run_integration_tests(self) -> List[TestResult]:
        """集成测试"""
        results = []
        
        # 测试1：记忆网关上报告器
        start = time.time()
        try:
            sys.path.insert(0, os.path.join(self.project_root, 'mechanism_implementation'))
            from integrators.memory_gateway_reporter import MemoryGatewayReporter
            
            reporter = MemoryGatewayReporter()
            status = reporter.get_status()
            
            if status and isinstance(status, dict):
                results.append(TestResult(
                    test_name="记忆网关连接测试",
                    test_type="integration",
                    status="pass",
                    duration=time.time() - start,
                    details=f"网关状态: {status.get('status', 'unknown')}, 真值: {status.get('data', {}).get('stats', {}).get('truths', 'N/A')}",
                ))
            else:
                results.append(TestResult(
                    test_name="记忆网关连接测试",
                    test_type="integration",
                    status="fail",
                    duration=time.time() - start,
                    error="网关返回异常",
                ))
        except Exception as e:
            results.append(TestResult(
                test_name="记忆网关连接测试",
                test_type="integration",
                status="fail",
                duration=time.time() - start,
                error=str(e),
            ))
        
        # 测试2：上报告器真实上报
        start = time.time()
        try:
            test_key = f"CICD.TEST.{int(time.time())}"
            result = reporter.report_truth(
                truth_key=test_key,
                truth_value="CI/CD流水线测试真值，自动生成",
                confidence=0.5,
                truth_type="data",
            )
            if result.success:
                results.append(TestResult(
                    test_name="真值上报测试",
                    test_type="integration",
                    status="pass",
                    duration=time.time() - start,
                    details=f"上报成功，真值库: {result.truth_count}",
                ))
            else:
                results.append(TestResult(
                    test_name="真值上报测试",
                    test_type="integration",
                    status="fail",
                    duration=time.time() - start,
                    error="上报失败",
                ))
        except Exception as e:
            results.append(TestResult(
                test_name="真值上报测试",
                test_type="integration",
                status="fail",
                duration=time.time() - start,
                error=str(e),
            ))
        
        return results
    
    def run_simulation_tests(self) -> List[TestResult]:
        """仿真测试"""
        results = []
        
        # 多节点协同决策仿真
        start = time.time()
        try:
            sys.path.insert(0, os.path.join(self.project_root, 'mechanism_implementation'))
            from servers.homologous_protocol_server import HomologousProtocolServer, NodeType
            
            server = HomologousProtocolServer()
            
            # 注册3个节点
            for i in range(3):
                server.node_manager.register(
                    node_id=f"test-node-{i}",
                    node_name=f"测试节点{i}",
                    node_type=NodeType.WORK.value,
                )
            
            # 创建决策
            decision = server.decision_arbiter.create(
                question="CI/CD测试决策",
                options=[{"name": "A"}, {"name": "B"}],
            )
            
            # 投票
            for i in range(3):
                server.decision_arbiter.vote(
                    decision_id=decision.decision_id,
                    node_id=f"test-node-{i}",
                    option_index=0,
                    benefit_score=80,
                    risk_score=70,
                    cost_score=90,
                )
            
            # 仲裁
            result = server.decision_arbiter.arbitrate(decision.decision_id)
            
            if result and 'best_option_index' in result:
                results.append(TestResult(
                    test_name="多节点协同决策仿真",
                    test_type="simulation",
                    status="pass",
                    duration=time.time() - start,
                    details=f"3节点投票，仲裁结果: 选项{result['best_option_index']}",
                ))
            else:
                results.append(TestResult(
                    test_name="多节点协同决策仿真",
                    test_type="simulation",
                    status="fail",
                    duration=time.time() - start,
                    error="仲裁失败",
                ))
        except Exception as e:
            results.append(TestResult(
                test_name="多节点协同决策仿真",
                test_type="simulation",
                status="fail",
                duration=time.time() - start,
                error=str(e),
            ))
        
        return results
    
    def run(self) -> CICDReport:
        """运行完整流水线"""
        print(f"CI/CD流水线启动: {self.pipeline_id}")
        print("=" * 50)
        
        # 阶段1：代码检查
        print("\n【阶段1】代码检查")
        lint_result = self.run_lint()
        self.report.add_result(lint_result)
        print(f"  {lint_result.status.upper()}: {lint_result.test_name} ({lint_result.duration:.3f}s)")
        
        # 阶段2：单元测试
        print("\n【阶段2】单元测试")
        unit_results = self.run_unit_tests()
        for r in unit_results:
            self.report.add_result(r)
            print(f"  {r.status.upper()}: {r.test_name} ({r.duration:.3f}s)")
        
        # 阶段3：集成测试
        print("\n【阶段3】集成测试")
        integration_results = self.run_integration_tests()
        for r in integration_results:
            self.report.add_result(r)
            print(f"  {r.status.upper()}: {r.test_name} ({r.duration:.3f}s)")
        
        # 阶段4：仿真测试
        print("\n【阶段4】仿真测试")
        simulation_results = self.run_simulation_tests()
        for r in simulation_results:
            self.report.add_result(r)
            print(f"  {r.status.upper()}: {r.test_name} ({r.duration:.3f}s)")
        
        # 完成
        self.report.finished_at = time.time()
        self.report.overall_status = "pass" if self.report.failed == 0 else "fail"
        
        print("\n" + "=" * 50)
        print(f"流水线完成: {self.report.overall_status.upper()}")
        print(f"  总测试: {self.report.total_tests}")
        print(f"  通过: {self.report.passed}")
        print(f"  失败: {self.report.failed}")
        print(f"  跳过: {self.report.skipped}")
        print(f"  通过率: {self.report.passed/self.report.total_tests*100:.1f}%")
        print(f"  总耗时: {self.report.finished_at - self.report.started_at:.3f}s")
        
        return self.report
    
    def save_report(self, output_path: str):
        """保存报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.report.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {output_path}")


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pipeline = CICDPipeline(project_root)
    report = pipeline.run()
    pipeline.save_report(os.path.join(project_root, "ci_cd", "latest_report.json"))
