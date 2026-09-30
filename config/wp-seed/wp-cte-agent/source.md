---
name: cte-agent
description: "CTE-Agent V3.0 三位一体自洽智能体。ZONGYUAN-ROOT V4.0阶段三。从闭环引擎升级为自洽智能体，实现Lv8完全自治。五大核心组件：TrinityAgentCore+AutonomousProblemDetector+SelfVerifyingTruthEngine+EvolutionaryStrategyGenerator+AgentMemorySystem。完整智能体循环：感知→推理→决策→行动→学习。触发词：CTE-Agent、自洽智能体、三位一体智能体、Lv8自治、自主问题发现、自校验真值、进化策略生成、智能体记忆。"
version: 3.0.0
author: 元极恒一自治体系
---

# CTE-Agent V3.0｜三位一体自洽智能体

ZONGYUAN-ROOT V4.0 阶段三。从"闭环引擎"升级为"自洽智能体"，Lv8完全自治。

> DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 版本: V3.0 | 自治等级: Lv8

## 五大核心组件

| 组件 | 脚本 | 功能 |
|------|------|------|
| TrinityAgentCore | trinity_agent_core.py | 整合闭环引擎+自主决策+环境感知，完整智能体循环 |
| AutonomousProblemDetector | detector_verifier.py | 基于因果推理自动发现系统瓶颈、知识空白、进化方向 |
| SelfVerifyingTruthEngine | detector_verifier.py | 真值提炼后自动进行多轮交叉校验（因果+逻辑+历史） |
| EvolutionaryStrategyGenerator | trinity_agent_core.py | 基于真值校验和因果推理自动生成进化策略并执行 |
| AgentMemorySystem | agent_memory.py | 四层记忆架构，经验积累与迁移学习，跨任务知识复用 |

## 完整智能体循环

```
感知(Perceive) → 推理(Reason) → 决策(Decide) → 行动(Act) → 学习(Learn)
```

## 四层记忆架构

L1工作记忆 | L2情景记忆 | L3语义记忆 | L4程序记忆

## 自治指标（Lv8目标）

自主问题发现率>90% | 真值自校验通过率>95% | 进化策略成功率>80% | 人工干预0次

## 命令速查

```bash
python3 scripts/cte_agent.py --cycles 5    # 运行5轮自洽循环
python3 scripts/cte_agent.py --single-cycle # 单轮循环
python3 scripts/cte_agent.py --status       # 查看状态
python3 scripts/cte_agent.py --memory       # 查看记忆系统
```

## 约束

- Lv8完全自治意味着零人工干预，但保留紧急人工干预接口
- 所有产出遵循元秩序归档规范，DID固定为 DID-BR-000002
