#!/usr/bin/env python3
"""
数据持久层接入验证 - 记忆网关真值库接入仿真
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

验证内容：
1. 从云端记忆网关拉取真值样本
2. 用数据持久层存储（内容寻址+多副本+Merkle校验）
3. 验证去重、完整性、分层、统计
4. 生成接入报告
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.storage_engine import UnifiedStorageEngine
from core.replication import ReplicationManager, IntegrityVerifier
from backends.local_storage import LocalStorageBackend


CLOUD_SSH = "ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=15 root@123.207.202.158"


def fetch_truths_from_cloud(limit=50):
    """从本地样本文件读取真值（已通过SSH预下载）"""
    print(f"[1/5] 读取真值样本(已从云端9120预下载)...")
    sample_path = "/tmp/truths_sample.json"
    if not os.path.exists(sample_path):
        print("  ❌ 样本文件不存在，请先执行下载")
        return []

    with open(sample_path, "r", encoding="utf-8") as f:
        truths = json.load(f)

    # 过滤掉key为空的无效条目
    truths = [t for t in truths if t.get("key")]
    print(f"  ✅ 有效真值 {len(truths)} 条")

    categories = {}
    for t in truths:
        c = t.get("category", "uncategorized") or "uncategorized"
        categories[c] = categories.get(c, 0) + 1
    print(f"  📊 类别分布: {json.dumps(categories, ensure_ascii=False)}")
    return truths


def store_truths_in_dpl(truths, tmpdir):
    """用数据持久层存储真值"""
    print(f"[2/5] 用数据持久层存储 {len(truths)} 条真值...")

    engine = UnifiedStorageEngine(base_dir=os.path.join(tmpdir, "truth_storage"), replicas=2)
    backend1 = LocalStorageBackend("truth-primary", os.path.join(tmpdir, "backend1"))
    backend2 = LocalStorageBackend("truth-replica", os.path.join(tmpdir, "backend2"))
    engine.register_backend(backend1)
    engine.register_backend(backend2)
    engine.initialize()

    stored = 0
    duplicates = 0
    categories = {}

    for t in truths:
        # 真值内容 = key + value（确保唯一）
        content = json.dumps({"key": t["key"], "value": t["value"]}, ensure_ascii=False).encode("utf-8")
        category = t.get("category", "uncategorized")
        categories[category] = categories.get(category, 0) + 1

        oid, obj = engine.put(
            content,
            metadata={"truth_key": t["key"], "truth_hash": t["hash"], "category": category},
            tier="hot" if category in ("metalaw", "achievement", "architecture") else "warm",
            tags=[category, "truth"],
            source=f"memory_gateway:{t.get('node_id','unknown')}",
        )
        if obj:
            if obj.access_count > 1:
                duplicates += 1
            else:
                stored += 1

    print(f"  ✅ 存储完成: 新增 {stored} 条, 去重 {duplicates} 条")
    print(f"  📊 类别分布: {json.dumps(categories, ensure_ascii=False)}")
    return engine


def verify_integrity(engine):
    """验证完整性"""
    print("[3/5] 完整性校验（逐对象哈希 + Merkle树）...")

    verifier = IntegrityVerifier(engine)
    result = verifier.full_verify()

    print(f"  总对象数: {result['total_objects']}")
    print(f"  健康对象: {result['healthy_objects']}")
    print(f"  损坏对象: {len(result['corrupted_objects'])}")
    print(f"  完整率: {result['integrity_rate']*100:.1f}%")
    print(f"  Merkle根哈希: {result['merkle_root_hash'][:16]}...")

    return result


def verify_replicas(engine):
    """验证副本"""
    print("[4/5] 多副本校验与自动修复...")

    rm = ReplicationManager(engine, target_replicas=2)
    verify = rm.verify_all_replicas()

    print(f"  总副本数: {verify['total_replicas']}")
    print(f"  健康副本: {verify['healthy']}")
    print(f"  损坏副本: {len(verify['corrupted'])}")
    print(f"  丢失副本: {len(verify['missing'])}")
    print(f"  副本健康率: {verify['replica_health_rate']*100:.1f}%")

    # 确保副本数
    ensure = rm.ensure_replica_count()
    print(f"  副本不足对象: {ensure['under_replicated']}")

    return verify


def get_stats(engine):
    """获取统计"""
    stats = engine.get_stats()
    print(f"[5/5] 存储统计:")
    print(f"  总对象: {stats.total_objects}")
    print(f"  总大小: {stats.total_size} bytes ({stats.total_size/1024:.1f} KB)")
    print(f"  Hot层: {stats.hot_objects}, Warm层: {stats.warm_objects}, Cold层: {stats.cold_objects}")
    print(f"  总副本: {stats.total_replicas}, 健康副本: {stats.healthy_replicas}")
    return stats


def main():
    print("=" * 60)
    print("数据持久层 × 记忆网关真值库 接入验证")
    print("DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 拉取真值
        truths = fetch_truths_from_cloud(limit=50)
        if not truths:
            print("❌ 无法拉取真值，退出")
            return 1

        # 2. 存储
        engine = store_truths_in_dpl(truths, tmpdir)

        # 3. 完整性校验
        integrity = verify_integrity(engine)

        # 4. 副本校验
        replicas = verify_replicas(engine)

        # 5. 统计
        stats = get_stats(engine)

        # 生成报告
        report = {
            "test": "数据持久层接入记忆网关真值库验证",
            "timestamp": time.time(),
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω",
            "source": "云端记忆网关9120 (1355条真值库)",
            "sample_size": len(truths),
            "storage": {
                "engine": "UnifiedStorageEngine V1.0",
                "backends": 2,
                "target_replicas": 2,
                "total_objects": stats.total_objects,
                "total_size_bytes": stats.total_size,
                "tier_distribution": {
                    "hot": stats.hot_objects,
                    "warm": stats.warm_objects,
                    "cold": stats.cold_objects,
                    "archive": stats.archive_objects,
                },
            },
            "integrity": {
                "total": integrity["total_objects"],
                "healthy": integrity["healthy_objects"],
                "corrupted": len(integrity["corrupted_objects"]),
                "rate": integrity["integrity_rate"],
                "merkle_root": integrity["merkle_root_hash"],
            },
            "replicas": {
                "total": replicas["total_replicas"],
                "healthy": replicas["healthy"],
                "corrupted": len(replicas["corrupted"]),
                "missing": len(replicas["missing"]),
                "health_rate": replicas["replica_health_rate"],
            },
            "conclusion": "接入验证通过" if integrity["integrity_rate"] == 1.0 and replicas["replica_health_rate"] == 1.0 else "存在问题需修复",
        }

        report_path = os.path.join(os.path.dirname(__file__), "integration_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"接入验证结论: {report['conclusion']}")
        print(f"报告已保存: {report_path}")
        print(f"{'='*60}")

        return 0 if report["conclusion"] == "接入验证通过" else 1


if __name__ == "__main__":
    sys.exit(main())
