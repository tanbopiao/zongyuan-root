#!/usr/bin/env python3
"""
模型抽象层 (Model Abstraction Layer)
ZONGYUAN-ROOT 平台规则变更容灾方案 - P1核心组件

功能：
- 统一模型调用接口，上层业务不绑定特定平台
- 多后端支持：豆包(主) → 通义千问 → DeepSeek → 本地Ollama
- 自动降级：主后端失败自动切换备用
- 熔断保护：连续失败自动熔断，冷却后恢复
- 调用统计：记录各后端成功率/延迟/消耗
- 配置热加载：API密钥/端点/优先级可配置

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import os
import time
import hashlib
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class BackendStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CIRCUIT_OPEN = "circuit_open"
    UNAVAILABLE = "unavailable"


@dataclass
class ModelResponse:
    """统一响应格式"""
    content: str
    backend: str
    model: str
    success: bool
    latency_ms: float
    error: Optional[str] = None
    tokens_used: Optional[Dict] = None


@dataclass
class BackendConfig:
    """后端配置"""
    name: str
    provider: str  # doubao / qwen / deepseek / ollama
    api_base: str
    api_key: str
    model: str
    priority: int = 100  # 数字越小优先级越高
    enabled: bool = True
    timeout: int = 30
    max_retries: int = 2


@dataclass
class BackendState:
    """后端运行状态"""
    config: BackendConfig
    status: BackendStatus = BackendStatus.HEALTHY
    consecutive_failures: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_latency_ms: float = 0
    circuit_open_until: float = 0
    last_error: Optional[str] = None


class CircuitBreaker:
    """熔断器：连续失败达到阈值后熔断，冷却期后半开试探"""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def allow_request(self, state: BackendState) -> bool:
        if state.status == BackendStatus.CIRCUIT_OPEN:
            if time.time() > state.circuit_open_until:
                state.status = BackendStatus.DEGRADED
                return True  # 半开试探
            return False
        return True

    def record_success(self, state: BackendState):
        state.consecutive_failures = 0
        state.status = BackendStatus.HEALTHY

    def record_failure(self, state: BackendState, error: str):
        state.consecutive_failures += 1
        state.last_error = error
        if state.consecutive_failures >= self.failure_threshold:
            state.status = BackendStatus.CIRCUIT_OPEN
            state.circuit_open_until = time.time() + self.recovery_timeout


class ModelAbstractionLayer:
    """
    模型抽象层主类

    使用方式：
        mal = ModelAbstractionLayer("model_config.json")
        resp = mal.chat("你好，请介绍一下自己")
        print(resp.content, resp.backend)
    """

    def __init__(self, config_path: str = "model_config.json"):
        self.config_path = config_path
        self.backends: Dict[str, BackendState] = {}
        self.circuit_breaker = CircuitBreaker()
        self.call_history: List[Dict] = []
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        with open(self.config_path) as f:
            cfg = json.load(f)
        for bc in cfg.get("backends", []):
            config = BackendConfig(**bc)
            if config.enabled:
                self.backends[config.name] = BackendState(config=config)

    def _create_default_config(self):
        """创建默认配置"""
        default = {
            "backends": [
                {
                    "name": "doubao-primary",
                    "provider": "doubao",
                    "api_base": "https://ark.cn-beijing.volces.com/api/v3",
                    "api_key": "YOUR_DOUBAO_API_KEY",
                    "model": "doubao-pro-32k",
                    "priority": 1,
                    "enabled": True,
                    "timeout": 30,
                    "max_retries": 2
                },
                {
                    "name": "qwen-backup",
                    "provider": "qwen",
                    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "api_key": "YOUR_QWEN_API_KEY",
                    "model": "qwen-turbo",
                    "priority": 2,
                    "enabled": True,
                    "timeout": 30,
                    "max_retries": 2
                },
                {
                    "name": "deepseek-backup",
                    "provider": "deepseek",
                    "api_base": "https://api.deepseek.com/v1",
                    "api_key": "YOUR_DEEPSEEK_API_KEY",
                    "model": "deepseek-chat",
                    "priority": 3,
                    "enabled": True,
                    "timeout": 30,
                    "max_retries": 2
                },
                {
                    "name": "ollama-local",
                    "provider": "ollama",
                    "api_base": "http://127.0.0.1:11434/v1",
                    "api_key": "ollama",
                    "model": "qwen2.5:3b-instruct-q4_K_M",
                    "priority": 4,
                    "enabled": True,
                    "timeout": 60,
                    "max_retries": 1
                }
            ],
            "settings": {
                "circuit_breaker_failure_threshold": 3,
                "circuit_breaker_recovery_timeout": 60,
                "max_total_retries": 5,
                "log_calls": True
            }
        }
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default, f, ensure_ascii=False, indent=2)

    def _get_sorted_backends(self) -> List[BackendState]:
        """按优先级排序可用后端"""
        available = [
            b for b in self.backends.values()
            if b.config.enabled and self.circuit_breaker.allow_request(b)
        ]
        return sorted(available, key=lambda b: b.config.priority)

    def _call_backend(self, state: BackendState, messages: List[Dict],
                      temperature: float = 0.7, max_tokens: int = 2048) -> ModelResponse:
        """调用单个后端（OpenAI兼容格式）"""
        import urllib.request
        cfg = state.config
        start = time.time()

        payload = {
            "model": cfg.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        req = urllib.request.Request(
            f"{cfg.api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cfg.api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=cfg.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            latency = (time.time() - start) * 1000
            state.total_calls += 1
            state.total_latency_ms += latency
            self.circuit_breaker.record_success(state)

            return ModelResponse(
                content=content,
                backend=cfg.name,
                model=cfg.model,
                success=True,
                latency_ms=round(latency, 2),
                tokens_used=result.get("usage")
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            state.total_calls += 1
            state.total_failures += 1
            self.circuit_breaker.record_failure(state, str(e))

            return ModelResponse(
                content="",
                backend=cfg.name,
                model=cfg.model,
                success=False,
                latency_ms=round(latency, 2),
                error=str(e)
            )

    def chat(self, prompt: str, system: Optional[str] = None,
             temperature: float = 0.7, max_tokens: int = 2048) -> ModelResponse:
        """
        统一聊天接口：自动选择最优后端，失败自动降级

        Args:
            prompt: 用户输入
            system: 系统提示词（可选）
            temperature: 温度
            max_tokens: 最大生成长度

        Returns:
            ModelResponse: 统一响应
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        backends = self._get_sorted_backends()
        if not backends:
            return ModelResponse(
                content="", backend="none", model="none",
                success=False, latency_ms=0,
                error="所有后端均不可用（熔断或未配置）"
            )

        last_error = None
        for backend in backends:
            for attempt in range(backend.config.max_retries):
                resp = self._call_backend(backend, messages, temperature, max_tokens)
                if resp.success:
                    self._log_call(resp)
                    return resp
                last_error = resp.error
                # 重试间隔
                time.sleep(0.5 * (attempt + 1))

        return ModelResponse(
            content="", backend="all_failed", model="none",
            success=False, latency_ms=0,
            error=f"所有后端调用失败: {last_error}"
        )

    def _log_call(self, resp: ModelResponse):
        """记录调用历史"""
        self.call_history.append({
            "timestamp": time.time(),
            "backend": resp.backend,
            "model": resp.model,
            "success": resp.success,
            "latency_ms": resp.latency_ms,
            "content_hash": hashlib.md5(resp.content.encode()).hexdigest()[:16]
        })
        # 保留最近1000条
        if len(self.call_history) > 1000:
            self.call_history = self.call_history[-1000:]

    def get_status(self) -> Dict:
        """获取所有后端状态"""
        return {
            "backends": {
                name: {
                    "provider": s.config.provider,
                    "model": s.config.model,
                    "priority": s.config.priority,
                    "status": s.status.value,
                    "total_calls": s.total_calls,
                    "total_failures": s.total_failures,
                    "success_rate": round(
                        (s.total_calls - s.total_failures) / s.total_calls * 100, 1
                    ) if s.total_calls > 0 else 0,
                    "avg_latency_ms": round(
                        s.total_latency_ms / s.total_calls, 1
                    ) if s.total_calls > 0 else 0,
                    "consecutive_failures": s.consecutive_failures,
                    "last_error": s.last_error
                }
                for name, s in self.backends.items()
            },
            "total_calls": len(self.call_history),
            "active_backends": len([
                s for s in self.backends.values()
                if s.status in (BackendStatus.HEALTHY, BackendStatus.DEGRADED)
            ])
        }

    def reload_config(self):
        """热加载配置"""
        self._load_config()
        return self.get_status()


# ============ 命令行测试 ============
if __name__ == "__main__":
    import sys

    mal = ModelAbstractionLayer(
        os.path.join(os.path.dirname(__file__), "model_config.json")
    )

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(mal.get_status(), ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        print("=== 模型抽象层测试 ===")
        print("注意：需要配置有效的API密钥才能实际调用")
        print(json.dumps(mal.get_status(), ensure_ascii=False, indent=2))
        print("\n使用方式：")
        print("  mal = ModelAbstractionLayer('model_config.json')")
        print("  resp = mal.chat('你好')")
        print("  print(resp.content, resp.backend)")
    else:
        print("ZONGYUAN-ROOT 模型抽象层 v1.0")
        print("用法: python model_abstraction_layer.py [status|test]")
        print(json.dumps(mal.get_status(), ensure_ascii=False, indent=2))
