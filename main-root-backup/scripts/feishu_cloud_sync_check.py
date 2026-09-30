#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 飞书-云服务器双向漂移检测
对比飞书Base快照元数据 和 本地工程目录资产
exit 0=无漂移；exit 1=发现致命漂移
"""
import os
import json
import hashlib
import sys
from datetime import datetime

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_LOCAL = os.path.join(BASE_ROOT, "lock_archive", "asset_manifest.json")
AUDIT_OUTPUT = os.path.join(BASE_ROOT, "log", "sync_drift_audit.json")
IGNORE_DIRS = {"_trash_legacy_backup", "runtime", "log", ".terraform", "__pycache__"}

errors = []
warnings = []


def calc_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_local_manifest():
    if not os.path.exists(MANIFEST_LOCAL):
        errors.append(f"本地manifest不存在 {MANIFEST_LOCAL}，无法执行双向比对")
        return None
    with open(MANIFEST_LOCAL, "r", encoding="utf-8") as f:
        return json.load(f)


def scan_local_files(root_path):
    asset_dict = {}
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for name in files:
            fullpath = os.path.join(root, name)
            rel_path = os.path.relpath(fullpath, root_path)
            try:
                sha = calc_sha256(fullpath)
                asset_dict[rel_path] = sha
            except Exception as e:
                warnings.append(f"文件读取失败 {rel_path}:{str(e)}")
    return asset_dict


def main():
    print("==== 飞书-云服务器双向漂移检测开始 ====")
    local_manifest = load_local_manifest()
    if local_manifest is None:
        ret_code = 1
    else:
        local_assets = scan_local_files(BASE_ROOT)
        manifest_assets = local_manifest.get("asset_items", {})

        for rel in local_assets:
            if rel not in manifest_assets:
                warnings.append(f"【本地新增未归档】{rel}")
        for rel in manifest_assets:
            if rel not in local_assets:
                errors.append(f"【致命-本地资产缺失】{rel}")
            else:
                hash_manifest = manifest_assets[rel]["sha256"]
                hash_real = local_assets[rel]
                if hash_manifest != hash_real:
                    errors.append(f"【致命-文件篡改】{rel} 基线hash:{hash_manifest} 实际hash:{hash_real}")

        ret_code = 1 if len(errors) > 0 else 0

    audit_report = {
        "check_time": datetime.now().isoformat(),
        "DID": "DID-BR-000002",
        "sovereign_root": "Ω-TAN-7-001",
        "errors": errors,
        "warnings": warnings,
        "drift_detected": len(errors) > 0
    }
    os.makedirs(os.path.dirname(AUDIT_OUTPUT), exist_ok=True)
    with open(AUDIT_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, ensure_ascii=False, indent=2)

    print(f"审计报告输出:{AUDIT_OUTPUT}")
    if warnings:
        for w in warnings:
            print(f"[WARN] {w}")
    if errors:
        print("[FATAL] 检测到致命双向漂移，禁止执行全域锁档")
        for e in errors:
            print(f"[FATAL] {e}")
    else:
        print("[OK]双向资产比对校验通过")

    sys.exit(ret_code)


if __name__ == "__main__":
    main()
