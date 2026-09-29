import json
from pathlib import Path
from datetime import datetime
from .self_learning import SelfLearningEngine
from .self_evolution import SelfEvolutionEngine
from .self_optimization import SelfOptimizationEngine

class TriadOrchestrator:
    def __init__(self, base_path=None):
        if base_path is None:
            base_path = Path(__file__).parent
        self.base = Path(base_path)
        cfg_fit = json.loads((self.base / "config/fitness_weight.json").read_text(encoding="utf-8"))
        cfg_safe = json.loads((self.base / "config/safety_guard.json").read_text(encoding="utf-8"))
        self.learn = SelfLearningEngine(self.base)
        self.evo = SelfEvolutionEngine(self.base, cfg_fit)
        self.opt = SelfOptimizationEngine(self.base, cfg_safe)

    def run_full_cycle(self, inspect_report_path: str):
        date_tag = datetime.utcnow().strftime("%Y%m%d")
        report = self.learn.load_inspection_report(Path(inspect_report_path))

        # Step1 自学习蒸馏
        distilled = self.learn.distill_pattern(report)
        learn_file = self.learn.save_distilled(distilled, date_tag)

        # Step2 自进化计算适应度Φ
        truth = report.get("truth_purity", 96.0)
        drift = report.get("drift_rate", 1.2)
        op_success = report.get("op_success_rate", 0.963)
        health = report.get("health_score", 97)
        phi = self.evo.calc_phi(truth, drift, op_success, health)

        parent_cfg = {"drift_warning_threshold": 10.0}
        candidate_baseline = self.evo.generate_candidate_baseline(parent_cfg, {})

        gen_list = self.evo.read_gen_log()["generations"]
        next_gen = len(gen_list) + 1
        self.evo.record_generation(next_gen, phi, candidate_baseline)

        # Step3 自优化输出配置补丁
        patch = self.opt.build_patch(candidate_baseline, next_gen)
        patch_path = self.opt.export_patch_file(patch, next_gen)

        return {
            "cycle_date": date_tag,
            "generation": next_gen,
            "phi": phi,
            "distilled_count": len(distilled),
            "distilled_file": learn_file,
            "config_patch": patch_path,
            "status": "TRIAD_CYCLE_COMPLETE"
        }
