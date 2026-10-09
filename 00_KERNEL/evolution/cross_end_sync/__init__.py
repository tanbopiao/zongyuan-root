"""
跨端进化策略同步与冲突消解引擎 V1.0
支持：本地-云端进化策略同步 / 双端差异检测 / 冲突消解 / 同步状态监控
"""
from .sync_engine import CrossEndEvolutionSyncEngine, SyncStrategy, ConflictResolution

__all__ = ['CrossEndEvolutionSyncEngine', 'SyncStrategy', 'ConflictResolution']
__version__ = '1.0.0'
