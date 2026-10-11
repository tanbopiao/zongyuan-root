#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — AI 模型训练数据市场（EVO-P2-001）

功能：
  1. 将真值库中的高质量数据打包为训练数据集
  2. 数据清洗 + 脱敏 + 格式标准化
  3. 数据集目录与定价
  4. 数据集导出（JSONL 格式）

使用方式：
  python3 data_marketplace.py             # 生成/更新数据集目录
  python3 data_marketplace.py --list      # 列出所有数据集
"""
import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
MARKETPLACE_DIR = EVOLUTION_DIR / "data_marketplace"
DATASETS_DIR = MARKETPLACE_DIR / "datasets"
MARKETPLACE_DIR.mkdir(parents=True, exist_ok=True)
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = MARKETPLACE_DIR / "marketplace.log"
CATALOG_FILE = MARKETPLACE_DIR / "catalog.json"

SERVICES_DIR = WORKSPACE / "scripts" / "services"
sys.path.insert(0, str(SERVICES_DIR))

DID_TAG = "DID-BR-000002"


def log(level: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def clean_text(text: str) -> str:
    """数据清洗：去除多余空白、HTML 标签等。"""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def desensitize(text: str) -> str:
    """脱敏：替换可能的敏感信息。"""
    text = re.sub(r"\b\d{11}\b", "[PHONE]", text)  # 手机号
    text = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]", text)  # 邮箱
    return text


def build_datasets(truths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从真值构建训练数据集。"""
    datasets = []

    # 按类别分组
    category_map: Dict[str, List[Dict]] = {}
    for t in truths:
        key = t.get("key", "")
        cat = key
        for sep in [".", "_", "-"]:
            if sep in key:
                cat = key.split(sep)[0]
                break
        category_map.setdefault(cat, []).append(t)

    # 为每个主要类别创建数据集
    for cat, items in category_map.items():
        if len(items) < 10:
            continue

        # 清洗 + 脱敏
        cleaned = []
        for item in items:
            text = clean_text(json.dumps(item.get("value", ""), ensure_ascii=False))
            text = desensitize(text)
            if len(text) > 20:
                cleaned.append({
                    "id": item.get("seq"),
                    "category": cat,
                    "text": text,
                    "source": item.get("key", ""),
                })

        if not cleaned:
            continue

        ds_id = f"DS-{cat.upper()}-{len(cleaned)}"
        ds_path = DATASETS_DIR / f"{ds_id}.jsonl"

        with open(ds_path, "w", encoding="utf-8") as f:
            for c in cleaned:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

        datasets.append({
            "dataset_id": ds_id,
            "category": cat,
            "sample_count": len(cleaned),
            "file_size": ds_path.stat().st_size,
            "format": "JSONL",
            "price": round(max(99, len(cleaned) * 0.5), 2),  # 定价模型
            "did_tag": DID_TAG,
            "created_at": datetime.now().isoformat(),
        })

    return datasets


def main():
    list_only = "--list" in sys.argv

    if list_only:
        if CATALOG_FILE.exists():
            print(CATALOG_FILE.read_text(encoding="utf-8"))
        else:
            print("暂无数据集，请先运行构建")
        return 0

    log("INFO", "=" * 50)
    log("INFO", "训练数据市场引擎启动 (EVO-P2-001)")
    log("INFO", "=" * 50)

    try:
        from autonomous_kernel import AutonomousKernel
        kernel = AutonomousKernel()
        truths = kernel.truths
        log("INFO", f"加载 {len(truths)} 条真值用于数据集构建")
    except Exception as e:
        log("WARN", f"内核加载失败: {e}")
        truths = []

    datasets = build_datasets(truths)
    log("INFO", f"生成 {len(datasets)} 个数据集")

    catalog = {
        "generated_at": datetime.now().isoformat(),
        "did_tag": DID_TAG,
        "total_datasets": len(datasets),
        "total_samples": sum(d["sample_count"] for d in datasets),
        "datasets": datasets,
    }
    CATALOG_FILE.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    for d in datasets[:5]:
        log("INFO", f"  {d['dataset_id']}: {d['sample_count']} 样本, ¥{d['price']}")
    if len(datasets) > 5:
        log("INFO", f"  ... 共 {len(datasets)} 个数据集")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(0)
