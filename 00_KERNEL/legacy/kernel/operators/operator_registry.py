#!/usr/bin/env python3
"""
算子注册表 - 算子的统一注册/发现/查询/管理中心
"""
import threading
import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .base_operator import BaseOperator, OperatorMetadata


@dataclass
class OperatorRegistration:
    """算子注册信息"""
    operator: BaseOperator
    registered_at: float = field(default_factory=time.time)
    category: str = ""
    tags: List[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.operator.metadata.to_dict(),
            "registered_at": self.registered_at,
            "category": self.category,
            "tags": self.tags,
            "enabled": self.enabled,
            "stats": self.operator.get_stats(),
        }


class OperatorRegistry:
    """
    算子注册表 - 线程安全的算子注册中心
    支持算子注册/注销/查询/列表/分类/标签/自动发现
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._operators: Dict[str, OperatorRegistration] = {}
        self._categories: Dict[str, List[str]] = {}
        self._tags_index: Dict[str, List[str]] = {}
        self._registry_lock = threading.RLock()
        self._initialized = True

    def register(self, operator: BaseOperator, category: str = "", tags: Optional[List[str]] = None) -> bool:
        """注册算子"""
        with self._registry_lock:
            op_id = operator.metadata.operator_id
            op_name = operator.metadata.operator_name

            if op_name in self._operators:
                return False  # 已存在

            registration = OperatorRegistration(
                operator=operator,
                category=category or operator.metadata.category,
                tags=tags or operator.metadata.tags,
            )
            self._operators[op_name] = registration

            # 更新分类索引
            cat = category or operator.metadata.category
            if cat not in self._categories:
                self._categories[cat] = []
            self._categories[cat].append(op_name)

            # 更新标签索引
            for tag in (tags or operator.metadata.tags):
                if tag not in self._tags_index:
                    self._tags_index[tag] = []
                self._tags_index[tag].append(op_name)

            return True

    def unregister(self, operator_name: str) -> bool:
        """注销算子"""
        with self._registry_lock:
            if operator_name not in self._operators:
                return False

            registration = self._operators.pop(operator_name)

            # 从分类索引移除
            cat = registration.category
            if cat in self._categories and operator_name in self._categories[cat]:
                self._categories[cat].remove(operator_name)
                if not self._categories[cat]:
                    del self._categories[cat]

            # 从标签索引移除
            for tag in registration.tags:
                if tag in self._tags_index and operator_name in self._tags_index[tag]:
                    self._tags_index[tag].remove(operator_name)
                    if not self._tags_index[tag]:
                        del self._tags_index[tag]

            return True

    def get(self, operator_name: str) -> Optional[BaseOperator]:
        """获取算子实例"""
        with self._registry_lock:
            registration = self._operators.get(operator_name)
            if registration and registration.enabled:
                return registration.operator
            return None

    def list_all(self) -> List[str]:
        """列出所有算子名称"""
        with self._registry_lock:
            return list(self._operators.keys())

    def list_by_category(self, category: str) -> List[str]:
        """按分类列出算子"""
        with self._registry_lock:
            return self._categories.get(category, [])

    def list_by_tag(self, tag: str) -> List[str]:
        """按标签列出算子"""
        with self._registry_lock:
            return self._tags_index.get(tag, [])

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        with self._registry_lock:
            return list(self._categories.keys())

    def get_tags(self) -> List[str]:
        """获取所有标签"""
        with self._registry_lock:
            return list(self._tags_index.keys())

    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有算子统计"""
        with self._registry_lock:
            return {
                "total_operators": len(self._operators),
                "categories": {cat: len(ops) for cat, ops in self._categories.items()},
                "tags": {tag: len(ops) for tag, ops in self._tags_index.items()},
                "operators": {
                    name: reg.to_dict()
                    for name, reg in self._operators.items()
                },
            }

    def register_core_operators(self):
        """注册所有核心算子"""
        from .core_operators import CORE_OPERATORS

        count = 0
        for name, operator_class in CORE_OPERATORS.items():
            try:
                operator = operator_class()
                if self.register(operator):
                    count += 1
            except Exception:
                pass
        return count
