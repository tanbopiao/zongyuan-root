#!/usr/bin/env python3
"""V2.6.0 20并发稳定压测"""
import urllib.request, json, time
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:8021"
ENDPOINTS = [
    ("/v2/status", "POST", {}),
    ("/operator/hub/stats", "POST", {}),
    ("/operator/hub/analytics", "POST", {}),
    ("/optimization/check", "POST", {}),
    ("/optimization/compare", "POST", {}),
    ("/drama/works/trending", "POST", {}),
    ("/drama/works/list", "POST", {"device_id": "stress_20"}),
]

def test_endpoint(ep):
    path, method, data = ep
    start = time.time()
    try:
        req = urllib.request.Request(BASE + path,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
        elapsed = (time.time() - start) * 1000
        return {"success": status == 200, "time_ms": round(elapsed, 1)}
    except Exception as e:
        return {"success": False, "time_ms": 0, "error": str(e)[:50]}

def run_stress(workers=20, rounds=5):
    print("20并发稳定压测: %d并发 x %d轮" % (workers, rounds))
    all_results = []
    for round_num in range(rounds):
        start = time.time()
        tasks = ENDPOINTS * (workers // len(ENDPOINTS) + 1)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(test_endpoint, tasks))
        elapsed = time.time() - start
        success = sum(1 for r in results if r["success"])
        avg_time = sum(r["time_ms"] for r in results if r["success"]) / max(1, success)
        print("  第%d轮: %d/%d成功, 平均%.1fms, 耗时%.2fs" % (round_num+1, success, len(results), avg_time, elapsed))
        all_results.extend(results)
    total = len(all_results)
    success = sum(1 for r in all_results if r["success"])
    avg_time = sum(r["time_ms"] for r in all_results if r["success"]) / max(1, success)
    max_time = max((r["time_ms"] for r in all_results if r["success"]), default=0)
    rate = round(success/total*100, 1)
    print("\n汇总: %d请求, %d成功(%.1f%%), 平均%.1fms, 最大%.1fms" % (total, success, rate, avg_time, max_time))
    print("稳态判定: %s" % ("PASS" if rate >= 95 else "FAIL"))
    return {"total": total, "success": success, "rate": rate, "avg_ms": round(avg_time, 1), "max_ms": round(max_time, 1)}

if __name__ == "__main__":
    run_stress(workers=20, rounds=5)
