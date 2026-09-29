"""
API调用算子 - ZONGYUAN-ROOT 算子化架构
标准化HTTP API调用，支持GET/POST、超时、重试、错误处理

算子ID: OP-API-CALL-001
算子名称: api_call
类别: API/网络
版本: V1.0

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
"""

import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from operator_base import BaseOperator, OperatorMetadata


class APICallOperator(BaseOperator):
    """API调用算子 - 标准化HTTP API调用"""

    def __init__(self):
        metadata = OperatorMetadata(
            operator_id="OP-API-CALL-001",
            operator_name="api_call",
            version="V1.0",
            description="标准化HTTP API调用，支持GET/POST、超时、重试、错误处理",
            category="api_call",
            inputs_schema={
                "url": "API地址（必需）",
                "method": "HTTP方法：GET/POST（默认GET）",
                "headers": "请求头字典（可选）",
                "data": "请求体数据（可选，POST时使用）",
                "timeout": "超时秒数（默认30）",
                "max_retries": "最大重试次数（默认2）",
            },
            outputs_schema={
                "response": "响应数据字典",
                "status_code": "HTTP状态码",
                "success": "是否调用成功",
                "retries": "实际重试次数",
            },
        )
        super().__init__(metadata)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行API调用"""
        url = inputs.get("url", "")
        method = inputs.get("method", "GET").upper()
        headers = inputs.get("headers", {})
        data = inputs.get("data", None)
        timeout = inputs.get("timeout", 30)
        max_retries = inputs.get("max_retries", 2)

        if not url:
            return {
                "response": {},
                "status_code": 0,
                "success": False,
                "error": "URL不能为空",
                "retries": 0,
            }

        retries = 0
        last_error = None

        while retries <= max_retries:
            try:
                # 构建请求
                req = urllib.request.Request(url, method=method)

                # 设置请求头
                req.add_header("Content-Type", "application/json")
                for key, value in headers.items():
                    req.add_header(key, str(value))

                # 设置请求体
                request_data = None
                if data is not None and method == "POST":
                    if isinstance(data, (dict, list)):
                        request_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
                    else:
                        request_data = str(data).encode("utf-8")

                # 发送请求
                with urllib.request.urlopen(req, data=request_data, timeout=timeout) as response:
                    status_code = response.getcode()
                    response_body = response.read().decode("utf-8", errors="replace")

                    # 尝试解析JSON
                    try:
                        response_data = json.loads(response_body)
                    except (json.JSONDecodeError, ValueError):
                        response_data = {"raw_text": response_body[:1000]}

                    return {
                        "response": response_data,
                        "status_code": status_code,
                        "success": 200 <= status_code < 300,
                        "retries": retries,
                        "response_time_ms": 0,
                    }

            except urllib.error.HTTPError as e:
                status_code = e.code
                try:
                    error_body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    error_body = str(e)
                last_error = f"HTTP错误 {status_code}: {error_body[:200]}"

                # 4xx错误不重试
                if 400 <= status_code < 500:
                    break

            except urllib.error.URLError as e:
                last_error = f"URL错误: {str(e.reason)}"
            except Exception as e:
                last_error = f"请求异常: {type(e).__name__}: {str(e)}"

            retries += 1
            if retries <= max_retries:
                time.sleep(1 * retries)  # 指数退避

        return {
            "response": {},
            "status_code": 0,
            "success": False,
            "error": last_error,
            "retries": retries,
        }


# 算子单例
api_call_operator = APICallOperator()
