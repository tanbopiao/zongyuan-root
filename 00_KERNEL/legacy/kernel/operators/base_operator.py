#!/usr/bin/env python3
"""
算子标准定义 - 所有算子必须遵循的统一接口规范
算子即太极：阴阳具足（输入/输出）、四象完备（成功/失败/高/低质量）、五行可运（5种组合模式）
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Callable
from enum import Enum
import hashlib
import time
import json
import uuid
import threading


class OperatorStatus(Enum):
    """算子状态 - 四象状态机"""
    PENDING = "pending"           # 待执行
    RUNNING = "running"           # 执行中
    SUCCESS_HIGH = "success_high"  # 太阳：成功+高质量
    SUCCESS_LOW = "success_low"    # 少阳：成功+低质量
    FAILURE_RECOVERABLE = "failure_recoverable"  # 少阴：失败+可恢复
    FAILURE_UNRECOVERABLE = "failure_unrecoverable"  # 太阴：失败+不可恢复
    SKIPPED = "skipped"           # 跳过


class OperatorQuality(Enum):
    """算子执行质量"""
    HIGH = "high"     # 高质量
    MEDIUM = "medium"  # 中等质量
    LOW = "low"       # 低质量


@dataclass
class OperatorInput:
    """算子输入 - 阴"""
    params: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    raw_input: Any = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


@dataclass
class OperatorOutput:
    """算子输出 - 阳"""
    success: bool = False
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    quality: OperatorQuality = OperatorQuality.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    trace_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "quality": self.quality.value,
            "metadata": self.metadata,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "trace_hash": self.trace_hash,
        }


@dataclass
class OperatorMetadata:
    """算子元数据"""
    operator_id: str = ""
    operator_name: str = ""
    operator_version: str = "1.0.0"
    description: str = ""
    category: str = ""  # 算子分类：truth/security/deploy/compute/io
    author: str = "ZONGYUAN-ROOT"
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    operator_hash: str = ""

    def __post_init__(self):
        if not self.operator_id:
            self.operator_id = f"op-{uuid.uuid4().hex[:12]}"
        if not self.operator_hash:
            self.operator_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        content = json.dumps({
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "operator_version": self.operator_version,
            "category": self.category,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest().upper()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "operator_version": self.operator_version,
            "description": self.description,
            "category": self.category,
            "author": self.author,
            "created_at": self.created_at,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "operator_hash": self.operator_hash,
        }


class BaseOperator:
    """
    算子基类 - 所有算子的父类
    每个算子都是一个独立自足的小太极：阴阳具足（输入/输出）、四象完备（状态机）
    """

    def __init__(self, metadata: Optional[OperatorMetadata] = None):
        self.metadata = metadata or OperatorMetadata()
        self.status = OperatorStatus.PENDING
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_execution_time_ms = 0.0
        self._lock = threading.Lock()

    def execute(self, inputs: OperatorInput) -> OperatorOutput:
        """
        执行算子 - 模板方法模式
        子类实现 _execute 方法，基类负责状态管理、计时、统计
        """
        start_time = time.time()
        self.status = OperatorStatus.RUNNING

        try:
            output = self._execute(inputs)

            # 计算执行时间
            output.execution_time_ms = (time.time() - start_time) * 1000

            # 计算追踪哈希
            output.trace_hash = hashlib.sha256(
                f"{self.metadata.operator_id}:{time.time()}:{json.dumps(str(output.data), default=str)}".encode()
            ).hexdigest().upper()

            # 更新状态和统计
            with self._lock:
                self.execution_count += 1
                self.total_execution_time_ms += output.execution_time_ms
                if output.success:
                    self.success_count += 1
                    self.status = (OperatorStatus.SUCCESS_HIGH
                                   if output.quality == OperatorQuality.HIGH
                                   else OperatorStatus.SUCCESS_LOW)
                else:
                    self.failure_count += 1
                    self.status = (OperatorStatus.FAILURE_RECOVERABLE
                                   if output.error_code and "recoverable" in output.error_code
                                   else OperatorStatus.FAILURE_UNRECOVERABLE)

            return output

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            with self._lock:
                self.execution_count += 1
                self.failure_count += 1
                self.total_execution_time_ms += execution_time
                self.status = OperatorStatus.FAILURE_UNRECOVERABLE

            return OperatorOutput(
                success=False,
                error=str(e),
                error_code="unrecoverable_exception",
                quality=OperatorQuality.LOW,
                execution_time_ms=execution_time,
                trace_hash=hashlib.sha256(f"{self.metadata.operator_id}:error:{time.time()}".encode()).hexdigest().upper(),
            )

    def _execute(self, inputs: OperatorInput) -> OperatorOutput:
        """
        子类必须实现的核心执行逻辑
        """
        raise NotImplementedError("子类必须实现 _execute 方法")

    def get_stats(self) -> Dict[str, Any]:
        """获取算子统计信息"""
        with self._lock:
            avg_time = self.total_execution_time_ms / max(self.execution_count, 1)
            success_rate = self.success_count / max(self.execution_count, 1)
            return {
                "operator_id": self.metadata.operator_id,
                "operator_name": self.metadata.operator_name,
                "status": self.status.value,
                "execution_count": self.execution_count,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": round(success_rate, 4),
                "avg_execution_time_ms": round(avg_time, 2),
                "operator_hash": self.metadata.operator_hash,
            }

    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self.execution_count = 0
            self.success_count = 0
            self.failure_count = 0
            self.total_execution_time_ms = 0.0
            self.status = OperatorStatus.PENDING
