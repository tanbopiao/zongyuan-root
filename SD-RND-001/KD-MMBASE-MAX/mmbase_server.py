"""
KD-MMBASE-MAX 极致多模态基座 · 统一入口
17核心模块 + 2内核桥接初始化
基座编号: KD-MMBASE-V1.0-MAX
DID: DID-BR-000002
溯源: Ω₀⊂⊙∞⊂Ω
"""
import os, sys, json, time, uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from core.router import MMRouter
from core.task_queue import TaskQueue
from core.retry_engine import RetryEngine
from core.drift_checker import DriftChecker
from core.archive_engine import ArchiveEngine
from core.monitor import MonitorEngine
from core.quality_scorer import QualityScorer
from adapters.image_adapter import ImageAdapter
from adapters.video_adapter import VideoAdapter
from adapters.understand_adapter import UnderstandAdapter
from adapters.search_adapter import SearchAdapter
from adapters.audio_adapter import AudioAdapter


class MMBaseServer:
    """极致多模态基座 · 统一能力网关"""
    VERSION = "KD-MMBASE-V1.0-MAX"
    DID = "DID-BR-000002"
    TRACE = "Ω₀⊂⊙∞⊂Ω"

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.session_id = f"MM-{uuid.uuid4().hex[:12]}"
        self.start_time = time.time()
        # 核心模块初始化
        self.router = MMRouter(self.config)
        self.queue = TaskQueue(self.config)
        self.retry = RetryEngine(self.config)
        self.drift = DriftChecker(self.config)
        self.archive = ArchiveEngine(self.config)
        self.monitor = MonitorEngine(self.config)
        self.quality = QualityScorer(self.config)
        # 多模态适配器
        self.adapters = {
            "image": ImageAdapter(self.config),
            "video": VideoAdapter(self.config),
            "understand": UnderstandAdapter(self.config),
            "search": SearchAdapter(self.config),
            "audio": AudioAdapter(self.config),
        }
        # 内核桥接（LOIP治理 + Ω-Brainμ召回）
        self.loip_bridge = None
        self.brain_recall = None
        self._init_kernel_bridges()
        self.monitor.log("mmbase_init", {"version": self.VERSION, "session": self.session_id})

    def _load_config(self, path: Optional[str]) -> Dict:
        if path and Path(path).exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {
            "max_concurrency": 6,
            "retry_max": 5,
            "retry_backoff": 2,
            "drift_threshold": 0.88,
            "quality_min": 4.5,
            "archive_dir": "./archive",
            "l0_axioms_path": "../../meta_laws",
        }

    def _init_kernel_bridges(self):
        """初始化内核桥接：LOIP治理 + Ω-Brainμ前置召回"""
        try:
            loip_path = BASE_DIR.parent.parent / "loip-sdk"
            if loip_path.exists():
                sys.path.insert(0, str(loip_path))
                from loip import LOIP
                baseline = loip_path / "loip_baseline.json"
                self.loip_bridge = LOIP(
                    baseline_path=str(baseline if baseline.exists() else loip_path / "loip_baseline.json"),
                    audit_dir=str(BASE_DIR / "loip_audit"),
                )
                self.monitor.log("loip_bridge_ok", {})
        except Exception as e:
            self.monitor.log("loip_bridge_fail", {"error": str(e)})

    def submit(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """统一任务提交入口"""
        task_id = f"TASK-{uuid.uuid4().hex[:10]}"
        self.monitor.log("task_submit", {"task_id": task_id, "type": task_type})
        # 1. Ω-Brainμ前置召回（如已接入）
        recall_ctx = {}
        # 2. 路由分发
        route = self.router.route(task_type, payload)
        # 3. 入队
        self.queue.enqueue(task_id, route)
        # 4. 执行（含重试熔断）
        raw = self.retry.execute(
            lambda: self._execute_adapter(route["adapter"], payload),
            task_id=task_id,
        )
        result = raw.get("data", raw)
        # 5. 漂移校验（L0天元法则四层）
        drift_result = self.drift.check(task_type, result, payload)
        # 6. 质量评分
        quality_result = self.quality.score(result, drift_result)
        # 7. LOIP治理桥接（如已接入）
        loip_result = None
        if self.loip_bridge and result.get("text"):
            loip_result = self.loip_bridge.process(
                user_input=json.dumps(payload, ensure_ascii=False),
                ai_output=result.get("text", ""),
            )
        # 8. 锁档归档
        archive_id = self.archive.archive(task_id, result, drift_result, quality_result, loip_result)
        return {
            "task_id": task_id,
            "session_id": self.session_id,
            "route": route,
            "result": result,
            "drift_check": drift_result,
            "quality": quality_result,
            "loip_governance": loip_result,
            "archive_id": archive_id,
            "timestamp": time.time(),
        }

    def _execute_adapter(self, adapter_name: str, payload: Dict) -> Dict:
        adapter = self.adapters.get(adapter_name)
        if not adapter:
            return {"error": f"unknown adapter: {adapter_name}"}
        return adapter.execute(payload)

    def status(self) -> Dict:
        return {
            "version": self.VERSION,
            "session": self.session_id,
            "uptime": round(time.time() - self.start_time, 1),
            "adapters": list(self.adapters.keys()),
            "loip_bridge": "active" if self.loip_bridge else "not_connected",
            "queue_size": self.queue.size(),
            "monitor": self.monitor.summary(),
        }


if __name__ == "__main__":
    server = MMBaseServer()
    print(json.dumps(server.status(), ensure_ascii=False, indent=2))
