#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜统一数据库连接模块
功能：封装sqlite3.connect，自动设置PRAGMA（WAL/NORMAL/20MB缓存），确保所有连接配置一致
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002

使用方式：
    from comm.db_utils import get_connection, get_master_db, query_one, query_all, execute

    # 获取设置好PRAGMA的连接
    conn = get_connection("/path/to/db.sqlite")

    # 便捷函数
    row = query_one(conn, "SELECT * FROM nodes WHERE id=?", (1,))
    rows = query_all(conn, "SELECT * FROM nodes")
    execute(conn, "INSERT INTO nodes VALUES (?,?)", (1, "test"))
"""

import os
import sqlite3
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.resolve()

# 数据库路径常量
MASTER_DB = BASE_DIR / "master" / "core" / "master_state.db"
ASSET_INDEX_DB = BASE_DIR / "db" / "asset_index.db"
OPERATOR_RESULTS_DB = BASE_DIR / "db" / "operator_results.db"
FEDERATION_STATE_DB = BASE_DIR / "db" / "federation_state.db"

# PRAGMA默认配置
DEFAULT_PRAGMAS = {
    "journal_mode": "WAL",       # WAL模式，支持读写并发
    "synchronous": "NORMAL",      # NORMAL同步，WAL下安全，性能比FULL高2-3倍
    "cache_size": -20000,         # 20MB缓存（负号表示KB）
    "foreign_keys": "ON",         # 启用外键约束
    "temp_store": "MEMORY",       # 临时表存内存
}


def get_connection(db_path, pragmas=None):
    """
    获取设置好PRAGMA的SQLite连接

    Args:
        db_path: 数据库路径（str或Path）
        pragmas: 自定义PRAGMA字典，覆盖默认值

    Returns:
        sqlite3.Connection: 设置好PRAGMA的连接
    """
    db_path = str(db_path)

    # 确保目录存在
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # 创建连接
    conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)

    # 应用PRAGMA
    effective_pragmas = DEFAULT_PRAGMAS.copy()
    if pragmas:
        effective_pragmas.update(pragmas)

    for key, value in effective_pragmas.items():
        try:
            conn.execute(f"PRAGMA {key}={value}")
        except Exception:
            pass  # 忽略PRAGMA设置失败

    return conn


def get_master_db(pragmas=None):
    """获取主中枢数据库连接"""
    return get_connection(MASTER_DB, pragmas)


def get_asset_db(pragmas=None):
    """获取资产索引数据库连接"""
    return get_connection(ASSET_INDEX_DB, pragmas)


def get_operator_db(pragmas=None):
    """获取算子结果数据库连接"""
    return get_connection(OPERATOR_RESULTS_DB, pragmas)


def get_federation_db(pragmas=None):
    """获取联邦状态数据库连接"""
    return get_connection(FEDERATION_STATE_DB, pragmas)


def query_one(conn, sql, params=None):
    """
    执行查询并返回第一行

    Args:
        conn: 数据库连接
        sql: SQL语句
        params: 参数元组

    Returns:
        tuple or None: 第一行数据
    """
    cursor = conn.execute(sql, params or ())
    return cursor.fetchone()


def query_all(conn, sql, params=None):
    """
    执行查询并返回所有行

    Args:
        conn: 数据库连接
        sql: SQL语句
        params: 参数元组

    Returns:
        list: 所有行数据
    """
    cursor = conn.execute(sql, params or ())
    return cursor.fetchall()


def execute(conn, sql, params=None):
    """
    执行SQL语句（INSERT/UPDATE/DELETE）

    Args:
        conn: 数据库连接
        sql: SQL语句
        params: 参数元组

    Returns:
        int: 受影响的行数
    """
    cursor = conn.execute(sql, params or ())
    return cursor.rowcount


def execute_many(conn, sql, params_list):
    """
    批量执行SQL语句

    Args:
        conn: 数据库连接
        sql: SQL语句
        params_list: 参数元组列表

    Returns:
        int: 受影响的行数
    """
    cursor = conn.executemany(sql, params_list)
    return cursor.rowcount


def table_exists(conn, table_name):
    """
    检查表是否存在

    Args:
        conn: 数据库连接
        table_name: 表名

    Returns:
        bool: 表是否存在
    """
    result = query_one(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return result is not None


def get_table_count(conn, table_name):
    """
    获取表行数

    Args:
        conn: 数据库连接
        table_name: 表名

    Returns:
        int: 行数
    """
    if not table_exists(conn, table_name):
        return 0
    result = query_one(conn, f"SELECT COUNT(*) FROM '{table_name}'")
    return result[0] if result else 0


def get_db_info(conn):
    """
    获取数据库配置信息

    Args:
        conn: 数据库连接

    Returns:
        dict: 数据库配置
    """
    info = {}
    for pragma in ["journal_mode", "synchronous", "cache_size", "page_size", "page_count"]:
        try:
            result = conn.execute(f"PRAGMA {pragma}").fetchone()
            info[pragma] = result[0] if result else None
        except Exception:
            info[pragma] = None
    return info


def verify_connection(conn):
    """
    验证连接是否正常（PRAGMA设置是否生效）

    Args:
        conn: 数据库连接

    Returns:
        dict: 验证结果
    """
    info = get_db_info(conn)
    return {
        "valid": info.get("journal_mode") == "wal",
        "journal_mode": info.get("journal_mode"),
        "synchronous": info.get("synchronous"),
        "cache_size": info.get("cache_size"),
        "expected": {
            "journal_mode": "wal",
            "synchronous": 1,
            "cache_size": -20000,
        },
    }


# 模块初始化时确保数据库目录存在
for db_path in [MASTER_DB, ASSET_INDEX_DB, OPERATOR_RESULTS_DB, FEDERATION_STATE_DB]:
    db_dir = db_path.parent
    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
