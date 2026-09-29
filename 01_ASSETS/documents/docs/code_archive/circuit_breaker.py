"""
熔断保护器 - 多重熔断机制
防止自治优化失控
"""
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class CircuitState(Enum):
    """熔断状态"""
    CLOSED = "closed"           # 正常运行
    OPEN = "open"               # 熔断打开，暂停执行
    HALF_OPEN = "half_open"     # 半开，试探性执行

@dataclass
class CircuitBreakerConfig:
    """熔断配置"""
    # 连续失败熔断
    max_consecutive_failures: int = 3
    
    # 失败率熔断
    failure_rate_threshold: float = 0.3
    failure_rate_window: int = 10  # 最近N次
    
    # 系统稳定性熔断
    system_stability_threshold: float = 0.6
    
    # 用户活跃熔断（用户正在使用时不做激进优化）
    user_active_check: bool = True
    
    # 低电量熔断（笔记本）
    low_battery_threshold: int = 20
    
    # 高温熔断
    high_temperature_threshold: int = 90
    
    # 冷却时间
    cooldown_period: int = 3600  # 1小时
    
    # 半开试探次数
    half_open_max_attempts: int = 3

class CircuitBreaker:
    """多重熔断保护器"""
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.recent_results = deque(maxlen=self.config.failure_rate_window)
        self.last_failure_time = None
        self.last_open_time = None
        self.half_open_attempts = 0
        self.open_reason = ""
        self.logger = logging.getLogger(__name__)
    
    def can_execute(self, operation_risk: str = "L2") -> bool:
        """检查是否可以执行操作"""
        
        # 如果熔断打开，检查是否过了冷却期
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_open_time > self.config.cooldown_period:
                self.logger.info("熔断冷却期已过，进入半开状态")
                self.state = CircuitState.HALF_OPEN
                self.half_open_attempts = 0
            else:
                remaining = self.config.cooldown_period - (time.time() - self.last_open_time)
                self.logger.warning(f"熔断中，剩余冷却时间: {remaining:.0f}秒，原因: {self.open_reason}")
                return False
        
        # 半开状态，只允许有限次数试探
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_attempts >= self.config.half_open_max_attempts:
                self.logger.warning("半开状态试探次数已达上限")
                return False
            # 半开状态只允许低风险操作
            if operation_risk in ["L3", "L4"]:
                self.logger.warning("半开状态不允许高风险操作")
                return False
        
        # 多重熔断检查
        checks = [
            self._check_consecutive_failures(),
            self._check_failure_rate(),
            self._check_system_stability(),
            self._check_user_active(operation_risk),
            self._check_battery(),
            self._check_temperature()
        ]
        
        for check_name, check_passed, reason in checks:
            if not check_passed:
                self._open_circuit(reason)
                return False
        
        return True
    
    def _check_consecutive_failures(self):
        """检查连续失败"""
        if self.consecutive_failures >= self.config.max_consecutive_failures:
            return ("连续失败", False, f"连续失败{self.consecutive_failures}次，超过阈值{self.config.max_consecutive_failures}")
        return ("连续失败", True, "")
    
    def _check_failure_rate(self):
        """检查失败率"""
        if len(self.recent_results) >= self.config.failure_rate_window:
            failures = sum(1 for r in self.recent_results if not r)
            failure_rate = failures / len(self.recent_results)
            if failure_rate > self.config.failure_rate_threshold:
                return ("失败率", False, f"最近{len(self.recent_results)}次失败率{failure_rate:.1%}，超过阈值{self.config.failure_rate_threshold:.0%}")
        return ("失败率", True, "")
    
    def _check_system_stability(self):
        """检查系统稳定性"""
        try:
            import psutil
            # 简单的系统稳定性评分
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            stability_score = 1.0
            if cpu_percent > 90:
                stability_score -= 0.3
            if memory_percent > 95:
                stability_score -= 0.4
            if disk_percent > 95:
                stability_score -= 0.2
            
            if stability_score < self.config.system_stability_threshold:
                return ("系统稳定性", False, f"系统稳定性评分{stability_score:.2f}，低于阈值{self.config.system_stability_threshold}")
        except:
            pass
        return ("系统稳定性", True, "")
    
    def _check_user_active(self, operation_risk):
        """检查用户是否活跃（L3操作在用户活跃时不执行）"""
        if not self.config.user_active_check:
            return ("用户活跃", True, "")
        
        if operation_risk != "L3":
            return ("用户活跃", True, "")
        
        try:
            import psutil
            # 检查用户输入活动（简化版：检查CPU是否有用户进程高占用）
            # 实际实现可以检查鼠标键盘输入
            pass
        except:
            pass
        return ("用户活跃", True, "")
    
    def _check_battery(self):
        """检查电池状态"""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged:
                if battery.percent < self.config.low_battery_threshold:
                    return ("低电量", False, f"电池电量{battery.percent}%，低于阈值{self.config.low_battery_threshold}%且未充电")
        except:
            pass
        return ("低电量", True, "")
    
    def _check_temperature(self):
        """检查温度"""
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > self.config.high_temperature_threshold:
                            return ("高温", False, f"{name}温度{entry.current}°C，超过阈值{self.config.high_temperature_threshold}°C")
        except:
            pass
        return ("高温", True, "")
    
    def _open_circuit(self, reason: str):
        """打开熔断"""
        self.state = CircuitState.OPEN
        self.last_open_time = time.time()
        self.open_reason = reason
        self.logger.warning(f"熔断打开: {reason}")
    
    def record_result(self, success: bool):
        """记录执行结果"""
        self.recent_results.append(success)
        
        if success:
            self.consecutive_failures = 0
            # 半开状态成功，恢复正常
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_attempts += 1
                if self.half_open_attempts >= self.config.half_open_max_attempts:
                    self.logger.info("半开状态试探全部成功，恢复正常运行")
                    self.state = CircuitState.CLOSED
                    self.half_open_attempts = 0
        else:
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            # 半开状态失败，重新打开熔断
            if self.state == CircuitState.HALF_OPEN:
                self._open_circuit("半开状态试探失败")
    
    def reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.recent_results.clear()
        self.last_failure_time = None
        self.last_open_time = None
        self.half_open_attempts = 0
        self.open_reason = ""
        self.logger.info("熔断器已重置")
    
    def get_status(self) -> Dict[str, Any]:
        """获取熔断状态"""
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "recent_results": list(self.recent_results),
            "failure_rate": (sum(1 for r in self.recent_results if not r) / len(self.recent_results)) if self.recent_results else 0,
            "last_failure_time": self.last_failure_time,
            "last_open_time": self.last_open_time,
            "open_reason": self.open_reason,
            "half_open_attempts": self.half_open_attempts,
            "config": {
                "max_consecutive_failures": self.config.max_consecutive_failures,
                "failure_rate_threshold": self.config.failure_rate_threshold,
                "cooldown_period": self.config.cooldown_period
            }
        }

# 单例
_circuit_breaker = None

def get_circuit_breaker() -> CircuitBreaker:
    """获取熔断器单例"""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    cb = get_circuit_breaker()
    print("=" * 50)
    print("熔断保护器测试")
    print("=" * 50)
    
    print(f"\n初始状态: {cb.get_status()}")
    
    # 模拟连续失败
    print("\n模拟连续失败...")
    for i in range(4):
        cb.record_result(False)
        print(f"  第{i+1}次失败后: state={cb.state.value}, consecutive_failures={cb.consecutive_failures}")
    
    print(f"\n熔断后状态: {cb.get_status()}")
    
    # 检查是否可以执行
    print(f"\n是否可以执行: {cb.can_execute()}")
    
    # 重置
    cb.reset()
    print(f"\n重置后状态: {cb.get_status()}")
