#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目准入校验器 · 对应 META-LAW-ENG-001 边界前置准入 / AGENT-PREREQ-001 任务准入边界

provenance: reconstructed from "ZONGYUAN-ROOT 全量记忆激活配置 v1.0-20261017" 第4.2节
            （原始终端全网0命中，按权威描述重建）

功能：对一次交付/任务做准入校验 —— 合规通过则 PASS，缺项则 BLOCK 并列出缺失原因。
用法：python3 project_gate_check.py --manifest manifest.json
      python3 project_gate_check.py --name X --path Y --acceptance acceptance_metrics_template.json
"""
import argparse
import json
import os
import sys

# 准入必备项（缺一即 BLOCK）—— 对齐 META-LAW-ENG-001/002/003/005
REQUIRED = ["name", "path", "type", "meta_class", "acceptance", "risk_level"]


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check(manifest):
    missing = [k for k in REQUIRED if k not in manifest or manifest[k] in (None, "", [])]
    errs = []
    if "path" in manifest and not os.path.exists(manifest["path"]):
        errs.append(f"path_not_found: {manifest['path']}")
    risk = str(manifest.get("risk_level", "")).upper()
    if risk and risk not in ("P0", "P1", "P2", "P3"):
        errs.append(f"invalid_risk_level: {risk}")
    if risk in ("P0", "P1"):
        errs.append(f"hard_isolation_required: {risk} 需人工放行（META-LAW-ENG-003）")
    acc = manifest.get("acceptance")
    if isinstance(acc, dict) and not acc.get("metrics"):
        errs.append("acceptance_metrics_empty: 无量化指标视为未验收（META-LAW-ENG-002）")
    return missing, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest")
    ap.add_argument("--name")
    ap.add_argument("--path")
    ap.add_argument("--acceptance")
    a = ap.parse_args()
    if a.manifest:
        m = load_json(a.manifest)
    else:
        m = {"name": a.name, "path": a.path}
        if a.acceptance and os.path.exists(a.acceptance):
            m["acceptance"] = load_json(a.acceptance)
    missing, errs = check(m)
    if not missing and not errs:
        print("GATE: PASS · 合规通过")
        return 0
    print("GATE: BLOCK · 准入被拦截")
    for k in missing:
        print(f"  - missing_field: {k}")
    for e in errs:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
