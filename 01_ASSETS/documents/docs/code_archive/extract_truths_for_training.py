#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从记忆网关9120批量提取高质量真值，转换为训练数据问答对
"""
import requests
import json
import time
import re
from typing import List, Dict

GATEWAY_URL = "http://127.0.0.1:9120"
OUTPUT_FILE = "/tmp/memory_gateway_training_data.json"

# 高质量真值关键词筛选
HIGH_QUALITY_KEYWORDS = [
    # 体系核心
    "identity.", "architecture.", "truth.", "evolution.", "metalaw.",
    "META-", "axiom", "theorem", "method", "protocol", "decision.",
    # 元法则
    "TRUTH-FIRST", "HOMO-NODE", "SSH-DISABLE", "ZERO-COST",
    "9120", "HANDshake", "CLOUD-AUTHORITY",
    # 品牌
    "ZONGYUAN", "huodouai", "火斗云智", "元极恒一",
    # 技术架构
    "CTE", "SM-BS", "causal", "singularity", "Merkle",
    # 决策
    "three-dimension", "steady-state", "利益", "风险", "成本",
    # 节点
    "node.", "engineer-node", "compute-node", "central-agent",
    # 安全
    "efuse", "zkp", "zero-knowledge", "security",
    # 业务
    "weak-current", "commercial-dispute", "legal", "contract",
]

# 低质量/不适合作为训练数据的关键词
EXCLUDE_KEYWORDS = [
    "COMPUTE_INJECTION.", "ACHIEVEMENT.", "ACTIVATION.",
    "ADAPTER.TEST", "AGI-", "heartbeat", "ping",
    "log.", "audit.", "backup.", "temp.",
]

def is_high_quality(key: str) -> bool:
    """判断真值key是否为高质量训练数据"""
    key_lower = key.lower()
    
    # 排除低质量
    for excl in EXCLUDE_KEYWORDS:
        if excl.lower() in key_lower:
            return False
    
    # 包含高质量关键词
    for kw in HIGH_QUALITY_KEYWORDS:
        if kw.lower() in key_lower:
            return True
    
    return False

def key_to_question(key: str, value: str) -> str:
    """将真值key转换为自然语言问题"""
    # 移除前缀和日期后缀
    q = key
    q = re.sub(r'\.\d{8}.*$', '', q)  # 移除日期后缀
    q = re.sub(r'^[A-Z]+\.', '', q)  # 移除分类前缀
    
    # 转换点分隔为空格
    q = q.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    
    # 首字母大写
    q = q.strip()
    if q:
        q = q[0].upper() + q[1:]
    
    return f"什么是{q}？"

def get_all_truth_keys() -> List[str]:
    """获取所有真值key列表"""
    all_keys = []
    offset = 0
    limit = 5000
    
    while True:
        try:
            resp = requests.get(
                f"{GATEWAY_URL}/api/truths",
                params={"offset": offset, "limit": limit},
                timeout=30
            )
            data = resp.json()
            keys = data.get("truths", [])
            if not keys:
                break
            all_keys.extend(keys)
            print(f"  获取key列表: {len(all_keys)}/{data.get('count', '?')}")
            if len(keys) < limit:
                break
            offset += limit
            time.sleep(0.1)
        except Exception as e:
            print(f"  获取key列表失败: {e}")
            break
    
    return all_keys

def get_truth_value(key: str) -> Dict:
    """获取单个真值的value"""
    try:
        resp = requests.get(
            f"{GATEWAY_URL}/api/truth/{key}",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data
    except Exception as e:
        pass
    return None

def main():
    print("=" * 60)
    print("从记忆网关提取高质量真值作为训练数据")
    print("=" * 60)
    
    # 1. 获取所有key
    print("\n[1/4] 获取所有真值key列表...")
    all_keys = get_all_truth_keys()
    print(f"  总计: {len(all_keys)} 条真值")
    
    # 2. 筛选高质量key
    print("\n[2/4] 筛选高质量真值...")
    high_quality_keys = [k for k in all_keys if is_high_quality(k)]
    print(f"  筛选后: {len(high_quality_keys)} 条高质量真值")
    
    # 显示筛选出的key示例
    print("\n  示例key:")
    for k in high_quality_keys[:20]:
        print(f"    - {k}")
    
    # 3. 批量获取value
    print(f"\n[3/4] 批量获取真值内容（{len(high_quality_keys)}条）...")
    training_data = []
    success_count = 0
    fail_count = 0
    
    for i, key in enumerate(high_quality_keys):
        if (i + 1) % 50 == 0:
            print(f"  进度: {i+1}/{len(high_quality_keys)} (成功: {success_count}, 失败: {fail_count})")
        
        truth_data = get_truth_value(key)
        if truth_data and truth_data.get("truth_value"):
            value = str(truth_data.get("truth_value", ""))
            # 过滤掉太短或太长的value
            if 10 < len(value) < 2000:
                question = key_to_question(key, value)
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
        
        # 限速
        time.sleep(0.05)
    
    # 4. 保存
    print(f"\n[4/4] 保存训练数据...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"提取完成！")
    print(f"  总key数: {len(all_keys)}")
    print(f"  高质量key数: {len(high_quality_keys)}")
    print(f"  成功提取: {success_count} 条")
    print(f"  失败/过滤: {fail_count} 条")
    print(f"  保存路径: {OUTPUT_FILE}")
    print(f"{'='*60}")
    
    # 显示分类统计
    from collections import Counter
    categories = Counter(d.get("category", "unknown") for d in training_data)
    print("\n分类统计:")
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}")
    
    # 显示示例
    print("\n示例数据:")
    for d in training_data[:5]:
        print(f"\n  Q: {d['question']}")
        print(f"  A: {d['answer'][:100]}...")
        print(f"  来源: {d['truth_key']} ({d['category']})")

if __name__ == "__main__":
    main()
