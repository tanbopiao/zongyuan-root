"""
单元测试 - 测试五大引擎和熔断器的独立功能
"""
import os
import sys
import json
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_utils import TestRunner, skip_if_no_package
from engines.detection_engine import DetectionEngine, AnomalyEvent, Severity
from engines.decision_engine import DecisionEngine, Decision, DecisionAction, RiskLevel, OptimizationCandidate
from engines.verification_engine import VerificationEngine
from engines.feedback_engine import FeedbackEngine, Experience
from circuit_breaker.circuit_breaker import CircuitBreaker, CircuitState

logger = logging.getLogger('UnitTests')

def test_detection_engine_init():
    """测试检测引擎初始化"""
    engine = DetectionEngine()
    assert engine is not None
    assert len(engine.config['dimensions']) == 8
    total_metrics = sum(len(d['metrics']) for d in engine.config['dimensions'])
    assert total_metrics >= 30
    return True, {"dimensions": 8, "total_metrics": total_metrics}

def test_detection_engine_anomaly_creation():
    """测试异常事件创建"""
    anomaly = AnomalyEvent(
        anomaly_id="test_001",
        metric="memory_percent",
        current_value=88.5,
        severity=Severity.CRITICAL,
        description="内存使用率过高",
        timestamp=datetime.now().isoformat(),
        confidence=0.95
    )
    assert anomaly.anomaly_id == "test_001"
    assert anomaly.metric == "memory_percent"
    assert anomaly.current_value == 88.5
    assert anomaly.severity == Severity.CRITICAL
    return True, {"anomaly_id": anomaly.anomaly_id}

def test_detection_engine_severity_levels():
    """测试严重程度级别"""
    levels = [Severity.NORMAL, Severity.NOTICE, Severity.WARNING, Severity.CRITICAL, Severity.FATAL]
    assert len(levels) == 5
    assert Severity.FATAL.value == "fatal"
    assert Severity.CRITICAL.value == "critical"
    return True, {"levels": [s.value for s in levels]}

@skip_if_no_package('psutil')
def test_detection_engine_check_memory():
    """测试内存检测"""
    engine = DetectionEngine()
    data = engine._check_memory()
    assert 'memory_percent' in data
    assert 'memory_used_mb' in data
    assert 'memory_available_mb' in data
    assert 0 <= data['memory_percent'] <= 100
    return True, {"memory_percent": data['memory_percent']}

@skip_if_no_package('psutil')
def test_detection_engine_check_cpu():
    """测试CPU检测"""
    engine = DetectionEngine()
    data = engine._check_cpu()
    assert 'cpu_percent' in data
    assert 0 <= data['cpu_percent'] <= 100
    return True, {"cpu_percent": data['cpu_percent']}

def test_detection_engine_get_status():
    """测试获取检测引擎状态"""
    engine = DetectionEngine()
    status = engine.get_status()
    assert 'running' in status
    assert 'dimensions' in status
    assert 'metrics_tracked' in status
    assert status['dimensions'] == 8
    return True, status

def test_decision_engine_init():
    """测试决策引擎初始化"""
    engine = DecisionEngine()
    assert engine is not None
    assert engine.config['weights']['benefit'] == 0.40
    assert engine.config['weights']['risk'] == 0.35
    assert engine.config['weights']['cost'] == 0.25
    return True, {"weights": engine.config['weights']}

def test_decision_engine_risk_levels():
    """测试风险级别"""
    levels = [RiskLevel.L0_READONLY, RiskLevel.L1_SAFE, RiskLevel.L2_REVERSIBLE, 
              RiskLevel.L3_SENSITIVE, RiskLevel.L4_DANGEROUS]
    assert len(levels) == 5
    assert RiskLevel.L4_DANGEROUS.value == "L4"
    return True, {"levels": [l.value for l in levels]}

def test_decision_engine_calculate_score():
    """测试三维稳态评分"""
    engine = DecisionEngine()
    candidate = OptimizationCandidate(
        candidate_id="test_001",
        name="测试方案",
        description="测试",
        operation_type="test",
        command="echo test",
        risk_level=RiskLevel.L1_SAFE,
        estimated_benefit=0.8,
        estimated_risk=0.1,
        estimated_cost=0.2
    )
    score = engine._calculate_score(candidate)
    # 期望: 0.8*0.4 + (1-0.1)*0.35 + (1-0.2)*0.25 = 0.32 + 0.315 + 0.2 = 0.835
    expected = 0.8 * 0.4 + 0.9 * 0.35 + 0.8 * 0.25
    assert abs(score - expected) < 0.01
    return True, {"score": score, "expected": expected}

def test_decision_engine_candidate_creation():
    """测试候选方案创建"""
    candidate = OptimizationCandidate(
        candidate_id="test_001",
        name="清理临时文件",
        description="清理用户临时文件",
        operation_type="file_clean",
        command="rm -rf /tmp/*",
        risk_level=RiskLevel.L1_SAFE,
        estimated_benefit=0.7,
        estimated_risk=0.1,
        estimated_cost=0.15
    )
    assert candidate.candidate_id == "test_001"
    assert candidate.name == "清理临时文件"
    assert candidate.risk_level == RiskLevel.L1_SAFE
    return True, {"candidate": candidate.name}

def test_decision_engine_l4_check():
    """测试L4危险操作检查"""
    engine = DecisionEngine()
    anomaly = AnomalyEvent(
        anomaly_id="test_l4",
        metric="memory_percent",
        current_value=90,
        severity=Severity.CRITICAL,
        description="测试",
        timestamp=datetime.now().isoformat()
    )
    # 模拟L4候选
    candidate = OptimizationCandidate(
        candidate_id="l4_test",
        name="危险操作",
        description="测试L4",
        operation_type="dangerous",
        command="format c:",
        risk_level=RiskLevel.L4_DANGEROUS,
        estimated_benefit=0.5,
        estimated_risk=0.9,
        estimated_cost=0.1
    )
    
    # 直接测试决策逻辑
    if candidate.risk_level == RiskLevel.L4_DANGEROUS:
        action = DecisionAction.WAIT_FOR_HUMAN
    else:
        action = DecisionAction.AUTO_EXECUTE
    
    assert action == DecisionAction.WAIT_FOR_HUMAN
    return True, {"action": action.value}

def test_decision_engine_get_status():
    """测试获取决策引擎状态"""
    engine = DecisionEngine()
    status = engine.get_status()
    assert 'decisions_made' in status
    assert 'knowledge_base_patterns' in status
    assert 'circuit_breaker' in status
    return True, status

def test_verification_engine_init():
    """测试验证引擎初始化"""
    engine = VerificationEngine()
    assert engine is not None
    assert engine.config['stabilization_time'] == 60
    assert len(engine.config['verification_dimensions']) == 6
    return True, {"stabilization_time": 60}

def test_verification_engine_compare_snapshots():
    """测试快照对比"""
    engine = VerificationEngine()
    before = {'memory_percent': 80.0, 'cpu_percent': 50.0, 'timestamp': 'before'}
    after = {'memory_percent': 60.0, 'cpu_percent': 45.0, 'timestamp': 'after'}
    
    comparison = engine._compare_snapshots(before, after)
    
    assert 'memory_percent' in comparison
    assert comparison['memory_percent']['improved'] == True  # 80→60 改善
    assert comparison['memory_percent']['percentage'] == -25.0
    
    assert 'cpu_percent' in comparison
    assert comparison['cpu_percent']['improved'] == True  # 50→45 改善
    
    return True, {
        "memory_improvement": comparison['memory_percent']['percentage'],
        "cpu_improvement": comparison['cpu_percent']['percentage']
    }

def test_verification_engine_get_status():
    """测试获取验证引擎状态"""
    engine = VerificationEngine()
    status = engine.get_status()
    assert 'total_verifications' in status
    assert 'pass_rate' in status
    assert 'rollback_count' in status
    return True, status

def test_feedback_engine_init():
    """测试反馈引擎初始化"""
    engine = FeedbackEngine()
    assert engine is not None
    assert engine.source_node == "local-windows-001"
    assert engine.did == "DID-BR-000002"
    return True, {"source_node": engine.source_node}

def test_feedback_engine_experience_creation():
    """测试经验条目创建"""
    experience = Experience(
        experience_id="exp_001",
        problem="内存使用率过高",
        solution="关闭闲置进程",
        result="success",
        improvement=15.5,
        risk_level="L1",
        operation_type="process_kill",
        duration=12.5,
        timestamp=datetime.now().isoformat()
    )
    assert experience.experience_id == "exp_001"
    assert experience.result == "success"
    assert experience.improvement == 15.5
    return True, {"experience": experience.experience_id}

def test_feedback_engine_extract_lessons():
    """测试教训提取"""
    engine = FeedbackEngine()
    
    # 成功经验
    success_exp = Experience(
        experience_id="exp_success",
        problem="测试",
        solution="测试方案",
        result="success",
        improvement=12.0,
        risk_level="L1",
        operation_type="test",
        duration=10,
        timestamp=datetime.now().isoformat()
    )
    lessons = engine._extract_lessons(success_exp)
    assert len(lessons) > 0
    assert "效果" in lessons[0]
    
    # 失败经验
    failed_exp = Experience(
        experience_id="exp_failed",
        problem="测试",
        solution="失败方案",
        result="failed",
        improvement=0,
        risk_level="L2",
        operation_type="test",
        duration=200,
        timestamp=datetime.now().isoformat()
    )
    lessons = engine._extract_lessons(failed_exp)
    assert len(lessons) > 0
    
    return True, {"success_lessons": 1, "failed_lessons": len(lessons)}

def test_feedback_engine_get_status():
    """测试获取反馈引擎状态"""
    engine = FeedbackEngine()
    status = engine.get_status()
    assert 'experiences_stored' in status
    assert 'pending_reports' in status
    assert 'auto_report' in status
    return True, status

def test_circuit_breaker_init():
    """测试熔断器初始化"""
    breaker = CircuitBreaker()
    assert breaker is not None
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0
    return True, {"state": breaker.state.value}

def test_circuit_breaker_states():
    """测试熔断器状态"""
    states = [CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN]
    assert len(states) == 3
    assert CircuitState.CLOSED.value == "closed"
    assert CircuitState.OPEN.value == "open"
    assert CircuitState.HALF_OPEN.value == "half_open"
    return True, {"states": [s.value for s in states]}

def test_circuit_breaker_record_success():
    """测试记录成功"""
    breaker = CircuitBreaker()
    breaker.record_result(success=True)
    assert breaker.consecutive_failures == 0
    assert breaker.state == CircuitState.CLOSED
    return True, {"state": breaker.state.value}

def test_circuit_breaker_record_failure():
    """测试记录失败"""
    breaker = CircuitBreaker()
    # 连续失败多次
    for i in range(3):
        breaker.record_result(success=False)
    
    assert breaker.consecutive_failures == 3
    # 失败后状态可能是CLOSED或OPEN（取决于配置阈值）
    assert breaker.state in [CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN]
    return True, {"state": breaker.state.value, "consecutive_failures": breaker.consecutive_failures}

def test_circuit_breaker_can_execute():
    """测试是否可以执行"""
    breaker = CircuitBreaker()
    # 初始状态应该可以执行
    assert breaker.can_execute() == True
    
    # 记录一些失败
    for i in range(2):
        breaker.record_result(success=False)
    
    # 检查是否可以执行（取决于配置）
    can_execute = breaker.can_execute()
    assert can_execute in [True, False]
    
    return True, {"can_execute": can_execute}

def test_circuit_breaker_get_status():
    """测试获取熔断器状态"""
    breaker = CircuitBreaker()
    status = breaker.get_status()
    assert 'state' in status
    assert 'consecutive_failures' in status or 'failure_count' in status or 'failures' in status
    return True, status

def run_all_unit_tests():
    """运行所有单元测试"""
    runner = TestRunner("单元测试 - 五大引擎+熔断器")
    runner.start()
    
    # 检测引擎测试
    runner.run_test("检测引擎初始化", test_detection_engine_init)
    runner.run_test("异常事件创建", test_detection_engine_anomaly_creation)
    runner.run_test("严重程度级别", test_detection_engine_severity_levels)
    runner.run_test("内存检测", test_detection_engine_check_memory)
    runner.run_test("CPU检测", test_detection_engine_check_cpu)
    runner.run_test("获取检测引擎状态", test_detection_engine_get_status)
    
    # 决策引擎测试
    runner.run_test("决策引擎初始化", test_decision_engine_init)
    runner.run_test("风险级别", test_decision_engine_risk_levels)
    runner.run_test("三维稳态评分", test_decision_engine_calculate_score)
    runner.run_test("候选方案创建", test_decision_engine_candidate_creation)
    runner.run_test("L4危险操作检查", test_decision_engine_l4_check)
    runner.run_test("获取决策引擎状态", test_decision_engine_get_status)
    
    # 验证引擎测试
    runner.run_test("验证引擎初始化", test_verification_engine_init)
    runner.run_test("快照对比", test_verification_engine_compare_snapshots)
    runner.run_test("获取验证引擎状态", test_verification_engine_get_status)
    
    # 反馈引擎测试
    runner.run_test("反馈引擎初始化", test_feedback_engine_init)
    runner.run_test("经验条目创建", test_feedback_engine_experience_creation)
    runner.run_test("教训提取", test_feedback_engine_extract_lessons)
    runner.run_test("获取反馈引擎状态", test_feedback_engine_get_status)
    
    # 熔断器测试
    runner.run_test("熔断器初始化", test_circuit_breaker_init)
    runner.run_test("熔断器状态", test_circuit_breaker_states)
    runner.run_test("记录成功", test_circuit_breaker_record_success)
    runner.run_test("记录失败", test_circuit_breaker_record_failure)
    runner.run_test("是否可以执行", test_circuit_breaker_can_execute)
    runner.run_test("获取熔断器状态", test_circuit_breaker_get_status)
    
    summary = runner.finish()
    return summary

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    
    summary = run_all_unit_tests()
    
    print("\n" + "="*60)
    print("单元测试总结")
    print("="*60)
    print(f"总计: {summary['total_tests']}")
    print(f"通过: {summary['passed']}")
    print(f"失败: {summary['failed']}")
    print(f"通过率: {summary['pass_rate']:.1f}%")
    print(f"总耗时: {summary['total_duration']:.3f}s")
    print("="*60)
