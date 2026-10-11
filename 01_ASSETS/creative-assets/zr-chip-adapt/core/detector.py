"""
zr-chip-adapt · core/detector.py
芯片自动识别 —— 通过系统命令探测可用芯片及厂商。

锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Optional


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def detect_chips() -> dict:
    """
    探测本机可用芯片，返回 { vendor: {cmd, available} }。
    命令探测失败不抛异常，仅标记 unavailable。
    """
    probes = [
        ("nvidia",   "nvidia-smi", "--query-gpu=name,memory.total,memory.free --format=csv,noheader"),
        ("rocm",     "rocm-smi",   "--showmeminfo vram"),
        ("ascend",   "npu-smi",    "info"),
        ("cambricon","cnmon",      "info"),
        ("mthreads", "mthreads-gmi","info"),
    ]
    result = {}
    for vendor, cmd, arg in probes:
        ok = _which(cmd)
        detail = ""
        if ok:
            try:
                r = subprocess.run([cmd, arg], capture_output=True, text=True, timeout=5)
                detail = (r.stdout or r.stderr).strip().splitlines()
                detail = detail[0] if detail else ""
            except Exception as e:
                detail = f"err:{e}"
        result[vendor] = {"cmd": cmd, "available": ok, "sample": detail}
    return result


def first_available() -> Optional[str]:
    """返回第一个可用的厂商名（按优先级：nvidia > rocm > ascend > cambricon > mthreads）"""
    det = detect_chips()
    for vendor in ("nvidia", "rocm", "ascend", "cambricon", "mthreads"):
        if det.get(vendor, {}).get("available"):
            return vendor
    return None
