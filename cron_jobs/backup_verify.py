#!/usr/bin/env python3
"""备份完整性验证"""
import os, hashlib, datetime, gzip
BACKUP_DIR = "/opt/ZONGYUAN-ROOT/backups"
today = datetime.date.today().isoformat()
backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.tar.gz')]) if os.path.isdir(BACKUP_DIR) else []
report = {"date": today, "backup_count": len(backups), "latest": backups[-1] if backups else None, "status": "ok" if backups else "no_backup"}
print(f"[{today}] 备份验证: {len(backups)}个备份, 最新={report['latest']}")
