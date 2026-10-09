import json, copy
from pathlib import Path

class SelfEvolutionEngine:
    def __init__(self, root_path: Path, fitness_cfg: dict):
        self.root = root_path
        self.fitness = fitness_cfg
        self.gen_log_path = self.root / "data/evolution/generation_log.json"
        self.gen_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.gen_log_path.exists():
            self.write_gen_log({"generations": []})

    def write_gen_log(self, data: dict):
        with open(self.gen_log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def read_gen_log(self) -> dict:
        with open(self.gen_log_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def calc_phi(self, truth_score: float, drift_rate: float, op_success: float, health: float) -> float:
        w1 = self.fitness.get("w1", 0.4)
        w2 = self.fitness.get("w2", 0.3)
        w3 = self.fitness.get("w3", 0.2)
        w4 = self.fitness.get("w4", 0.1)
        # 所有指标归一化到0-1范围
        phi = w1 * (truth_score / 100.0) + w2 * (1.0 - drift_rate / 100.0) + w3 * op_success + w4 * (health / 100.0)
        return round(phi, 4)

    def generate_candidate_baseline(self, parent_config: dict, guard: dict) -> dict:
        new_cfg = copy.deepcopy(parent_config)
        max_delta = guard.get("max_single_adjust", 0.05)
        if "drift_warning_threshold" in new_cfg:
            delta = min(max_delta, max(-max_delta, 0.01))
            new_cfg["drift_warning_threshold"] = round(new_cfg["drift_warning_threshold"] + delta, 4)
        return new_cfg

    def record_generation(self, gen_id: int, phi: float, baseline_snapshot: dict, status="stable"):
        log = self.read_gen_log()
        log["generations"].append({
            "gen_id": gen_id, "phi": phi, "baseline": baseline_snapshot, "status": status
        })
        self.write_gen_log(log)
