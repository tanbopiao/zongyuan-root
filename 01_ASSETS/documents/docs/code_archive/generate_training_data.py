#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 自研小模型训练数据生成器
利用7B大脑作为教师模型，批量生成高质量问答对
"""
import requests
import json
import time
import random
import os

# 7B大脑地址（GPU实例本地）
BRAIN_URL = "http://127.0.0.1:7861"

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

def call_brain(context, max_retries=3):
    """调用7B大脑生成回答"""
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{BRAIN_URL}/decide",
                json={"context": context},
                timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("decision", "")
            else:
                print(f"  尝试 {attempt+1}/{max_retries} 失败: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  尝试 {attempt+1}/{max_retries} 异常: {e}")
        time.sleep(2)
    return ""

def generate_qa_pairs(dimension, questions, num_per_question=3):
    """为每个问题生成多个变体问答对"""
    pairs = []
    for i, question in enumerate(questions):
        print(f"  [{i+1}/{len(questions)}] {question[:30]}...")
        answer = call_brain(f"请回答以下问题，要求准确、简洁、专业：{question}")
        if answer:
            pairs.append({
                "dimension": dimension,
                "question": question,
                "answer": answer.strip(),
                "source": "7B-teacher"
            })
        # 生成变体问题
        variants = call_brain(f"基于问题'{question}'，生成{num_per_question}个不同表述方式的等价问题，每行一个，不要编号")
        if variants:
            for line in variants.split("\n"):
                line = line.strip().lstrip("0123456789.、) ")
                if line and len(line) > 5:
                    variant_answer = call_brain(f"请回答以下问题，要求准确、简洁、专业：{line}")
                    if variant_answer:
                        pairs.append({
                            "dimension": dimension,
                            "question": line,
                            "answer": variant_answer.strip(),
                            "source": "7B-teacher-variant"
                        })
        time.sleep(0.5)
    return pairs

def main():
    print("=" * 60)
    print("ZONGYUAN-ROOT 自研小模型训练数据生成器")
    print("=" * 60)
    
    # 检查7B大脑可用性
    try:
        health = requests.get(f"{BRAIN_URL}/health", timeout=10)
        print(f"7B大脑状态: {health.json()}")
    except Exception as e:
        print(f"7B大脑不可用: {e}")
        return
    
    all_pairs = []
    output_dir = "/mnt/workspace/training/data"
    os.makedirs(output_dir, exist_ok=True)
    
    for dimension, questions in DIMENSIONS.items():
        print(f"\n{'='*40}")
        print(f"维度: {dimension} ({len(questions)}个基础问题)")
        print(f"{'='*40}")
        
        pairs = generate_qa_pairs(dimension, questions, num_per_question=2)
        all_pairs.extend(pairs)
        print(f"  本维度生成: {len(pairs)} 条")
        
        # 每完成一个维度就保存一次
        with open(f"{output_dir}/training_data_raw.json", "w", encoding="utf-8") as f:
            json.dump(all_pairs, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"数据生成完成！总计: {len(all_pairs)} 条")
    print(f"保存路径: {output_dir}/training_data_raw.json")
    print(f"{'='*60}")
    
    # 统计各维度数量
    from collections import Counter
    dim_counts = Counter(p["dimension"] for p in all_pairs)
    print("\n各维度数量:")
    for dim, count in dim_counts.items():
        print(f"  {dim}: {count}")

if __name__ == "__main__":
    main()
