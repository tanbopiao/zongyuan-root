#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 数据湖知识授权平台（EVO-P2-003）

功能：
  1. 基于 ModelScope 数据湖的知识资产管理
  2. 知识授权与计费
  3. 许可证管理
  4. 授权统计报告

使用方式：
  python3 data_lake_license.py             # 同步授权状态并生成报告
  python3 data_lake_license.py --status    # 查看授权状态
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
LICENSE_DIR = EVOLUTION_DIR / "data_lake_license"
LICENSE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LICENSE_DIR / "license.log"
LICENSES_FILE = LICENSE_DIR / "licenses.json"
REPORT_FILE = LICENSE_DIR / "report.json"

SERVICES_DIR = WORKSPACE / "scripts" / "services"
sys.path.insert(0, str(SERVICES_DIR))

DID_TAG = "DID-BR-000002"
ARCHIVE_NODE = "ZONGYUAN-ROOT"

# 授权等级
LICENSE_TIERS = {
    "free": {"name": "免费版", "max_queries": 100, "price": 0, "features": ["基础查询"]},
    "standard": {"name": "标准版", "max_queries": 10000, "price": 299, "features": ["基础查询", "高级检索", "导出"]},
    "enterprise": {"name": "企业版", "max_queries": -1, "price": 9999, "features": ["全部功能", "定制化", "SLA"]},
}


def log(level: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_licenses() -> List[Dict[str, Any]]:
    if LICENSES_FILE.exists():
        return json.loads(LICENSES_FILE.read_text(encoding="utf-8"))
    return []


def save_licenses(licenses: List[Dict[str, Any]]):
    LICENSES_FILE.write_text(json.dumps(licenses, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_data_lake() -> Dict[str, Any]:
    """同步数据湖资产状态。"""
    try:
        from archive_datalake import ARCHIVED_FILES
        archived_count = len(ARCHIVED_FILES) if isinstance(ARCHIVED_FILES, list) else 0
    except Exception:
        archived_count = 0

    # 统计本地真值
    try:
        from autonomous_kernel import AutonomousKernel
        kernel = AutonomousKernel()
        truth_count = kernel.get_stats().get("total", 0)
    except Exception:
        truth_count = 0

    return {
        "archived_files": archived_count,
        "truth_count": truth_count,
        "sync_time": datetime.now().isoformat(),
    }


def check_license_validity(license_data: Dict[str, Any]) -> Dict[str, Any]:
    """检查许可证有效性。"""
    now = datetime.now()
    try:
        expiry = datetime.fromisoformat(license_data.get("expires_at", ""))
        is_expired = now > expiry
    except Exception:
        is_expired = False

    queries_used = license_data.get("queries_used", 0)
    tier = LICENSE_TIERS.get(license_data.get("tier", "free"), {})
    max_queries = tier.get("max_queries", 100)
    quota_exceeded = max_queries > 0 and queries_used >= max_queries

    return {
        "license_id": license_data.get("license_id"),
        "valid": not is_expired and not quota_exceeded,
        "is_expired": is_expired,
        "quota_exceeded": quota_exceeded,
        "remaining_queries": max(0, max_queries - queries_used) if max_queries > 0 else -1,
    }


def main():
    show_status = "--status" in sys.argv

    if show_status:
        if REPORT_FILE.exists():
            print(REPORT_FILE.read_text(encoding="utf-8"))
        else:
            print("暂无授权报告，请先运行同步")
        return 0

    log("INFO", "=" * 50)
    log("INFO", "数据湖授权平台引擎启动 (EVO-P2-003)")
    log("INFO", "=" * 50)

    # 1. 同步数据湖
    lake_status = sync_data_lake()
    log("INFO", f"数据湖同步: {lake_status['archived_files']} 个归档文件, {lake_status['truth_count']} 条真值")

    # 2. 加载许可证
    licenses = load_licenses()

    # 3. 检查每个许可证有效性
    checks = []
    for lic in licenses:
        check = check_license_validity(lic)
        checks.append(check)

    valid_count = sum(1 for c in checks if c["valid"])
    log("INFO", f"许可证状态: {valid_count}/{len(licenses)} 有效")

    # 4. 生成报告
    revenue = sum(
        LICENSE_TIERS.get(l.get("tier", "free"), {}).get("price", 0)
        for l in licenses
        if check_license_validity(l)["valid"]
    )

    report = {
        "generated_at": datetime.now().isoformat(),
        "did_tag": DID_TAG,
        "data_lake": lake_status,
        "total_licenses": len(licenses),
        "valid_licenses": valid_count,
        "monthly_revenue": revenue,
        "license_checks": checks,
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log("INFO", f"授权报告已保存: {REPORT_FILE}")
    log("INFO", f"有效许可证: {valid_count}/{len(licenses)}, 月度收入: ¥{revenue}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(0)
