"""
测试工具类 - 提供测试辅助功能
"""
import os
import sys
import time
import json
import logging
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from contextlib import contextmanager

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger('TestUtils')

@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    passed: bool
    duration: float = 0
    error: str = ""
    details: Dict = field(default_factory=dict)
    timestamp: str = ""

class TestRunner:
    """测试运行器"""
    
    def __init__(self, name: str = "TestSuite"):
        self.name = name
        self.results = []
        self.start_time = None
        self.temp_dirs = []
    
    def start(self):
        """开始测试"""
        self.start_time = time.time()
        logger.info(f"{'='*60}")
        logger.info(f"测试套件开始: {self.name}")
        logger.info(f"{'='*60}")
    
    def run_test(self, test_name: str, test_func: Callable, **kwargs) -> TestResult:
        """运行单个测试"""
        start = time.time()
        try:
            result = test_func(**kwargs)
            duration = time.time() - start
            
            if isinstance(result, tuple) and len(result) == 2:
                passed, details = result
            else:
                passed = bool(result)
                details = {}
            
            test_result = TestResult(
                test_name=test_name,
                passed=passed,
                duration=duration,
                details=details if isinstance(details, dict) else {},
                timestamp=datetime.now().isoformat()
            )
            
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {status} - {test_name} ({duration:.3f}s)")
            
        except Exception as e:
            duration = time.time() - start
            test_result = TestResult(
                test_name=test_name,
                passed=False,
                duration=duration,
                error=str(e),
                timestamp=datetime.now().isoformat()
            )
            logger.error(f"  ❌ FAIL - {test_name} ({duration:.3f}s): {e}")
        
        self.results.append(test_result)
        return test_result
    
    def finish(self) -> Dict:
        """结束测试并返回总结"""
        total_duration = time.time() - self.start_time if self.start_time else 0
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        summary = {
            "test_suite": self.name,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "total_duration": total_duration,
            "results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "duration": r.duration,
                    "error": r.error,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        logger.info(f"{'='*60}")
        logger.info(f"测试套件完成: {self.name}")
        logger.info(f"  总计: {total}, 通过: {passed}, 失败: {failed}")
        logger.info(f"  通过率: {summary['pass_rate']:.1f}%")
        logger.info(f"  总耗时: {total_duration:.3f}s")
        logger.info(f"{'='*60}")
        
        # 清理临时目录
        for temp_dir in self.temp_dirs:
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
        
        return summary
    
    def create_temp_dir(self) -> str:
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp(prefix="aios_test_")
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def assert_equal(self, actual, expected, message: str = "") -> bool:
        """断言相等"""
        if actual != expected:
            raise AssertionError(f"{message}: 期望 {expected}, 实际 {actual}")
        return True
    
    def assert_true(self, condition, message: str = "") -> bool:
        """断言为真"""
        if not condition:
            raise AssertionError(f"{message}: 条件为假")
        return True
    
    def assert_in(self, item, container, message: str = "") -> bool:
        """断言包含"""
        if item not in container:
            raise AssertionError(f"{message}: {item} 不在 {container} 中")
        return True

@contextmanager
def mock_time(mock_time_value: float):
    """模拟时间"""
    original_time = time.time
    time.time = lambda: mock_time_value
    try:
        yield
    finally:
        time.time = original_time

@contextmanager
def capture_logs(logger_name: str = None):
    """捕获日志"""
    import io
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    
    target_logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    original_level = target_logger.level
    target_logger.addHandler(handler)
    target_logger.setLevel(logging.DEBUG)
    
    try:
        yield log_stream
    finally:
        target_logger.removeHandler(handler)
        target_logger.setLevel(original_level)

def load_test_config() -> Dict:
    """加载测试配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'test_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def is_windows() -> bool:
    """检查是否Windows环境"""
    return sys.platform.startswith('win')

def is_linux() -> bool:
    """检查是否Linux环境"""
    return sys.platform.startswith('linux')

def skip_if_not_windows(test_func):
    """Windows专用测试装饰器"""
    def wrapper(*args, **kwargs):
        if not is_windows():
            logger.info(f"  ⏭️  SKIP - {test_func.__name__} (非Windows环境)")
            return True, {"skipped": True, "reason": "非Windows环境"}
        return test_func(*args, **kwargs)
    wrapper.__name__ = test_func.__name__
    return wrapper

def skip_if_no_package(package_name: str):
    """缺少包时跳过的装饰器"""
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            try:
                __import__(package_name)
            except ImportError:
                logger.info(f"  ⏭️  SKIP - {test_func.__name__} (缺少 {package_name})")
                return True, {"skipped": True, "reason": f"缺少 {package_name}"}
            return test_func(*args, **kwargs)
        wrapper.__name__ = test_func.__name__
        return wrapper
    return decorator

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    runner = TestRunner("TestUtils Self Test")
    runner.start()
    
    # 测试基本功能
    def test_basic():
        return True, {"test": "basic"}
    
    runner.run_test("basic_test", test_basic)
    
    summary = runner.finish()
    print(f"\n测试结果: {json.dumps(summary, indent=2, ensure_ascii=False)}")
