"""
zr-chip-adapt · backends/_base.py
芯片后端通用基类：封装 mock 模式与统一接口的默认实现。
每个具体芯片后端只需声明 vendor/探测命令/默认模拟指标，并继承本类。
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from __future__ import annotations

import shutil
import subprocess
import time
from typing import Any, Dict, List

from core.interface import InferenceBackend, InferenceResult, DeviceMetrics


class ChipBackendBase(InferenceBackend):
    """
    通用芯片后端。子类需定义：
      name, vendor, probe_cmd, probe_args, default_mem_total_mb
    """
    vendor: str = "unknown"
    probe_cmd: str = ""
    probe_args: list = []
    default_mem_total_mb: float = 0.0
    default_mem_free_mb: float = 0.0

    def __init__(self, mock: bool = None):
        # mock 默认 = 探测命令不可用时自动启用
        self._mock = mock if mock is not None else not self._probe_available()

    def _probe_available(self) -> bool:
        if not self.probe_cmd or shutil.which(self.probe_cmd) is None:
            return False
        return True

    def _run_probe(self) -> str:
        try:
            r = subprocess.run([self.probe_cmd] + self.probe_args,
                               capture_output=True, text=True, timeout=5)
            return (r.stdout or r.stderr).strip()
        except Exception as e:
            return f"err:{e}"

    def get_device_metrics(self) -> DeviceMetrics:
        if self._mock:
            return DeviceMetrics(
                backend=self.name, vendor=self.vendor, device_name=f"{self.vendor} (mock)",
                memory_total_mb=self.default_mem_total_mb,
                memory_free_mb=self.default_mem_free_mb,
                compute_unit=f"{self.vendor} Core", is_available=False,
                raw={"mock": True},
            )
        out = self._run_probe()
        return DeviceMetrics(
            backend=self.name, vendor=self.vendor, device_name=f"{self.vendor} (probe)",
            memory_total_mb=self.default_mem_total_mb,
            memory_free_mb=self.default_mem_free_mb,
            compute_unit=f"{self.vendor} Core", is_available=True,
            raw={"probe_sample": out[:200]},
        )

    def infer(self, prompt: str, **kwargs) -> InferenceResult:
        # POC：返回占位回显，真实推理由模型引擎注入
        t0 = time.time()
        latency = (time.time() - t0) * 1000
        tag = "(mock)" if self._mock else "(probe)"
        return InferenceResult(
            text=f"[{self.name}{tag}] 约束层推理通路OK | prompt_len={len(prompt)}",
            usage_tokens={"prompt": len(prompt), "completion": 0},
            latency_ms=round(latency, 2),
            backend=self.name,
            extra={"mock": self._mock},
        )

    def quantize(self, model_ref: Any, bit: int, **kwargs) -> Any:
        return {"backend": self.name, "bit": bit, "status": "ok(mock)", "mock": self._mock}

    def set_context_len(self, length: int, **kwargs) -> None:
        self._ctx_len = length

    def batch(self, requests: List[str], **kwargs) -> List[InferenceResult]:
        return [self.infer(r) for r in requests]
