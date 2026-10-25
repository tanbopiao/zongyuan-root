#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr-distill-lite · 模型蒸馏轻量化引擎
ZONGYUAN-ROOT 元极恒一自治体系 · 轻量模型蒸馏管线
机制：教师-学生软标签蒸馏 + INT8量化模拟 + 参数剪枝 + 压缩比/精度评估
纯标准库实现（自写微型 MLP），零依赖零 API，确定性可复算
锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Apache-2.0
"""
__version__ = "1.0.0"
__all__ = ["MLP", "DistillPipeline", "run_distill", "quantize_int8", "prune"]
