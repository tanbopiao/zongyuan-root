#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 本地独有真值推送云端引擎

将本地根内核中云端缺失的真值推送到云端中枢，实现双向同步。
策略：遍历本地真值，通过 key 检查云端是否已有，缺失则推送。
"""
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# ============ 配置 ============
HUB = "https://www.huodouai.com"
TRUTH_API = f"{HUB}/api/truth"
REPORT_API = f"{HUB}/api/report/truth"
DID = "DID-BR-000002"
LIMIT = 200
ALL_TRUTHS_FILE = Path("/workspace/persistence_root/all_truths.json")
LOG_FILE = Path("/workspace/evolution/kernel_comparison/push_cloud.log")
REPORT_DIR = Path("/workspace/evolution/kernel_comparison")
PUSH_REPORT = REPORT_DIR / "push_report.json"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch_cloud_keys():
    """从云端获取所有已有 key 集合"""
    import re
    import string

    cloud_keys = set()
    prefixes_tried = set()

    # 按前缀系统拉取，只收集 key
    chars = list(string.ascii_uppercase) + list(string.ascii_lowercase) + list(string.digits)
    for ch in chars:
        url = f"{TRUTH_API}?limit={LIMIT}&key={ch}"
        try:
            r = subprocess.run(["/usr/bin/curl", "-s", url, "-H", f"X-DID: {DID}", "--max-time", "30"],
                               capture_output=True, text=True, timeout=35)
            results = json.loads(r.stdout).get("results", [])
            for t in results:
                cloud_keys.add(t["key"])
        except:
            pass

    # 也尝试已知前缀
    known = ["REPORT", "TRUTH", "NODE", "SFMP", "kernel", "cloud", "META", "seed",
             "ARB", "DID", "AI", "HEARTBEAT", "TEST", "truth-", "node", "meta"]
    for p in known:
        url = f"{TRUTH_API}?limit={LIMIT}&key={p}"
        try:
            r = subprocess.run(["/usr/bin/curl", "-s", url, "-H", f"X-DID: {DID}", "--max-time", "30"],
                               capture_output=True, text=True, timeout=35)
            results = json.loads(r.stdout).get("results", [])
            for t in results:
                cloud_keys.add(t["key"])
        except:
            pass

    return cloud_keys


def push_truth(truth):
    """推送单条真值到云端"""
    key = truth.get("key", "")
    value = truth.get("value", {})
    ts = truth.get("ts", "")

    payload = {
        "truth_id": f"HZ-KERNEL-SYNC-{truth.get('seq', '000')}",
        "name": f"本地内核真值同步",
        "content": f"seq={truth.get('seq')}, key={key[:40]}",
        "source": "local_root_kernel_sync",
        "risk_level": "低风险",
        "key": key,
        "value": value if isinstance(value, dict) else {"content": str(value)},
    }
    if ts:
        payload["ts"] = ts

    try:
        r = subprocess.run(
            ["/usr/bin/curl", "-s", "-X", "POST", REPORT_API,
             "-H", "Content-Type: application/json",
             "-H", f"X-DID: {DID}",
             "-d", json.dumps(payload, ensure_ascii=False),
             "--max-time", "15"],
            capture_output=True, text=True, timeout=20
        )
        resp = json.loads(r.stdout)
        return resp.get("ok", False), resp
    except Exception as e:
        return False, {"error": str(e)}


def main():
    log("=" * 60)
    log("本地独有真值推送云端引擎启动")
    log("=" * 60)

    # 1. 加载本地真值
    truths = json.loads(ALL_TRUTHS_FILE.read_text(encoding="utf-8"))
    local_keys = {t["key"] for t in truths}
    log(f"本地真值: {len(truths)} 条, {len(local_keys)} 个唯一 key")

    # 2. 获取云端已有 key
    log("获取云端已有 key 集合...")
    cloud_keys = fetch_cloud_keys()
    log(f"云端已有 key: {len(cloud_keys)} 个")

    # 3. 找出本地独有（云端缺失）的真值
    local_only_keys = local_keys - cloud_keys
    local_only_truths = [t for t in truths if t["key"] in local_only_keys]
    log(f"本地独有真值: {len(local_only_truths)} 条需要推送")

    if not local_only_truths:
        log("无需推送，本地与云端已完全同步")
        return 0

    # 4. 批量推送（限制每秒不超过 2 次避免压垮云端）
    pushed = 0
    failed = 0
    errors = []

    for i, t in enumerate(local_only_truths):
        ok, resp = push_truth(t)
        if ok:
            pushed += 1
        else:
            failed += 1
            if len(errors) < 10:
                errors.append({"key": t["key"][:50], "error": str(resp.get("error", resp))[:100]})

        if (i + 1) % 50 == 0:
            log(f"  进度: {i+1}/{len(local_only_truths)}, 推送={pushed}, 失败={failed}")

        # 限速：每 2 条暂停 0.3 秒
        if (i + 1) % 2 == 0:
            time.sleep(0.3)

    log(f"推送完成: 成功={pushed}, 失败={failed}, 总计={len(local_only_truths)}")

    # 5. 验证云端新总数
    try:
        r = subprocess.run(
            ["/usr/bin/curl", "-s", f"{HUB}/api/status", "-H", f"X-DID: {DID}", "--max-time", "10"],
            capture_output=True, text=True, timeout=15
        )
        hub = json.loads(r.stdout)
        cloud_after = hub.get("truth_count", 0)
    except:
        cloud_after = 0

    log(f"推送后云端真值总数: {cloud_after}")

    # 6. 保存报告
    report = {
        "push_time": datetime.now().isoformat(),
        "local_truths": len(truths),
        "local_only": len(local_only_truths),
        "pushed": pushed,
        "failed": failed,
        "cloud_before": len(cloud_keys),
        "cloud_after": cloud_after,
        "errors_sample": errors,
    }
    PUSH_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"报告已保存: {PUSH_REPORT}")
    log("=" * 60)
    return pushed


if __name__ == "__main__":
    main()
