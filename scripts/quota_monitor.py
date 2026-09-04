#!/usr/bin/env python3
"""
M1: 配额实时监控与自动降级脚本
监控各类API配额使用率，触发P0-P3告警，自动降级模型等级
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 配额类型定义
QUOTA_TYPES = {
    "text_inference": {"name": "文本推理", "daily_limit": 1000, "warning": 60, "critical": 80, "exhausted": 95},
    "image_generation": {"name": "图像生成", "daily_limit": 50, "warning": 60, "critical": 80, "exhausted": 95},
    "video_generation": {"name": "视频生成", "daily_limit": 10, "warning": 60, "critical": 80, "exhausted": 95},
    "audio_generation": {"name": "音频生成", "daily_limit": 20, "warning": 60, "critical": 80, "exhausted": 95},
    "search_api": {"name": "搜索调用", "daily_limit": 100, "warning": 60, "critical": 80, "exhausted": 95},
    "embedding_api": {"name": "向量检索", "daily_limit": 500, "warning": 60, "critical": 80, "exhausted": 95},
}

class QuotaMonitor:
    def __init__(self):
        self.usage_file = LOG_DIR / "quota_usage.json"
        self.usage = self._load_usage()

    def _load_usage(self):
        if self.usage_file.exists():
            with open(self.usage_file) as f:
                data = json.load(f)
                # 检查是否跨天，跨天重置
                today = datetime.now().strftime("%Y-%m-%d")
                if data.get("date") != today:
                    return self._reset_usage()
                return data
        return self._reset_usage()

    def _reset_usage(self):
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "usage": {k: 0 for k in QUOTA_TYPES},
            "alerts": [],
            "degradation_level": "normal"
        }

    def _save(self):
        with open(self.usage_file, "w") as f:
            json.dump(self.usage, f, ensure_ascii=False, indent=2)

    def record_usage(self, quota_type: str, count: int = 1):
        """记录配额使用"""
        if quota_type in self.usage["usage"]:
            self.usage["usage"][quota_type] += count
            self._check_threshold(quota_type)
            self._save()

    def _check_threshold(self, quota_type: str):
        """检查阈值并触发告警/降级"""
        config = QUOTA_TYPES[quota_type]
        used = self.usage["usage"][quota_type]
        limit = config["daily_limit"]
        percent = (used / limit) * 100

        if percent >= config["exhausted"]:
            level = "P0"
            self.usage["degradation_level"] = "exhausted"
            alert = f"[{level}] {config['name']}配额耗尽({percent:.0f}%)，切换纯本地模式"
        elif percent >= config["critical"]:
            level = "P1"
            self.usage["degradation_level"] = "critical"
            alert = f"[{level}] {config['name']}配额紧张({percent:.0f}%)，仅保留文本+图像fast"
        elif percent >= config["warning"]:
            level = "P2"
            self.usage["degradation_level"] = "warning"
            alert = f"[{level}] {config['name']}配额预警({percent:.0f}%)，关闭Pro模型"
        else:
            return

        self.usage["alerts"].append({
            "time": datetime.now().isoformat(),
            "level": level,
            "type": quota_type,
            "percent": round(percent, 1),
            "message": alert
        })

    def get_status(self) -> dict:
        """获取配额状态"""
        status = {"date": self.usage["date"], "degradation_level": self.usage["degradation_level"], "quotas": {}}
        for qtype, config in QUOTA_TYPES.items():
            used = self.usage["usage"].get(qtype, 0)
            limit = config["daily_limit"]
            percent = (used / limit) * 100
            status["quotas"][qtype] = {
                "name": config["name"],
                "used": used,
                "limit": limit,
                "percent": round(percent, 1),
                "status": "normal" if percent < 60 else "warning" if percent < 80 else "critical"
            }
        status["recent_alerts"] = self.usage["alerts"][-5:]
        return status

    def get_effective_model_tier(self, task_type: str = "general") -> str:
        """根据配额状态获取应使用的模型等级"""
        level = self.usage["degradation_level"]
        if level == "exhausted":
            return "local_only"
        elif level == "critical":
            if task_type in ["video", "audio"]:
                return "disabled"
            return "fast"
        elif level == "warning":
            return "standard"
        else:
            return "pro"  # normal状态可用Pro

    def generate_report(self) -> str:
        """生成配额报告"""
        status = self.get_status()
        lines = [f"📊 配额监控报告 {status['date']}", f"降级等级: {status['degradation_level']}", "=" * 30]
        for qtype, q in status["quotas"].items():
            bar = "█" * int(q["percent"] / 5) + "░" * (20 - int(q["percent"] / 5))
            lines.append(f"{q['name']:8} {bar} {q['percent']:5.1f}% ({q['used']}/{q['limit']})")
        if status["recent_alerts"]:
            lines.append("\n⚠️ 最近告警:")
            for a in status["recent_alerts"]:
                lines.append(f"  {a['message']}")
        return "\n".join(lines)

if __name__ == "__main__":
    monitor = QuotaMonitor()
    # 模拟记录一些使用
    monitor.record_usage("text_inference", 5)
    monitor.record_usage("image_generation", 2)
    print(monitor.generate_report())
    print(f"\n当前有效模型等级: {monitor.get_effective_model_tier('general')}")
