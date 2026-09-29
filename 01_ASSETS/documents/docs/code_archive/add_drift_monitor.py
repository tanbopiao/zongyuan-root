#!/usr/bin/env python3
"""添加认知漂移监控到ai_proxy"""
import re

AI_PROXY = "/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py"

with open(AI_PROXY, encoding="utf-8") as f:
    c = f.read()

if "DRIFT_METRICS" not in c:
    monitor_code = '''

# ========== 认知漂移监控（MR-DRIFT-001） ==========
DRIFT_METRICS = {"total": 0, "errors": 0, "sec_total": 0, "sec_errors": 0, "start": __import__("time").time()}
def _drift_hit(sec=False, err=False):
    DRIFT_METRICS["total"] += 1
    if sec: DRIFT_METRICS["sec_total"] += 1
    if err:
        DRIFT_METRICS["errors"] += 1
        if sec: DRIFT_METRICS["sec_errors"] += 1
def get_drift_metrics():
    import time as _t
    elapsed = _t.time() - DRIFT_METRICS["start"]
    err_rate = DRIFT_METRICS["errors"] / max(DRIFT_METRICS["total"], 1) * 100
    sec_err_rate = DRIFT_METRICS["sec_errors"] / max(DRIFT_METRICS["sec_total"], 1) * 100
    return {
        "total_requests": DRIFT_METRICS["total"],
        "error_rate": round(err_rate, 2),
        "sec_tower_requests": DRIFT_METRICS["sec_total"],
        "sec_tower_error_rate": round(sec_err_rate, 2),
        "uptime_seconds": int(elapsed),
        "drift_level": "critical" if err_rate > 20 else "warning" if err_rate > 5 else "healthy"
    }
'''
    c += monitor_code
    print("✅ 漂移监控代码已添加")
else:
    print("⚠️ 漂移监控已存在，跳过")

# 在/status端点返回漂移指标
if '"status": "ok"' in c and "get_drift_metrics" in c:
    c = c.replace('"status": "ok"', '"status": "ok", "drift_metrics": get_drift_metrics()')
    print("✅ /status端点集成漂移监控")

with open(AI_PROXY, "w", encoding="utf-8") as f:
    f.write(c)

print(f"✅ 完成，文件大小: {len(c)} 字节")
