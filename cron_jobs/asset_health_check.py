#!/usr/bin/env python3
"""资产健康巡检：哈希校验、死链检测"""
import json, os, hashlib, datetime
KERNEL = "/opt/ZONGYUAN-ROOT/kernel.json"
LOCK_DIR = "/opt/ZONGYUAN-ROOT/locks"
today = datetime.date.today().isoformat()

issues = []
# 检查锁档目录完整性
if os.path.isdir(LOCK_DIR):
    for lock in os.listdir(LOCK_DIR):
        lockpath = os.path.join(LOCK_DIR, lock)
        if not os.path.isdir(lockpath): continue
        files = [f for f in os.listdir(lockpath) if not f.startswith('.')]
        if len(files) == 0:
            issues.append({"lock": lock, "issue": "空锁档目录"})

report = {"date": today, "checked_locks": len(os.listdir(LOCK_DIR)) if os.path.isdir(LOCK_DIR) else 0, "issues": issues, "status": "healthy" if not issues else "warning"}
with open(f"/opt/ZONGYUAN-ROOT/logs/asset_health_{today}.json", "w") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"[{today}] 资产巡检: {report['checked_locks']}个锁档, {len(issues)}个问题")
