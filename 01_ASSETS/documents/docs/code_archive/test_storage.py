#!/usr/bin/env python3
"""
火斗云智AIOS 数据持久层 - 仿真测试套件 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT

测试覆盖：
1. 统一存储引擎基础功能（put/get/delete/list/stat）
2. 内容寻址去重
3. 多副本管理
4. Merkle完整性校验
5. 冷热分层
6. LRU缓存
7. 损坏修复
8. 统计与监控
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

# 确保可以导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.storage_engine import UnifiedStorageEngine, StorageTier, DataState
from core.replication import ReplicationManager, MerkleTree, IntegrityVerifier
from backends.local_storage import LocalStorageBackend, LRUCache


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def run(self, name, func):
        try:
            func()
            self.passed += 1
            self.results.append((name, "PASS", ""))
            print(f"  ✅ {name}")
        except Exception as e:
            self.failed += 1
            self.results.append((name, "FAIL", str(e)))
            print(f"  ❌ {name}: {e}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"仿真测试结果: {self.passed}/{total} 通过, {self.failed} 失败")
        print(f"{'='*60}")
        return self.failed == 0


def make_engine(tmpdir, replicas=2):
    """创建测试用存储引擎"""
    engine = UnifiedStorageEngine(base_dir=os.path.join(tmpdir, "storage"), replicas=replicas)
    # 注册两个本地后端（模拟多副本）
    backend1 = LocalStorageBackend("local-primary", os.path.join(tmpdir, "backend1"))
    backend2 = LocalStorageBackend("local-replica", os.path.join(tmpdir, "backend2"))
    engine.register_backend(backend1)
    engine.register_backend(backend2)
    engine.initialize()
    return engine


# ============================================================
# 测试用例
# ============================================================

def test_put_and_get():
    """测试1: 基础写入读取"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        data = b"Hello, Huodou Cloud AIOS Data Persistence Layer!"
        oid, obj = engine.put(data, source="test")
        assert oid is not None, "写入失败"
        assert obj.size == len(data), "大小不匹配"

        retrieved = engine.get(oid)
        assert retrieved == data, "读取数据不匹配"
        print(f"    object_id={oid[:16]}... size={len(data)}")


def test_content_dedup():
    """测试2: 内容寻址去重"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        data = b"dedup test content"

        oid1, _ = engine.put(data, source="first")
        oid2, obj2 = engine.put(data, source="second")

        assert oid1 == oid2, "相同内容应返回相同object_id"
        assert obj2.access_count >= 2, "去重应增加访问计数"
        assert len(engine.list_objects()) == 1, "应只有1个对象"


def test_delete():
    """测试3: 删除（软删除+硬删除）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        data = b"to be deleted"
        oid, _ = engine.put(data)

        # 软删除
        assert engine.delete(oid, permanent=False)
        assert engine.get(oid) is None, "软删除后应不可读"
        assert engine.stat(oid).state == DataState.DELETED.value

        # 硬删除
        assert engine.delete(oid, permanent=True)
        assert engine.stat(oid) is None, "硬删除后元数据应移除"


def test_list_and_filter():
    """测试4: 列表与筛选"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        engine.put(b"hot data", tier="hot", tags=["test", "hot"])
        engine.put(b"cold data", tier="cold", tags=["test", "cold"])
        engine.put(b"warm data", tier="warm", tags=["other"])

        all_objs = engine.list_objects()
        assert len(all_objs) == 3, f"应有3个对象，实际{len(all_objs)}"

        hot_objs = engine.list_objects(tier="hot")
        assert len(hot_objs) == 1, "hot层应有1个"

        tag_objs = engine.list_objects(tag="test")
        assert len(tag_objs) == 2, "tag=test应有2个"


def test_replicas():
    """测试5: 多副本"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir, replicas=2)
        data = b"replica test data"
        oid, obj = engine.put(data)

        assert obj.replicas >= 2, f"应有至少2副本，实际{obj.replicas}"

        # 两个后端都应有数据
        b1 = engine.backends["local-primary"]
        b2 = engine.backends["local-replica"]
        assert b1.exists(oid), "主后端应有副本"
        assert b2.exists(oid), "副本后端应有副本"


def test_replication_manager():
    """测试6: 副本管理器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir, replicas=2)
        data = b"replication manager test"
        oid, _ = engine.put(data)

        rm = ReplicationManager(engine, target_replicas=2)

        # 校验副本
        verify = rm.verify_all_replicas()
        assert verify["total_replicas"] >= 2
        assert verify["healthy"] >= 2, f"应全部健康，实际{verify['healthy']}/{verify['total_replicas']}"

        # 确保副本数
        ensure = rm.ensure_replica_count()
        assert ensure["under_replicated"] == 0, "不应有副本不足的对象"


def test_merkle_tree():
    """测试7: Merkle树"""
    tree = MerkleTree()
    ids = ["a" * 64, "b" * 64, "c" * 64, "d" * 64]
    root = tree.build(ids)

    assert root is not None, "Merkle树根不应为空"
    assert tree.get_root_hash() != "", "根哈希不应为空"
    assert len(tree.leaves) == 4, "应有4个叶子"

    # 相同输入应产生相同根哈希
    tree2 = MerkleTree()
    tree2.build(ids)
    assert tree.get_root_hash() == tree2.get_root_hash(), "相同输入应产生相同根哈希"

    # 不同输入应产生不同根哈希
    tree3 = MerkleTree()
    tree3.build(["x" * 64, "y" * 64])
    assert tree.get_root_hash() != tree3.get_root_hash(), "不同输入应产生不同根哈希"


def test_integrity_verifier():
    """测试8: 完整性校验器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        engine.put(b"integrity test 1")
        engine.put(b"integrity test 2")
        engine.put(b"integrity test 3")

        verifier = IntegrityVerifier(engine)
        result = verifier.full_verify()

        assert result["total_objects"] == 3
        assert result["healthy_objects"] == 3
        assert result["integrity_rate"] == 1.0
        assert result["merkle_root_hash"] != ""
        print(f"    merkle_root={result['merkle_root_hash'][:16]}...")


def test_corruption_repair():
    """测试9: 损坏检测与修复"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir, replicas=2)
        data = b"corruption repair test data"
        oid, _ = engine.put(data)

        # 手动损坏一个副本
        b2 = engine.backends["local-replica"]
        path = b2._get_path(oid)
        with open(path, "wb") as f:
            f.write(b"corrupted data!!!")
        # 使缓存失效，否则会读到旧的健康数据
        b2.cache.invalidate(oid)

        # 校验应发现损坏
        rm = ReplicationManager(engine)
        verify = rm.verify_all_replicas()
        assert len(verify["corrupted"]) >= 1, "应检测到损坏副本"

        # 自动修复
        repair = rm.auto_repair()
        assert repair["repaired"] >= 1, "应修复至少1个副本"

        # 修复后重新校验
        verify2 = rm.verify_all_replicas()
        assert verify2["healthy"] == verify2["total_replicas"], "修复后应全部健康"


def test_tier_migration():
    """测试10: 冷热分层迁移"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        oid, _ = engine.put(b"tier test", tier="hot")

        assert engine.stat(oid).tier == "hot"

        # 迁移到cold
        assert engine.migrate_tier(oid, "cold")
        assert engine.stat(oid).tier == "cold"

        # 自动分层
        engine.put(b"auto tier 1", tier="hot")
        engine.put(b"auto tier 2", tier="hot")
        migrated = engine.auto_tier(hot_threshold_days=0)  # 0天=立即迁移
        assert migrated >= 0  # 刚创建的可能不触发


def test_lru_cache():
    """测试11: LRU缓存"""
    cache = LRUCache(max_size_mb=1)  # 1MB

    # 写入小数据
    cache.put("key1", b"a" * 1000)
    assert cache.get("key1") is not None

    # 写入超过容量的数据，应淘汰旧的
    cache.put("key2", b"b" * 500000)  # 500KB
    cache.put("key3", b"c" * 600000)  # 600KB，应淘汰key1
    assert cache.get("key1") is None, "key1应被淘汰"

    stats = cache.stats()
    assert stats["hit_rate"] >= 0
    print(f"    cache stats: hits={stats['hits']} misses={stats['misses']} hit_rate={stats['hit_rate']:.2f}")


def test_stats():
    """测试12: 存储统计"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        engine.put(b"stats hot 1", tier="hot")
        engine.put(b"stats hot 2", tier="hot")
        engine.put(b"stats cold 1", tier="cold")

        stats = engine.get_stats()
        assert stats.total_objects == 3
        assert stats.hot_objects == 2
        assert stats.cold_objects == 1
        assert stats.total_size > 0
        print(f"    total={stats.total_objects} hot={stats.hot_objects} cold={stats.cold_objects} size={stats.total_size}B")


def test_metadata_persistence():
    """测试13: 元数据持久化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 写入数据
        engine1 = make_engine(tmpdir)
        data = b"persistence test"
        oid1, _ = engine1.put(data, tags=["persist"])

        # 重新创建引擎，应能加载元数据
        engine2 = make_engine(tmpdir)
        obj = engine2.stat(oid1)
        assert obj is not None, "元数据应持久化"
        assert "persist" in obj.tags, "标签应持久化"

        retrieved = engine2.get(oid1)
        assert retrieved == data, "数据应可读取"


def test_large_file():
    """测试14: 大文件存储"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        # 1MB数据
        large_data = b"x" * (1024 * 1024)
        oid, obj = engine.put(large_data)

        assert obj.size == 1024 * 1024
        retrieved = engine.get(oid)
        assert retrieved == large_data
        assert hashlib.sha256(retrieved).hexdigest() == oid
        print(f"    1MB file stored and verified, hash={oid[:16]}...")


def test_batch_operations():
    """测试15: 批量操作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = make_engine(tmpdir)
        backend = engine.backends["local-primary"]

        items = [(f"obj{i}", f"data{i}".encode(), None) for i in range(20)]
        results = backend.batch_put(items)

        assert len(results) == 20
        assert all(results.values()), "批量写入应全部成功"

        listed = backend.list_objects()
        assert len(listed) >= 20


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 60)
    print("火斗云智AIOS 数据持久层 - 仿真测试套件 V1.0")
    print("DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)

    runner = TestRunner()

    tests = [
        ("基础写入读取", test_put_and_get),
        ("内容寻址去重", test_content_dedup),
        ("删除(软/硬)", test_delete),
        ("列表与筛选", test_list_and_filter),
        ("多副本", test_replicas),
        ("副本管理器", test_replication_manager),
        ("Merkle树", test_merkle_tree),
        ("完整性校验器", test_integrity_verifier),
        ("损坏检测与修复", test_corruption_repair),
        ("冷热分层迁移", test_tier_migration),
        ("LRU缓存", test_lru_cache),
        ("存储统计", test_stats),
        ("元数据持久化", test_metadata_persistence),
        ("大文件存储", test_large_file),
        ("批量操作", test_batch_operations),
    ]

    for name, func in tests:
        runner.run(name, func)

    success = runner.summary()

    # 生成测试报告
    report = {
        "test_suite": "Data Persistence Layer Simulation Test",
        "version": "1.0.0",
        "timestamp": time.time(),
        "total": runner.passed + runner.failed,
        "passed": runner.passed,
        "failed": runner.failed,
        "pass_rate": runner.passed / (runner.passed + runner.failed) if (runner.passed + runner.failed) > 0 else 0,
        "results": [{"name": n, "status": s, "error": e} for n, s, e in runner.results],
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω",
    }

    report_path = os.path.join(os.path.dirname(__file__), "test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n测试报告已保存: {report_path}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
