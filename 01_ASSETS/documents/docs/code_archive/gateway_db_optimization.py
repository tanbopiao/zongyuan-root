#!/usr/bin/env python3
"""
记忆网关数据库连接优化模块 V1.0
用于网关应用程序的数据库连接初始化，确保WAL/busy_timeout/synchronous等优化设置生效。

执行时间：2026-09-16
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
体系：ZONGYUAN-ROOT元极恒一自治体系 | 火斗云智AIOS
"""

import sqlite3
import threading
import time
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from queue import Queue, Empty

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class OptimizedSQLiteConnection:
    """
    优化的SQLite连接封装
    自动应用WAL模式、busy_timeout、synchronous等优化设置
    """

    # 默认优化配置
    DEFAULT_CONFIG = {
        "journal_mode": "WAL",           # WAL模式：读写并发
        "busy_timeout": 5000,             # 锁等待超时：5秒
        "synchronous": "NORMAL",          # 同步模式：NORMAL（WAL下安全）
        "cache_size": -64000,             # 缓存大小：64MB
        "temp_store": "MEMORY",           # 临时表存储：内存
        "mmap_size": 268435456,          # 内存映射大小：256MB
        "foreign_keys": "ON",             # 外键约束：开启
    }

    def __init__(self, db_path: str, config: Dict[str, Any] = None):
        """
        初始化优化的SQLite连接

        Args:
            db_path: 数据库文件路径
            config: 自定义配置（覆盖默认配置）
        """
        self.db_path = db_path
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def connect(self) -> sqlite3.Connection:
        """
        创建并优化数据库连接

        Returns:
            优化后的sqlite3.Connection对象
        """
        with self._lock:
            if self._conn is None:
                self._conn = self._create_optimized_connection()
            return self._conn

    def _create_optimized_connection(self) -> sqlite3.Connection:
        """
        创建优化的数据库连接，应用所有PRAGMA设置

        Returns:
            优化后的sqlite3.Connection对象
        """
        logger.info(f"创建优化的数据库连接: {self.db_path}")

        # 创建连接，设置超时
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.config["busy_timeout"] / 1000.0,  # 转换为秒
            check_same_thread=False,  # 允许多线程使用
            isolation_level=None,     # 自动提交模式
        )

        # 应用PRAGMA设置
        pragmas = [
            ("journal_mode", self.config["journal_mode"]),
            ("busy_timeout", self.config["busy_timeout"]),
            ("synchronous", self.config["synchronous"]),
            ("cache_size", self.config["cache_size"]),
            ("temp_store", self.config["temp_store"]),
            ("mmap_size", self.config["mmap_size"]),
            ("foreign_keys", self.config["foreign_keys"]),
        ]

        for pragma_name, pragma_value in pragmas:
            try:
                conn.execute(f"PRAGMA {pragma_name} = {pragma_value};")
                logger.debug(f"  PRAGMA {pragma_name} = {pragma_value}")
            except Exception as e:
                logger.warning(f"  设置PRAGMA {pragma_name}失败: {e}")

        # 验证关键设置
        self._verify_settings(conn)

        # 注册自定义函数（可选）
        self._register_functions(conn)

        logger.info("数据库连接优化完成")
        return conn

    def _verify_settings(self, conn: sqlite3.Connection):
        """验证关键PRAGMA设置是否生效"""
        checks = [
            ("journal_mode", "wal"),
            ("busy_timeout", 5000),
        ]

        for pragma_name, expected_value in checks:
            try:
                cursor = conn.execute(f"PRAGMA {pragma_name};")
                actual_value = cursor.fetchone()[0]
                if str(actual_value).lower() == str(expected_value).lower():
                    logger.info(f"  ✅ {pragma_name} = {actual_value}")
                else:
                    logger.warning(f"  ⚠️  {pragma_name} = {actual_value} (预期: {expected_value})")
            except Exception as e:
                logger.warning(f"  验证{pragma_name}失败: {e}")

    def _register_functions(self, conn: sqlite3.Connection):
        """注册自定义SQL函数"""
        try:
            # 真值纯度评分函数
            def truth_purity_score(confidence: float, source_count: int) -> float:
                """计算真值纯度评分（0-100）"""
                if confidence is None:
                    return 0.0
                base_score = float(confidence) * 80
                source_bonus = min(source_count or 0, 5) * 4
                return min(100.0, base_score + source_bonus)

            conn.create_function("truth_purity_score", 2, truth_purity_score)

            # 漂移率计算函数
            def drift_rate(current: float, baseline: float) -> float:
                """计算漂移率（百分比）"""
                if baseline is None or baseline == 0:
                    return 0.0
                return abs(float(current) - float(baseline)) / float(baseline) * 100

            conn.create_function("drift_rate", 2, drift_rate)

            logger.debug("自定义SQL函数注册完成")
        except Exception as e:
            logger.warning(f"注册自定义函数失败: {e}")

    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                logger.info("数据库连接已关闭")

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DatabaseConnectionPool:
    """
    数据库连接池
    管理多个优化的数据库连接，避免频繁创建销毁
    """

    def __init__(self, db_path: str, pool_size: int = 5, config: Dict[str, Any] = None):
        """
        初始化连接池

        Args:
            db_path: 数据库文件路径
            pool_size: 连接池大小
            config: 自定义配置
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.config = config or {}
        self._pool: Queue = Queue(maxsize=pool_size)
        self._created = 0
        self._lock = threading.Lock()

        # 预创建连接
        for _ in range(min(pool_size, 2)):  # 预创建2个连接
            self._pool.put(self._create_connection())

        logger.info(f"数据库连接池初始化完成: 大小={pool_size}, 已创建={self._created}")

    def _create_connection(self) -> sqlite3.Connection:
        """创建新的优化数据库连接"""
        optimized = OptimizedSQLiteConnection(self.db_path, self.config)
        conn = optimized.connect()
        with self._lock:
            self._created += 1
        return conn

    def get_connection(self, timeout: float = 5.0) -> sqlite3.Connection:
        """
        从连接池获取连接

        Args:
            timeout: 等待超时时间（秒）

        Returns:
            sqlite3.Connection对象

        Raises:
            TimeoutError: 等待超时
        """
        try:
            conn = self._pool.get(timeout=timeout)
            return conn
        except Empty:
            # 连接池已满，创建新连接（如果未超过上限）
            with self._lock:
                if self._created < self.pool_size:
                    return self._create_connection()
            raise TimeoutError(f"获取数据库连接超时（{timeout}秒）")

    def release_connection(self, conn: sqlite3.Connection):
        """
        释放连接回连接池

        Args:
            conn: 要释放的连接
        """
        try:
            self._pool.put_nowait(conn)
        except Exception:
            # 连接池已满，关闭连接
            conn.close()
            with self._lock:
                self._created -= 1

    @contextmanager
    def connection(self, timeout: float = 5.0):
        """上下文管理器：自动获取和释放连接"""
        conn = self.get_connection(timeout)
        try:
            yield conn
        finally:
            self.release_connection(conn)

    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
        with self._lock:
            self._created = 0
        logger.info("所有数据库连接已关闭")


# ========== 网关应用程序集成示例 ==========

class GatewayDatabase:
    """
    网关数据库类
    网关应用程序应使用此类进行数据库操作
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = "/opt/gateway/data/truths.db"):
        if self._initialized:
            return
        self.db_path = db_path
        self.pool = DatabaseConnectionPool(db_path, pool_size=5)
        self._initialized = True
        logger.info(f"网关数据库初始化完成: {db_path}")

    def execute_query(self, query: str, params: tuple = None, fetch: str = "all") -> List:
        """
        执行查询

        Args:
            query: SQL查询语句
            params: 查询参数
            fetch: 取回方式（all/one/single）

        Returns:
            查询结果
        """
        with self.pool.connection() as conn:
            cursor = conn.execute(query, params or ())
            if fetch == "all":
                return cursor.fetchall()
            elif fetch == "one":
                return cursor.fetchone()
            elif fetch == "single":
                row = cursor.fetchone()
                return row[0] if row else None
            return cursor.fetchall()

    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        执行更新（INSERT/UPDATE/DELETE）

        Args:
            query: SQL语句
            params: 参数

        Returns:
            影响的行数
        """
        with self.pool.connection() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.rowcount

    def execute_batch(self, query: str, params_list: List[tuple]) -> int:
        """
        批量执行

        Args:
            query: SQL语句
            params_list: 参数列表

        Returns:
            影响的总行数
        """
        with self.pool.connection() as conn:
            cursor = conn.executemany(query, params_list)
            return cursor.rowcount

    def get_status(self) -> Dict[str, Any]:
        """获取数据库状态"""
        with self.pool.connection() as conn:
            status = {}
            for pragma in ["journal_mode", "busy_timeout", "synchronous", "cache_size"]:
                cursor = conn.execute(f"PRAGMA {pragma};")
                status[pragma] = cursor.fetchone()[0]
            return status

    def close(self):
        """关闭数据库"""
        self.pool.close_all()


# ========== 快速初始化函数 ==========

def init_gateway_database(db_path: str = "/opt/gateway/data/truths.db") -> GatewayDatabase:
    """
    快速初始化网关数据库

    Args:
        db_path: 数据库路径

    Returns:
        GatewayDatabase实例
    """
    return GatewayDatabase(db_path)


def optimize_existing_database(db_path: str):
    """
    优化已存在的数据库（一次性优化脚本）

    Args:
        db_path: 数据库路径
    """
    logger.info(f"开始优化数据库: {db_path}")

    # 创建优化连接（会自动应用所有PRAGMA）
    optimized = OptimizedSQLiteConnection(db_path)
    conn = optimized.connect()

    # 创建索引（如果不存在）
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_truth_key ON truths(truth_key);",
        "CREATE INDEX IF NOT EXISTS idx_truth_type ON truths(truth_type);",
        "CREATE INDEX IF NOT EXISTS idx_source_node ON truths(source_node);",
        "CREATE INDEX IF NOT EXISTS idx_created_at ON truths(created_at);",
    ]

    for index_sql in indexes:
        try:
            conn.execute(index_sql)
            logger.info(f"  ✅ 索引创建/已存在: {index_sql.split('ON')[1].split('(')[0].strip()}")
        except Exception as e:
            logger.warning(f"  ⚠️  创建索引失败: {e}")

    # 执行ANALYZE
    try:
        conn.execute("ANALYZE;")
        logger.info("  ✅ ANALYZE完成")
    except Exception as e:
        logger.warning(f"  ⚠️  ANALYZE失败: {e}")

    # 验证状态
    status = {}
    for pragma in ["journal_mode", "busy_timeout", "synchronous"]:
        cursor = conn.execute(f"PRAGMA {pragma};")
        status[pragma] = cursor.fetchone()[0]

    logger.info(f"数据库优化完成: {status}")
    optimized.close()

    return status


if __name__ == "__main__":
    # 测试：优化数据库
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_optimize.db"

    # 创建测试数据库
    import os
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS truths (id INTEGER PRIMARY KEY, truth_key TEXT UNIQUE, truth_value TEXT, truth_type TEXT, source_node TEXT, confidence REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        conn.execute("INSERT OR IGNORE INTO truths (truth_key, truth_value, truth_type, source_node, confidence) VALUES ('TEST.001', '测试', 'data', 'test', 0.9);")
        conn.commit()
        conn.close()

    # 执行优化
    status = optimize_existing_database(db_path)
    print("\n优化结果:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    # 测试连接池
    print("\n测试连接池:")
    db = GatewayDatabase(db_path)
    result = db.execute_query("SELECT count(*) FROM truths;", fetch="single")
    print(f"  真值总数: {result}")
    print(f"  数据库状态: {db.get_status()}")
    db.close()

    # 清理
    if db_path == "/tmp/test_optimize.db":
        os.remove(db_path)
        for ext in ["-wal", "-shm"]:
            f = db_path + ext
            if os.path.exists(f):
                os.remove(f)
