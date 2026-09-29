import json, hashlib
from pathlib import Path

class SelfLearningEngine:
    def __init__(self, root_path: Path):
        self.root = root_path
        self.raw_dir = self.root / "data/evolution/raw"
        self.candidate_dir = self.root / "data/evolution/candidate_baseline"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.candidate_dir.mkdir(parents=True, exist_ok=True)

    def hash_asset(self, payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def load_inspection_report(self, report_path: Path) -> dict:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def distill_pattern(self, report: dict) -> list:
        candidates = []
        anomalies = report.get("anomalies", [])
        for item in anomalies:
            if item.get("level") in ("LOW", "MEDIUM"):
                candidate = {
                    "source_inspect_id": report.get("inspect_id"),
                    "pattern": item.get("content"),
                    "confidence": 0.65,
                    "proposed_rule": f"Auto-rule: {item.get('content')}",
                    "meta_class": "M3"
                }
                candidate["asset_hash"] = self.hash_asset(candidate)
                candidates.append(candidate)
        return candidates

    def save_distilled(self, candidate_list: list, date_tag: str):
        out = self.candidate_dir / f"distilled_{date_tag}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"candidates": candidate_list}, f, indent=2, ensure_ascii=False)
        return str(out)
