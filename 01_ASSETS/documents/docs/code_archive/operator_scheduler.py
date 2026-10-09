#!/usr/bin/env python3
"""ZONGYUAN-ROOT 27算子调度唤醒中枢 V1.0"""
import json, os, sys
from datetime import datetime

OPERATORS = {
    "layer1": {"name": "第一层：真值过滤", "ops": {
        "P4_truth_reconciliation": {"name": "P4真值对账", "trigger": "new_truth_arrived", "status": "sleeping", "cost": "low"},
        "P7_external_anchoring": {"name": "P7外部锚定", "trigger": "P4_completed", "status": "sleeping", "cost": "medium"},
        "truth_distillation": {"name": "真值提炼蒸馏", "trigger": "P7_completed", "status": "sleeping", "cost": "high"}
    }},
    "layer2": {"name": "第二层：流形度量", "ops": {
        "riemann_metric": {"name": "黎曼流形度量", "trigger": "truth_distilled", "status": "sleeping"},
        "sm_bs_mapping": {"name": "SM-BS双向映射", "trigger": "riemann_completed", "status": "sleeping"},
        "drift_inspection": {"name": "漂移巡检量化", "trigger": "scheduled_daily", "status": "sleeping"}
    }},
    "layer3": {"name": "第三层：知识图谱", "ops": {
        "entity_relation_extraction": {"name": "实体关系抽取", "trigger": "truth_distilled", "status": "sleeping"},
        "kg_completion": {"name": "知识图谱补全", "trigger": "extraction_completed", "status": "sleeping"},
        "cross_doc_entity_linking": {"name": "跨文档实体链接", "trigger": "extraction_completed", "status": "sleeping"}
    }},
    "layer4": {"name": "第四层：因果推理", "ops": {
        "causal_chain_trace": {"name": "因果链溯源", "trigger": "decision_requested", "status": "sleeping"},
        "singularity_prediction": {"name": "奇点概率预测", "trigger": "causal_completed", "status": "sleeping"},
        "causal_intervention": {"name": "因果干预模拟", "trigger": "singularity_completed", "status": "sleeping"}
    }},
    "layer5": {"name": "第五层：CTE适配器", "ops": {
        "causal_to_truth": {"name": "CausalToTruth", "trigger": "causal_completed", "status": "sleeping"},
        "truth_to_evolution": {"name": "TruthToEvolution", "trigger": "truth_updated", "status": "sleeping"},
        "evolution_to_causal": {"name": "EvolutionToCausal", "trigger": "evolution_completed", "status": "sleeping"}
    }},
    "layer6": {"name": "第六层：结构化归档", "ops": {
        "four_layer_structuring": {"name": "四层结构化拆分", "trigger": "new_asset_arrived", "status": "sleeping"},
        "nine_metaclass": {"name": "九大元类归类", "trigger": "structuring_completed", "status": "sleeping"},
        "merkle_dag_append": {"name": "Merkle-DAG追加", "trigger": "classification_completed", "status": "sleeping"}
    }},
    "layer7": {"name": "第七层：资产对账", "ops": {
        "feishu_m9_reconciliation": {"name": "飞书M9对账巡检", "trigger": "scheduled_daily", "status": "sleeping"}
    }},
    "layer8": {"name": "第八层：安全确权", "ops": {
        "efuse_circuit_breaker": {"name": "eFuse熔断触发", "trigger": "critical_conflict", "status": "sleeping"},
        "zkp_privacy_verify": {"name": "ZKP零知识校验", "trigger": "sensitive_data", "status": "sleeping"}
    }},
    "layer9": {"name": "第九层：决策法律", "ops": {
        "solution_generation": {"name": "方案生成评估", "trigger": "decision_requested", "status": "sleeping"},
        "risk_identification": {"name": "风险识别分级", "trigger": "solution_generated", "status": "sleeping"},
        "legal_opinion": {"name": "法律意见书生成", "trigger": "risk_identified", "status": "sleeping"}
    }},
    "layer10": {"name": "第十层：业务约束", "ops": {
        "lv6_civilization": {"name": "Lv6文明仿真约束", "trigger": "simulation_requested", "status": "sleeping"},
        "character_metarule": {"name": "角色元规则隔离", "trigger": "character_generation", "status": "sleeping"},
        "drama_keyframe": {"name": "9:16关键帧一致性", "trigger": "keyframe_generation", "status": "sleeping"}
    }}
}

class Scheduler:
    def __init__(self):
        self.state_file = "/opt/ZONGYUAN-ROOT/data/operator_scheduler_state.json"
        self.load()

    def load(self):
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                self.state = json.load(f)
        else:
            self.state = {"awakened": [], "log": []}

    def save(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def wake(self, op_id, reason=""):
        for layer_id, layer in OPERATORS.items():
            if op_id in layer["ops"]:
                layer["ops"][op_id]["status"] = "awakened"
                layer["ops"][op_id]["last_awakened"] = datetime.now().isoformat()
                if op_id not in self.state["awakened"]:
                    self.state["awakened"].append(op_id)
                self.state["log"].append({"time": datetime.now().isoformat(), "op": op_id, "action": "awakened", "reason": reason})
                self.save()
                return True
        return False

    def handle_event(self, event_type):
        awakened = []
        for layer_id, layer in OPERATORS.items():
            for op_id, op in layer["ops"].items():
                if op.get("trigger") == event_type:
                    if self.wake(op_id, "event:" + event_type):
                        awakened.append(op_id)
        return awakened

    def status(self):
        total = 0
        awakened_list = self.state.get("awakened", [])
        for layer_id, layer in OPERATORS.items():
            for op_id, op in layer["ops"].items():
                total += 1
        awakened = len(awakened_list)
        sleeping = total - awakened
        return {"total": total, "awakened": awakened, "sleeping": sleeping, "rate": str(round(awakened/total*100, 1)) + "%", "layers": len(OPERATORS), "awakened_list": awakened_list}

    def list_sleeping(self):
        result = []
        awakened_list = self.state.get("awakened", [])
        for layer_id, layer in OPERATORS.items():
            for op_id, op in layer["ops"].items():
                if op_id not in awakened_list:
                    result.append({"layer": layer["name"], "id": op_id, "name": op["name"], "trigger": op["trigger"]})
        return result

if __name__ == "__main__":
    s = Scheduler()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(s.status(), indent=2, ensure_ascii=False))
        elif cmd == "sleeping":
            print(json.dumps(s.list_sleeping(), indent=2, ensure_ascii=False))
        elif cmd == "wake" and len(sys.argv) > 2:
            r = s.wake(sys.argv[2], "manual")
            msg = "成功" if r else "失败(未找到)"
            print("唤醒" + sys.argv[2] + ": " + msg)
        elif cmd == "event" and len(sys.argv) > 2:
            print(json.dumps(s.handle_event(sys.argv[2]), ensure_ascii=False))
    else:
        print(json.dumps(s.status(), indent=2, ensure_ascii=False))
