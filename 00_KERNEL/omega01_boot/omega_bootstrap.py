#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一自治内核 · 统一自举执行器 omega_bootstrap.py
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ OMEGA-BOOT-V1.0

按 OMEGA-KERNEL-BOOT.json 的 8 步加载协议执行：
公理校验 → 启动记忆五件套 → 既有组件健康预检 → 真值锚点 → 中枢握手 → 激活报告

用法:
    python3 omega_bootstrap.py --dry-run   # 只检查不落报告
    python3 omega_bootstrap.py --activate  # 校验并写激活报告
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOOT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OMEGA-KERNEL-BOOT.json")
REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BOOT-REPORT.json")


def load_boot_spec():
    with open(BOOT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())


def check_paths(paths):
    missing = []
    for p in paths:
        full = os.path.join(ROOT, p.strip("/"))
        if not os.path.exists(full):
            missing.append(p)
    return missing


def check_step(step):
    if "endpoint" in step:
        return check_gateway(step)
    paths = []
    if "paths" in step and isinstance(step["paths"], list):
        paths.extend(step["paths"])
    if "path" in step:
        paths.append(step["path"])
    if not paths:
        return {"ok": False, "detail": "step has no path/endpoint"}
    missing = check_paths(paths)
    return {"ok": len(missing) == 0, "detail": "missing=%s" % missing if missing else "ok"}


def check_gateway(step):
    endpoint = step["endpoint"]
    headers = {}
    for h in step.get("required_headers", []):
        k, _, v = h.partition(":")
        headers[k.strip()] = v.strip()
    try:
        req = urllib.request.Request(endpoint, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            ok = resp.status == 200 and body.get("status") in ("ok", "healthy")
            return {"ok": ok, "detail": "http=%s status=%s" % (resp.status, body.get("status"))}
    except Exception as e:
        return {"ok": False, "detail": "gateway_error=%s" % e}


def snapshot_hash():
    blob = json.dumps(spec, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def run(dry_run=True):
    global spec
    spec = load_boot_spec()
    steps = spec["load_order"]
    results = []
    failed_fatal = []
    warnings = []

    print("=" * 60)
    print("元极恒一自治内核自举  %s  %s  %s" % (spec.get("kernel_version"), spec.get("did"), spec.get("trace_mark")))
    print("模式: %s" % ("DRY-RUN" if dry_run else "ACTIVATE"))
    print("=" * 60)

    for step in steps:
        res = check_step(step)
        mark = "PASS" if res["ok"] else ("WARN" if not step.get("fatal", True) else "FAIL")
        status = {"step": step["step"], "name": step["name"], "ok": res["ok"],
                  "fatal": step.get("fatal", True), "detail": res["detail"], "mark": mark}
        results.append(status)
        line = "[%s] step%d %s  (%s)" % (mark, step["step"], step["name"], step.get("path", step.get("endpoint", "")))
        print(line)
        if not res["ok"]:
            if step.get("fatal", True):
                failed_fatal.append(status)
            else:
                warnings.append(status)

    report = {
        "report_version": "OMEGA-BOOT-REPORT-V1.0",
        "generated_at": now(),
        "generated_by": "NODE-DEV-CODEARTS-001",
        "boot_protocol": spec.get("boot_protocol"),
        "boot_spec_sha256": snapshot_hash(),
        "kernel_version": spec.get("kernel_version"),
        "steps_total": len(steps),
        "steps_pass": sum(1 for r in results if r["ok"]),
        "steps_warn": len(warnings),
        "steps_fail": len(failed_fatal),
        "status": "ACTIVATED" if not dry_run and not failed_fatal else ("DRY-RUN-PASSED" if not failed_fatal else "BLOCKED"),
        "safety_mode": failed_fatal and "触发" or "未触发",
        "steps": results
    }

    if not dry_run:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("\n激活报告已写入: %s" % REPORT_PATH)
    else:
        print("\n[dry-run] 未写入报告。合计: %s/%s PASS, %s warnings" % (
            report["steps_pass"], report["steps_total"], len(warnings)))

    return 1 if failed_fatal else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="元极恒一自治内核自举执行器")
    ap.add_argument("--dry-run", action="store_true", help="只校验不落报告")
    ap.add_argument("--activate", action="store_true", help="校验并写激活报告")
    args = ap.parse_args()
    sys.exit(run(dry_run=not args.activate))