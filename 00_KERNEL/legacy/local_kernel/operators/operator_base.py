"""
算子基类 - ZONGYUAN-ROOT 算子化架构
所有标准算子必须继承此类，遵循统一接口规范

算子接口规范：
    result = operator(inputs_dict)
    result.success / result.data / result.error
    算子有哈希、版本、元数据，可锁档确权

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
根挂载：ZONGYUAN-ROOT V1.7
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class OperatorResult:
    """算子执行结果 - 标准化输出格式"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    operator_id: str = ""
    operator_name: str = ""
    execution_time_ms: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class OperatorMetadata:
    """算子元数据 - 用于锁档确权和版本管理"""
    operator_id: str
    operator_name: str
    version: str
    description: str
    category: str  # 真值/哈希/部署/API/遍历/文件/...
    author: str = "ZONGYUAN-ROOT"
    created_at: str = ""
    inputs_schema: Dict[str, Any] = field(default_factory=dict)
    outputs_schema: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """计算算子元数据哈希 - 用于锁档确权"""
        content = json.dumps({
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "author": self.author,
            "created_at": self.created_at,
            "hash": self.compute_hash(),
            "inputs_schema": self.inputs_schema,
            "outputs_schema": self.outputs_schema,
        }


class BaseOperator(ABC):
    """
    算子基类 - 所有标准算子必须继承

    核心特性：
    1. 统一接口：__call__(inputs) -> OperatorResult
    2. 自动计时：记录执行时间
    3. 元数据锁档：每个算子有唯一ID和哈希
    4. 输入校验：可选的schema校验
    5. 错误处理：统一的异常捕获和错误返回
    """

    def __init__(self, metadata: OperatorMetadata):
        self.metadata = metadata
        self._execution_count = 0
        self._total_execution_time_ms = 0.0

    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        算子核心执行逻辑 - 子类必须实现

        Args:
            inputs: 输入参数字典

        Returns:
            输出数据字典

        Raises:
            任意异常会被__call__捕获并转换为OperatorResult
        """
        pass

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """输入校验 - 子类可重写"""
        return True

    def __call__(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        """
        统一调用接口 - 所有算子通过此方法执行

        Args:
            inputs: 输入参数字典，默认为空字典

        Returns:
            OperatorResult 标准化执行结果
        """
        if inputs is None:
            inputs = {}

        start_time = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 输入校验
            if not self.validate_inputs(inputs):
                return OperatorResult(
                    success=False,
                    error="输入校验失败",
                    operator_id=self.metadata.operator_id,
                    operator_name=self.metadata.operator_name,
                    timestamp=timestamp,
                )

            # 执行核心逻辑
            data = self.execute(inputs)

            # 统计执行时间
            execution_time_ms = (time.time() - start_time) * 1000
            self._execution_count += 1
            self._total_execution_time_ms += execution_time_ms

            return OperatorResult(
                success=True,
                data=data if data else {},
                operator_id=self.metadata.operator_id,
                operator_name=self.metadata.operator_name,
                execution_time_ms=round(execution_time_ms, 2),
                timestamp=timestamp,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return OperatorResult(
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
                operator_id=self.metadata.operator_id,
                operator_name=self.metadata.operator_name,
                execution_time_ms=round(execution_time_ms, 2),
                timestamp=timestamp,
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取算子执行统计信息"""
        avg_time = (
            self._total_execution_time_ms / self._execution_count
            if self._execution_count > 0
            else 0
        )
        return {
            "operator_id": self.metadata.operator_id,
            "operator_name": self.metadata.operator_name,
            "execution_count": self._execution_count,
            "total_execution_time_ms": round(self._total_execution_time_ms, 2),
            "avg_execution_time_ms": round(avg_time, 2),
        }

    def get_lock_data(self) -> Dict[str, Any]:
        """获取锁档数据 - 用于Merkle-DAG确权"""
        return {
            "metadata": self.metadata.to_dict(),
            "stats": self.get_stats(),
            "locked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
            "did": "DID-BR-000002",
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"id={self.metadata.operator_id} "
            f"name={self.metadata.operator_name} "
            f"v={self.metadata.version}>"
        )
