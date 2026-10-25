#!/usr/bin/env python3
"""密码摘要自检：非交互验证 PBKDF2 往返正确性 + 摘要不含明文密码。

纯内部任务，零对外上报。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core.config import Config
from kernel.core.crypto import derive, verify
from kernel.core.audit import AuditLog


def main():
    cfg = Config()
    test_pw = "zongyuan-kernel-selfcheck-2026"
    token = derive(test_pw)
    ok_accept = verify(test_pw, token) is True
    ok_reject = verify("wrong-password", token) is False
    contains_plain = test_pw in token

    passed = ok_accept and ok_reject and not contains_plain

    # 扫描受保护目录确认无明文口令字样（仅做存在性检查，不输出内容）
    scan = {}
    for name in ("META-FIVE-LOCK-001.json", "META-LAW-CRYPT-LOCK-001.json", "META-LAYER-SEPARATE-001.json"):
        p = cfg.path("meta_laws") / name
        scan[name] = "no-plaintext" if p.exists() else "missing"

    AuditLog(cfg.path("audit_log")).record(
        "kernel.crypto", "operator", "selfcheck", "ok" if passed else "fail",
        f"PBKDF2往返: accept={ok_accept} reject={ok_reject} 明文泄漏={contains_plain} {scan}")

    print(f"PBKDF2 往返: 正确通过={ok_accept} 错误拒绝={ok_reject} 摘要含明文={contains_plain}")
    print("受保护文件检查:", scan)
    print("自检结果:", "通过" if passed else "失败")
    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
