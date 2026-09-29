#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本地数据库直接提取高质量真值，转换为训练数据问答对
简单可靠，不依赖API
"""
import sqlite3
import json
import re
import sys

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
OUTPUT_FILE = "/tmp/training_data_from_db.json"
MAX_TRUTHS = int(sys.argv[1]) if len(sys.argv) > 1 else 100

# 高质量真值key关键词
HIGH_QUALITY_KEYWORDS = [
    "identity.", "architecture.", "metalaw.", "truth.", "evolution.",
    "decision.", "method.", "protocol.", "risk.", "security.",
    "META-", "AXIOM", "THEOREM", "METHOD", "PROTOCOL",
    "ZONGYUAN", "huodouai", "元极恒一", "火斗云智",
    "CTE", "SM-BS", "causal", "singularity", "Merkle",
    "three-dimension", "steady-state", "GPU-BRAIN", "gpu_brain",
    "llm.", "model.", "training.", "fine-tune", "lora",
    "node.", "engineer-node", "compute-node", "central-agent",
    "efuse", "zkp", "zero-knowledge",
    "weak-current", "commercial-dispute", "legal", "contract",
    "9120", "HANDshake", "CLOUD-AUTHORITY",
    "TRUTH-FIRST", "HOMO-NODE", "SSH-DISABLE", "ZERO-COST",
]

# 排除关键词
EXCLUDE_KEYWORDS = [
    "COMPUTE_INJECTION.", "ACHIEVEMENT.", "ACTIVATION.",
    "ADAPTER.TEST", "AGI-", "heartbeat", "ping",
    "log.", "audit.", "backup.", "temp.",
    "2026091", "2026090", ".T",
]

def is_high_quality(key):
    key_lower = key.lower()
    for excl in EXCLUDE_KEYWORDS:
        if excl.lower() in key_lower:
            return False
    for kw in HIGH_QUALITY_KEYWORDS:
        if kw.lower() in key_lower:
            return True
    return False

def key_to_question(key):
    q = key
    q = re.sub(r'\.\d{8}.*$', '', q)
    q = re.sub(r'^[A-Z]+\.', '', q)
    q = q.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    q = q.strip()
    if q:
        q = q[0].upper() + q[1:]
    return f"什么是{q}？"

def main():
    print(f"从数据库提取高质量真值（最多{MAX_TRUTHS}条）...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有有效真值
    cursor.execute("""
        SELECT truth_key, truth_value, category, meta_class 
        FROM truths 
        WHERE truth_value IS NOT NULL 
        AND length(truth_value) > 10 
        AND length(truth_value) < 2000
        ORDER BY id
    """)
    all_truths = cursor.fetchall()
    print(f"数据库中有效真值: {len(all_truths)} 条")
    
    # 筛选高质量
    high_quality = []
    for truth_key, truth_value, category, meta_class in all_truths:
        if is_high_quality(truth_key):
            high_quality.append((truth_key, truth_value, category, meta_class))
    
    print(f"筛选后高质量真值: {len(high_quality)} 条")
    
    # 限制数量
    if len(high_quality) > MAX_TRUTHS:
        high_quality = high_quality[:MAX_TRUTHS]
        print(f"截取前{MAX_TRUTHS}条")
    
    # 转换为问答对
    training_data = []
    for truth_key, truth_value, category, meta_class in high_quality:
        question = key_to_question(truth_key)
        training_data.append({
            "question": question,
            "answer": truth_value,
            "truth_key": truth_key,
            "category": meta_class or category or "unknown",
            "source": "memory_gateway_db"
        })
    
    # 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n提取完成！")
    print(f"  保存路径: {OUTPUT_FILE}")
    print(f"  数据条数: {len(training_data)}")
    
    # 分类统计
    from collections import Counter
    categories = Counter(d["category"] for d in training_data)
    print("\n分类统计:")
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}")
    
    # 示例
    print("\n示例数据:")
    for d in training_data[:3]:
        print(f"\n  Q: {d['question']}")
        print(f"  A: {d['answer'][:100]}...")
        print(f"  来源: {d['truth_key']} ({d['category']})")
    
    conn.close()

if __name__ == "__main__":
    main()
