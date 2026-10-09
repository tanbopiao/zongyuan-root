"""
HRM-SDK 离线持久化队列（手动栈迭代，禁止递归）
内核不可达时暂存待提交请求，网络恢复后自动重提交
"""
import json
import os
import time

from .config import LOCAL_QUEUE_STORE_PATH, LOCAL_QUEUE_MAX


class LocalQueue:
    """基于手动栈的持久化队列（堆区数组模拟栈，不使用递归）"""

    def __init__(self, store_path: str = LOCAL_QUEUE_STORE_PATH, max_size: int = LOCAL_QUEUE_MAX):
        self.store_path = store_path
        self.max_size = max_size
        self._stack = self._load()

    def _load(self) -> list:
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    def _persist(self):
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(self._stack, f, ensure_ascii=False, indent=2)

    def push(self, item: dict) -> bool:
        """压入待提交请求；超限返回 False 并丢弃（业务应感知）"""
        if len(self._stack) >= self.max_size:
            return False
        item["_queued_at"] = time.time()
        self._stack.append(item)
        self._persist()
        return True

    def pop(self) -> dict | None:
        """弹出栈顶（LIFO 手动栈迭代）"""
        if not self._stack:
            return None
        item = self._stack.pop()
        self._persist()
        return item

    def size(self) -> int:
        return len(self._stack)

    def clear(self):
        self._stack = []
        if os.path.exists(self.store_path):
            os.remove(self.store_path)
