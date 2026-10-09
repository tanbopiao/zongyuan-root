#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一自治内核 · 自检模块 SELF-CHECK.py
用于 CI 与本地部署前快速校验：语法、依赖、启动清单结构、启动记忆五件套存在性。
"""
import json
import os
import py_compile
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REQUIRED = [
    "00_KERNEL/startup_memory/ROOT_ENTRY.md",
    "00_KERNEL/startup_memory/KNOWLEDGE-INDEX.md",
    "00_KERNEL/startup_memory/WAKEUP_PROTOCOL.md",
    "00_KERNEL/startup_memory/ACTIVE_LOCK.json",
    "00_KERNEL/startup_memory/GLOBAL_MEMORY_SNAPSHOT.json",
    "00_KERNEL/omega01_boot/OMEGA-KERNEL-BOOT.json",
    "02_SKILLS/README.md",
]
PY_FILES = [
    "00_KERNEL/omega01_boot/omega_bootstrap.py",
    "00_KERNEL/omega01_boot/SELF-CHECK.py",
]


def main():
    failed = False

    print("[SELF-CHECK] 1/3 语法编译")
    for rel in PY_FILES:
        p = os.path.join(ROOT, rel)
        try:
            py_compile.compile(p, doraise=True)
            print("  OK  %s" % rel)
        except py_compile.PyCompileError as e:
            print("  ERR %s  %s" % (rel, e))
            failed = True

    print("[SELF-CHECK] 2/3 必要文件存在性")
    for rel in REQUIRED:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            print("  OK  %s" % rel)
        else:
            print("  MISSING  %s" % rel)
            failed = True

    print("[SELF-CHECK] 3/3 启动清单 JSON 可解析性")
    boot = os.path.join(HERE, "OMEGA-KERNEL-BOOT.json")
    try:
        d = json.load(open(boot, encoding="utf-8"))
        steps = d.get("load_order", [])
        if len(steps) == 8 and all("step" in s for s in steps):
            print("  OK  boot json, steps=%d" % len(steps))
        else:
            print("  ERR boot json steps != 8")
            failed = True
    except Exception as e:
        print("  ERR  %s" % e)
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())