#!/usr/bin/env python3
"""
协议适配器基类 - 所有异构协议转换为统一协议的抽象基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
import time
import uuid
import logging

from ..unified_protocol import (
    UnifiedRequest, UnifiedResponse, ProtocolType, AuthType, DataFormat,
    ZR_PROTOCOL_VERSION, ZR_ERROR_CODES
)

logger = logging.getLogger(__name__)


class BaseProtocolAdapter(ABC):
    """协议适配器抽象基类"""

    protocol_type: ProtocolType = ProtocolType.REST_JSON
    adapter_name: str = "base"
    adapter_version: str = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_response_time_ms = 0.0

    @abstractmethod
    def to_unified_request(self, raw_request: Any) -> UnifiedRequest:
        """将原始请求转换为统一请求格式"""
        pass

    @abstractmethod
    def from_unified_request(self, unified_request: UnifiedRequest) -> Any:
        """将统一请求转换为原始协议格式"""
        pass

    @abstractmethod
    def to_unified_response(self, raw_response: Any, request_id: str) -> UnifiedResponse:
        """将原始响应转换为统一响应格式"""
        pass

    @abstractmethod
    def from_unified_response(self, unified_response: UnifiedResponse) -> Any:
        """将统一响应转换为原始协议格式"""
        pass

    def execute(self, unified_request: UnifiedRequest) -> UnifiedResponse:
        """执行请求：统一请求 → 原始协议 → 执行 → 统一响应"""
        start_time = time.time()
        self.request_count += 1

        try:
            # 转换为原始协议
            raw_request = self.from_unified_request(unified_request)

            # 执行原始请求
            raw_response = self._execute_raw(raw_request, unified_request)

            # 转换为统一响应
            unified_response = self.to_unified_response(raw_response, unified_request.request_id)
            unified_response.trace_hash = unified_request.trace_hash

            self.success_count += 1
            unified_response.response_time_ms = (time.time() - start_time) * 1000
            self.total_response_time_ms += unified_response.response_time_ms

            return unified_response

        except Exception as e:
            self.failure_count += 1
            error_response = UnifiedResponse(
                request_id=unified_request.request_id,
                status_code=500,
                success=False,
                error={
                    "code": 1006,
                    "message": f"协议转换失败: {str(e)}",
                    "adapter": self.adapter_name,
                },
                trace_hash=unified_request.trace_hash,
                response_time_ms=(time.time() - start_time) * 1000,
            )
            logger.error(f"[{self.adapter_name}] 协议执行失败: {str(e)}")
            return error_response

    @abstractmethod
    def _execute_raw(self, raw_request: Any, unified_request: UnifiedRequest) -> Any:
        """执行原始协议请求（子类实现）"""
        pass

    def health_check(self) -> bool:
        """健康检查"""
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        avg_time = self.total_response_time_ms / max(self.request_count, 1)
        success_rate = self.success_count / max(self.request_count, 1)
        return {
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "protocol_type": self.protocol_type.value,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(success_rate, 4),
            "avg_response_time_ms": round(avg_time, 2),
        }

    def _generate_request_id(self) -> str:
        """生成请求ID"""
        return f"zr-{uuid.uuid4().hex[:16]}"
