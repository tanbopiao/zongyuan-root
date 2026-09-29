#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 自研小模型训练数据生成器（外部API版）
利用云端中枢的免费API并行生成高质量训练数据
比本地7B大脑快5-10倍
"""
import sys
import os
import json
import time
from typing import List, Dict

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unified_llm_api import UnifiedLLMAPI, quick_chat

# 训练数据维度
DIMENSIONS = {
    "体系架构": [
        "什么是元极恒一自治体系？",
        "ZONGYUAN-ROOT的核心架构是什么？",
        "Lv10超认知永恒自治是什么意思？",
        "元极恒一体系分为哪几类节点？",
        "元极恒一的最高指导理论是什么？",
        "六态运行模式是什么？",
        "四网体系是什么？",
        "元极恒一体系的发展历程是怎样的？",
        "ZONGYUAN-ROOT V4.0阶段有哪些？",
        "元极恒一体系与传统AI系统有什么区别？",
    ],
    "决策理论": [
        "三维稳态决策公式是什么？",
        "为什么利益占40%、风险占35%、成本占25%？",
        "如何用三维稳态公式做决策？",
        "三维稳态决策的适用场景是什么？",
        "什么是最优稳态解？",
        "决策时如何平衡利益、风险和成本？",
        "元极恒一体系的决策流程是怎样的？",
        "什么是熵减收敛归一？",
        "如何评估一个决策的质量？",
        "三维稳态决策与传统决策方法有什么区别？",
    ],
    "真值体系": [
        "9120记忆网关的作用是什么？",
        "什么是真值库？",
        "真值蒸馏的过程是怎样的？",
        "如何保证真值的纯度？",
        "真值冲突如何消解？",
        "什么是真值对账算子？",
        "外部锚定算子的作用是什么？",
        "真值纯度评分如何计算？",
        "真值库的规模有多大？",
        "如何向真值库写入新真值？",
    ],
    "节点体系": [
        "工程师节点的职责是什么？",
        "算力节点的职责是什么？",
        "中枢智能的职责是什么？",
        "节点之间如何通信？",
        "节点注册的流程是怎样的？",
        "什么是节点心跳？",
        "节点故障如何处理？",
        "如何新增一个节点？",
        "节点权限如何管理？",
        "节点之间的协作机制是什么？",
    ],
    "元法则": [
        "SSH禁用元法则的核心内容是什么？",
        "为什么要禁用SSH直连？",
        "零成本优先调度的原则是什么？",
        "唯一握手点9120是什么意思？",
        "本地与云端如何同步？",
        "什么是云端权威源？",
        "真值优先原则是什么？",
        "如何保证操作的可追溯性？",
        "元法则的优先级如何排序？",
        "违反元法则会有什么后果？",
    ],
    "进化体系": [
        "什么是元学习自进化？",
        "主动真值校验网络是什么？",
        "系统如何自主进化？",
        "进化的驱动力是什么？",
        "什么是适应度Φ？",
        "进化压力来自哪里？",
        "如何评估进化的效果？",
        "进化与学习有什么区别？",
        "系统的进化方向是什么？",
        "什么是Lv8完全自治？",
    ],
    "品牌体系": [
        "火斗云智AIOS是什么？",
        "火斗云智的核心理念是什么？",
        "昆仑洞天是什么？",
        "九天玄女是谁？",
        "太阴月神是谁？",
        "女娲是谁？",
        "东方神话AI创世宇宙是什么？",
        "火斗云智与ZONGYUAN-ROOT的关系是什么？",
        "对外品牌如何统一？",
        "内部体系名称是什么？",
    ],
    "安全体系": [
        "eFuse熔断触发算子的作用是什么？",
        "什么是ZKP零知识隐私校验？",
        "Merkle-DAG主链是什么？",
        "如何防止哈希链篡改？",
        "什么是局部分支熔断隔离？",
        "敏感数据如何保护？",
        "账本完整性如何核验？",
        "什么是确权标识？",
        "DID-BR-000002是什么？",
        "Ω₀⊂⊙∞⊂Ω是什么意思？",
    ],
    "业务体系": [
        "弱电工程业务的流程是什么？",
        "商业纠纷台账如何管理？",
        "方案生成评估算子的作用是什么？",
        "风险识别分级算子如何工作？",
        "法律意见书生成算子的流程是什么？",
        "如何评估一个业务方案的风险？",
        "合同审查的要点是什么？",
        "什么是三维稳态评估？",
        "业务决策的流程是怎样的？",
        "如何生成多套备选方案？",
    ],
    "技术栈": [
        "CTE三位一体适配器是什么？",
        "CausalToTruth适配器的作用是什么？",
        "TruthToEvolution适配器的作用是什么？",
        "EvolutionToCausal适配器的作用是什么？",
        "什么是SM-BS双向稳态映射？",
        "黎曼流形世界模型度量算子是什么？",
        "因果奇点内核的作用是什么？",
        "什么是因果链溯源回溯？",
        "奇点概率预测如何计算？",
        "因果干预模拟的原理是什么？",
    ],
}

SYSTEM_PROMPT = """你是ZONGYUAN-ROOT元极恒一自治体系的知识专家。
请准确、简洁、专业地回答关于元极恒一体系的问题。
要求：
1. 回答必须基于元极恒一体系的真实概念和架构
2. 语言简洁明了，避免冗余
3. 专业术语准确
4. 每个回答控制在100-300字之间
5. 不要编造不存在的概念"""

def generate_qa_for_dimension(dimension: str, questions: List[str], 
                                api: UnifiedLLMAPI, num_variants: int = 2) -> List[Dict]:
    """为一个维度生成问答对"""
    pairs = []
    
    # 为每个问题生成回答
    messages_list = []
    for q in questions:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q}
        ]
        messages_list.append(messages)
    
    # 并行调用
    print(f"  并行调用 {len(messages_list)} 个问题...")
    results = api.chat_parallel(messages_list, max_workers=5, temperature=0.7, max_tokens=512)
    
    for i, (question, result) in enumerate(zip(questions, results)):
        if "error" not in result and result.get("content"):
            pairs.append({
                "dimension": dimension,
                "question": question,
                "answer": result["content"].strip(),
                "provider": result.get("provider", ""),
                "model": result.get("model", ""),
                "latency": result.get("latency", 0),
                "source": "external_api"
            })
            print(f"    [{i+1}/{len(questions)}] {question[:25]}... OK ({result.get('provider', '')} {result.get('latency', 0):.1f}s)")
        else:
            print(f"    [{i+1}/{len(questions)}] {question[:25]}... FAIL: {result.get('error', 'unknown')}")
    
    # 为每个问题生成变体问题
    if num_variants > 0 and pairs:
        print(f"  生成 {num_variants} 个变体问题...")
        variant_messages = []
        for p in pairs[:5]:  # 只取前5个生成变体，避免太多
            variant_messages.append([
                {"role": "system", "content": "你是一个问题改写专家。请基于给定问题，生成不同表述方式的等价问题。"},
                {"role": "user", "content": f"基于问题'{p['question']}'，生成{num_variants}个不同表述方式的等价问题，每行一个，不要编号，不要解释。"}
            ])
        
        variant_results = api.chat_parallel(variant_messages, max_workers=3, temperature=0.8, max_tokens=300)
        
        for base_pair, v_result in zip(pairs[:5], variant_results):
            if "error" not in v_result and v_result.get("content"):
                for line in v_result["content"].split("\n"):
                    line = line.strip().lstrip("0123456789.、) ")
                    if line and len(line) > 5 and len(line) < 100:
                        # 为变体问题生成回答
                        variant_answer = quick_chat(line, system_prompt=SYSTEM_PROMPT, temperature=0.7, max_tokens=512)
                        if variant_answer.get("content"):
                            pairs.append({
                                "dimension": base_pair["dimension"],
                                "question": line,
                                "answer": variant_answer["content"].strip(),
                                "provider": variant_answer.get("provider", ""),
                                "model": variant_answer.get("model", ""),
                                "latency": variant_answer.get("latency", 0),
                                "source": "external_api_variant",
                                "base_question": base_pair["question"]
                            })
                            print(f"    变体: {line[:30]}... OK")
    
    return pairs

def main():
    print("=" * 60)
    print("ZONGYUAN-ROOT 自研小模型训练数据生成器（外部API版）")
    print("=" * 60)
    
    # 初始化统一API
    api = UnifiedLLMAPI(primary_api="siliconflow", enable_failover=True)
    
    # 测试API连通性
    print("\n[1/3] 测试API连通性...")
    try:
        test_result = quick_chat("请回复'API连接正常'。", temperature=0.1, max_tokens=20)
        print(f"  主API ({test_result.get('provider', '')}): {test_result.get('content', '')[:50]}")
    except Exception as e:
        print(f"  主API测试失败: {e}，将使用故障转移")
    
    # 生成数据
    print(f"\n[2/3] 开始生成训练数据（{len(DIMENSIONS)}个维度，每个维度{len(list(DIMENSIONS.values())[0])}个基础问题）...")
    
    all_pairs = []
    output_dir = "/mnt/workspace/training/data"
    os.makedirs(output_dir, exist_ok=True)
    
    start_time = time.time()
    
    for dimension, questions in DIMENSIONS.items():
        print(f"\n--- 维度: {dimension} ({len(questions)}个基础问题) ---")
        pairs = generate_qa_for_dimension(dimension, questions, api, num_variants=1)
        all_pairs.extend(pairs)
        print(f"  本维度生成: {len(pairs)} 条")
        
        # 每完成一个维度就保存一次
        with open(f"{output_dir}/training_data_external.json", "w", encoding="utf-8") as f:
            json.dump(all_pairs, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - start_time
    
    # 统计
    print(f"\n[3/3] 数据生成完成！")
    print(f"  总计: {len(all_pairs)} 条")
    print(f"  耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print(f"  平均: {elapsed/len(all_pairs):.1f}秒/条")
    print(f"  保存路径: {output_dir}/training_data_external.json")
    
    # 各维度统计
    from collections import Counter
    dim_counts = Counter(p["dimension"] for p in all_pairs)
    print(f"\n各维度数量:")
    for dim, count in dim_counts.items():
        print(f"  {dim}: {count}")
    
    # API使用统计
    provider_counts = Counter(p.get("provider", "unknown") for p in all_pairs)
    print(f"\nAPI使用统计:")
    for provider, count in provider_counts.items():
        print(f"  {provider}: {count}")
    
    print(f"\n{'='*60}")
    print("数据生成完成，可以开始训练了！")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
