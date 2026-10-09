import sys
sys.path.insert(0, "/opt/ZONGYUAN-ROOT/ai-native-ops")
from operator_scheduler import OperatorScheduler

scheduler = OperatorScheduler()

operators_to_awaken = [
    "P7_external_anchoring",
    "truth_distillation",
    "riemann_metric",
    "sm_bs_mapping",
    "drift_detection",
    "entity_relation_extraction",
    "knowledge_graph_completion",
    "cross_document_entity_linking",
    "singularity_prediction",
    "causal_intervention_simulation",
    "risk_identification",
    "legal_opinion_generation",
]

print("批量唤醒关键算子...")
awakened = 0
for op_id in operators_to_awaken:
    result = scheduler.awaken_operator(op_id, reason="批量唤醒-提升体系能力")
    if result.get("success", False):
        awakened += 1
        print("  [OK] " + op_id)
    else:
        msg = result.get("message", "already awakened")
        print("  [SKIP] " + op_id + ": " + str(msg))

print("")
print("本次唤醒: " + str(awakened) + " 个算子")
status = scheduler.get_status()
print("当前已唤醒: " + str(status["awakened"]) + "/" + str(status["total"]) + " (" + status["rate"] + ")")
