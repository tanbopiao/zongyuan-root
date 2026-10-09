#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 协议融合引擎
所有同源协议融合的核心入口
"""
from .unified_protocol import (
    UnifiedRequest, UnifiedResponse, ServiceEndpoint,
    ProtocolType, AuthType, DataFormat,
    ZR_PROTOCOL_VERSION, ZR_ERROR_CODES,
)
from .registry.protocol_registry import ProtocolRegistry
from .adapters.base_adapter import BaseProtocolAdapter
from .adapters.rest_json_adapter import RestJsonAdapter
from .gateway.unified_api_gateway import UnifiedAPIGateway

__version__ = "1.0.0"
__all__ = [
    "UnifiedRequest",
    "UnifiedResponse",
    "ServiceEndpoint",
    "ProtocolType",
    "AuthType",
    "DataFormat",
    "ZR_PROTOCOL_VERSION",
    "ZR_ERROR_CODES",
    "ProtocolRegistry",
    "BaseProtocolAdapter",
    "RestJsonAdapter",
    "UnifiedAPIGateway",
]
