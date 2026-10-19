#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pytest 全局路径注入：保证测试可导入内核模块（DID-BR-000002）"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (ROOT, ROOT / "00_KERNEL"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
