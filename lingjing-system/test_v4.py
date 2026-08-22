# -*- coding:utf-8 -*-
"""
灵境V4.0 测试用例集
SNAP-ZROOT-LINGJING-BRANCH-D-009
覆盖：日志清理截断、KV抽象层、一致性哈希分片、负载均衡
"""
import os, sys, time, json, hashlib, tempfile, shutil
from pathlib import Path

# 将源码目录加入路径
sys.path.insert(0, os.path.dirname(__file__))

def test_kv_backend_abstraction():
    """测试1：KV抽象层 - 简易文件KV读写"""
    print("[测试1] KV抽象层 - 简易文件KV")
    from lingjing_v4 import SimpleFileKV
    tmpdir = tempfile.mkdtemp()
    kv = SimpleFileKV(Path(tmpdir))
    kv.put("key1", "value1")
    kv.put("key2", "value2")
    assert kv.get("key1") == "value1", "读取失败"
    assert kv.get("key2") == "value2", "读取失败"
    assert kv.get("nonexistent") is None, "不存在的key应返回None"
    shutil.rmtree(tmpdir)
    print("  ✅ 通过")

def test_consistent_hash_partitioner():
    """测试2：一致性哈希分片 - 相同domain路由一致"""
    print("[测试2] 一致性哈希分片")
    from lingjing_v4 import ConsistentHashPartitioner
    p = ConsistentHashPartitioner(num_partitions=4, virtual_nodes=100)
    # 相同domain应路由到相同分片
    p1 = p.get_partition("sim_layer")
    p2 = p.get_partition("sim_layer")
    assert p1 == p2, "相同domain路由不一致"
    # 不同domain可能路由到不同分片
    domains = [f"domain_{i}" for i in range(20)]
    partitions = set(p.get_partition(d) for d in domains)
    assert len(partitions) > 1, "20个domain应分布到多个分片"
    # 负载报告
    report = p.get_load_report()
    assert report["num_partitions"] == 4
    assert report["total_events"] == 22  # 2次sim_layer + 20个domain
    print("  ✅ 通过")

def test_dynamic_partition_expansion():
    """测试3：动态扩容 - 增加分片后环更新"""
    print("[测试3] 动态分片扩容")
    from lingjing_v4 import ConsistentHashPartitioner
    p = ConsistentHashPartitioner(num_partitions=2, virtual_nodes=50)
    assert p.num_partitions == 2
    new_pid = p.add_partition()
    assert new_pid == 2
    assert p.num_partitions == 3
    # 新分片应能被路由到
    found = False
    for i in range(100):
        if p.get_partition(f"test_{i}") == 2:
            found = True
            break
    assert found, "新分片应能被路由到"
    print("  ✅ 通过")

def test_merkle_tree_with_kv():
    """测试4：冷热混合Merkle树 - 增量追加与根哈希"""
    print("[测试4] 冷热混合Merkle树")
    from lingjing_v4 import HybridIncrMerkleTree
    tmpdir = tempfile.mkdtemp()
    tree = HybridIncrMerkleTree(tree_height=8, cache_size=4, kv_dir=Path(tmpdir))
    # 追加10个叶子
    for i in range(10):
        tree.append(hashlib.sha256(f"leaf_{i}".encode()).hexdigest())
    assert tree.size == 10
    root1 = tree.root()
    assert root1 is not None, "根哈希不应为None"
    # 再追加，根哈希应变化
    tree.append(hashlib.sha256("leaf_10".encode()).hexdigest())
    root2 = tree.root()
    assert root1 != root2, "追加后根哈希应变化"
    tree.close()
    shutil.rmtree(tmpdir)
    print("  ✅ 通过")

def test_log_segmentation():
    """测试5：日志分段 - 段满自动切新段"""
    print("[测试5] 日志分段与清理")
    import lingjing_v4
    # 临时修改常量以便测试
    original_max = lingjing_v4.LOG_SEG_MAX_LINES
    lingjing_v4.LOG_SEG_MAX_LINES = 5
    tmpdir = tempfile.mkdtemp()
    lingjing_v4.BASE_PATH = Path(tmpdir)
    lingjing_v4.QUEUE_LOG_PATH = Path(tmpdir) / "queue_log"
    lingjing_v4.OFFSET_PATH = Path(tmpdir) / "offsets"
    lingjing_v4.QUEUE_LOG_PATH.mkdir(exist_ok=True)
    lingjing_v4.OFFSET_PATH.mkdir(exist_ok=True)

    from lingjing_v4 import PersistPartitionQueue, LingjingEvent
    q = PersistPartitionQueue("test", max_q=100, worker_cnt=1)
    # 入队15条，应产生至少2个段
    for i in range(15):
        evt = LingjingEvent("test_domain", {"i": i})
        evt.sign = "test"
        q.enqueue(evt)
    time.sleep(0.5)
    # 检查段文件数量
    seg_files = list((Path(tmpdir) / "queue_log").glob("part_test_seg*.log"))
    assert len(seg_files) >= 2, f"应产生至少2个段，实际{len(seg_files)}"
    # 测试清理
    deleted = q._cleanup_old_segments()
    q.shutdown()
    lingjing_v4.LOG_SEG_MAX_LINES = original_max
    shutil.rmtree(tmpdir)
    print(f"  ✅ 通过 (段数:{len(seg_files)}, 清理旧段:{deleted})")

def test_event_signature():
    """测试6：事件签名与校验"""
    print("[测试6] 事件签名校验")
    from lingjing_v4 import PartitionAsyncBus, LingjingEvent
    bus = PartitionAsyncBus(initial_partitions=2)
    evt = LingjingEvent("test_domain", {"data": "test"})
    bus.sign_event(evt)
    assert evt.sign != "", "签名不应为空"
    assert bus.verify_event(evt), "合法事件应通过校验"
    # 篡改payload
    evt.payload = {"data": "tampered"}
    assert not bus.verify_event(evt), "篡改后应校验失败"
    print("  ✅ 通过")

def test_load_balancing_report():
    """测试7：负载均衡报告"""
    print("[测试7] 负载均衡报告")
    from lingjing_v4 import PartitionAsyncBus, LingjingEvent
    bus = PartitionAsyncBus(initial_partitions=4)
    # 发送一批事件
    for i in range(50):
        evt = LingjingEvent(f"domain_{i % 5}", {"i": i})
        bus.sign_event(evt)
        bus.publish(evt)
    time.sleep(0.5)
    report = bus.get_load_report()
    assert report["num_partitions"] == 4
    assert report["total_events"] == 50
    assert sum(report["partition_load"].values()) == 50
    print(f"  ✅ 通过 (负载分布:{report['partition_load']})")

def run_all_tests():
    print("=" * 60)
    print("灵境V4.0 测试用例集")
    print("=" * 60)
    tests = [
        test_kv_backend_abstraction,
        test_consistent_hash_partitioner,
        test_dynamic_partition_expansion,
        test_merkle_tree_with_kv,
        test_log_segmentation,
        test_event_signature,
        test_load_balancing_report,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            failed += 1
    print("=" * 60)
    print(f"结果: {passed} 通过, {failed} 失败, 共 {len(tests)} 项")
    print("=" * 60)
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
