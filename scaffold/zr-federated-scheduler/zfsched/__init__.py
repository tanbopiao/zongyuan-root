#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr-federated-scheduler · 开源联邦调度引擎
ZONGYUAN-ROOT 元极恒一自治体系 · 多节点联邦任务调度
共识机制：任务认领仲裁（防多节点重复抢占）+ 心跳超时回收 + 失败重试
锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Apache-2.0
"""
__version__ = "1.0.0"
__all__ = ["Node", "Task", "FederatedScheduler", "run_simulation"]
