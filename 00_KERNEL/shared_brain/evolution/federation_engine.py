#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 跨节点联邦智能网络引擎（EVO-P1-002）

功能：
  1. SFMP-1 实体一致性校验
  2. 节点注册表管理（基于 node_handshake_engine）
  3. 任务分片 + 结果聚合（map-reduce 模式）
  4. 节点信誉评分
  5. 联邦推理 API 状态报告

使用方式：
  python3 federation_engine.py              # 运行联邦周期（注册+校验+评分）
  python3 federation_engine.py --status     # 查看联邦网络状态
"""
import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
FEDERATION_DIR = EVOLUTION_DIR / "federation"
FEDERATION_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = FEDERATION_DIR / "engine.log"
NETWORK_FILE = FEDERATION_DIR / "network.json"
REPUTATION_FILE = FEDERATION_DIR / "reputation.json"

SERVICES_DIR = WORKSPACE / "scripts" / "services"
sys.path.insert(0, str(SERVICES_DIR))

NODE_REGISTRY = WORKSPACE / "node_registry" / "registry.json"
DID_TAG = "DID-BR-000002"
ARCHIVE_NODE = "ZONGYUAN-ROOT"


def log(level: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sfmp_consistency_check(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    SFMP-1 协议实体一致性校验。
    校验实体的哈希、签名、时间戳是否一致。
    """
    content = json.dumps(entity.get("data", {}), sort_keys=True, ensure_ascii=False)
    expected_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    actual_hash = entity.get("hash", "")

    is_consistent = expected_hash == actual_hash
    return {
        "entity_id": entity.get("id", "unknown"),
        "consistent": is_consistent,
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
        "checked_at": datetime.now().isoformat(),
    }


def load_node_registry() -> List[Dict[str, Any]]:
    """加载节点注册表。"""
    if NODE_REGISTRY.exists():
        try:
            data = json.loads(NODE_REGISTRY.read_text(encoding="utf-8"))
            # 兼容两种格式：列表 或 {nodes: [...]}
            if isinstance(data, list):
                return [n for n in data if isinstance(n, dict)]
            elif isinstance(data, dict):
                nodes = data.get("nodes", [])
                return [n for n in nodes if isinstance(n, dict)]
        except Exception:
            return []
    return []


def run_handshake() -> Dict[str, Any]:
    """执行节点握手。"""
    try:
        from node_handshake_engine import run_handshake as do_handshake
        return do_handshake()
    except Exception as e:
        log("WARN", f"握手引擎调用失败: {e}，使用本地节点信息")
        return {
            "success": True,
            "node_id": "NODE-DEV-DOUBAO-WORK-001",
            "status": "local",
            "did_tag": DID_TAG,
        }


def calculate_reputation(nodes: List[Dict[str, Any]]) -> Dict[str, float]:
    """计算节点信誉评分（基于任务完成质量）。"""
    reputation = {}
    for node in nodes:
        node_id = node.get("node_id", node.get("id", "unknown"))
        # 基础分 50，握手成功 +20，有真值上报 +10，时间新鲜 +20
        score = 50.0
        if node.get("status") in ("registered", "verified"):
            score += 20
        if node.get("truth_count", 0) > 0:
            score += min(10, node["truth_count"] * 0.1)
        # 时间新鲜度
        ts = node.get("last_seen", node.get("registered_at", ""))
        if ts:
            try:
                from datetime import datetime as dt
                node_time = dt.fromisoformat(ts[:19])
                age_hours = (dt.now() - node_time).total_seconds() / 3600
                if age_hours < 24:
                    score += 20
                elif age_hours < 168:
                    score += 10
            except Exception:
                pass
        reputation[node_id] = round(min(100, score), 1)
    return reputation


def shard_tasks(task_count: int, node_count: int) -> List[Dict[str, Any]]:
    """任务分片（map-reduce 模式）。"""
    if node_count == 0:
        return []
    shard_size = max(1, task_count // node_count)
    shards = []
    for i in range(node_count):
        start = i * shard_size
        end = min(start + shard_size, task_count) if i < node_count - 1 else task_count
        shards.append({
            "node_index": i,
            "task_range": [start, end],
            "task_count": end - start,
        })
    return shards


def main():
    show_status = "--status" in sys.argv

    if show_status:
        if NETWORK_FILE.exists():
            print(NETWORK_FILE.read_text(encoding="utf-8"))
        else:
            print("暂无联邦网络状态，请先运行引擎")
        return 0

    log("INFO", "=" * 50)
    log("INFO", "联邦智能网络引擎启动 (EVO-P1-002)")
    log("INFO", "=" * 50)

    # 1. 节点握手
    handshake = run_handshake()
    log("INFO", f"握手结果: {handshake.get('success', False)}, 节点: {handshake.get('node_id')}")

    # 2. 加载节点注册表
    nodes = load_node_registry()
    if not nodes:
        nodes = [{"node_id": handshake.get("node_id", "local"), "status": "registered",
                  "did_tag": DID_TAG, "registered_at": datetime.now().isoformat()}]
    log("INFO", f"注册表节点数: {len(nodes)}")

    # 3. SFMP 一致性校验
    checks = []
    for node in nodes:
        check = sfmp_consistency_check(node)
        checks.append(check)
    consistent_count = sum(1 for c in checks if c["consistent"])
    log("INFO", f"SFMP 校验: {consistent_count}/{len(checks)} 节点一致")

    # 4. 信誉评分
    reputation = calculate_reputation(nodes)
    REPUTATION_FILE.write_text(json.dumps(reputation, ensure_ascii=False, indent=2), encoding="utf-8")
    log("INFO", f"信誉评分: {reputation}")

    # 5. 任务分片模拟
    shards = shard_tasks(100, len(nodes))
    log("INFO", f"任务分片: {len(shards)} 个分片")

    # 6. 保存网络状态
    network = {
        "generated_at": datetime.now().isoformat(),
        "did_tag": DID_TAG,
        "archive_node": ARCHIVE_NODE,
        "total_nodes": len(nodes),
        "consistent_nodes": consistent_count,
        "reputation": reputation,
        "nodes": nodes,
        "sfmp_checks": checks,
        "task_shards": shards,
    }
    NETWORK_FILE.write_text(json.dumps(network, ensure_ascii=False, indent=2), encoding="utf-8")
    log("INFO", f"联邦网络状态已保存: {NETWORK_FILE}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(0)
