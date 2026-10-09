#!/usr/bin/env python3
"""
REST JSON 协议适配器 - 处理标准RESTful JSON API协议
"""
from typing import Any, Dict, Optional
import requests
import json
import time
import logging

from .base_adapter import BaseProtocolAdapter
from ..unified_protocol import (
    UnifiedRequest, UnifiedResponse, ProtocolType, AuthType, DataFormat
)

logger = logging.getLogger(__name__)


class RestJsonAdapter(BaseProtocolAdapter):
    """REST JSON 协议适配器"""

    protocol_type = ProtocolType.REST_JSON
    adapter_name = "rest_json"
    adapter_version = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = config.get("base_url", "") if config else ""
        self.timeout = config.get("timeout", 30) if config else 30
        self.default_headers = config.get("default_headers", {}) if config else {}
        self.session = requests.Session()

    def to_unified_request(self, raw_request: Any) -> UnifiedRequest:
        """将原始requests请求转换为统一请求"""
        if isinstance(raw_request, dict):
            return UnifiedRequest(
                request_id=raw_request.get("request_id", self._generate_request_id()),
                source_service=raw_request.get("source_service", ""),
                target_service=raw_request.get("target_service", ""),
                endpoint=raw_request.get("endpoint", raw_request.get("url", "")),
                method=raw_request.get("method", "GET").upper(),
                headers=raw_request.get("headers", {}),
                params=raw_request.get("params", {}),
                body=raw_request.get("body", raw_request.get("json", None)),
                data_format=DataFormat.JSON,
                auth_type=AuthType.API_KEY if raw_request.get("api_key") else AuthType.NONE,
            )
        raise ValueError(f"不支持的原始请求类型: {type(raw_request)}")

    def from_unified_request(self, unified_request: UnifiedRequest) -> Dict[str, Any]:
        """将统一请求转换为requests格式"""
        url = unified_request.endpoint
        if self.base_url and not url.startswith("http"):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"

        headers = {**self.default_headers, **unified_request.headers}
        headers["Content-Type"] = "application/json"

        return {
            "method": unified_request.method,
            "url": url,
            "headers": headers,
            "params": unified_request.params,
            "json": unified_request.body,
            "timeout": unified_request.timeout or self.timeout,
        }

    def to_unified_response(self, raw_response: Any, request_id: str) -> UnifiedResponse:
        """将requests响应转换为统一响应"""
        if isinstance(raw_response, requests.Response):
            try:
                data = raw_response.json()
            except (json.JSONDecodeError, ValueError):
                data = raw_response.text

            return UnifiedResponse(
                request_id=request_id,
                status_code=raw_response.status_code,
                success=200 <= raw_response.status_code < 300,
                data=data,
                error=None if 200 <= raw_response.status_code < 300 else {
                    "code": raw_response.status_code,
                    "message": f"HTTP {raw_response.status_code}",
                },
                headers=dict(raw_response.headers),
                response_time_ms=raw_response.elapsed.total_seconds() * 1000,
            )
        raise ValueError(f"不支持的原始响应类型: {type(raw_response)}")

    def from_unified_response(self, unified_response: UnifiedResponse) -> Dict[str, Any]:
        """将统一响应转换为标准JSON格式"""
        return {
            "status_code": unified_response.status_code,
            "success": unified_response.success,
            "data": unified_response.data,
            "error": unified_response.error,
            "trace_hash": unified_response.trace_hash,
        }

    def _execute_raw(self, raw_request: Dict[str, Any], unified_request: UnifiedRequest) -> Any:
        """执行REST请求"""
        return self.session.request(**raw_request)

    def health_check(self) -> bool:
        """健康检查"""
        if not self.base_url:
            return True
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5,
            )
            return response.status_code < 500
        except Exception:
            return False
