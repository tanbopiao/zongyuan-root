#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 全域成果自动备份脚本
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
每日凌晨3点自动执行，保留最近7天备份
"""
import os
import shutil
import sqlite3
import json
import time
from datetime import datetime, timedelta

# 配置
BACKUP_DIR = "/opt/ZONGYUAN-ROOT/backups/daily"
RETENTION_DAYS = 7

# 需要备份的文件列表
FILES_TO_BACKUP = [
    # 真值库
    "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    # 知识图谱
    "/opt/ZONGYUAN-ROOT/knowledge_graph/kg_graph.json",
    # 控制台数据
    "/opt/ZONGYUAN-ROOT/data/console_history.json",
    "/opt/ZONGYUAN-ROOT/data/console_alerts.json",
    # 算子状态
    "/opt/ZONGYUAN-ROOT/data/operator_scheduler_state.json",
    # 元法则
    "/opt/ZONGYUAN-ROOT/data/meta_rules.json",
    # 部署验证日志
    "/opt/ZONGYUAN-ROOT/data/deployment_verification_log.json",
    # 内核状态
    "/opt/ZONGYUAN-ROOT/kernel/kernel_state.json",
    # M9账本
    "/opt/ZONGYUAN-ROOT/M9_global_ledger.json",
]

# 需要备份的目录（关键代码）
DIRS_TO_BACKUP = [
    "/opt/ZONGYUAN-ROOT/ai-native-ops",
    "/opt/ZONGYUAN-ROOT/scripts",
]

def get_backup_path():
    """获取今日备份目录路径"""
    today = datetime.now().strftime("%Y%m%d")
    backup_path = os.path.join(BACKUP_DIR, today)
    return backup_path

def backup_files(backup_path):
    """备份文件"""
    files_dir = os.path.join(backup_path, "files")
    os.makedirs(files_dir, exist_ok=True)
    
    success = 0
    failed = 0
    
    for filepath in FILES_TO_BACKUP:
        if os.path.exists(filepath):
            try:
                # 数据库文件特殊处理：使用sqlite备份
                if filepath.endswith(".db"):
                    backup_file = os.path.join(files_dir, os.path.basename(filepath))
                    conn = sqlite3.connect(filepath)
                    backup_conn = sqlite3.connect(backup_file)
                    conn.backup(backup_conn)
                    backup_conn.close()
                    conn.close()
                else:
                    shutil.copy2(filepath, files_dir)
                success += 1
            except Exception as e:
                print(f"  [FAIL] {filepath}: {e}")
                failed += 1
        else:
            print(f"  [SKIP] {filepath}: 不存在")
    
    return success, failed

def backup_dirs(backup_path):
    """备份目录"""
    dirs_dir = os.path.join(backup_path, "dirs")
    os.makedirs(dirs_dir, exist_ok=True)
    
    success = 0
    failed = 0
    
    for dirpath in DIRS_TO_BACKUP:
        if os.path.exists(dirpath):
            try:
                dest = os.path.join(dirs_dir, os.path.basename(dirpath))
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(dirpath, dest)
                success += 1
            except Exception as e:
                print(f"  [FAIL] {dirpath}: {e}")
                failed += 1
        else:
            print(f"  [SKIP] {dirpath}: 不存在")
    
    return success, failed

def generate_manifest(backup_path, files_success, files_failed, dirs_success, dirs_failed):
    """生成备份清单"""
    manifest = {
        "backup_id": f"BACKUP-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω",
        "files": {
            "total": len(FILES_TO_BACKUP),
            "success": files_success,
            "failed": files_failed,
        },
        "dirs": {
            "total": len(DIRS_TO_BACKUP),
            "success": dirs_success,
            "failed": dirs_failed,
        },
        "system_state": {},
    }
    
    # 采集系统状态
    try:
        import requests
        # 真值库状态
        resp = requests.get("http://127.0.0.1:9120/api/truths?limit=1", timeout=5)
        manifest["system_state"]["truth_api"] = "ok"
    except:
        manifest["system_state"]["truth_api"] = "unavailable"
    
    try:
        import requests
        # 知识图谱状态
        resp = requests.get("http://127.0.0.1:8070/api/v1/kg/stat", timeout=5)
        kg_data = resp.json()
        manifest["system_state"]["knowledge_graph"] = kg_data
    except:
        manifest["system_state"]["knowledge_graph"] = "unavailable"
    
    # 写入清单
    manifest_path = os.path.join(backup_path, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    return manifest

def cleanup_old_backups():
    """清理过期备份（保留最近7天）"""
    if not os.path.exists(BACKUP_DIR):
        return 0, 0
    
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted = 0
    kept = 0
    
    for dirname in os.listdir(BACKUP_DIR):
        dirpath = os.path.join(BACKUP_DIR, dirname)
        if os.path.isdir(dirpath):
            try:
                dir_date = datetime.strptime(dirname, "%Y%m%d")
                if dir_date < cutoff_date:
                    shutil.rmtree(dirpath)
                    deleted += 1
                else:
                    kept += 1
            except:
                # 非日期格式的目录，保留
                kept += 1
    
    return deleted, kept

def main():
    print("=" * 60)
    print("  ZONGYUAN-ROOT 全域成果自动备份")
    print("=" * 60)
    print(f"  时间: {datetime.now().isoformat()}")
    print(f"  DID: DID-BR-000002")
    print(f"  溯源: Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)
    print()
    
    # 创建备份目录
    backup_path = get_backup_path()
    os.makedirs(backup_path, exist_ok=True)
    print(f"备份目录: {backup_path}")
    print()
    
    # 备份文件
    print("【1】备份文件...")
    files_success, files_failed = backup_files(backup_path)
    print(f"  完成: 成功 {files_success}, 失败 {files_failed}")
    print()
    
    # 备份目录
    print("【2】备份目录...")
    dirs_success, dirs_failed = backup_dirs(backup_path)
    print(f"  完成: 成功 {dirs_success}, 失败 {dirs_failed}")
    print()
    
    # 生成清单
    print("【3】生成备份清单...")
    manifest = generate_manifest(backup_path, files_success, files_failed, dirs_success, dirs_failed)
    print(f"  备份ID: {manifest['backup_id']}")
    print()
    
    # 清理过期备份
    print("【4】清理过期备份...")
    deleted, kept = cleanup_old_backups()
    print(f"  保留: {kept} 个, 删除: {deleted} 个")
    print()
    
    # 计算备份大小
    total_size = 0
    for root, dirs, files in os.walk(backup_path):
        for f in files:
            fp = os.path.join(root, f)
            total_size += os.path.getsize(fp)
    
    print("=" * 60)
    print("  备份完成")
    print("=" * 60)
    print(f"  备份大小: {total_size / 1024 / 1024:.2f} MB")
    print(f"  文件备份: {files_success} 成功 / {files_failed} 失败")
    print(f"  目录备份: {dirs_success} 成功 / {dirs_failed} 失败")
    print(f"  保留备份: {kept} 个 (最近{RETENTION_DAYS}天)")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit(main())
