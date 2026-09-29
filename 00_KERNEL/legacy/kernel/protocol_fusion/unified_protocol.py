#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 统一协议标准 v1.0
所有同源协议融合的核心标准定义
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from enum import Enum
import hashlib
import time
import json


class ProtocolType(Enum):
    """协议类型枚举"""
    REST_JSON = "rest_json"
    REST_FORM = "rest_form"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    SSE = "sse"
    MESSAGE_QUEUE = "message_queue"
    FUNCTION_CALL = "function_call"
    OPERATOR_CALL = "operator_call"
    INTERNAL_IPC = "internal_ipc"


class AuthType(Enum):
    """认证类型枚举"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    HMAC_SIGNATURE = "hmac_signature"
    INTERNAL_TRUST = "internal_trust"


class DataFormat(Enum):
    """数据格式枚举"""
    JSON = "json"
    XML = "xml"
    FORM_DATA = "form_data"
    PROTOBUF = "protobuf"
    MESSAGE_PACK = "message_pack"
    PLAIN_TEXT = "plain_text"
    BINARY = "binary"


@dataclass
class UnifiedRequest:
    """统一请求标准格式 - 所有协议融合后的标准请求"""
    request_id: str
    protocol_version: str = "ZR-PROTO-V1.0"
    timestamp: float = field(default_factory=time.time)
    source_service: str = ""
    target_service: str = ""
    endpoint: str = ""
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    body: Any = None
    data_format: DataFormat = DataFormat.JSON
    auth_type: AuthType = AuthType.INTERNAL_TRUST
    auth_credentials: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    retry_count: int = 0
    max_retries: int = 3
    trace_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.trace_hash:
            self.trace_hash = self._compute_trace_hash()

    def _compute_trace_hash(self) -> str:
        """计算请求溯源哈希"""
        content = f"{self.request_id}:{self.timestamp}:{self.source_service}:{self.target_service}:{self.endpoint}"
        return hashlib.sha256(content.encode()).hexdigest().upper()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "protocol_version": self.protocol_version,
            "timestamp": self.timestamp,
            "source_service": self.source_service,
            "target_service": self.target_service,
            "endpoint": self.endpoint,
            "method": self.method,
            "headers": self.headers,
            "params": self.params,
            "body": self.body,
            "data_format": self.data_format.value,
            "auth_type": self.auth_type.value,
            "auth_credentials": self.auth_credentials,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "trace_hash": self.trace_hash,
            "metadata": self.metadata,
        }


@dataclass
class UnifiedResponse:
    """统一响应标准格式 - 所有协议融合后的标准响应"""
    request_id: str
    status_code: int = 200
    success: bool = True
    data: Any = None
    error: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    response_time_ms: float = 0.0
    protocol_version: str = "ZR-PROTO-V1.0"
    timestamp: float = field(default_factory=time.time)
    trace_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "status_code": self.status_code,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "headers": self.headers,
            "response_time_ms": self.response_time_ms,
            "protocol_version": self.protocol_version,
            "timestamp": self.timestamp,
            "trace_hash": self.trace_hash,
            "metadata": self.metadata,
        }


@dataclass
class ServiceEndpoint:
    """服务端点定义 - 注册到协议注册表的服务端点"""
    service_name: str
    service_version: str
    endpoint_url: str
    protocol_type: ProtocolType
    auth_type: AuthType
    data_format: DataFormat = DataFormat.JSON
    health_check_url: str = ""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: str = "active"
    last_health_check: float = 0.0
    success_rate: float = 1.0
    avg_response_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "endpoint_url": self.endpoint_url,
            "protocol_type": self.protocol_type.value,
            "auth_type": self.auth_type.value,
            "data_format": self.data_format.value,
            "health_check_url": self.health_check_url,
            "description": self.description,
            "capabilities": self.capabilities,
            "status": self.status,
            "last_health_check": self.last_health_check,
            "success_rate": self.success_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
            "metadata": self.metadata,
        }


# 协议标准常量
ZR_PROTOCOL_VERSION = "ZR-PROTO-V1.0"
ZR_PROTOCOL_MAGIC = "ZR-PROTO"
ZR_PROTOCOL_HEADER = "X-ZR-Protocol-Version"
ZR_TRACE_HEADER = "X-ZR-Trace-Hash"
ZR_SERVICE_HEADER = "X-ZR-Service-Name"

# 标准错误码
ZR_ERROR_CODES = {
    1000: "协议版本不兼容",
    1001: "服务未注册",
    1002: "服务不可用",
    1003: "认证失败",
    1004: "请求超时",
    1005: "数据格式错误",
    1006: "协议转换失败",
    1007: "熔断触发",
    1008: "限流触发",
    1009: "溯源哈希校验失败",
}
