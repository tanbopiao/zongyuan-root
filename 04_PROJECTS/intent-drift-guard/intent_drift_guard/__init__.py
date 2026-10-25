"""
intent_drift_guard —— AI Agent 意图漂移防控算子套件 (v1.0)

四层阈值防线 + 三级熔断打断, 插件/中间件形态低侵入挂载。

五大算子:
    1. anchor      目标结构化锚定算子 (只读锁档 / 对齐校验)
    2. semantic    语义漂移监测算子 (BGE-m3 / 距离>0.3 / 20步上限)
    3. behavior    行为风控监测算子 (死循环3次 / 资源 / 上下文90%)
    4. collab      跨Agent协同校验算子 (父子相似度<0.6 拦截)
    5. breaker     三级熔断自愈调度算子 (预警-限制-终止)

对外唯一入口: middleware.IntentDriftGuard
"""

__version__ = "1.0.0"

from .middleware import IntentDriftGuard  # noqa: F401
from .config import ThresholdConfig  # noqa: F401

__all__ = ["IntentDriftGuard", "ThresholdConfig", "__version__"]
