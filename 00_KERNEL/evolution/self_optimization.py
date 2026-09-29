import json
from pathlib import Path

class SelfOptimizationEngine:
    def __init__(self, root_path: Path, safety_guard: dict):
        self.root = root_path
        self.guard = safety_guard

    def build_patch(self, candidate_baseline: dict, gen_id: int) -> dict:
        return {
            "patch_id": f"patch-gen{gen_id}",
            "target_config": candidate_baseline,
            "change_scope": "minor",
            "require_pre_release_inspect": True,
            "auto_rollback_threshold": self.guard.get("rollback_health_drop", 8)
        }

    def export_patch_file(self, patch: dict, gen_id: int):
        out = self.root / f"data/evolution/candidate_baseline/config_patch_gen{gen_id}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(patch, f, indent=2, ensure_ascii=False)
        return str(out)
