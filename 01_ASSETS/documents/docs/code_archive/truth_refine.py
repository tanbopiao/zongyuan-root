#!/usr/bin/env python3
"""
真值自动提炼机制 - 内核自治增强
对记忆网关中的真值进行去重、合并、分类优化、低价值归档
每日运行一次，保持真值库精炼高效
"""
import os
import sys
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict

# 配置
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
ARCHIVE_PATH = "/opt/ZONGYUAN-ROOT/data/truth_archive.db"
REFINE_LOG = "/opt/ZONGYUAN-ROOT/logs/truth_refine.log"
REPORT_PATH = "/opt/ZONGYUAN-ROOT/health_reports/truth_refine_report.json"

# 真值价值评估权重
VALUE_WEIGHTS = {
    "meta_rule": 100,      # 元法则最高价值
    "axiom": 90,           # 公理
    "protocol": 85,        # 协议
    "theorem": 80,         # 定理
    "method": 70,          # 方法
    "decision": 65,        # 决策
    "data": 50,            # 数据
    "case": 45,            # 案例
    "risk": 60,            # 风险
    "creative": 40,        # 创意
    "lock": 55,            # 锁档
    "compute_injection": 50,  # 算力注入
}

# 低价值阈值（低于此值考虑归档）
LOW_VALUE_THRESHOLD = 35

# 重复真值相似度阈值
SIMILARITY_THRESHOLD = 0.9

def log_refine(message):
    os.makedirs(os.path.dirname(REFINE_LOG), exist_ok=True)
    with open(REFINE_LOG, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def calculate_truth_value(truth):
    """计算真值价值评分"""
    category = truth.get("category", "data")
    base_value = VALUE_WEIGHTS.get(category, 50)
    
    # 时效性衰减（超过30天的真值价值衰减）
    created_at = truth.get("created_at", "")
    if created_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00").replace("+00:00", ""))
            days_old = (datetime.now() - created).days
            if days_old > 30:
                base_value *= max(0.5, 1 - (days_old - 30) * 0.01)
        except:
            pass
    
    # 版本号加成（高版本真值更有价值）
    version = truth.get("version", 1)
    if version > 1:
        base_value += min(version * 2, 20)
    
    return round(base_value, 1)

def find_duplicates(cursor):
    """查找重复真值"""
    cursor.execute("SELECT id, truth_key, truth_value, truth_hash, category FROM truths ORDER BY truth_key")
    rows = cursor.fetchall()
    
    duplicates = []
    seen_keys = {}
    
    for row in rows:
        truth_id, truth_key, truth_value, truth_hash, category = row
        
        # 完全相同的key视为重复
        if truth_key in seen_keys:
            duplicates.append({
                "original": seen_keys[truth_key],
                "duplicate": {
                    "id": truth_id,
                    "key": truth_key,
                    "hash": truth_hash,
                    "category": category
                }
            })
        else:
            seen_keys[truth_key] = {
                "id": truth_id,
                "key": truth_key,
                "hash": truth_hash,
                "category": category
            }
    
    return duplicates

def merge_duplicates(cursor, duplicates):
    """合并重复真值（保留版本最高的，删除其他）"""
    merged_count = 0
    
    for dup in duplicates:
        original = dup["original"]
        duplicate = dup["duplicate"]
        
        # 获取两个真值的完整信息
        cursor.execute("SELECT version, updated_at FROM truths WHERE id = ?", (original["id"],))
        orig_version, orig_updated = cursor.fetchone()
        
        cursor.execute("SELECT version, updated_at FROM truths WHERE id = ?", (duplicate["id"],))
        dup_version, dup_updated = cursor.fetchone()
        
        # 保留版本更高或更新时间更近的
        if dup_version > orig_version or (dup_version == orig_version and dup_updated > orig_updated):
            keep_id = duplicate["id"]
            delete_id = original["id"]
        else:
            keep_id = original["id"]
            delete_id = duplicate["id"]
        
        # 删除重复真值
        cursor.execute("DELETE FROM truths WHERE id = ?", (delete_id,))
        merged_count += 1
        log_refine(f"[MERGE] 删除重复真值: id={delete_id}, key={original['key']}, 保留id={keep_id}")
    
    return merged_count

def find_low_value_truths(cursor):
    """查找低价值真值"""
    cursor.execute("SELECT id, truth_key, truth_value, category, created_at, version FROM truths")
    rows = cursor.fetchall()
    
    low_value = []
    
    for row in rows:
        truth_id, truth_key, truth_value, category, created_at, version = row
        
        truth = {
            "id": truth_id,
            "key": truth_key,
            "value": truth_value,
            "category": category,
            "created_at": created_at,
            "version": version
        }
        
        value = calculate_truth_value(truth)
        
        if value < LOW_VALUE_THRESHOLD:
            low_value.append({
                "id": truth_id,
                "key": truth_key,
                "category": category,
                "value_score": value,
                "created_at": created_at
            })
    
    return low_value

def archive_low_value(cursor, low_value_truths):
    """归档低价值真值到归档数据库"""
    if not low_value_truths:
        return 0
    
    # 确保归档数据库存在
    archive_conn = sqlite3.connect(ARCHIVE_PATH)
    archive_cursor = archive_conn.cursor()
    
    archive_cursor.execute("""
        CREATE TABLE IF NOT EXISTS archived_truths (
            id INTEGER PRIMARY KEY,
            truth_key TEXT,
            truth_value TEXT,
            truth_hash TEXT,
            category TEXT,
            node_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            version INTEGER,
            archived_at TEXT,
            value_score REAL
        )
    """)
    
    archived_count = 0
    
    for truth in low_value_truths:
        truth_id = truth["id"]
        
        # 获取完整真值数据
        cursor.execute("SELECT * FROM truths WHERE id = ?", (truth_id,))
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        
        if row:
            truth_data = dict(zip(columns, row))
            
            # 插入归档库
            archive_cursor.execute("""
                INSERT OR REPLACE INTO archived_truths 
                (id, truth_key, truth_value, truth_hash, category, node_id, 
                 created_at, updated_at, version, archived_at, value_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                truth_data.get("id"),
                truth_data.get("truth_key"),
                truth_data.get("truth_value"),
                truth_data.get("truth_hash"),
                truth_data.get("category"),
                truth_data.get("node_id"),
                truth_data.get("created_at"),
                truth_data.get("updated_at"),
                truth_data.get("version"),
                datetime.now().isoformat(),
                truth["value_score"]
            ))
            
            # 从主库删除
            cursor.execute("DELETE FROM truths WHERE id = ?", (truth_id,))
            
            archived_count += 1
            log_refine(f"[ARCHIVE] 归档低价值真值: id={truth_id}, key={truth['key']}, 价值分={truth['value_score']}")
    
    archive_conn.commit()
    archive_conn.close()
    
    return archived_count

def analyze_categories(cursor):
    """分析真值分类分布"""
    cursor.execute("SELECT category, COUNT(*) FROM truths GROUP BY category ORDER BY COUNT(*) DESC")
    rows = cursor.fetchall()
    
    categories = {}
    total = 0
    
    for category, count in rows:
        categories[category] = count
        total += count
    
    return categories, total

def generate_report(stats):
    """生成提炼报告"""
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "summary": {
            "total_before": stats.get("total_before", 0),
            "total_after": stats.get("total_after", 0),
            "duplicates_merged": stats.get("duplicates_merged", 0),
            "low_value_archived": stats.get("low_value_archived", 0),
            "reduction_percent": round(
                (stats.get("total_before", 0) - stats.get("total_after", 0)) / 
                max(stats.get("total_before", 1), 1) * 100, 1
            )
        }
    }
    
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report

def main():
    log_refine("=" * 60)
    log_refine("真值自动提炼机制启动")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # 1. 提炼前统计
    categories_before, total_before = analyze_categories(cursor)
    stats["total_before"] = total_before
    stats["categories_before"] = categories_before
    log_refine(f"提炼前真值总数: {total_before}")
    log_refine(f"分类分布: {json.dumps(categories_before, ensure_ascii=False)}")
    
    # 2. 查找并合并重复真值
    log_refine("-" * 40)
    log_refine("步骤1: 查找重复真值")
    duplicates = find_duplicates(cursor)
    log_refine(f"发现重复真值: {len(duplicates)}组")
    
    if duplicates:
        merged = merge_duplicates(cursor, duplicates)
        conn.commit()
        stats["duplicates_merged"] = merged
        log_refine(f"已合并重复真值: {merged}条")
    else:
        stats["duplicates_merged"] = 0
        log_refine("无重复真值")
    
    # 3. 查找并归档低价值真值
    log_refine("-" * 40)
    log_refine("步骤2: 查找低价值真值")
    low_value = find_low_value_truths(cursor)
    log_refine(f"发现低价值真值: {len(low_value)}条 (阈值<{LOW_VALUE_THRESHOLD})")
    
    if low_value:
        archived = archive_low_value(cursor, low_value)
        conn.commit()
        stats["low_value_archived"] = archived
        log_refine(f"已归档低价值真值: {archived}条")
    else:
        stats["low_value_archived"] = 0
        log_refine("无低价值真值需要归档")
    
    # 4. 提炼后统计
    log_refine("-" * 40)
    log_refine("步骤3: 提炼后统计")
    categories_after, total_after = analyze_categories(cursor)
    stats["total_after"] = total_after
    stats["categories_after"] = categories_after
    log_refine(f"提炼后真值总数: {total_after}")
    log_refine(f"分类分布: {json.dumps(categories_after, ensure_ascii=False)}")
    
    reduction = total_before - total_after
    reduction_pct = round(reduction / max(total_before, 1) * 100, 1)
    log_refine(f"净减少: {reduction}条 ({reduction_pct}%)")
    
    # 5. 生成报告
    report = generate_report(stats)
    
    conn.close()
    
    log_refine("-" * 40)
    log_refine("真值自动提炼完成")
    log_refine(f"报告已保存: {REPORT_PATH}")
    log_refine("=" * 60)
    
    # 输出摘要
    print("\n" + "=" * 60)
    print("  真值自动提炼报告")
    print("=" * 60)
    print(f"  提炼前: {total_before}条")
    print(f"  提炼后: {total_after}条")
    print(f"  合并重复: {stats.get('duplicates_merged', 0)}条")
    print(f"  归档低价值: {stats.get('low_value_archived', 0)}条")
    print(f"  净减少: {reduction}条 ({reduction_pct}%)")
    print("=" * 60)
    print(f"  报告: {REPORT_PATH}")
    print(f"  日志: {REFINE_LOG}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
