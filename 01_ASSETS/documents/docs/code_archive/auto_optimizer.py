#!/usr/bin/env python3
"""自我优化引擎：基于运行数据自动调整参数"""
import json
import os
from datetime import datetime
from collections import Counter

OUTPUT_DIR = "/home/user/Doubao/chats/38439832899843586/auto_optimization"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 读取自动化运行日志
log_dir = "/home/user/Doubao/chats/38439832899843586/auto_logs"
logs = []
if os.path.exists(log_dir):
    for f in os.listdir(log_dir):
        if f.endswith('.log'):
            with open(os.path.join(log_dir, f)) as fh:
                logs.append(fh.read())

# 分析运行数据
anomalies = []
success_count = 0
fail_count = 0
task_times = []

for log in logs:
    if '异常' in log or '告警' in log or '失败' in log:
        anomalies.append(log[:100])
    if '完成' in log:
        success_count += 1
    if '失败' in log:
        fail_count += 1

# 基于数据生成优化参数
optimization = {
    "optimization_id": "OPT-" + datetime.now().strftime("%Y%m%d_%H%M%S"),
    "based_on_data": {
        "total_logs": len(logs),
        "success_count": success_count,
        "fail_count": fail_count,
        "anomaly_count": len(anomalies),
        "success_rate": success_count / (success_count + fail_count) if (success_count + fail_count) > 0 else 1.0
    },
    "auto_adjusted_params": {
        "monitor_interval_seconds": 300 if len(anomalies) == 0 else 120,
        "heartbeat_interval_seconds": 300 if len(anomalies) == 0 else 180,
        "sync_batch_size": 50 if success_count > 10 else 20,
        "max_retry_count": 3 if fail_count == 0 else 5,
        "timeout_seconds": 10 if len(anomalies) == 0 else 15,
        "alert_threshold": 1 if len(anomalies) > 0 else 3
    },
    "optimization_recommendations": [
        {"param": "monitor_interval", "current": 300, "recommended": 120 if anomalies else 300, "reason": "检测到异常时缩短监控间隔"},
        {"param": "max_retry", "current": 3, "recommended": 5 if fail_count > 0 else 3, "reason": "失败率高时增加重试次数"},
        {"param": "alert_threshold", "current": 3, "recommended": 1 if anomalies else 3, "reason": "异常频繁时降低告警阈值"}
    ],
    "applied": False,
    "note": "参数基于实际运行数据分析自动调整，可通过apply命令应用"
}

with open(os.path.join(OUTPUT_DIR, "optimization_params.json"), 'w') as f:
    json.dump(optimization, f, indent=2, ensure_ascii=False)

print("✅ 自我优化参数调整完成")
print(f"  分析日志数: {len(logs)}")
print(f"  成功率: {optimization['based_on_data']['success_rate']:.2%}")
print(f"  异常数: {len(anomalies)}")
print()
print("【自动调整的参数】")
for k, v in optimization['auto_adjusted_params'].items():
    print(f"  {k}: {v}")
