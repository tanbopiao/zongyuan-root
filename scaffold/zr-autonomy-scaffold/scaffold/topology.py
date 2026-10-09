#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拓扑定义：十层依赖拓扑 + 27 大算子注册表
每算子：id / 名称 / 层级 / 消耗级别(light|heavy) / 轻量模式是否跳过深度计算
"""
OPERATOR_REGISTRY = [
    # 第一层：真值过滤与深度蒸馏
    {"id": "P4_TRUTH_RECONCILE",   "name": "P4真值对账算子",           "layer": 1, "cost": "light"},
    {"id": "P7_EXTERNAL_ANCHOR",   "name": "P7外部锚定算子",           "layer": 1, "cost": "light"},
    {"id": "TRUTH_DISTILL",        "name": "真值提炼蒸馏算子",         "layer": 1, "cost": "heavy"},
    # 第二层：流形度量与 SM-BS 稳态映射
    {"id": "RIEMANN_METRIC",       "name": "黎曼流形世界模型度量算子", "layer": 2, "cost": "light"},
    {"id": "SM_BS_STEADY_MAP",     "name": "SM-BS双向稳态映射算子",    "layer": 2, "cost": "heavy"},
    {"id": "DRIFT_QUANTIZE",       "name": "漂移巡检量化算子",         "layer": 2, "cost": "light"},
    # 第三层：知识图谱秩序化重建
    {"id": "ENTITY_RELATION_EXTRACT", "name": "实体关系抽取算子",      "layer": 3, "cost": "light"},
    {"id": "KG_COMPLETION",        "name": "知识图谱补全算子",         "layer": 3, "cost": "light"},
    {"id": "CROSS_DOC_ENTITY_LINK",   "name": "跨文档实体链接算子",    "layer": 3, "cost": "light"},
    # 第四层：因果级推理
    {"id": "CAUSAL_TRACE",         "name": "因果链溯源回溯算子",       "layer": 4, "cost": "light"},
    {"id": "SINGULARITY_PREDICT",  "name": "奇点概率预测算子",         "layer": 4, "cost": "light"},
    {"id": "CAUSAL_INTERVENE",     "name": "因果干预模拟算子",         "layer": 4, "cost": "light"},
    # 第五层：CTE 三位一体适配器流转
    {"id": "CAUSAL_TO_TRUTH",      "name": "CausalToTruth适配器",     "layer": 5, "cost": "heavy"},
    {"id": "TRUTH_TO_EVOLUTION",   "name": "TruthToEvolution适配器",  "layer": 5, "cost": "heavy"},
    {"id": "EVOLUTION_TO_CAUSAL",  "name": "EvolutionToCausal适配器", "layer": 5, "cost": "light"},
    # 第六层：结构化归档深化
    {"id": "FOUR_LAYER_SPLIT",     "name": "四层结构化拆分算子",       "layer": 6, "cost": "light"},
    {"id": "NINE_META_CLASS",      "name": "九大元类归类算子",         "layer": 6, "cost": "light"},
    {"id": "MERKLE_DAG_APPEND",    "name": "Merkle-DAG主链追加校验",   "layer": 6, "cost": "light"},
    # 第七层：资产对账治理
    {"id": "FEISHU_LEDGER_RECON",  "name": "飞书资源↔M9账本对账巡检", "layer": 7, "cost": "light"},
    # 第八层：安全确权
    {"id": "EFUSE_TRIGGER",        "name": "eFuse熔断触发算子",       "layer": 8, "cost": "light"},
    {"id": "ZKP_VERIFY",           "name": "ZKP零知识隐私校验算子",   "layer": 8, "cost": "light"},
    # 第九层：决策与法律护盾
    {"id": "PLAN_GENERATE_EVAL",   "name": "方案生成评估算子",         "layer": 9, "cost": "light"},
    {"id": "RISK_IDENTIFY",        "name": "风险识别分级算子",         "layer": 9, "cost": "light"},
    {"id": "LEGAL_OPINION",        "name": "法律意见书生成算子",       "layer": 9, "cost": "heavy"},
    # 第十层：业务实体约束
    {"id": "LV6_SIM_CONSTRAINT",   "name": "Lv6多主体文明仿真约束",   "layer": 10, "cost": "light"},
    {"id": "ROLE_META_ISOLATION",  "name": "角色元规则隔离校验",       "layer": 10, "cost": "light"},
    {"id": "KEYFRAME_CONSISTENCY", "name": "9:16国风关键帧一致性",    "layer": 10, "cost": "light"},
]

LAYER_TOPOLOGY = {layer: [op["id"] for op in OPERATOR_REGISTRY if op["layer"] == layer]
                  for layer in range(1, 11)}

HEAVY_OPS = [op["id"] for op in OPERATOR_REGISTRY if op["cost"] == "heavy"]


def validate_topology():
    """校验拓扑完整性：27 算子、十层齐全、无重复 id"""
    assert len(OPERATOR_REGISTRY) == 27, f"算子数量异常: {len(OPERATOR_REGISTRY)}"
    assert set(LAYER_TOPOLOGY.keys()) == set(range(1, 11)), "十层不齐全"
    ids = [op["id"] for op in OPERATOR_REGISTRY]
    assert len(ids) == len(set(ids)), "存在重复算子 id"
    return True


if __name__ == "__main__":
    validate_topology()
    print(f"拓扑校验通过：27 算子 / {len(LAYER_TOPOLOGY)} 层 / 重消耗算子 {len(HEAVY_OPS)} 个")
    for layer in range(1, 11):
        print(f"  L{layer}: {', '.join(LAYER_TOPOLOGY[layer])}")
