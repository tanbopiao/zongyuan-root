#!/usr/bin/env python3
"""
P1-8: 备份与灾难恢复脚本
定期备份ZONGYUAN-ROOT到本地备份目录，支持恢复
"""
import json
import hashlib
import shutil
import tarfile
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
BACKUP_DIR = ROOT / "backups"
MAX_BACKUPS = 7

def create_backup() -> dict:
    """创建全量备份"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"zongyuan_root_backup_{timestamp}.tar.gz"
    
    # 计算备份前哈希
    assets = []
    for fp in ROOT.rglob("*"):
        if fp.is_file() and "cache" not in str(fp) and "backups" not in str(fp):
            h = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            assets.append({"path": str(fp.relative_to(ROOT)), "sha256": h.hexdigest()})
    
    # 创建tar.gz
    with tarfile.open(backup_file, "w:gz") as tar:
        for fp in ROOT.rglob("*"):
            if fp.is_file() and "cache" not in str(fp) and "backups" not in str(fp):
                tar.add(fp, arcname=str(fp.relative_to(ROOT)))
    
    # 备份元数据
    meta = {
        "backup_id": f"BK-{timestamp}",
        "created_at": datetime.now().isoformat(),
        "asset_count": len(assets),
        "backup_file": backup_file.name,
        "backup_size": backup_file.stat().st_size,
        "merkle_root": hashlib.sha256("".join(sorted(a["sha256"] for a in assets)).encode()).hexdigest(),
        "assets": assets
    }
    meta_file = BACKUP_DIR / f"zongyuan_root_backup_{timestamp}_meta.json"
    with open(meta_file, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    # 清理旧备份
    backups = sorted(BACKUP_DIR.glob("*.tar.gz"))
    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        old.unlink()
        old_meta = BACKUP_DIR / (old.stem.replace(".tar", "") + "_meta.json")
        if old_meta.exists():
            old_meta.unlink()
    
    return {"status": "success", "backup_file": backup_file.name, "asset_count": len(assets), "size_mb": round(backup_file.stat().st_size / 1024 / 1024, 2)}

def list_backups() -> list:
    """列出所有备份"""
    BACKUP_DIR.mkdir(exist_ok=True)
    backups = []
    for meta_file in sorted(BACKUP_DIR.glob("*_meta.json")):
        with open(meta_file) as f:
            meta = json.load(f)
        backups.append({
            "backup_id": meta["backup_id"],
            "created_at": meta["created_at"],
            "asset_count": meta["asset_count"],
            "size_mb": round(meta.get("backup_size", 0) / 1024 / 1024, 2)
        })
    return backups

def restore_backup(backup_id: str) -> dict:
    """从备份恢复"""
    meta_file = BACKUP_DIR / f"{backup_id.replace('BK-', 'zongyuan_root_backup_')}_meta.json"
    if not meta_file.exists():
        # 尝试模糊匹配
        for f in BACKUP_DIR.glob("*_meta.json"):
            with open(f) as mf:
                if json.load(mf).get("backup_id") == backup_id:
                    meta_file = f
                    break
    if not meta_file.exists():
        return {"status": "error", "message": f"备份不存在: {backup_id}"}
    
    with open(meta_file) as f:
        meta = json.load(f)
    
    backup_file = BACKUP_DIR / meta["backup_file"]
    if not backup_file.exists():
        return {"status": "error", "message": f"备份文件不存在: {backup_file}"}
    
    # 恢复到临时目录验证
    restore_dir = ROOT / "cache" / "restore_temp"
    if restore_dir.exists():
        shutil.rmtree(restore_dir)
    restore_dir.mkdir(parents=True)
    
    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(restore_dir)
    
    return {"status": "restored_to_temp", "restore_dir": str(restore_dir), "asset_count": meta["asset_count"], "warning": "已恢复到临时目录，确认后请手动替换ROOT"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "create":
            print(json.dumps(create_backup(), ensure_ascii=False, indent=2))
        elif sys.argv[1] == "list":
            print(json.dumps(list_backups(), ensure_ascii=False, indent=2))
        elif sys.argv[1] == "restore" and len(sys.argv) > 2:
            print(json.dumps(restore_backup(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(list_backups(), ensure_ascii=False, indent=2))
