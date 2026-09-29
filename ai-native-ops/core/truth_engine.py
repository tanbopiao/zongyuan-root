"""
ANCE 真值引擎
部署经验沉淀为可复用配置，Merkle锁档确权
"""
import json
import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class DeploymentTruth:
    """部署真值"""
    truth_id: str
    pattern: str
    cloud: str
    spec: Dict
    software: List[str]
    domain: Optional[str]
    ssl: bool
    iac_artifacts: Dict
    verification: Dict
    created_at: str
    sha256: str = ""
    reuse_count: int = 0

    def compute_hash(self) -> str:
        content = json.dumps({
            "pattern": self.pattern,
            "cloud": self.cloud,
            "spec": self.spec,
            "software": self.software,
            "iac_artifacts": self.iac_artifacts,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()


class TruthEngine:
    """真值引擎"""

    def __init__(self, cache_dir: str = "truth_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.truths: List[DeploymentTruth] = []
        self._load()

    def _load(self):
        """加载真值缓存"""
        index_file = os.path.join(self.cache_dir, "index.json")
        if os.path.exists(index_file):
            with open(index_file) as f:
                data = json.load(f)
            for item in data:
                self.truths.append(DeploymentTruth(**item))

    def _save(self):
        """保存真值缓存"""
        index_file = os.path.join(self.cache_dir, "index.json")
        data = [t.__dict__ for t in self.truths]
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record(self, deployment_plan, execution_dag, verification_report,
               iac_artifacts: Dict) -> DeploymentTruth:
        """记录一次成功部署为真值"""
        pattern = self._derive_pattern(deployment_plan)
        truth = DeploymentTruth(
            truth_id=f"TRUTH-DEPLOY-{int(time.time())}",
            pattern=pattern,
            cloud=deployment_plan.cloud_provider,
            spec=deployment_plan.resources[0] if deployment_plan.resources else {},
            software=deployment_plan.software_stack,
            domain=deployment_plan.domain,
            ssl=deployment_plan.ssl_enabled,
            iac_artifacts=iac_artifacts,
            verification=verification_report.to_dict() if verification_report else {},
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        )
        truth.sha256 = truth.compute_hash()
        self.truths.append(truth)
        self._save()
        return truth

    def recall(self, deployment_plan) -> Optional[DeploymentTruth]:
        """召回相似部署真值"""
        target_pattern = self._derive_pattern(deployment_plan)
        best_match = None
        best_score = 0

        for truth in self.truths:
            score = self._similarity(deployment_plan, truth)
            if score > best_score and score >= 0.6:
                best_score = score
                best_match = truth

        if best_match:
            best_match.reuse_count += 1
            self._save()
        return best_match

    def _derive_pattern(self, plan) -> str:
        """派生部署模式标识"""
        parts = [plan.cloud_provider]
        if plan.resources:
            r = plan.resources[0]
            parts.append(f"{r.get('cpu', '?')}c{r.get('memory_gb', '?')}g")
        parts.extend(sorted(plan.software_stack))
        if plan.ssl_enabled:
            parts.append("ssl")
        return "_".join(parts)

    def _similarity(self, plan, truth: DeploymentTruth) -> float:
        """计算相似度"""
        score = 0.0
        if plan.cloud_provider == truth.cloud:
            score += 0.3
        if set(plan.software_stack) == set(truth.software):
            score += 0.4
        elif set(plan.software_stack) & set(truth.software):
            score += 0.2
        if plan.ssl_enabled == truth.ssl:
            score += 0.15
        if plan.resources and truth.spec:
            if (plan.resources[0].get("cpu") == truth.spec.get("cpu") and
                plan.resources[0].get("memory_gb") == truth.spec.get("memory_gb")):
                score += 0.15
        return min(score, 1.0)

    def get_merkle_root(self) -> str:
        """计算所有真值的Merkle根"""
        hashes = sorted([t.sha256 for t in self.truths if t.sha256])
        if not hashes:
            return ""
        while len(hashes) > 1:
            nxt = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + (hashes[i+1] if i+1 < len(hashes) else "")
                nxt.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = nxt
        return hashes[0]

    def get_stats(self) -> Dict:
        return {
            "total_truths": len(self.truths),
            "total_reuses": sum(t.reuse_count for t in self.truths),
            "patterns": list(set(t.pattern for t in self.truths)),
            "merkle_root": self.get_merkle_root(),
            "by_cloud": {
                cloud: sum(1 for t in self.truths if t.cloud == cloud)
                for cloud in set(t.cloud for t in self.truths)
            },
        }
