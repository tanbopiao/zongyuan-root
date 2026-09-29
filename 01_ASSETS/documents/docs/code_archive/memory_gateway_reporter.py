"""
记忆网关自动上报器 V1.0
所有机制通用的记忆网关上报告组件，支持真值上报、状态查询、批量上报。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error


@dataclass
class TruthItem:
    """真值条目"""
    truth_key: str
    truth_value: str
    source_node: str = "zongyuan-root-autonomy"
    confidence: float = 0.9
    truth_type: str = "data"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "truth_key": self.truth_key,
            "truth_value": self.truth_value,
            "source_node": self.source_node,
            "confidence": self.confidence,
            "truth_type": self.truth_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class ReportResult:
    """上报结果"""
    success: bool
    truth_count: int = 0
    action: str = ""  # inserted/unchanged/updated
    message: str = ""
    errors: List[str] = field(default_factory=list)
    response_data: Dict = field(default_factory=dict)
    elapsed_ms: float = 0.0


class MemoryGatewayReporter:
    """记忆网关自动上报器"""

    # 真值类型有效值
    VALID_TRUTH_TYPES = [
        "meta_law", "rule", "config", "decision",
        "data", "creative", "risk", "protocol", "unknown"
    ]

    # 默认配置
    DEFAULT_CONFIG = {
        "gateway_url": "https://www.huodouai.com/api/report/truth",
        "status_url": "https://www.huodouai.com/api/report/status",
        "nodes_url": "https://www.huodouai.com/api/report/nodes",
        "node_register_url": "https://www.huodouai.com/api/report/node/register",
        "source_node": "zongyuan-root-autonomy",
        "default_confidence": 0.9,
        "default_truth_type": "data",
        "timeout": 10,
        "max_retries": 5,
        "retry_delay_base": 1,  # 指数退避基数（秒）
        "retry_delay_max": 30,  # 最大重试延迟（秒）
        "batch_size": 20,
        "batch_interval": 0.3,  # 批量上报间隔（秒），避免高并发
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
    }

    # 可重试错误类型
    RETRYABLE_ERRORS = [
        "database is locked",      # SQLite锁定
        "502 Bad Gateway",          # 网关错误
        "503 Service Unavailable",  # 服务不可用
        "504 Gateway Timeout",      # 网关超时
        "Connection refused",       # 连接拒绝
        "Connection reset",         # 连接重置
        "timeout",                  # 超时
        "EOF",                      # 连接意外结束
    ]

    # 不可重试错误类型
    NON_RETRYABLE_ERRORS = [
        "400 Bad Request",     # 请求格式错误
        "401 Unauthorized",    # 未授权
        "403 Forbidden",       # 禁止访问
        "404 Not Found",       # 未找到
        "validation error",    # 验证错误
        "invalid truth_type",  # 无效真值类型
    ]

    def __init__(self, config: Dict = None):
        """
        初始化记忆网关上报告器

        Args:
            config: 配置字典，覆盖默认配置
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._report_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._last_truth_count = 0
        self._report_history: List[ReportResult] = []

    def report_truth(self, truth_key: str, truth_value: str,
                     confidence: float = None, truth_type: str = None,
                     source_node: str = None, metadata: Dict = None) -> ReportResult:
        """
        上报单条真值到记忆网关

        Args:
            truth_key: 真值键（大写点分命名，如 MECHANISM.PSMRS.V1.0）
            truth_value: 真值内容
            confidence: 置信度（0-1），默认使用配置
            truth_type: 真值类型，默认使用配置
            source_node: 来源节点，默认使用配置
            metadata: 附加元数据

        Returns:
            ReportResult上报结果
        """
        item = TruthItem(
            truth_key=truth_key,
            truth_value=truth_value,
            source_node=source_node or self.config["source_node"],
            confidence=confidence if confidence is not None else self.config["default_confidence"],
            truth_type=truth_type or self.config["default_truth_type"],
            metadata=metadata or {},
        )

        # 验证真值类型
        if item.truth_type not in self.VALID_TRUTH_TYPES:
            item.truth_type = "unknown"

        # 验证置信度
        item.confidence = max(0.0, min(1.0, item.confidence))

        return self._do_report(item)

    def report_batch(self, items: List[TruthItem]) -> List[ReportResult]:
        """
        批量上报真值

        Args:
            items: 真值条目列表

        Returns:
            上报结果列表
        """
        results = []
        batch_size = self.config["batch_size"]
        batch_interval = self.config.get("batch_interval", 0.3)

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            for item in batch:
                result = self._do_report(item)
                results.append(result)
                # 避免请求过快导致SQLite锁定
                time.sleep(batch_interval)

        return results

    def report_from_metadata(self, metadata: Dict, content: str,
                              prefix: str = "RESULT") -> ReportResult:
        """
        从成果元数据自动生成真值并上报

        Args:
            metadata: 成果元数据字典
            content: 成果内容（用于生成真值摘要）
            prefix: 真值键前缀

        Returns:
            ReportResult上报结果
        """
        # 生成真值键
        result_id = metadata.get("result_id", "")
        content_hash = metadata.get("content_hash", "")
        truth_key = f"{prefix}.{result_id or content_hash[:12]}.{datetime.now().strftime('%Y%m%d')}"

        # 生成真值内容（摘要）
        summary = self._generate_summary(metadata, content)

        # 确定真值类型
        result_type = metadata.get("result_type", "document")
        truth_type_map = {
            "code": "data", "document": "data", "data": "data",
            "model": "data", "config": "config", "visualization": "creative",
            "media": "creative", "analysis": "data", "decision": "decision",
            "protocol": "protocol",
        }
        truth_type = truth_type_map.get(result_type, "data")

        # 确定置信度
        confidence = metadata.get("confidence", self.config["default_confidence"])

        # 附加元数据
        meta = {
            "result_name": metadata.get("result_name", ""),
            "result_type": result_type,
            "meta_class": metadata.get("meta_class", ""),
            "format": metadata.get("format", ""),
            "size_bytes": metadata.get("size_bytes", 0),
            "tags": metadata.get("tags", []),
            "priority": metadata.get("priority", ""),
            "content_hash": content_hash,
            "did": self.config["did"],
            "trace_mark": self.config["trace_mark"],
        }

        return self.report_truth(
            truth_key=truth_key,
            truth_value=summary,
            confidence=confidence,
            truth_type=truth_type,
            metadata=meta,
        )

    def get_status(self) -> Dict:
        """
        获取记忆网关状态

        Returns:
            网关状态字典
        """
        try:
            response = self._http_get(self.config["status_url"])
            self._last_truth_count = response.get("truth_count", response.get("meta", {}).get("truth_count", 0))
            return {
                "success": True,
                "data": response,
                "truth_count": self._last_truth_count,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "truth_count": self._last_truth_count,
            }

    def register_node(self, node_id: str, node_name: str,
                      node_type: str = "worker") -> Dict:
        """
        注册节点

        Args:
            node_id: 节点ID
            node_name: 节点名称
            node_type: 节点类型

        Returns:
            注册结果
        """
        payload = {
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
        }
        try:
            response = self._http_post(self.config["node_register_url"], payload)
            return {"success": True, "data": response}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _do_report(self, item: TruthItem) -> ReportResult:
        """执行单条上报（含指数退避重试+错误分类）"""
        start_time = time.time()
        payload = item.to_dict()

        last_error = ""
        last_error_type = "unknown"
        attempts_made = 0

        for attempt in range(self.config["max_retries"]):
            attempts_made = attempt + 1
            try:
                response = self._http_post(self.config["gateway_url"], payload)

                # 解析响应（兼容多种格式）
                success = response.get("success", False) or response.get("status") == "reported"
                truth_count = response.get("truth_count", response.get("meta", {}).get("truth_count", 0))
                action = response.get("action", response.get("validation", {}).get("action", ""))
                message = response.get("message", "")
                error_msg = response.get("error", "")

                # 处理业务层错误（如database is locked）
                if not success and error_msg:
                    if self._is_retryable_error(error_msg):
                        last_error = error_msg
                        last_error_type = "business_retryable"
                        if attempt < self.config["max_retries"] - 1:
                            delay = self._exponential_backoff(attempt)
                            time.sleep(delay)
                            continue
                    else:
                        # 不可重试的业务错误，直接返回
                        result = ReportResult(
                            success=False,
                            truth_count=truth_count,
                            action=action,
                            message=f"业务错误（不可重试）: {error_msg}",
                            errors=[error_msg],
                            response_data=response,
                            elapsed_ms=(time.time() - start_time) * 1000,
                        )
                        self._report_count += 1
                        self._fail_count += 1
                        self._report_history.append(result)
                        if len(self._report_history) > 100:
                            self._report_history = self._report_history[-100:]
                        return result

                result = ReportResult(
                    success=success,
                    truth_count=truth_count,
                    action=action,
                    message=message,
                    response_data=response,
                    elapsed_ms=(time.time() - start_time) * 1000,
                )

                self._report_count += 1
                if success:
                    self._success_count += 1
                    self._last_truth_count = truth_count
                else:
                    self._fail_count += 1

                self._report_history.append(result)
                if len(self._report_history) > 100:
                    self._report_history = self._report_history[-100:]

                return result

            except Exception as e:
                last_error = str(e)
                last_error_type = self._classify_error(last_error)

                # 不可重试错误，直接返回
                if self._is_non_retryable_error(last_error):
                    result = ReportResult(
                        success=False,
                        message=f"不可重试错误（{last_error_type}）: {last_error}",
                        errors=[last_error],
                        elapsed_ms=(time.time() - start_time) * 1000,
                    )
                    self._report_count += 1
                    self._fail_count += 1
                    self._report_history.append(result)
                    if len(self._report_history) > 100:
                        self._report_history = self._report_history[-100:]
                    return result

                # 可重试错误，指数退避后重试
                if attempt < self.config["max_retries"] - 1:
                    delay = self._exponential_backoff(attempt)
                    time.sleep(delay)

        # 所有重试都失败
        result = ReportResult(
            success=False,
            message=f"上报失败（{attempts_made}次重试后，{last_error_type}）: {last_error}",
            errors=[last_error],
            elapsed_ms=(time.time() - start_time) * 1000,
        )
        self._report_count += 1
        self._fail_count += 1
        self._report_history.append(result)
        if len(self._report_history) > 100:
            self._report_history = self._report_history[-100:]
        return result

    def _exponential_backoff(self, attempt: int) -> float:
        """
        指数退避计算：delay = min(base * 2^attempt, max_delay)
        添加±20%随机抖动，避免惊群效应
        """
        import random
        base = self.config["retry_delay_base"]
        max_delay = self.config["retry_delay_max"]
        delay = min(base * (2 ** attempt), max_delay)
        # 添加±20%随机抖动
        jitter = delay * 0.2 * random.uniform(-1, 1)
        return max(0.1, delay + jitter)

    def _is_retryable_error(self, error_msg: str) -> bool:
        """判断错误是否可重试"""
        error_lower = error_msg.lower()
        return any(err.lower() in error_lower for err in self.RETRYABLE_ERRORS)

    def _is_non_retryable_error(self, error_msg: str) -> bool:
        """判断错误是否不可重试"""
        error_lower = error_msg.lower()
        return any(err.lower() in error_lower for err in self.NON_RETRYABLE_ERRORS)

    def _classify_error(self, error_msg: str) -> str:
        """错误分类"""
        error_lower = error_msg.lower()
        if "database is locked" in error_lower:
            return "sqlite_locked"
        elif "502" in error_lower or "bad gateway" in error_lower:
            return "gateway_502"
        elif "503" in error_lower or "service unavailable" in error_lower:
            return "service_503"
        elif "504" in error_lower or "gateway timeout" in error_lower:
            return "gateway_504"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "connection" in error_lower:
            return "connection_error"
        elif "400" in error_lower or "bad request" in error_lower:
            return "bad_request_400"
        elif "401" in error_lower or "unauthorized" in error_lower:
            return "unauthorized_401"
        elif "403" in error_lower or "forbidden" in error_lower:
            return "forbidden_403"
        elif "404" in error_lower or "not found" in error_lower:
            return "not_found_404"
        else:
            return "unknown"

    def _http_post(self, url: str, payload: Dict) -> Dict:
        """HTTP POST请求"""
        if HAS_REQUESTS:
            response = requests.post(
                url,
                json=payload,
                timeout=self.config["timeout"],
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        else:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.config["timeout"]) as resp:
                return json.loads(resp.read().decode("utf-8"))

    def _http_get(self, url: str) -> Dict:
        """HTTP GET请求"""
        if HAS_REQUESTS:
            response = requests.get(url, timeout=self.config["timeout"])
            response.raise_for_status()
            return response.json()
        else:
            with urllib.request.urlopen(url, timeout=self.config["timeout"]) as resp:
                return json.loads(resp.read().decode("utf-8"))

    def _generate_summary(self, metadata: Dict, content: str, max_len: int = 2000) -> str:
        """从成果元数据和内容生成真值摘要"""
        name = metadata.get("result_name", "未知成果")
        result_type = metadata.get("result_type", "unknown")
        meta_class = metadata.get("meta_class", "unknown")
        tags = metadata.get("tags", [])
        size = metadata.get("size_bytes", 0)

        # 内容摘要（取前N字符）
        content_clean = re.sub(r'\s+', ' ', content).strip() if content else ""
        content_summary = content_clean[:500] if content_clean else ""

        summary = (
            f"【成果上报】{name}\n"
            f"类型: {result_type} | 元类: {meta_class} | "
            f"大小: {self._human_size(size)} | 标签: {', '.join(tags[:5])}\n"
        )
        if content_summary:
            summary += f"内容摘要: {content_summary}..."

        return summary[:max_len]

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """人类可读文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def get_stats(self) -> Dict:
        """获取上报器统计"""
        return {
            "total_reports": self._report_count,
            "success_count": self._success_count,
            "fail_count": self._fail_count,
            "success_rate": (self._success_count / self._report_count * 100) if self._report_count > 0 else 0,
            "last_truth_count": self._last_truth_count,
            "gateway_url": self.config["gateway_url"],
            "source_node": self.config["source_node"],
            "status": "running",
        }

    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取最近上报历史"""
        history = self._report_history[-limit:]
        return [
            {
                "success": r.success,
                "truth_count": r.truth_count,
                "action": r.action,
                "message": r.message[:100],
                "elapsed_ms": round(r.elapsed_ms, 1),
            }
            for r in history
        ]


# 正则导入（用于内容清理）
import re
