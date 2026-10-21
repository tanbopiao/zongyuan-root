# -*- coding: utf-8 -*-
"""FM-Core 内核包：Phase1 最小内核（记忆原子 / 提案 / 共识 / 冲突 / 生命周期 / 审计）。"""
from .kernel import MemoryKernel, KERNEL_NAME, KERNEL_VERSION, AXIOM

__all__ = ["MemoryKernel", "KERNEL_NAME", "KERNEL_VERSION", "AXIOM"]
