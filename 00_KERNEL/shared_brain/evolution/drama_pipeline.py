#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 短剧流水线商业化引擎（EVO-P0-002）

功能：
  1. 八段式流水线管理（剧本→分镜→画面→配音→剪辑→审核→发布→结算）
  2. 批次管理（批次号/集数/状态/成本/收益）
  3. DID 确权锚点（DID-BR-000002），每集生成溯源凭证
  4. 批次状态统计与成本核算

使用方式：
  python3 drama_pipeline.py --batch        # 批次模式：推进所有 pending 批次
  python3 drama_pipeline.py --batch --limit 5  # 最多推进 5 个批次
  python3 drama_pipeline.py --status       # 查看批次状态统计
  python3 drama_pipeline.py --create "主题"  # 创建新批次
"""
import os
import sys
import json
import time
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
DRAMA_DIR = EVOLUTION_DIR / "drama"
DRAMA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = DRAMA_DIR / "pipeline.log"
BATCHES_FILE = DRAMA_DIR / "batches.jsonl"
SETTLEMENT_FILE = DRAMA_DIR / "settlement.jsonl"

# ============ 八段式流水线定义 ============

PIPELINE_STAGES = [
    {"id": "script", "name": "剧本创作", "cost": 5.0, "duration_min": 30},
    {"id": "storyboard", "name": "分镜设计", "cost": 8.0, "duration_min": 45},
    {"id": "visual", "name": "画面生成", "cost": 12.0, "duration_min": 60},
    {"id": "voice", "name": "配音合成", "cost": 5.0, "duration_min": 30},
    {"id": "edit", "name": "剪辑合成", "cost": 8.0, "duration_min": 45},
    {"id": "review", "name": "合规审核", "cost": 3.0, "duration_min": 20},
    {"id": "publish", "name": "发布分发", "cost": 2.0, "duration_min": 15},
    {"id": "settlement", "name": "收益结算", "cost": 0.0, "duration_min": 10},
]

DID_TAG = "DID-BR-000002"
ARCHIVE_NODE = "ZONGYUAN-ROOT"

# 分发平台
DISTRIBUTION_PLATFORMS = ["抖音", "快手", "视频号", "小红书", "B站"]


def log(level: str, message: str):
    """统一日志输出。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def generate_batch_id() -> str:
    """生成批次号。"""
    date_str = datetime.now().strftime("%Y%m%d")
    seq = int(time.time()) % 10000
    return f"DRAMA-{date_str}-{seq:04d}"


def generate_did_proof(batch_id: str, episode: int) -> str:
    """生成 DID 确权溯源凭证。"""
    raw = f"{batch_id}-EP{episode}-{DID_TAG}-{time.time()}"
    proof_hash = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    return f"DID-PROOF-{proof_hash}"


def load_batches() -> List[Dict[str, Any]]:
    """加载所有批次记录。"""
    batches = []
    if BATCHES_FILE.exists():
        with open(BATCHES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    batches.append(json.loads(line))
    return batches


def save_batch(batch: Dict[str, Any]):
    """保存（追加）批次记录。"""
    with open(BATCHES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(batch, ensure_ascii=False) + "\n")


def update_batch_status(batch_id: str, updates: Dict[str, Any]) -> bool:
    """更新批次状态（重写整个文件以保证一致性）。"""
    batches = load_batches()
    found = False
    updated_batches = []
    for b in batches:
        if b.get("batch_id") == batch_id:
            b.update(updates)
            found = True
        updated_batches.append(b)

    if not found:
        return False

    with open(BATCHES_FILE, "w", encoding="utf-8") as f:
        for b in updated_batches:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")
    return True


def create_batch(topic: str, episode_count: int = 1) -> Dict[str, Any]:
    """创建新批次。"""
    batch_id = generate_batch_id()
    now = datetime.now().isoformat()

    episodes = []
    for i in range(1, episode_count + 1):
        episodes.append({
            "episode": i,
            "stage": 0,  # 当前阶段索引
            "status": "pending",
            "did_proof": generate_did_proof(batch_id, i),
            "cost": 0.0,
            "revenue": 0.0,
        })

    batch = {
        "batch_id": batch_id,
        "topic": topic,
        "episode_count": episode_count,
        "episodes": episodes,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "did_tag": DID_TAG,
        "archive_node": ARCHIVE_NODE,
        "total_cost": 0.0,
        "total_revenue": 0.0,
    }

    save_batch(batch)
    log("INFO", f"新批次创建: {batch_id}, 主题: {topic}, 集数: {episode_count}")
    return batch


def advance_batch(batch: Dict[str, Any]) -> Dict[str, Any]:
    """
    推进一个批次到下一个阶段。
    模拟八段式流水线执行（实际生产环境对接真实生成服务）。
    """
    batch_id = batch["batch_id"]
    progressed = False
    total_cost = 0.0

    for ep in batch.get("episodes", []):
        if ep["status"] == "completed":
            total_cost += ep.get("cost", 0.0)
            continue

        current_stage_idx = ep["stage"]
        if current_stage_idx >= len(PIPELINE_STAGES):
            ep["status"] = "completed"
            total_cost += ep.get("cost", 0.0)
            continue

        stage = PIPELINE_STAGES[current_stage_idx]

        # 执行当前阶段（模拟）
        log("INFO", f"批次 {batch_id} 第 {ep['episode']} 集 → 阶段: {stage['name']}")

        # 累加到当前阶段的成本
        ep["cost"] = round(ep.get("cost", 0.0) + stage["cost"], 2)
        ep["stage"] = current_stage_idx + 1

        # 如果是结算阶段，标记完成并写入结算记录
        if stage["id"] == "settlement":
            ep["status"] = "completed"
            ep["revenue"] = round(ep["cost"] * 2.5, 2)  # 模拟毛利率 ~60%
            _record_settlement(batch_id, ep)
            log("INFO", f"批次 {batch_id} 第 {ep['episode']} 集完成，成本: ¥{ep['cost']}, 预估收益: ¥{ep['revenue']}")

        progressed = True
        total_cost += ep.get("cost", 0.0)
        break  # 每批次每次只推进一个阶段（避免单次执行过久）

    # 判断批次整体状态
    all_completed = all(ep["status"] == "completed" for ep in batch.get("episodes", []))
    if all_completed:
        batch["status"] = "completed"
        batch["total_revenue"] = round(sum(ep.get("revenue", 0.0) for ep in batch["episodes"]), 2)
    elif progressed:
        batch["status"] = "in_progress"
    else:
        batch["status"] = batch.get("status", "pending")

    batch["total_cost"] = round(total_cost, 2)
    batch["updated_at"] = datetime.now().isoformat()

    return batch


def _record_settlement(batch_id: str, episode: Dict[str, Any]):
    """记录结算信息。"""
    settlement = {
        "batch_id": batch_id,
        "episode": episode["episode"],
        "did_proof": episode["did_proof"],
        "cost": episode["cost"],
        "revenue": episode["revenue"],
        "profit": round(episode["revenue"] - episode["cost"], 2),
        "margin": round((episode["revenue"] - episode["cost"]) / max(episode["revenue"], 0.01) * 100, 1),
        "platforms": DISTRIBUTION_PLATFORMS,
        "settled_at": datetime.now().isoformat(),
        "did_tag": DID_TAG,
    }
    with open(SETTLEMENT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(settlement, ensure_ascii=False) + "\n")


def run_batch_mode(limit: int = 10):
    """批次模式：推进所有 pending/in_progress 批次。"""
    batches = load_batches()
    pending = [b for b in batches if b.get("status") in ("pending", "in_progress")]

    if not pending:
        log("INFO", "无待处理批次")
        return

    log("INFO", f"待处理批次数: {len(pending)}，本次最多推进 {limit} 个")

    advanced = 0
    for batch in pending[:limit]:
        try:
            updated = advance_batch(batch)
            update_batch_status(batch["batch_id"], updated)
            advanced += 1
            time.sleep(0.5)  # 避免过快
        except Exception as e:
            log("ERROR", f"批次 {batch.get('batch_id')} 推进失败: {e}")

    log("INFO", f"批次模式完成，推进 {advanced} 个批次")


def show_status():
    """显示批次状态统计。"""
    batches = load_batches()
    if not batches:
        print("暂无批次记录")
        return

    status_counts = {}
    total_cost = 0.0
    total_revenue = 0.0

    for b in batches:
        status = b.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        total_cost += b.get("total_cost", 0.0)
        total_revenue += b.get("total_revenue", 0.0)

    print("=" * 50)
    print("短剧流水线批次状态统计")
    print("=" * 50)
    print(f"总批次数: {len(batches)}")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    print(f"总成本: ¥{round(total_cost, 2)}")
    print(f"总收益: ¥{round(total_revenue, 2)}")
    if total_cost > 0:
        print(f"毛利率: {round((total_revenue - total_cost) / max(total_revenue, 0.01) * 100, 1)}%")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="火斗云智短剧流水线商业化引擎")
    parser.add_argument("--batch", action="store_true", help="批次模式：推进待处理批次")
    parser.add_argument("--limit", type=int, default=10, help="批次模式最多推进数量")
    parser.add_argument("--status", action="store_true", help="查看批次状态统计")
    parser.add_argument("--create", type=str, help="创建新批次，参数为主题")
    parser.add_argument("--episodes", type=int, default=1, help="创建批次时的集数")

    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    if args.create:
        batch = create_batch(args.create, args.episodes)
        print(f"批次已创建: {batch['batch_id']}")
        return 0

    if args.batch:
        log("INFO", "=" * 50)
        log("INFO", "短剧流水线批次模式启动 (EVO-P0-002)")
        log("INFO", "=" * 50)
        run_batch_mode(limit=args.limit)
        return 0

    # 默认：显示状态
    show_status()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("ERROR", f"短剧流水线异常: {e}")
        sys.exit(0)
