"""
自治内核自我修复引擎 V1.0
支持：异常自动诊断 / 根因分析 / 自动修复 / 修复验证 / 修复历史记录
"""
from .healing_engine import SelfHealingEngine, AnomalySeverity, RepairStatus, RepairStrategy

__all__ = ['SelfHealingEngine', 'AnomalySeverity', 'RepairStatus', 'RepairStrategy']
__version__ = '1.0.0'
