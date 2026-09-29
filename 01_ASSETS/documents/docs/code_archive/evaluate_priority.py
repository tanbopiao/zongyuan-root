import sys
sys.path.insert(0, '/opt/ZONGYUAN-ROOT')
from engine.axiom.decision.axiom_decision_engine import get_decision_engine

engine = get_decision_engine()

options = [
    {
        "option_id": "OPT-1",
        "name": "公理体系白皮书",
        "description": "撰写完整的公理体系技术白皮书",
        "benefit": 88, "risk": 10, "cost": 25, "feasibility": 92,
        "truth_basis": True, "truth_confidence": 0.90,
        "resource_consumption": {"cpu": 15, "memory": 20, "network": 5},
        "risks": ["文档较长"], "benefits": ["体系化理论", "对外展示价值高"],
    },
    {
        "option_id": "OPT-2",
        "name": "公理可视化增强",
        "description": "增加公理演化时间轴、热力图、影响力分析",
        "benefit": 75, "risk": 12, "cost": 30, "feasibility": 85,
        "truth_basis": True, "truth_confidence": 0.85,
        "resource_consumption": {"cpu": 20, "memory": 25, "network": 8},
        "risks": ["ECharts较复杂"], "benefits": ["增强展示效果"],
    },
    {
        "option_id": "OPT-3",
        "name": "决策历史可视化页面",
        "description": "构建决策历史可视化页面",
        "benefit": 70, "risk": 10, "cost": 28, "feasibility": 88,
        "truth_basis": True, "truth_confidence": 0.82,
        "resource_consumption": {"cpu": 18, "memory": 22, "network": 6},
        "risks": ["数据量较少"], "benefits": ["决策可追溯"],
    },
    {
        "option_id": "OPT-4",
        "name": "多智能体仲裁机制",
        "description": "构建多智能体仲裁机制",
        "benefit": 72, "risk": 20, "cost": 40, "feasibility": 70,
        "truth_basis": True, "truth_confidence": 0.75,
        "resource_consumption": {"cpu": 30, "memory": 35, "network": 15},
        "risks": ["协调较复杂"], "benefits": ["决策更民主"],
    },
    {
        "option_id": "OPT-5",
        "name": "决策引擎集成到MR-010调度器",
        "description": "将公理决策引擎集成到调度器",
        "benefit": 95, "risk": 25, "cost": 35, "feasibility": 75,
        "truth_basis": True, "truth_confidence": 0.80,
        "resource_consumption": {"cpu": 25, "memory": 30, "network": 10},
        "risks": ["修改风险高"], "benefits": ["决策落地到运行系统", "最高价值"],
    },
]

result = engine.evaluate_plans(
    title="公理体系后续工作优先级评估",
    description="基于三维稳态公理评估5个后续工作选项",
    options=options,
)

print("=== 公理决策引擎评估结果 ===")
print("推荐优先执行: " + result.recommended_option)
print("综合得分: " + str(result.overall_score))
print("置信度: " + str(result.confidence))
print("需人工审核: " + str(result.needs_human_review))
print()
print("=== 最优稳态执行顺序（从高到低）===")
for i, opt in enumerate(result.options, 1):
    print(str(i) + ". " + opt.name + " (" + opt.option_id + "): " + str(opt.score) + "分")
    print("   利益" + str(opt.benefit) + "/风险" + str(opt.risk) + "/成本" + str(opt.cost) + "/可行性" + str(opt.feasibility))
    print()

print("=== 决策推理 ===")
for reasoning in result.decision_reasoning:
    print("  - " + reasoning)
