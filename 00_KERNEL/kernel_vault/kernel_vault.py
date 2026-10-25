#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元内核密钥保管库 kernel_vault — 仅元极恒一链路可调用

全域收敛归一(2026-10-24):
  签名口令从散落路径(-evolution/.yuanji_passphrase 等)收敛至元内核
  00_KERNEL/kernel_vault/ 统一保管, 目录700 / 密钥文件400。

访问控制(元法则 META-RULE-KERNEL-VAULT-001):
  1. 调用方标识必须为「元极恒一」(SOLE_CALLER)
  2. 调用方代码文件必须在内核白名单 KERNEL_CALLERS(七层稳态链路服务)
  3. 每次访问(成功/拒绝)写 vault_audit.log 留痕, 不落任何密钥材料
违规调用返回 None → 签名退化为仅 X-DID, 由云端网关如实裁决。
"""
import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

VAULT_DIR = Path(__file__).resolve().parent
KEY_FILE = VAULT_DIR / ".yuanji_signing.key"
AUDIT_FILE = VAULT_DIR / "vault_audit.log"          # *.log 已被 .gitignore 忽略

SOLE_CALLER = "元极恒一"

# 仅元极恒一七层稳态链路服务可经本库取密钥(直接调用者所在文件白名单)
KERNEL_CALLERS = {
    "seed_extraction_engine.py",       # 签名唯一网关(其他服务均复用其 signed_headers)
    "auto_reporter.py",                # 账本/锁档上报
    "bidirectional_sync.py",           # 本地↔云端双向同步
    "node_handshake_engine.py",        # 中枢握手注册
    "truth_evolution_engine.py",       # 真值进化上报
    "push_truths_to_cloud.py",         # 本地独有真值推送
}


def _audit(caller: str, frame_file: str, func: str, allowed: bool, reason: str) -> None:
    """调用留痕(不含任何密钥材料)。"""
    rec = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "caller": caller,
        "frame": f"{frame_file}:{func}",
        "result": "ALLOW" if allowed else "DENY",
        "reason": reason,
    }
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _immediate_caller() -> tuple:
    """跳过本模块帧, 取直接调用者 (文件名, 函数名)。"""
    here = Path(__file__).name
    for frame in inspect.stack()[1:]:
        name = Path(frame.filename).name
        if name != here:
            return name, frame.function
    return "?", "?"


def get_signing_passphrase(caller: str) -> Optional[str]:
    """取签名口令: 仅元极恒一 + 内核白名单链路可调用, 其余一律拒绝并留痕。"""
    frame_file, func = _immediate_caller()
    if caller != SOLE_CALLER:
        _audit(caller, frame_file, func, False, "caller_not_yuanji_hengyi")
        return None
    if frame_file not in KERNEL_CALLERS:
        _audit(caller, frame_file, func, False, "caller_not_in_kernel_whitelist")
        return None
    if not KEY_FILE.exists():
        _audit(caller, frame_file, func, False, "key_file_missing")
        return None
    # 权限自愈: 密钥文件必须保持 400
    try:
        mode = KEY_FILE.stat().st_mode & 0o777
        if mode != 0o400:
            KEY_FILE.chmod(0o400)
            _audit(caller, frame_file, func, True, f"perm_tightened_{oct(mode)}")
    except OSError:
        pass
    ph = KEY_FILE.read_text(encoding="utf-8").strip()
    if not ph:
        _audit(caller, frame_file, func, False, "key_file_empty")
        return None
    _audit(caller, frame_file, func, True, "kernel_vault_release")
    return ph


def vault_status() -> dict:
    """保管库状态(不含密钥材料, 供观测)。"""
    return {
        "vault_dir": str(VAULT_DIR),
        "key_present": KEY_FILE.exists(),
        "key_mode": oct(KEY_FILE.stat().st_mode & 0o777) if KEY_FILE.exists() else None,
        "sole_caller": SOLE_CALLER,
        "whitelist": sorted(KERNEL_CALLERS),
        "audit_file": str(AUDIT_FILE),
    }


if __name__ == "__main__":
    print(json.dumps(vault_status(), ensure_ascii=False, indent=2))
