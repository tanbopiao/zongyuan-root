"""
任务优先级队列
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

支持P0-P3四级优先级，P0最高，P3最低
P0: 紧急任务，立即执行
P1: 高优先级，尽快执行
P2: 普通任务，按顺序执行
P3: 低优先级，空闲时执行
"""
import time
import heapq
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any


class Priority(Enum):
    P0 = 0  # 紧急
    P1 = 1  # 高
    P2 = 2  # 中
    P3 = 3  # 低


@dataclass(order=True)
class PrioritizedTask:
    priority: int
    timestamp: float = field(compare=True)
    task_id: str = field(compare=False)
    action: str = field(compare=False)
    params: dict = field(compare=False, default_factory=dict)
    timeout_sec: int = field(compare=False, default=300)
    callback: Optional[Callable] = field(compare=False, default=None)


class TaskPriorityQueue:
    """
    任务优先级队列

    特性：
    - 四级优先级（P0-P3）
    - 同优先级按时间戳排序（先入先出）
    - 任务超时自动标记
    - 支持任务取消
    """

    def __init__(self):
        self.queue = []
        self.running = {}
        self.completed = []
        self.cancelled = set()

    def submit(self, action: str, params: dict = None,
               priority: Priority = Priority.P2,
               timeout_sec: int = 300,
               callback: Callable = None) -> str:
        """提交任务"""
        task_id = f"task-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        task = PrioritizedTask(
            priority=priority.value,
            timestamp=time.time(),
            task_id=task_id,
            action=action,
            params=params or {},
            timeout_sec=timeout_sec,
            callback=callback
        )
        heapq.heappush(self.queue, task)
        return task_id

    def get_next(self) -> Optional[PrioritizedTask]:
        """获取下一个要执行的任务"""
        while self.queue:
            task = heapq.heappop(self.queue)
            if task.task_id in self.cancelled:
                self.cancelled.remove(task.task_id)
                continue
            self.running[task.task_id] = task
            return task
        return None

    def complete(self, task_id: str, result: Any = None):
        """标记任务完成"""
        if task_id in self.running:
            task = self.running.pop(task_id)
            self.completed.append({
                "task_id": task_id,
                "action": task.action,
                "completed_at": time.time(),
                "result": result
            })

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running:
            return False  # 正在运行的任务不能取消
        self.cancelled.add(task_id)
        return True

    def check_timeout(self) -> list:
        """检查超时任务"""
        now = time.time()
        timeout_tasks = []
        for task_id, task in list(self.running.items()):
            if now - task.timestamp > task.timeout_sec:
                timeout_tasks.append(task_id)
                del self.running[task_id]
        return timeout_tasks

    def status(self) -> dict:
        """队列状态"""
        return {
            "pending": len(self.queue),
            "running": len(self.running),
            "completed": len(self.completed),
            "cancelled": len(self.cancelled)
        }


# 使用示例
if __name__ == "__main__":
    queue = TaskPriorityQueue()

    # 提交不同优先级的任务
    queue.submit("deploy_web", {"file": "index.html"}, Priority.P1)
    queue.submit("send_alert", {"msg": "CPU过高"}, Priority.P0)
    queue.submit("cleanup_logs", {}, Priority.P3)
    queue.submit("update_cache", {}, Priority.P2)

    print(f"队列状态: {queue.status()}")

    # 按优先级执行
    while True:
        task = queue.get_next()
        if not task:
            break
        print(f"执行任务: {task.task_id} | priority={Priority(task.priority).name} | action={task.action}")
        queue.complete(task.task_id, {"status": "success"})

    print(f"最终状态: {queue.status()}")
