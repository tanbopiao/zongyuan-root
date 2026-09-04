#!/usr/bin/env python3
"""
P1-9: 配额监控增强版
真实追踪API调用配额，自动降级
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
QUOTA_FILE = ROOT / "logs" / "quota_usage.json"

DEFAULT_QUOTA = {
    "daily_limit": 100,
    "used_today": 0,
    "last_reset": datetime.now().strftime("%Y-%m-%d"),
    "history": [],
    "api_calls": []
}

def _load():
    if QUOTA_FILE.exists():
        with open(QUOTA_FILE) as f:
            return json.load(f)
    return DEFAULT_QUOTA.copy()

def _save(data):
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _check_reset(data):
    today = datetime.now().strftime("%Y-%m-%d")
    if data["last_reset"] != today:
        data["history"].append({"date": data["last_reset"], "used": data["used_today"]})
        if len(data["history"]) > 30:
            data["history"] = data["history"][-30:]
        data["used_today"] = 0
        data["last_reset"] = today
    return data

def record_api_call(api_name: str, tokens_used: int = 0, cost: float = 0):
    """记录一次API调用"""
    data = _check_reset(_load())
    data["used_today"] += 1
    data["api_calls"].append({
        "time": datetime.now().isoformat(),
        "api": api_name,
        "tokens": tokens_used,
        "cost": cost
    })
    if len(data["api_calls"]) > 500:
        data["api_calls"] = data["api_calls"][-500:]
    _save(data)
    return get_status()

def get_status() -> dict:
    """获取配额状态"""
    data = _check_reset(_load())
    remaining = data["daily_limit"] - data["used_today"]
    usage_rate = data["used_today"] / data["daily_limit"] if data["daily_limit"] > 0 else 0
    level = "normal" if usage_rate < 0.7 else ("warning" if usage_rate < 0.9 else "critical")
    return {
        "daily_limit": data["daily_limit"],
        "used_today": data["used_today"],
        "remaining": remaining,
        "usage_rate": f"{usage_rate:.1%}",
        "level": level,
        "should_degrade": usage_rate >= 0.9,
        "last_reset": data["last_reset"],
        "total_calls_recorded": len(data["api_calls"])
    }

def get_weekly_usage() -> list:
    """获取近7天使用量"""
    data = _load()
    return data["history"][-7:]

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "record" and len(sys.argv) > 2:
            print(json.dumps(record_api_call(sys.argv[2]), ensure_ascii=False, indent=2))
        elif sys.argv[1] == "status":
            print(json.dumps(get_status(), ensure_ascii=False, indent=2))
        elif sys.argv[1] == "weekly":
            print(json.dumps(get_weekly_usage(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(get_status(), ensure_ascii=False, indent=2))
