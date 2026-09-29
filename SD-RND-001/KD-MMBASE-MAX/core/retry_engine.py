"""MM-RETRY 重试熔断引擎 · 5次指数退避 + 熔断→Lv3自愈联动"""
import time
from typing import Callable, Any, Dict

class RetryEngine:
    def __init__(self, config: Dict):
        self.max_retries = config.get("retry_max", 5)
        self.backoff_base = config.get("retry_backoff", 2)
        self.failure_count = 0
        self.circuit_open = False
        self.last_failure = None

    def execute(self, func: Callable, task_id: str = "") -> Dict[str, Any]:
        if self.circuit_open:
            return {"error": "circuit_breaker_open", "task_id": task_id}
        for attempt in range(self.max_retries):
            try:
                result = func()
                self.failure_count = 0
                return {"data": result, "attempts": attempt + 1, "task_id": task_id}
            except Exception as e:
                self.failure_count += 1
                self.last_failure = str(e)
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_base ** attempt)
                if self.failure_count >= self.max_retries * 2:
                    self.circuit_open = True
        return {"error": "max_retries_exceeded", "last_error": self.last_failure, "task_id": task_id}

    def reset(self) -> None:
        self.circuit_open = False
        self.failure_count = 0
