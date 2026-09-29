#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜算子结果持久化模块
功能：算子执行结果持久化到SQLite，支持记录、查询、统计、趋势分析
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import sys
import json
import time
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# 统一数据库连接模块（自动设置PRAGMA: WAL/NORMAL/20MB缓存）
sys.path.insert(0, str(Path(__file__).parent.parent))
from comm.db_utils import get_connection

BASE_DIR = Path(__file__).parent.parent.resolve()
DB_PATH = BASE_DIR / "db" / "operator_results.db"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_connection():
    """获取数据库连接（统一PRAGMA配置：WAL/NORMAL/20MB缓存）"""
    conn = get_connection(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 算子执行结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operator_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id TEXT UNIQUE,
            operator_id TEXT NOT NULL,
            operator_name TEXT,
            layer INTEGER,
            status TEXT NOT NULL,
            execution_count INTEGER,
            elapsed_ms REAL,
            input_summary TEXT,
            output_summary TEXT,
            full_result TEXT,
            error_message TEXT,
            timestamp REAL NOT NULL,
            created_at TEXT
        )
    """)

    # 算子统计表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operator_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_id TEXT UNIQUE,
            operator_name TEXT,
            layer INTEGER,
            total_executions INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            avg_elapsed_ms REAL DEFAULT 0,
            last_execution REAL,
            last_status TEXT,
            updated_at TEXT
        )
    """)

    # 每日巡检报告表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_inspection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id TEXT UNIQUE,
            inspection_date TEXT,
            operators_run INTEGER,
            operators_success INTEGER,
            operators_error INTEGER,
            total_elapsed_ms REAL,
            report_summary TEXT,
            full_report TEXT,
            timestamp REAL,
            created_at TEXT
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_operator_results_op_id ON operator_results(operator_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_operator_results_timestamp ON operator_results(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_operator_results_status ON operator_results(status)")

    conn.commit()
    conn.close()
    return True


def record_result(operator_result):
    """记录算子执行结果

    Args:
        operator_result: 算子run()返回的结果字典

    Returns:
        result_id: 结果记录ID
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    result_id = f"OR-{int(time.time())}-{hashlib.md5(json.dumps(operator_result, sort_keys=True, default=str).encode()).hexdigest()[:8]}"
    operator_id = operator_result.get("operator_id", "unknown")
    operator_name = operator_result.get("operator_name", "unknown")
    layer = operator_result.get("layer", 0)
    status = operator_result.get("status", "unknown")
    execution_count = operator_result.get("execution_count", 0)
    elapsed_ms = operator_result.get("elapsed_ms", 0)
    error_message = operator_result.get("error", "")
    timestamp = operator_result.get("timestamp", time.time())
    created_at = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    # 输入输出摘要
    input_summary = json.dumps({k: v for k, v in operator_result.items()
                                 if k in ["operator_id", "operator_name", "layer"]},
                                ensure_ascii=False)[:500]
    output_summary = json.dumps({k: v for k, v in operator_result.items()
                                  if k not in ["operator_id", "operator_name", "layer", "status",
                                               "execution_count", "elapsed_ms", "timestamp",
                                               "operator_id", "full_result"]},
                                 ensure_ascii=False, default=str)[:1000]
    full_result = json.dumps(operator_result, ensure_ascii=False, default=str)

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO operator_results
            (result_id, operator_id, operator_name, layer, status, execution_count,
             elapsed_ms, input_summary, output_summary, full_result, error_message,
             timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (result_id, operator_id, operator_name, layer, status, execution_count,
              elapsed_ms, input_summary, output_summary, full_result, error_message,
              timestamp, created_at))

        # 更新统计
        cursor.execute("""
            INSERT INTO operator_stats (operator_id, operator_name, layer, total_executions,
                                        success_count, error_count, avg_elapsed_ms, last_execution,
                                        last_status, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(operator_id) DO UPDATE SET
                total_executions = total_executions + 1,
                success_count = success_count + CASE WHEN ? = 'success' THEN 1 ELSE 0 END,
                error_count = error_count + CASE WHEN ? = 'error' THEN 1 ELSE 0 END,
                avg_elapsed_ms = (avg_elapsed_ms * (total_executions - 1) + ?) / total_executions,
                last_execution = ?,
                last_status = ?,
                updated_at = ?
        """, (operator_id, operator_name, layer,
              1 if status == "success" else 0,
              1 if status == "error" else 0,
              elapsed_ms, timestamp, status, created_at,
              status, status, elapsed_ms, timestamp, status, created_at))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"记录算子结果失败: {e}")
    finally:
        conn.close()

    return result_id


def query_results(operator_id=None, status=None, limit=50, offset=0):
    """查询算子执行结果

    Args:
        operator_id: 算子ID过滤（可选）
        status: 状态过滤（可选）
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        结果列表
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM operator_results WHERE 1=1"
    params = []

    if operator_id:
        query += " AND operator_id = ?"
        params.append(operator_id)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_operator_stats(operator_id=None):
    """获取算子统计信息

    Args:
        operator_id: 算子ID（可选，不传返回所有算子统计）

    Returns:
        统计信息列表
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    if operator_id:
        cursor.execute("SELECT * FROM operator_stats WHERE operator_id = ?", (operator_id,))
    else:
        cursor.execute("SELECT * FROM operator_stats ORDER BY layer, operator_id")

    stats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stats


def get_daily_summary(date=None):
    """获取每日执行摘要

    Args:
        date: 日期（YYYY-MM-DD），默认今天

    Returns:
        摘要信息
    """
    init_db()
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()

    start_ts = datetime.strptime(date, "%Y-%m-%d").timestamp()
    end_ts = start_ts + 86400

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
            AVG(elapsed_ms) as avg_elapsed,
            COUNT(DISTINCT operator_id) as operators_run
        FROM operator_results
        WHERE timestamp >= ? AND timestamp < ?
    """, (start_ts, end_ts))

    summary = dict(cursor.fetchone())
    conn.close()
    return summary


def record_daily_inspection(report):
    """记录每日巡检报告

    Args:
        report: 巡检报告字典

    Returns:
        inspection_id
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    inspection_id = f"DI-{datetime.now().strftime('%Y%m%d')}-{hashlib.md5(json.dumps(report, sort_keys=True, default=str).encode()).hexdigest()[:8]}"
    timestamp = time.time()
    created_at = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO daily_inspection
            (inspection_id, inspection_date, operators_run, operators_success,
             operators_error, total_elapsed_ms, report_summary, full_report,
             timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (inspection_id, report.get("date", created_at[:10]),
              report.get("operators_run", 0), report.get("operators_success", 0),
              report.get("operators_error", 0), report.get("total_elapsed_ms", 0),
              json.dumps(report.get("summary", {}), ensure_ascii=False)[:1000],
              json.dumps(report, ensure_ascii=False, default=str),
              timestamp, created_at))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"记录巡检报告失败: {e}")
    finally:
        conn.close()

    return inspection_id


def get_all_stats_summary():
    """获取全部统计摘要（用于仪表盘展示）"""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 总体统计
    cursor.execute("""
        SELECT
            COUNT(*) as total_results,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as total_success,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as total_error,
            AVG(elapsed_ms) as avg_elapsed,
            COUNT(DISTINCT operator_id) as operators_with_results,
            MIN(timestamp) as first_execution,
            MAX(timestamp) as last_execution
        FROM operator_results
    """)
    overall = dict(cursor.fetchone())

    # 按层统计
    cursor.execute("""
        SELECT layer,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
               SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
               AVG(elapsed_ms) as avg_elapsed
        FROM operator_results
        GROUP BY layer
        ORDER BY layer
    """)
    by_layer = [dict(row) for row in cursor.fetchall()]

    # 算子统计
    cursor.execute("""
        SELECT operator_id, operator_name, layer, total_executions,
               success_count, error_count, avg_elapsed_ms, last_status
        FROM operator_stats
        ORDER BY layer, operator_id
    """)
    operators = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "overall": overall,
        "by_layer": by_layer,
        "operators": operators,
        "db_path": str(DB_PATH),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("元极恒一｜算子结果持久化模块测试")
    print("=" * 60)

    # 初始化数据库
    init_db()
    print(f"\n✅ 数据库初始化完成: {DB_PATH}")

    # 模拟记录算子结果
    print("\n--- 模拟记录算子结果 ---")
    test_results = [
        {"operator_id": "P4_TRUTH_RECONCILIATION", "operator_name": "真值对账算子",
         "layer": 1, "status": "success", "execution_count": 1, "elapsed_ms": 12.5,
         "truth_purity": 85.5, "timestamp": time.time()},
        {"operator_id": "DRIFT_DETECTION", "operator_name": "漂移巡检量化算子",
         "layer": 2, "status": "success", "execution_count": 1, "elapsed_ms": 8.3,
         "drift_rate": 2.5, "timestamp": time.time()},
        {"operator_id": "EFUSE_TRIGGER", "operator_name": "eFuse熔断触发算子",
         "layer": 8, "status": "error", "execution_count": 1, "elapsed_ms": 5.1,
         "error": "测试错误", "timestamp": time.time()},
    ]

    for result in test_results:
        rid = record_result(result)
        print(f"  ✅ 记录: {result['operator_id']} -> {rid}")

    # 查询结果
    print("\n--- 查询最近结果 ---")
    results = query_results(limit=5)
    for r in results:
        print(f"  [{r['created_at']}] {r['operator_id']:30s} | {r['status']:8s} | {r['elapsed_ms']}ms")

    # 统计摘要
    print("\n--- 统计摘要 ---")
    summary = get_all_stats_summary()
    print(f"  总结果数: {summary['overall']['total_results']}")
    print(f"  成功: {summary['overall']['total_success']}, 失败: {summary['overall']['total_error']}")
    print(f"  有结果的算子数: {summary['overall']['operators_with_results']}")
    print(f"  按层分布: {len(summary['by_layer'])}层")

    print("\n" + "=" * 60)
    print("算子结果持久化模块测试完成")
    print("=" * 60)
