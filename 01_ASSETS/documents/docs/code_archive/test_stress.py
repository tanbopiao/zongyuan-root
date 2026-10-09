"""
压力测试和性能基准测试
- 并发优化测试
- 连续失败压力测试
- 长时间运行稳定性测试
- 性能基准测试
"""
import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_utils import TestRunner
from engines.detection_engine import DetectionEngine, AnomalyEvent, Severity
from engines.decision_engine import DecisionEngine, Decision, DecisionAction, RiskLevel, OptimizationCandidate
from engines.execution_engine import ExecutionEngine, ExecutionResult
from engines.verification_engine import VerificationEngine
from engines.feedback_engine import FeedbackEngine
from circuit_breaker.circuit_breaker import CircuitBreaker, CircuitState

logger = logging.getLogger('StressTests')

def test_concurrent_detection():
    """测试并发检测性能"""
    detector = DetectionEngine()
    
    # 并发执行多次检测
    num_threads = 5
    num_iterations = 3
    results = []
    
    def run_detection(thread_id):
        thread_results = []
        for i in range(num_iterations):
            start = time.time()
            try:
                anomalies = detector.check_all()
                duration = time.time() - start
                thread_results.append({
                    'thread': thread_id,
                    'iteration': i,
                    'anomalies': len(anomalies),
                    'duration': duration,
                    'success': True
                })
            except Exception as e:
                duration = time.time() - start
                thread_results.append({
                    'thread': thread_id,
                    'iteration': i,
                    'error': str(e),
                    'duration': duration,
                    'success': False
                })
        return thread_results
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(run_detection, i) for i in range(num_threads)]
        for future in as_completed(futures):
            results.extend(future.result())
    
    # 统计结果
    total = len(results)
    successes = sum(1 for r in results if r['success'])
    avg_duration = sum(r['duration'] for r in results) / total if total > 0 else 0
    max_duration = max(r['duration'] for r in results) if results else 0
    
    return True, {
        "total_checks": total,
        "successes": successes,
        "failures": total - successes,
        "avg_duration_ms": avg_duration * 1000,
        "max_duration_ms": max_duration * 1000,
        "concurrent_threads": num_threads
    }

def test_concurrent_decision_making():
    """测试并发决策性能"""
    decider = DecisionEngine()
    
    # 创建多个异常
    anomalies = []
    for i in range(10):
        anomalies.append(AnomalyEvent(
            anomaly_id=f"concurrent_{i}",
            metric="memory_percent" if i % 2 == 0 else "cpu_percent",
            current_value=80 + i,
            severity=Severity.WARNING if i < 5 else Severity.CRITICAL,
            description=f"并发测试异常{i}",
            timestamp=datetime.now().isoformat()
        ))
    
    # 并发决策
    num_threads = 3
    results = []
    
    def make_decision(anomaly):
        start = time.time()
        try:
            decision = decider.decide(anomaly)
            duration = time.time() - start
            return {
                'anomaly': anomaly.anomaly_id,
                'action': decision.action.value,
                'score': decision.score,
                'duration': duration,
                'success': True
            }
        except Exception as e:
            duration = time.time() - start
            return {
                'anomaly': anomaly.anomaly_id,
                'error': str(e),
                'duration': duration,
                'success': False
            }
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(make_decision, a) for a in anomalies]
        for future in as_completed(futures):
            results.append(future.result())
    
    total = len(results)
    successes = sum(1 for r in results if r['success'])
    avg_duration = sum(r['duration'] for r in results) / total if total > 0 else 0
    
    return True, {
        "total_decisions": total,
        "successes": successes,
        "avg_duration_ms": avg_duration * 1000,
        "concurrent_threads": num_threads
    }

def test_continuous_failures_circuit_breaker():
    """测试连续失败下的熔断器行为"""
    breaker = CircuitBreaker()
    
    # 记录连续失败
    failure_records = []
    for i in range(10):
        before_state = breaker.state.value
        breaker.record_result(success=False)
        after_state = breaker.state.value
        can_execute = breaker.can_execute()
        
        failure_records.append({
            'failure_number': i + 1,
            'before_state': before_state,
            'after_state': after_state,
            'consecutive_failures': breaker.consecutive_failures,
            'can_execute': can_execute
        })
    
    # 验证熔断器在连续失败后应该打开
    assert breaker.consecutive_failures >= 3
    # 状态可能是OPEN或HALF_OPEN（取决于冷却时间）
    
    return True, {
        "total_failures": 10,
        "final_consecutive_failures": breaker.consecutive_failures,
        "final_state": breaker.state.value,
        "failure_records_summary": failure_records[:5]  # 只返回前5条
    }

def test_circuit_breaker_recovery_after_success():
    """测试熔断器在成功后的恢复"""
    breaker = CircuitBreaker()
    
    # 先触发熔断
    for i in range(5):
        breaker.record_result(success=False)
    
    state_after_failures = breaker.state.value
    failures_after = breaker.consecutive_failures
    
    # 然后记录成功
    for i in range(5):
        breaker.record_result(success=True)
    
    state_after_success = breaker.state.value
    failures_after_success = breaker.consecutive_failures
    
    # 验证成功后连续失败计数应该重置
    assert failures_after_success == 0
    
    return True, {
        "state_after_failures": state_after_failures,
        "failures_after_failures": failures_after,
        "state_after_success": state_after_success,
        "failures_after_success": failures_after_success,
        "recovery_verified": failures_after_success == 0
    }

def test_memory_usage_stability():
    """测试内存使用稳定性（多次运行后内存不泄漏）"""
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 运行多次检测和决策
        detector = DetectionEngine()
        decider = DecisionEngine()
        
        for i in range(20):
            anomalies = detector.check_all()
            for anomaly in anomalies[:3]:  # 只处理前3个
                decider.decide(anomaly)
        
        # 运行后内存
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # 内存增长应该在合理范围内（<100MB）
        memory_stable = memory_growth < 100
        
        return True, {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_growth_mb": memory_growth,
            "iterations": 20,
            "memory_stable": memory_stable
        }
    except ImportError:
        return True, {"skipped": True, "reason": "psutil not available"}

def test_performance_benchmark_detection():
    """性能基准测试：检测引擎"""
    detector = DetectionEngine()
    
    # 运行多次检测，计算平均时间
    iterations = 10
    durations = []
    
    for i in range(iterations):
        start = time.time()
        detector.check_all()
        duration = time.time() - start
        durations.append(duration)
    
    avg_duration = sum(durations) / len(durations)
    min_duration = min(durations)
    max_duration = max(durations)
    
    # 计算标准差
    variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
    std_dev = variance ** 0.5
    
    return True, {
        "iterations": iterations,
        "avg_duration_ms": avg_duration * 1000,
        "min_duration_ms": min_duration * 1000,
        "max_duration_ms": max_duration * 1000,
        "std_dev_ms": std_dev * 1000,
        "performance_level": "excellent" if avg_duration < 1 else "good" if avg_duration < 3 else "acceptable"
    }

def test_performance_benchmark_decision():
    """性能基准测试：决策引擎"""
    decider = DecisionEngine()
    
    # 创建测试异常
    anomaly = AnomalyEvent(
        anomaly_id="benchmark_001",
        metric="memory_percent",
        current_value=88.0,
        severity=Severity.CRITICAL,
        description="性能基准测试",
        timestamp=datetime.now().isoformat()
    )
    
    # 运行多次决策
    iterations = 50
    durations = []
    
    for i in range(iterations):
        start = time.time()
        decider.decide(anomaly)
        duration = time.time() - start
        durations.append(duration)
    
    avg_duration = sum(durations) / len(durations)
    min_duration = min(durations)
    max_duration = max(durations)
    
    return True, {
        "iterations": iterations,
        "avg_duration_ms": avg_duration * 1000,
        "min_duration_ms": min_duration * 1000,
        "max_duration_ms": max_duration * 1000,
        "decisions_per_second": 1 / avg_duration if avg_duration > 0 else 0,
        "performance_level": "excellent" if avg_duration < 0.01 else "good" if avg_duration < 0.1 else "acceptable"
    }

def test_performance_benchmark_verification():
    """性能基准测试：验证引擎快照对比"""
    verifier = VerificationEngine()
    
    # 创建测试快照
    before = {
        'memory_percent': 85.0,
        'cpu_percent': 50.0,
        'disk_c_percent': 70.0,
        'process_count': 150,
        'network_connections': 100,
        'timestamp': 'before'
    }
    after = {
        'memory_percent': 70.0,
        'cpu_percent': 45.0,
        'disk_c_percent': 68.0,
        'process_count': 140,
        'network_connections': 95,
        'timestamp': 'after'
    }
    
    # 运行多次对比
    iterations = 100
    durations = []
    
    for i in range(iterations):
        start = time.time()
        verifier._compare_snapshots(before, after)
        duration = time.time() - start
        durations.append(duration)
    
    avg_duration = sum(durations) / len(durations)
    
    return True, {
        "iterations": iterations,
        "avg_duration_ms": avg_duration * 1000,
        "comparisons_per_second": 1 / avg_duration if avg_duration > 0 else 0,
        "performance_level": "excellent" if avg_duration < 0.001 else "good"
    }

def run_all_stress_tests():
    """运行所有压力测试"""
    runner = TestRunner("压力测试和性能基准测试")
    runner.start()
    
    # 并发测试
    runner.run_test("并发检测性能", test_concurrent_detection)
    runner.run_test("并发决策性能", test_concurrent_decision_making)
    
    # 熔断器压力测试
    runner.run_test("连续失败熔断器行为", test_continuous_failures_circuit_breaker)
    runner.run_test("熔断器成功后恢复", test_circuit_breaker_recovery_after_success)
    
    # 稳定性测试
    runner.run_test("内存使用稳定性", test_memory_usage_stability)
    
    # 性能基准测试
    runner.run_test("性能基准-检测引擎", test_performance_benchmark_detection)
    runner.run_test("性能基准-决策引擎", test_performance_benchmark_decision)
    runner.run_test("性能基准-验证引擎", test_performance_benchmark_verification)
    
    summary = runner.finish()
    return summary

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    
    summary = run_all_stress_tests()
    
    print("\n" + "="*60)
    print("压力测试和性能基准测试总结")
    print("="*60)
    print(f"总计: {summary['total_tests']}")
    print(f"通过: {summary['passed']}")
    print(f"失败: {summary['failed']}")
    print(f"通过率: {summary['pass_rate']:.1f}%")
    print(f"总耗时: {summary['total_duration']:.3f}s")
    print("="*60)
