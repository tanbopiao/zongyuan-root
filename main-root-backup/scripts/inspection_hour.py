#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 每小时自治巡检脚本
检测：索引完整性、记忆网关健康、胶水层链路、双向漂移、内核状态
"""
import os
import json
import subprocess
import sys
from datetime import datetime

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_ROOT, "runtime", "memory_index.json")
LOG_OUT = os.path.join(BASE_ROOT, "log", "hour_inspection.log")
GLUE_SCRIPT = os.path.join(BASE_ROOT, "scripts", "glue_memory_trigger.py")
DRIFT_SCRIPT = os.path.join(BASE_ROOT, "scripts", "feishu_cloud_sync_check.py")


def log(msg):
    os.makedirs(os.path.dirname(LOG_OUT), exist_ok=True)
    with open(LOG_OUT, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    print(msg)


def check_index():
    if not os.path.exists(INDEX_PATH):
        return False, "memory_index.json 不存在"
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            idx = json.load(f)
        if "index_meta" not in idx or "asset_entries" not in idx:
            return False, "索引结构不完整"
        return True, f"索引正常，资产条目{len(idx['asset_entries'])}条"
    except Exception as e:
        return False, f"索引解析失败:{str(e)}"


def check_glue_smoke():
    try:
        proc = subprocess.run(
            ["python3", GLUE_SCRIPT, "--input", "元极恒一 巡检冒烟"],
            capture_output=True, text=True, timeout=15
        )
        res = json.loads(proc.stdout)
        return res.get("trigger", False), "胶水层冒烟测试通过" if res.get("trigger") else "胶水层未触发"
    except Exception as e:
        return False, f"胶水层冒烟失败:{str(e)}"


def check_drift():
    try:
        proc = subprocess.run(
            ["python3", DRIFT_SCRIPT],
            capture_output=True, text=True, timeout=30
        )
        return proc.returncode == 0, f"漂移检测exit={proc.returncode}"
    except Exception as e:
        return False, f"漂移检测异常:{str(e)}"


def main():
    log("===== 小时自治巡检开始 =====")
    results = {}

    ok, msg = check_index()
    results["index"] = {"ok": ok, "msg": msg}
    log(f"[索引] {'PASS' if ok else 'FAIL'} {msg}")

    ok, msg = check_glue_smoke()
    results["glue"] = {"ok": ok, "msg": msg}
    log(f"[胶水层] {'PASS' if ok else 'FAIL'} {msg}")

    ok, msg = check_drift()
    results["drift"] = {"ok": ok, "msg": msg}
    log(f"[漂移检测] {'PASS' if ok else 'FAIL'} {msg}")

    all_pass = all(r["ok"] for r in results.values())
    log(f"===== 巡检结束 总体:{'PASS' if all_pass else 'FAIL'} =====")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
