#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从记忆网关9120批量提取高质量真值，转换为训练数据问答对
V2.0修复版：API不支持分页，一次获取所有key，添加多重保护
"""
import requests
import json
import time
import re
import signal
import sys
from typing import List, Dict

GATEWAY_URL = "http://127.0.0.1:9120"
OUTPUT_FILE = "/tmp/memory_gateway_training_data.json"

# 最大运行时间保护（秒）
MAX_RUNTIME = 300  # 5分钟
# 最大提取数量
MAX_TRUTHS = 2000
# 请求间隔（秒）
REQUEST_INTERVAL = 0.1
# 单次批量大小
BATCH_SIZE = 50

start_time = time.time()

def timeout_handler(signum, frame):
    """超时处理"""
    print(f"\n[WARN] 达到最大运行时间 {MAX_RUNTIME}秒，强制停止")
    save_and_exit()

def save_and_exit():
    """保存数据并退出"""
    if 'training_data' in globals():
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        print(f"已保存 {len(training_data)} 条到 {OUTPUT_FILE}")
    sys.exit(0)

# 注册超时信号
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(MAX_RUNTIME)

# 高质量真值关键词筛选
HIGH_QUALITY_KEYWORDS = [
    "identity.", "architecture.", "truth.", "evolution.", "metalaw.",
    "META-", "axiom", "theorem", "method", "protocol", "decision.",
    "TRUTH-FIRST", "HOMO-NODE", "SSH-DISABLE", "ZERO-COST",
    "9120", "HANDshake", "CLOUD-AUTHORITY",
    "ZONGYUAN", "huodouai", "火斗云智", "元极恒一",
    "CTE", "SM-BS", "causal", "singularity", "Merkle",
    "three-dimension", "steady-state", "利益", "风险", "成本",
    "node.", "engineer-node", "compute-node", "central-agent",
    "efuse", "zkp", "zero-knowledge", "security",
    "weak-current", "commercial-dispute", "legal", "contract",
    "GPU-BRAIN", "gpu_brain", "A10", "Qwen",
    "llm.", "model.", "training.", "fine-tune", "lora",
]

# 低质量/不适合作为训练数据的关键词
EXCLUDE_KEYWORDS = [
    "COMPUTE_INJECTION.", "ACHIEVEMENT.", "ACTIVATION.",
    "ADAPTER.TEST", "AGI-", "heartbeat", "ping",
    "log.", "audit.", "backup.", "temp.",
    "2026091", "2026090",  # 带日期的过程记录
    ".T",  # 时间戳后缀
]

def is_high_quality(key: str) -> bool:
    """判断真值key是否为高质量训练数据"""
    key_lower = key.lower()
    for excl in EXCLUDE_KEYWORDS:
        if excl.lower() in key_lower:
            return False
    for kw in HIGH_QUALITY_KEYWORDS:
        if kw.lower() in key_lower:
            return True
    return False

def key_to_question(key: str) -> str:
    """将真值key转换为自然语言问题"""
    q = key
    q = re.sub(r'\.\d{8}.*$', '', q)
    q = re.sub(r'^[A-Z]+\.', '', q)
    q = q.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    q = q.strip()
    if q:
        q = q[0].upper() + q[1:]
    return f"什么是{q}？"

def get_all_truth_keys() -> List[str]:
    """一次获取所有真值key（API不支持分页）"""
    print("[1/4] 一次获取所有真值key（API不支持分页）...")
    try:
        resp = requests.get(f"{GATEWAY_URL}/api/truths", timeout=60)
        data = resp.json()
        keys = data.get("truths", [])
        print(f"  获取到 {len(keys)} 条key")
        return keys
    except Exception as e:
        print(f"  获取失败: {e}")
        return []

def get_truth_value(key: str) -> Dict:
    """获取单个真值的value"""
    try:
        resp = requests.get(f"{GATEWAY_URL}/api/truth/{key}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def main():
    global training_data
    training_data = []
    
    print("=" * 60)
    print("从记忆网关提取高质量真值作为训练数据（V2.0修复版）")
    print(f"保护机制: 最大运行时间{MAX_RUNTIME}秒 / 最大提取{MAX_TRUTHS}条 / 请求间隔{REQUEST_INTERVAL}秒")
    print("=" * 60)
    
    # 1. 一次获取所有key
    all_keys = get_all_truth_keys()
    if not all_keys:
        print("未获取到key，退出")
        return
    
    # 2. 筛选高质量key
    print("\n[2/4] 筛选高质量真值...")
    high_quality_keys = [k for k in all_keys if is_high_quality(k)]
    print(f"  筛选后: {len(high_quality_keys)} 条（从{len(all_keys)}条中）")
    
    # 限制最大数量
    if len(high_quality_keys) > MAX_TRUTHS:
        print(f"  超过最大限制{MAX_TRUTHS}，截取前{MAX_TRUTHS}条")
        high_quality_keys = high_quality_keys[:MAX_TRUTHS]
    
    print("\n  示例key:")
    for k in high_quality_keys[:10]:
        print(f"    - {k}")
    
    # 3. 批量获取value
    print(f"\n[3/4] 批量获取真值内容（{len(high_quality_keys)}条，限速{REQUEST_INTERVAL}s/次）...")
    success_count = 0
    fail_count = 0
    
    for i, key in enumerate(high_quality_keys):
        # 检查运行时间
        if time.time() - start_time > MAX_RUNTIME - 10:
            print(f"\n[WARN] 接近最大运行时间，停止提取（已处理{i}条）")
            break
        
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            print(f"  进度: {i+1}/{len(high_quality_keys)} (成功:{success_count}, 失败:{fail_count}, 用时:{elapsed:.0f}s)")
        
        truth_data = get_truth_value(key)
        if truth_data and truth_data.get("truth_value"):
            value = str(truth_data.get("truth_value", ""))
            if 10 < len(value) < 2000:
                question = key_to_question(key)
                training_data.append({
                    "question": question,
                    "answer": value,
                    "truth_key": key,
                    "category": truth_data.get("meta_class", truth_data.get("category", "unknown")),
                    "source": "memory_gateway_9120"
                })
                success_count += 1
            else:
                fail_count += 1
        else:
            fail_count += 1
        
        time.sleep(REQUEST_INTERVAL)
    
    # 4. 保存
    print(f"\n[4/4] 保存训练数据...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"提取完成！用时{elapsed:.0f}秒")
    print(f"  总key数: {len(all_keys)}")
    print(f"  高质量key数: {len(high_quality_keys)}")
    print(f"  成功提取: {success_count} 条")
    print(f"  失败/过滤: {fail_count} 条")
    print(f"  保存路径: {OUTPUT_FILE}")
    print(f"{'='*60}")
    
    # 分类统计
    from collections import Counter
    categories = Counter(d.get("category", "unknown") for d in training_data)
    print("\n分类统计:")
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}")
    
    # 示例
    print("\n示例数据:")
    for d in training_data[:3]:
        print(f"\n  Q: {d['question']}")
        print(f"  A: {d['answer'][:100]}...")
        print(f"  来源: {d['truth_key']} ({d['category']})")

if __name__ == "__main__":
    main()
