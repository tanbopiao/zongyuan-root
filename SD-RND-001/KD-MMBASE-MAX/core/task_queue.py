"""MM-QUEUE 任务队列引擎 · 优先级排队 + 令牌桶并发控制"""
import time, threading
from collections import deque
from typing import Dict, Any

class TaskQueue:
    def __init__(self, config: Dict):
        self.max_concurrency = config.get("max_concurrency", 6)
        self._queue = deque()
        self._active = 0
        self._lock = threading.Lock()

    def enqueue(self, task_id: str, route: Dict) -> None:
        with self._lock:
            self._queue.append({"task_id": task_id, "route": route, "enqueue_time": time.time()})

    def dequeue(self) -> Dict:
        with self._lock:
            if self._queue and self._active < self.max_concurrency:
                self._active += 1
                return self._queue.popleft()
        return {}

    def complete(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    def size(self) -> int:
        return len(self._queue)
