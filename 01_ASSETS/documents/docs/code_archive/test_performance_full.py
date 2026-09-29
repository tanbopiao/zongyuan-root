#!/usr/bin/env python3
"""
数据持久层 - 全量规模性能测试
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

用真值样本扩展到1355条，测试：
1. 全量写入性能
2. 全量读取性能
3. 全量完整性校验
4. 全量副本校验
5. 批量查询性能
6. 内存/磁盘占用
"""

import hashlib
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.storage_engine import UnifiedStorageEngine
from core.replication import ReplicationManager, IntegrityVerifier
from backends.local_storage import LocalStorageBackend


def load_sample_truths():
    """加载真值样本"""
    sample_path = "/tmp/truths_sample.json"
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 没有样本就生成模拟数据
    return [{"key": f"simulated.truth.{i}", "value": f"模拟真值内容 {i}" * 10,
             "category": "simulated", "hash": "", "node_id": "sim"} for i in range(29)]


def expand_to_full_scale(samples, target=1355):
    """将样本扩展到目标规模（复制+变体）"""
    expanded = []
    i = 0
    while len(expanded) < target:
        base = samples[i % len(samples)]
        variant = {
            "key": f"{base['key']}#variant_{i}",
            "value": f"{base['value']} [variant {i}]",
            "category": base.get("category", "uncategorized"),
            "hash": base.get("hash", ""),
            "node_id": base.get("node_id", "unknown"),
        }
        expanded.append(variant)
        i += 1
    return expanded


def run_performance_test(truths):
    """运行性能测试"""
    print("=" * 60)
    print(f"数据持久层 - 全量规模性能测试 ({len(truths)} 条)")
    print("DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化引擎
        engine = UnifiedStorageEngine(base_dir=os.path.join(tmpdir, "storage"), replicas=2)
        b1 = LocalStorageBackend("primary", os.path.join(tmpdir, "b1"), cache_mb=64)
        b2 = LocalStorageBackend("replica", os.path.join(tmpdir, "b2"), cache_mb=64)
        engine.register_backend(b1)
        engine.register_backend(b2)
        engine.initialize()

        # ===== 1. 全量写入性能 =====
        print("\n[1/6] 全量写入性能测试...")
        t0 = time.time()
        stored = 0
        for t in truths:
            content = json.dumps({"key": t["key"], "value": t["value"]}, ensure_ascii=False).encode("utf-8")
            oid, obj = engine.put(
                content,
                metadata={"truth_key": t["key"], "category": t.get("category", "")},
                tier="hot" if t.get("category") in ("metalaw", "achievement", "architecture") else "warm",
                tags=[t.get("category", "uncategorized"), "truth"],
            )
            if obj:
                stored += 1
        write_time = time.time() - t0
        print(f"  写入 {stored} 条, 耗时 {write_time:.2f}s, 平均 {write_time/stored*1000:.2f}ms/条")
        print(f"  吞吐: {stored/write_time:.1f} 条/秒")

        # ===== 2. 全量读取性能 =====
        print("\n[2/6] 全量读取性能测试...")
        all_objs = engine.list_objects()
        t0 = time.time()
        read_count = 0
        for obj in all_objs[:500]:  # 测500条
            data = engine.get(obj.object_id)
            if data:
                read_count += 1
        read_time = time.time() - t0
        print(f"  读取 {read_count} 条, 耗时 {read_time:.2f}s, 平均 {read_time/read_count*1000:.2f}ms/条")
        print(f"  吞吐: {read_count/read_time:.1f} 条/秒")

        # ===== 3. 全量完整性校验 =====
        print("\n[3/6] 全量完整性校验（SHA256逐对象）...")
        verifier = IntegrityVerifier(engine)
        t0 = time.time()
        integrity = verifier.full_verify()
        verify_time = time.time() - t0
        print(f"  校验 {integrity['total_objects']} 条, 耗时 {verify_time:.2f}s")
        print(f"  健康: {integrity['healthy_objects']}, 损坏: {len(integrity['corrupted_objects'])}")
        print(f"  完整率: {integrity['integrity_rate']*100:.1f}%")
        print(f"  Merkle根: {integrity['merkle_root_hash'][:16]}...")

        # ===== 4. 全量副本校验 =====
        print("\n[4/6] 全量副本校验...")
        rm = ReplicationManager(engine, target_replicas=2)
        t0 = time.time()
        replica_result = rm.verify_all_replicas()
        replica_time = time.time() - t0
        print(f"  副本总数: {replica_result['total_replicas']}, 耗时 {replica_time:.2f}s")
        print(f"  健康: {replica_result['healthy']}, 损坏: {len(replica_result['corrupted'])}, 丢失: {len(replica_result['missing'])}")
        print(f"  副本健康率: {replica_result['replica_health_rate']*100:.1f}%")

        # ===== 5. 批量查询性能 =====
        print("\n[5/6] 批量查询性能测试...")
        t0 = time.time()
        hot_objs = engine.list_objects(tier="hot")
        warm_objs = engine.list_objects(tier="warm")
        query_time = time.time() - t0
        print(f"  Hot层: {len(hot_objs)} 条, Warm层: {len(warm_objs)} 条")
        print(f"  分层查询耗时: {query_time*1000:.2f}ms")

        # 按标签查询
        t0 = time.time()
        tagged = engine.list_objects(tag="achievement")
        tag_time = time.time() - t0
        print(f"  标签查询(achievement): {len(tagged)} 条, 耗时 {tag_time*1000:.2f}ms")

        # ===== 6. 存储统计 =====
        print("\n[6/6] 存储统计...")
        stats = engine.get_stats()
        print(f"  总对象: {stats.total_objects}")
        print(f"  总大小: {stats.total_size/1024:.1f} KB ({stats.total_size/1024/1024:.2f} MB)")
        print(f"  Hot: {stats.hot_objects}, Warm: {stats.warm_objects}, Cold: {stats.cold_objects}")
        print(f"  总副本: {stats.total_replicas}, 健康副本: {stats.healthy_replicas}")

        # 磁盘占用
        disk_usage = b1.get_disk_usage()
        print(f"  主后端磁盘: {disk_usage['used_bytes']/1024:.1f} KB / {disk_usage['total_bytes']/1024/1024:.0f} MB")

        # 缓存统计
        cache_stats = b1.cache.stats()
        print(f"  缓存: {cache_stats['items']} 项, {cache_stats['size_bytes']/1024:.1f} KB, 命中率 {cache_stats['hit_rate']*100:.1f}%")

        # ===== 汇总报告 =====
        report = {
            "test": "数据持久层全量规模性能测试",
            "scale": len(truths),
            "timestamp": time.time(),
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω",
            "write": {
                "count": stored,
                "time_sec": round(write_time, 2),
                "avg_ms": round(write_time/stored*1000, 2),
                "throughput": round(stored/write_time, 1),
            },
            "read": {
                "count": read_count,
                "time_sec": round(read_time, 2),
                "avg_ms": round(read_time/read_count*1000, 2),
                "throughput": round(read_count/read_time, 1),
            },
            "integrity": {
                "total": integrity["total_objects"],
                "healthy": integrity["healthy_objects"],
                "corrupted": len(integrity["corrupted_objects"]),
                "rate": integrity["integrity_rate"],
                "merkle_root": integrity["merkle_root_hash"],
                "time_sec": round(verify_time, 2),
            },
            "replicas": {
                "total": replica_result["total_replicas"],
                "healthy": replica_result["healthy"],
                "rate": replica_result["replica_health_rate"],
                "time_sec": round(replica_time, 2),
            },
            "storage": {
                "total_objects": stats.total_objects,
                "total_size_kb": round(stats.total_size/1024, 1),
                "tier_hot": stats.hot_objects,
                "tier_warm": stats.warm_objects,
                "total_replicas": stats.total_replicas,
            },
            "conclusion": "全量规模测试通过" if integrity["integrity_rate"] == 1.0 and replica_result["replica_health_rate"] == 1.0 else "存在问题",
        }

        report_path = os.path.join(os.path.dirname(__file__), "performance_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"结论: {report['conclusion']}")
        print(f"报告: {report_path}")
        print(f"{'='*60}")

        return report


def main():
    samples = load_sample_truths()
    print(f"加载样本: {len(samples)} 条")
    truths = expand_to_full_scale(samples, target=1355)
    print(f"扩展到全量规模: {len(truths)} 条")
    report = run_performance_test(truths)
    return 0 if report["conclusion"] == "全量规模测试通过" else 1


if __name__ == "__main__":
    sys.exit(main())
