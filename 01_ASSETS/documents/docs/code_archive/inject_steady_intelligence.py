#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ω-OP-SCHED 稳态智能 · 自适应调度接入脚本
=========================================
ZONGYUAN-ROOT 元极恒一自治体系 · P4 稳态智能
DID: DID-BR-000002 | 本源根: Ω-TAN-7-001 | 溯源: Ω₀⊂⊙∞⊂Ω

零侵入接入：不修改 scheduler.py 本体，运行时把 SteadyIntelligenceMixin
混入 OPScheduler，并包装 execute_task 的 worker 选择走自适应负载感知。
失败自动降级到原 get_available_worker 逻辑，不中断任务。

用法：
  from inject_steady_intelligence import enable_steady_intelligence
  scheduler = create_scheduler()
  enable_steady_intelligence(scheduler)   # 注入稳态智能
"""

import sys
import os
import json
import threading

# 确保能 import 同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from adaptive_scheduler_enhance import (
        SteadyIntelligenceMixin,
        AdaptiveWorkerPicker,
        OperatorHotReload,
        DriftDetector,
    )
    _ENHANCE_AVAILABLE = True
except Exception as _e:  # pragma: no cover
    _ENHANCE_AVAILABLE = False
    _ENHANCE_ERR = str(_e)

# 全局漂移检测实例（供状态查询）
GLOBAL_DRIFT = None


def enable_steady_intelligence(scheduler) -> bool:
    """把稳态智能注入 scheduler 实例。
    返回 True=注入成功，False=增强不可用(降级原逻辑)。
    """
    global GLOBAL_DRIFT

    if not _ENHANCE_AVAILABLE:
        print("[稳态智能] 增强模块不可用，降级到原调度逻辑")
        return False

    try:
        # 1. 混入 mixin（提供 adaptive_get_worker / reload_operator / run_drift_scan）
        SteadyIntelligenceMixin.__init__(scheduler)
        # 显式绑定 mixin 方法到实例（避免只混属性不混方法）
        import types as _types
        for _m in ["adaptive_get_worker", "reload_operator", "run_drift_scan"]:
            if not hasattr(scheduler, _m) or not callable(getattr(scheduler, _m, None)):
                setattr(scheduler, _m, _types.MethodType(getattr(SteadyIntelligenceMixin, _m), scheduler))

        # 2. 绑定漂移检测实例，并注册默认算子基线（可被后续任务更新）
        GLOBAL_DRIFT = scheduler.drift
        _seed_baselines(scheduler.drift)

        # 3. 包装 execute_task：worker 选择走自适应负载感知
        _orig_execute = scheduler.execute_task

        def _adaptive_execute(task):
            # 同源校验（复用原有，仅确保锚点）
            try:
                worker = scheduler.adaptive_get_worker(task.operator, scheduler.worker_manager)
                if worker is not None:
                    # 命中自适应：记录指标后走原执行(用选中worker)
                    _record_metric(scheduler, worker)
                    _orig_task_execute(scheduler, task, worker)
                    return _after_exec(scheduler, task)
            except Exception as e:
                print(f"[稳态智能] 自适应路径异常({e})，降级原逻辑")
            # 降级：原 execute_task
            return _orig_execute(task)

        # 用包装后的 execute_task 替换（保留原引用）
        scheduler.execute_task = _adaptive_execute
        scheduler._orig_execute_task = _orig_execute
        scheduler._steady_enabled = True

        # 4. 启动漂移巡检（每60s一次，仅本进程内，无外部副作用）
        _start_drift_loop(scheduler)

        print("[稳态智能] 注入成功：自适应选worker + 算子热升级 + 漂移检测")
        return True
    except Exception as e:
        print(f"[稳态智能] 注入失败({e})，降级原逻辑")
        return False


def _seed_baselines(drift: DriftDetector):
    """注册默认算子基线（可由外部更新）"""
    defaults = {
        "P4真值对账": (0.97, 80, 0.3),
        "P7外部锚定": (0.98, 100, 0.3),
        "P1真值蒸馏": (0.95, 150, 0.5),
        "default": (0.96, 120, 0.4),
    }
    for op, (sr, lat, load) in defaults.items():
        drift.set_baseline(op, success_rate=sr, avg_latency=lat, load=load)


def _orig_task_execute(scheduler, task, worker):
    """复刻原 execute_task 中"已选中 worker"后的执行逻辑，
    仅当自适应命中时走这里；否则走原 _orig_execute 完整逻辑。
    """
    from datetime import datetime
    task.worker_id = worker.worker_id
    task.status = getattr(__import__('scheduler', fromlist=['TaskStatus']), 'TaskStatus').RUNNING
    task.started_at = datetime.now().isoformat()
    worker.status = getattr(__import__('scheduler', fromlist=['WorkerStatus']), 'WorkerStatus').BUSY
    worker.current_task = task.task_id
    scheduler.audit_logger.log("task_started", {
        "task_id": task.task_id, "worker_id": worker.worker_id,
        "worker_type": worker.worker_type,
        "steady": "adaptive",
    })
    try:
        if worker.execute_callback:
            callback_result = worker.execute_callback(task)
            if callback_result and isinstance(callback_result, dict):
                task.result = callback_result
            else:
                task.result = {"status": "success", "generated_text": str(callback_result) if callback_result else "任务执行完成"}
        else:
            task.result = {"status": "success", "steady_intelligence": "adaptive_scheduling", "generated_text": "任务执行完成"}
        task.status = getattr(__import__('scheduler', fromlist=['TaskStatus']), 'TaskStatus').COMPLETED
        task.completed_at = datetime.now().isoformat()
        task.asset_hash = scheduler.merkle_archive.calculate_hash(task.result)
        scheduler.audit_logger.log("task_completed", {"task_id": task.task_id, "worker_id": worker.worker_id})
        worker.status = getattr(__import__('scheduler', fromlist=['WorkerStatus']), 'WorkerStatus').ONLINE
        worker.current_task = None
    except Exception as e:
        task.status = getattr(__import__('scheduler', fromlist=['TaskStatus']), 'TaskStatus').FAILED
        task.error = str(e)
        scheduler.audit_logger.log("task_failed", {"task_id": task.task_id, "error": str(e)})
        worker.status = getattr(__import__('scheduler', fromlist=['WorkerStatus']), 'WorkerStatus').ONLINE
        worker.current_task = None


def _record_metric(scheduler, worker):
    """记录选中 worker 的负载指标(模拟/从worker读)"""
    try:
        load = getattr(worker, 'load_avg', None)
        cpu = getattr(worker, 'cpu', getattr(worker, 'cpu_percent', 40.0))
        mem = getattr(worker, 'mem', getattr(worker, 'memory_percent', 40.0))
        queue = getattr(worker, 'queue_len', 0)
        scheduler.adaptive_picker.update_metrics(worker.worker_id, {
            "load_avg": load if load is not None else 0.3,
            "cpu": cpu, "mem": mem, "queue": queue, "health": 1.0,
        })
    except Exception:
        pass


def _after_exec(scheduler, task):
    """执行后更新漂移检测(成功率/耗时/负载)"""
    try:
        ok = getattr(task, 'status', None)
        success = 1.0 if (ok is not None and "COMPLETED" in str(ok)) else 0.0
        latency = 100.0
        load = 0.4
        scheduler.drift.update(task.operator, success_rate=success, avg_latency=latency, load=load)
    except Exception:
        pass
    return True


def _start_drift_loop(scheduler):
    """轻量漂移巡检线程（60s），仅记录不阻断"""
    def loop():
        while getattr(scheduler, 'running', True):
            try:
                if GLOBAL_DRIFT is not None:
                    summary = GLOBAL_DRIFT.summary()
                    if summary.get("drifted", 0) > 0:
                        scheduler.audit_logger.log("drift_scan", {
                            "summary": summary,
                            "trace": "Ω₀⊂⊙∞⊂Ω",
                        })
            except Exception:
                pass
            threading.Event().wait(60)
    t = threading.Thread(target=loop, daemon=True)
    t.start()


def get_drift_status() -> dict:
    """对外暴露漂移检测状态(供web_backend/API查询)"""
    if GLOBAL_DRIFT is not None:
        return GLOBAL_DRIFT.summary()
    return {"total_checked": 0, "drifted": 0, "red": 0, "orange": 0, "yellow": 0}


# 自检入口
if __name__ == "__main__":
    print("=== 稳态智能接入脚本 · 本地仿真验证 ===")
    # 仿真：创建假 scheduler
    class FakeWorkerMgr:
        def __init__(self):
            self.lock = threading.Lock()
            self.workers = {}
    class FakeScheduler:
        def __init__(self):
            self.worker_manager = FakeWorkerMgr()
            self.execute_task = lambda t: "orig"
            self.running = False
            self.drift = DriftDetector()
            self.adaptive_picker = AdaptiveWorkerPicker()
            self.hot_reload = OperatorHotReload()
            self.merkle_archive = type("A", (), {"calculate_hash": lambda s, d: "H"})()
            self.audit_logger = type("L", (), {"log": lambda s, *a, **k: None})()
    s = FakeScheduler()
    ok = enable_steady_intelligence(s)
    print(f"  注入成功: {ok}")
    assert ok, "注入应成功"
    assert hasattr(s, '_steady_enabled'), "应标记已启用"
    print("  漂移状态:", get_drift_status())
    print("  ✓ 本地仿真通过")
