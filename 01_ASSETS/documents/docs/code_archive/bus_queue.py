"""
真值总线内存队列模块
基于KERNEL-ENTRY-0199规范：总线队列按target_node分发
"""
import json
import uuid
from collections import deque, defaultdict
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass, field

from .frame import BaseFrame, parse_frame
from .frame_validator import FrameValidator, ValidationResult
from .error_codes import TruthBusError


@dataclass
class BusStats:
    """总线统计信息"""
    total_sent: int = 0
    total_received: int = 0
    total_failed: int = 0
    queue_size: int = 0
    active_nodes: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "total_sent": self.total_sent,
            "total_received": self.total_received,
            "total_failed": self.total_failed,
            "queue_size": self.queue_size,
            "active_nodes": self.active_nodes
        }


class TruthBusQueue:
    """
    真值总线内存队列
    - 按target_node分发帧
    - 发送前执行5重校验
    - 支持帧的发送、接收、查询
    """
    
    def __init__(self, max_queue_size: int = 1000,
                 validator: Optional[FrameValidator] = None,
                 on_frame_sent: Optional[Callable[[BaseFrame], None]] = None,
                 on_frame_received: Optional[Callable[[BaseFrame], None]] = None,
                 on_validation_failed: Optional[Callable[[BaseFrame, ValidationResult], None]] = None):
        """
        初始化总线队列
        max_queue_size: 每个节点队列最大长度
        validator: 帧校验器（可选，不配置则不校验）
        on_frame_sent: 帧发送成功回调
        on_frame_received: 帧接收成功回调
        on_validation_failed: 校验失败回调
        """
        self.max_queue_size = max_queue_size
        self.validator = validator
        self.on_frame_sent = on_frame_sent
        self.on_frame_received = on_frame_received
        self.on_validation_failed = on_validation_failed
        
        # 按target_node索引的帧队列
        self._queues: dict[str, deque] = defaultdict(deque)
        
        # 统计信息
        self.stats = BusStats()
        
        # 已注册的节点
        self._registered_nodes: set[str] = set()
    
    def register_node(self, node_id: str) -> bool:
        """注册节点到总线"""
        if node_id in self._registered_nodes:
            return False
        self._registered_nodes.add(node_id)
        self.stats.active_nodes = list(self._registered_nodes)
        return True
    
    def unregister_node(self, node_id: str) -> bool:
        """注销节点"""
        if node_id not in self._registered_nodes:
            return False
        self._registered_nodes.remove(node_id)
        # 清空该节点的队列
        if node_id in self._queues:
            del self._queues[node_id]
        self.stats.active_nodes = list(self._registered_nodes)
        return True
    
    def send(self, frame: BaseFrame) -> tuple[bool, Optional[str]]:
        """
        发送帧到总线
        返回：(是否成功, 错误信息)
        """
        # 校验帧
        if self.validator:
            result = self.validator.validate(frame)
            if not result.passed:
                self.stats.total_failed += 1
                error_msg = "; ".join(result.errors)
                if self.on_validation_failed:
                    self.on_validation_failed(frame, result)
                return False, f"帧校验失败: {error_msg}"
        
        # 获取目标节点
        target_node = frame.header.target_node
        if not target_node:
            self.stats.total_failed += 1
            return False, "目标节点ID为空（target_node）"
        
        # 检查队列是否已满
        if len(self._queues[target_node]) >= self.max_queue_size:
            self.stats.total_failed += 1
            return False, f"目标节点队列已满（最大{self.max_queue_size}）"
        
        # 入队
        self._queues[target_node].append(frame)
        self.stats.total_sent += 1
        self.stats.queue_size = sum(len(q) for q in self._queues.values())
        
        if self.on_frame_sent:
            self.on_frame_sent(frame)
        
        return True, None
    
    def receive(self, target_node: str) -> Optional[BaseFrame]:
        """
        接收目标节点的帧（FIFO）
        返回：帧对象或None（队列为空）
        """
        if target_node not in self._queues or not self._queues[target_node]:
            return None
        
        frame = self._queues[target_node].popleft()
        self.stats.total_received += 1
        self.stats.queue_size = sum(len(q) for q in self._queues.values())
        
        if self.on_frame_received:
            self.on_frame_received(frame)
        
        return frame
    
    def peek(self, target_node: str) -> Optional[BaseFrame]:
        """查看目标节点队列的下一帧，但不出队"""
        if target_node not in self._queues or not self._queues[target_node]:
            return None
        return self._queues[target_node][0]
    
    def get_queue_size(self, target_node: str) -> int:
        """获取目标节点队列长度"""
        return len(self._queues.get(target_node, []))
    
    def get_all_queue_sizes(self) -> dict[str, int]:
        """获取所有节点队列长度"""
        return {node: len(q) for node, q in self._queues.items() if q}
    
    def clear_queue(self, target_node: str) -> int:
        """清空目标节点队列，返回清除的帧数"""
        if target_node not in self._queues:
            return 0
        count = len(self._queues[target_node])
        self._queues[target_node].clear()
        self.stats.queue_size = sum(len(q) for q in self._queues.values())
        return count
    
    def get_stats(self) -> BusStats:
        """获取总线统计信息"""
        self.stats.queue_size = sum(len(q) for q in self._queues.values())
        return self.stats
    
    def get_registered_nodes(self) -> list[str]:
        """获取已注册节点列表"""
        return list(self._registered_nodes)
    
    def to_dict(self) -> dict:
        """导出总线状态（不包含帧内容，只包含统计和队列大小）"""
        return {
            "stats": self.stats.to_dict(),
            "registered_nodes": list(self._registered_nodes),
            "queue_sizes": {node: len(q) for node, q in self._queues.items()},
            "max_queue_size": self.max_queue_size
        }
