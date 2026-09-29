#!/usr/bin/env python3
"""
记忆网关SQLite性能优化 - 阶段一紧急修复（Python版本）
执行时间: 2026-09-16
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
体系: ZONGYUAN-ROOT元极恒一自治体系 | 火斗云智AIOS
"""

import sqlite3
import shutil
import os
import sys
from datetime import datetime

# 配置
DB_PATHS = [
    "/opt/gateway/data/truths.db",
    "/opt/gateway/truths.db",
    "/var/lib/gateway/truths.db",
    "./data/truths.db",
]

BACKUP_DIR = "/opt/gateway/backups"

def find_db():
    """自动查找数据库文件"""
    for path in DB_PATHS:
        if os.path.exists(path):
            return path
    # 搜索/opt目录
    for root, dirs, files in os.walk("/opt"):
        for f in files:
            if f.endswith(".db") and "truth" in f.lower():
                return os.path.join(root, f)
    return None

def backup_db(db_path):
    """备份数据库"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"truths_{timestamp}.db.backup")
    
    # 使用sqlite3在线备份
    conn = sqlite3.connect(db_path)
    backup_conn = sqlite3.connect(backup_path)
    conn.backup(backup_conn)
    backup_conn.close()
    conn.close()
    
    return backup_path

def optimize_db(db_path):
    """执行SQLite优化"""
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()
    
    results = {}
    
    # 1. 启用WAL模式
    cursor.execute("PRAGMA journal_mode=WAL;")
    wal_mode = cursor.fetchone()[0]
    results['journal_mode'] = wal_mode
    print(f"  ✅ WAL模式: {wal_mode}")
    
    # 2. 设置busy_timeout
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA busy_timeout;")
    timeout = cursor.fetchone()[0]
    results['busy_timeout'] = timeout
    print(f"  ✅ busy_timeout: {timeout}ms")
    
    # 3. 优化synchronous
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA synchronous;")
    sync = cursor.fetchone()[0]
    results['synchronous'] = sync
    print(f"  ✅ synchronous: {sync} (0=OFF, 1=NORMAL, 2=FULL)")
    
    # 4. 创建索引
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_truth_key ON truths(truth_key);",
        "CREATE INDEX IF NOT EXISTS idx_truth_type ON truths(truth_type);",
        "CREATE INDEX IF NOT EXISTS idx_source_node ON truths(source_node);",
        "CREATE INDEX IF NOT EXISTS idx_created_at ON truths(created_at);",
    ]
    for idx_sql in indexes:
        cursor.execute(idx_sql)
    print(f"  ✅ 索引创建完成（4个）")
    
    # 5. ANALYZE
    cursor.execute("ANALYZE;")
    print(f"  ✅ ANALYZE完成")
    
    # 6. 获取统计信息
    cursor.execute("SELECT count(*) FROM truths;")
    truth_count = cursor.fetchone()[0]
    results['truth_count'] = truth_count
    
    conn.commit()
    conn.close()
    
    return results

def main():
    print("=" * 50)
    print("  记忆网关SQLite优化 - 阶段一紧急修复")
    print("=" * 50)
    print()
    
    # 查找数据库
    print("【步骤1】查找数据库文件")
    db_path = find_db()
    if not db_path:
        print("  ❌ 未找到数据库文件，请手动配置DB_PATHS")
        sys.exit(1)
    print(f"  ✅ 找到数据库: {db_path}")
    print()
    
    # 备份
    print("【步骤2】备份数据库")
    backup_path = backup_db(db_path)
    backup_size = os.path.getsize(backup_path)
    print(f"  ✅ 备份完成: {backup_path} ({backup_size/1024:.1f} KB)")
    print()
    
    # 优化
    print("【步骤3】执行SQLite优化")
    results = optimize_db(db_path)
    print()
    
    # 结果汇总
    print("=" * 50)
    print("  ✅ 优化完成")
    print("=" * 50)
    print(f"  数据库: {db_path}")
    print(f"  真值总数: {results['truth_count']}")
    print(f"  journal_mode: {results['journal_mode']}")
    print(f"  busy_timeout: {results['busy_timeout']}ms")
    print(f"  synchronous: {results['synchronous']} (NORMAL)")
    print(f"  索引: 4个")
    print()
    print("  预期效果:")
    print("    - 并发写入: 1-2 QPS → 10-20 QPS")
    print("    - 锁定错误: 5-10% → <0.1%")
    print("    - 响应时间: 200-500ms → 50-100ms")
    print()
    print(f"  备份文件: {backup_path}")
    print()
    print("  确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 50)

if __name__ == "__main__":
    main()
