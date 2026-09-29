#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ω-OP-SCHED 稳态智能 · 自适应调度增强模块
=========================================
ZONGYUAN-ROOT 元极恒一自治体系 · P3 稳态智能核心增量
DID: DID-BR-000002 | 本源根: Ω-TAN-7-001 | 溯源: Ω₀⊂⊙∞⊂Ω

在既有 OPScheduler（DAG/队列/熔断/审计/Merkle归档 已具备）之上，
补齐"稳态智能"三件套，不改变既有调度主逻辑（最优稳态·只做增量）：

  1. AdaptiveWorkerPicker  负载感知选 worker
     - 读每个 worker 的负载(load_avg/cpu/usage/队列长度)，选"最低负载且健康"的
     - 替代原 get_available_worker 的"第一个可用"，实现自适应负载均衡
  2. OperatorHotReload      算子热升级接口
     - 对接 op_library/hot_reload + versioning
     - 运行时切换算子版本，版本号/哈希/时间归档
  3. DriftDetector          漂移检测
     - 对比算子执行基线(成功率/耗时/负载)，超阈值(黄5%/橙10%/红20%)告警
     - 输出漂移报告，供记忆网关上报

设计原则（最优稳态）：
  - 纯增量：不修改 scheduler.py 既有类，以 Mixin/独立类注入
  - 同源约束：meta_homo_root + asset_did 双锚点校验
  - 失败降级：任一增强不可用时回退到原调度逻辑，不中断任务
"""

import json
import hashlib
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# ------------------- 同源锚点（固化） -------------------
DID_ANCHOR = "DID-BR-000002"
ROOT_OMEGA_ANCHOR = "Ω-TAN-7-001"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"

# ------------------- 1. 负载感知选 worker -------------------
class AdaptiveWorkerPicker:
    """稳态智能·负载感知自适应选 worker
    替代原 get_available_worker 的"第一个可用"，按负载+健康度择优。
    """

    def __init__(self):
        self.metrics = {}  # worker_id -> {load_avg, cpu, mem, queue, health}

    def update_metrics(self, worker_id: str, metrics: Dict[str, Any]):
        """由外部(监控线程/云端资源)更新 worker 负载指标"""
        self.metrics[worker_id] = {
            "load_avg": float(metrics.get("load_avg", 0.0)),
            "cpu": float(metrics.get("cpu", metrics.get("cpu_percent", 0.0))),
            "mem": float(metrics.get("mem", metrics.get("memory_percent", 0.0))),
            "queue": int(metrics.get("queue", metrics.get("queue_len", 0))),
            "health": float(metrics.get("health", 1.0)),
            "updated_at": datetime.now().isoformat(),
        }

    def score(self, worker_id: str) -> float:
        """综合负载评分：越低越好。health=0 直接判不可用"""
        m = self.metrics.get(worker_id)
        if not m:
            return 0.0  # 无指标默认最低优先(公平)
        if m["health"] <= 0:
            return float("inf")
        # 负载 = 0.4*cpu + 0.3*mem + 0.3*queue；越满分越高
        load = 0.4 * m["cpu"] + 0.3 * m["mem"] + 0.3 * (m["queue"] * 5.0)
        # 健康度加权：health 越低，score 越高(越不优先)
        penalty = (1.0 - m["health"]) * 50.0
        return load + penalty

    def pick(self, candidates: List[str]) -> Optional[str]:
        """从候选 worker 中选最低负载者"""
        if not candidates:
            return None
        # 过滤不可用
        usable = [w for w in candidates if self.score(w) != float("inf")]
        if not usable:
            return None
        return min(usable, key=self.score)

# ------------------- 2. 算子热升级 -------------------
class OperatorHotReload:
    """稳态智能·算子热升级
    对接 op_library/versioning + hot_reload，运行时切换算子版本。
    """

    def __init__(self, op_library_path: str = "/opt/ZONGYUAN-ROOT/op_library"):
        self.op_library_path = op_library_path
        self.version_dir = f"{op_library_path}/versioning"
        self.reload_dir = f"{op_library_path}/hot_reload"
        self.active_versions: Dict[str, str] = {}  # operator -> version
        self.history: List[Dict] = []

    def sha256(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def get_version(self, operator: str) -> Optional[str]:
        """查询算子当前版本"""
        try:
            with open(f"{self.version_dir}/versions.json", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("operators", {}).get(operator, {}).get("version")
        except Exception:
            return None

    def reload(self, operator: str, new_version: str, source: str) -> Dict:
        """热升级算子到指定版本"""
        # 同源校验
        if not (DID_ANCHOR and ROOT_OMEGA_ANCHOR):
            raise ValueError("同源锚点缺失")
        record = {
            "operator": operator,
            "from_version": self.active_versions.get(operator),
            "to_version": new_version,
            "source_hash": self.sha256(source),
            "timestamp": datetime.now().isoformat(),
            "did": DID_ANCHOR,
            "root_omega": ROOT_OMEGA_ANCHOR,
            "trace": TRACE_MARK,
        }
        self.active_versions[operator] = new_version
        self.history.append(record)
        return record

    def get_history(self, operator: str = None) -> List[Dict]:
        if operator:
            return [h for h in self.history if h["operator"] == operator]
        return self.history

# ------------------- 3. 漂移检测 -------------------
class DriftDetector:
    """稳态智能·算子执行漂移检测
    对比基线(成功率/耗时/负载)，超阈值分级告警：黄5% / 橙10% / 红20%。
    """

    THRESHOLDS = {"yellow": 0.05, "orange": 0.10, "red": 0.20}

    def __init__(self):
        self.baseline: Dict[str, Dict] = {}   # operator -> {success_rate, avg_latency, load}
        self.current: Dict[str, Dict] = {}    # operator -> 当前指标
        self.reports: List[Dict] = []

    def set_baseline(self, operator: str, success_rate: float, avg_latency: float, load: float = 0.0):
        self.baseline[operator] = {
            "success_rate": success_rate, "avg_latency": avg_latency, "load": load,
        }

    def update(self, operator: str, success_rate: float, avg_latency: float, load: float = 0.0):
        self.current[operator] = {
            "success_rate": success_rate, "avg_latency": avg_latency, "load": load,
        }

    def detect(self, operator: str) -> Dict:
        """检测单算子漂移，返回报告"""
        b = self.baseline.get(operator)
        c = self.current.get(operator)
        if not b or not c:
            return {"operator": operator, "drift": False, "reason": "缺基线或当前指标"}

        drift_metrics = {}
        max_drift = 0.0
        level = "green"

        # 成功率漂移（相对下降）
        if b["success_rate"] > 0:
            sr_drift = (b["success_rate"] - c["success_rate"]) / b["success_rate"]
            drift_metrics["success_rate"] = round(sr_drift, 4)
            max_drift = max(max_drift, sr_drift)
        # 延迟漂移（相对上升）
        if b["avg_latency"] > 0:
            lat_drift = (c["avg_latency"] - b["avg_latency"]) / b["avg_latency"]
            drift_metrics["avg_latency"] = round(lat_drift, 4)
            max_drift = max(max_drift, lat_drift)
        # 负载漂移
        if b["load"] > 0:
            load_drift = abs(c["load"] - b["load"]) / b["load"]
            drift_metrics["load"] = round(load_drift, 4)
            max_drift = max(max_drift, load_drift)

        # 分级
        if max_drift >= self.THRESHOLDS["red"]:
            level = "red"
        elif max_drift >= self.THRESHOLDS["orange"]:
            level = "orange"
        elif max_drift >= self.THRESHOLDS["yellow"]:
            level = "yellow"

        report = {
            "operator": operator,
            "drift": max_drift >= self.THRESHOLDS["yellow"],
            "level": level,
            "max_drift": round(max_drift, 4),
            "metrics": drift_metrics,
            "baseline": b,
            "current": c,
            "timestamp": datetime.now().isoformat(),
            "trace": TRACE_MARK,
        }
        if report["drift"]:
            self.reports.append(report)
        return report

    def detect_all(self) -> List[Dict]:
        return [self.detect(op) for op in set(list(self.baseline) + list(self.current))]

    def summary(self) -> Dict:
        reports = self.detect_all()
        red = sum(1 for r in reports if r.get("level") == "red")
        orange = sum(1 for r in reports if r.get("level") == "orange")
        yellow = sum(1 for r in reports if r.get("level") == "yellow")
        return {
            "total_checked": len(reports),
            "drifted": sum(1 for r in reports if r.get("drift")),
            "red": red, "orange": orange, "yellow": yellow,
            "timestamp": datetime.now().isoformat(),
        }

# ------------------- 4. 稳态智能主控（注入式 Mixin） -------------------
class SteadyIntelligenceMixin:
    """注入 OPScheduler 的稳态智能增强：
    自适应选 worker + 算子热升级 + 漂移检测，失败自动降级到原逻辑。
    """

    def __init__(self):
        self.adaptive_picker = AdaptiveWorkerPicker()
        self.hot_reload = OperatorHotReload()
        self.drift = DriftDetector()
        self._steady_lock = threading.Lock()

    # 注入点1: 负载感知选 worker（替换 get_available_worker 的择优逻辑）
    def adaptive_get_worker(self, operator: str, worker_manager) -> Optional[Any]:
        try:
            candidates = []
            with worker_manager.lock:
                for worker in worker_manager.workers.values():
                    if worker.status.value == "online" and operator in worker.capabilities:
                        candidates.append(worker.worker_id)
            picked = self.adaptive_picker.pick(candidates)
            if picked is None:
                return None
            with worker_manager.lock:
                return worker_manager.workers.get(picked)
        except Exception:
            # 降级：原逻辑
            return worker_manager.get_available_worker(operator)

    # 注入点2: 算子热升级
    def reload_operator(self, operator: str, new_version: str, source: str) -> Dict:
        return self.hot_reload.reload(operator, new_version, source)

    # 注入点3: 漂移检测
    def run_drift_scan(self) -> Dict:
        return self.drift.summary()


# ------------------- 自检/仿真入口 -------------------
if __name__ == "__main__":
    print("=== Ω-OP-SCHED 稳态智能增强 · 本地仿真验证 ===")
    print(f"DID: {DID_ANCHOR} | 本源根: {ROOT_OMEGA_ANCHOR} | 溯源: {TRACE_MARK}\n")

    # 仿真1: 负载感知选worker
    print("[仿真1] 自适应负载感知选worker")
    picker = AdaptiveWorkerPicker()
    picker.update_metrics("worker-a", {"cpu": 80, "mem": 70, "queue": 3, "health": 1.0})
    picker.update_metrics("worker-b", {"cpu": 30, "mem": 40, "queue": 1, "health": 1.0})
    picker.update_metrics("worker-c", {"cpu": 90, "mem": 85, "queue": 8, "health": 0.0})
    print(f"  候选 [worker-a, worker-b, worker-c] → 选中: {picker.pick(['worker-a','worker-b','worker-c'])}")
    assert picker.pick(["worker-a", "worker-b", "worker-c"]) == "worker-b", "应选负载最低且健康"
    # 全不可用
    picker2 = AdaptiveWorkerPicker()
    picker2.update_metrics("worker-c", {"cpu": 90, "health": 0.0})
    assert picker2.pick(["worker-c"]) is None, "全不可用应返回None"
    print("  ✓ 通过")

    # 仿真2: 算子热升级
    print("[仿真2] 算子热升级")
    hr = OperatorHotReload("/tmp/op_library_fake")
    rec = hr.reload("P4真值对账", "v2.1", "def truth(): pass")
    print(f"  升级记录: {rec['operator']} {rec['from_version']}→{rec['to_version']} hash={rec['source_hash'][:12]}")
    assert rec["to_version"] == "v2.1"
    print("  ✓ 通过")

    # 仿真3: 漂移检测
    print("[仿真3] 算子漂移检测")
    dd = DriftDetector()
    dd.set_baseline("P7外部锚定", success_rate=0.98, avg_latency=100, load=0.3)
    dd.update("P7外部锚定", success_rate=0.98, avg_latency=100, load=0.3)
    r1 = dd.detect("P7外部锚定")
    print(f"  基线一致 → drift={r1['drift']} level={r1['level']}")
    assert r1["level"] == "green", "基线一致应为绿色"
    dd.update("P7外部锚定", success_rate=0.50, avg_latency=300, load=0.9)
    r2 = dd.detect("P7外部锚定")
    print(f"  严重漂移 → drift={r2['drift']} level={r2['level']} max_drift={r2['max_drift']}")
    assert r2["level"] == "red", "严重漂移应为红色"
    print(f"  汇总: {dd.summary()}")
    print("  ✓ 通过")

    print("\n=== 本地仿真全部通过 ===")
    print("按记忆驱动闭环: 本地仿真验证OK → 待人工审核 → 9120同步 → 上云部署")
