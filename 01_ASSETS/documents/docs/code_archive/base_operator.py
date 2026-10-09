#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 算子基类
所有算子必须继承此类，实现统一的接口规范
"""

import abc
import time
import hashlib
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class OperatorStatus(Enum):
    """算子状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class OperatorPriority(Enum):
    """算子优先级枚举"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class OperatorResult:
    """算子执行结果"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    operator_id: str = ""
    operator_name: str = ""
    timestamp: str = ""
    hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "timestamp": self.timestamp,
            "hash": self.hash
        }

    def calculate_hash(self) -> str:
        """计算结果哈希"""
        content = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()


class BaseOperator(abc.ABC):
    """算子基类 - 所有算子必须继承此类"""

    # 算子元数据（子类必须覆盖）
    OPERATOR_ID: str = "base-operator"
    OPERATOR_NAME: str = "基础算子"
    OPERATOR_VERSION: str = "1.0.0"
    OPERATOR_GROUP: str = "base"
    OPERATOR_DESCRIPTION: str = "算子基类"
    PRIORITY: OperatorPriority = OperatorPriority.MEDIUM
    TIMEOUT: int = 300  # 秒

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化算子"""
        self.config = config or {}
        self.status = OperatorStatus.IDLE
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.result: Optional[OperatorResult] = None
        self.error_count: int = 0
        self.success_count: int = 0

    @abc.abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> OperatorResult:
        """
        执行算子逻辑（子类必须实现）

        Args:
            input_data: 输入数据

        Returns:
            OperatorResult: 执行结果
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据（子类可覆盖）"""
        return True

    def pre_execute(self, input_data: Dict[str, Any]) -> None:
        """执行前钩子（子类可覆盖）"""
        pass

    def post_execute(self, result: OperatorResult) -> None:
        """执行后钩子（子类可覆盖）"""
        pass

    def on_error(self, error: Exception) -> None:
        """错误处理钩子（子类可覆盖）"""
        pass

    def run(self, input_data: Dict[str, Any]) -> OperatorResult:
        """
        运行算子（模板方法模式）

        Args:
            input_data: 输入数据

        Returns:
            OperatorResult: 执行结果
        """
        self.status = OperatorStatus.RUNNING
        self.start_time = time.time()

        try:
            # 验证输入
            if not self.validate_input(input_data):
                raise ValueError("输入数据验证失败")

            # 执行前钩子
            self.pre_execute(input_data)

            # 执行算子逻辑
            result = self.execute(input_data)

            # 执行后钩子
            self.post_execute(result)

            # 更新状态
            self.status = OperatorStatus.SUCCESS
            self.success_count += 1
            result.success = True

        except Exception as e:
            self.status = OperatorStatus.FAILED
            self.error_count += 1
            self.on_error(e)
            result = OperatorResult(
                success=False,
                error=str(e),
                operator_id=self.OPERATOR_ID,
                operator_name=self.OPERATOR_NAME
            )

        finally:
            self.end_time = time.time()
            result.execution_time = self.end_time - self.start_time
            result.operator_id = self.OPERATOR_ID
            result.operator_name = self.OPERATOR_NAME
            result.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
            result.hash = result.calculate_hash()
            self.result = result

        return result

    def get_status(self) -> Dict[str, Any]:
        """获取算子状态"""
        return {
            "operator_id": self.OPERATOR_ID,
            "operator_name": self.OPERATOR_NAME,
            "version": self.OPERATOR_VERSION,
            "group": self.OPERATOR_GROUP,
            "status": self.status.value,
            "priority": self.PRIORITY.value,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "last_execution_time": self.result.execution_time if self.result else None
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.OPERATOR_ID} status={self.status.value}>"
