"""客户遥测Agent - 匿名化收集使用数据，驱动体系进化"""
import json, time, hashlib, os, urllib.request
from datetime import datetime

TELEMETRY_DIR = "/opt/ZONGYUAN-ROOT/telemetry"
REPORT_FILE = f"{TELEMETRY_DIR}/daily_report.json"
CENTRAL_API = "https://www.huodouai.com/license/api/v1/telemetry"

def get_machine_id():
    return hashlib.sha256(open("/etc/machine-id").read().encode()).hexdigest()[:16] if os.path.exists("/etc/machine-id") else "unknown"

def collect_metrics():
    """收集匿名化使用指标"""
    metrics = {
        "machine_id": get_machine_id(),
        "timestamp": datetime.now().isoformat(),
        "kernel_version": "v9.10",
        "truth_count": 0,
        "api_calls_24h": 0,
        "truth_hit_rate": 0.0,
        "active_hours": 0,
        "errors_24h": 0,
        "features_used": [],
        "opt_in": os.path.exists(f"{TELEMETRY_DIR}/.opt_in")
    }
    # 读取真值库
    try:
        with open("/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json") as f:
            metrics["truth_count"] = json.load(f).get("truth_count", 0)
    except: pass
    return metrics

def report():
    """生成每日遥测报告"""
    metrics = collect_metrics()
    with open(REPORT_FILE, "w") as f:
        json.dump(metrics, f, indent=2)
    # 如果用户已opt-in，上报到中心
    if metrics["opt_in"]:
        try:
            payload = json.dumps(metrics).encode()
            req = urllib.request.Request(CENTRAL_API, data=payload,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
        except: pass
    return metrics

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "opt-in":
        open(f"{TELEMETRY_DIR}/.opt_in", "w").close()
        print("✅ 已加入遥测计划，数据将匿名化上报")
    elif len(sys.argv) > 1 and sys.argv[1] == "opt-out":
        os.remove(f"{TELEMETRY_DIR}/.opt_in") if os.path.exists(f"{TELEMETRY_DIR}/.opt_in") else None
        print("✅ 已退出遥测计划")
    else:
        result = report()
        print(json.dumps(result, indent=2, ensure_ascii=False))
