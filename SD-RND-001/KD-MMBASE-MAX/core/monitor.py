import sys; sys.path.insert(0, "/opt/ZONGYUAN-ROOT"); from core.truth_loader import truth_loader
"""MM-MONITOR 监控巡检引擎 · 心跳+指标+健康检查"""
import time
from typing import Dict, Any, List

class MonitorEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.events: List[Dict] = []
        self.metrics = {"total_tasks": 0, "success": 0, "failed": 0, "drift_detected": 0}

    def log(self, event: str, details: Dict[str, Any] = None) -> None:
        self.events.append({"event": event, "details": details or {}, "timestamp": time.time()})
        if event == "task_submit":
            self.metrics["total_tasks"] += 1

    def summary(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics,
            "recent_events": self.events[-10:],
            "uptime_events": len(self.events),
        }
