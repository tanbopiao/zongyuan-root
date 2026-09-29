#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2E 审批→执行闭环调度器 V1.1
DID: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
功能: 接收飞书审批结果 -> 预检(dry-run) -> 6类执行器路由 -> 快照回滚 -> 审计台账
用法:
  python3 a2e_dispatcher.py --task <task.json>          # 处理单个审批任务
  python3 a2e_dispatcher.py --status <task_id>          # 查询任务状态
  python3 a2e_dispatcher.py --list                      # 列出执行器
"""
import os
import sys
import json
import time
import shutil
import hashlib
import argparse
import traceback
from datetime import datetime

# ---------- 常量 ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXECUTORS_DIR = os.path.join(BASE_DIR, "executors")
PRECHECK_DIR = os.path.join(BASE_DIR, "precheck")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "snapshots")
REGISTRY_FILE = os.path.join(BASE_DIR, "registry.json")
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

# 高危操作类型（强制 dry-run + 快照 + 双人审批标记）
HIGH_RISK_ACTIONS = {"delete", "restart", "config_change", "service_stop", "batch_write"}

# ---------- 工具函数 ----------
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg: str, level: str = "INFO"):
    line = f"[{now_str()}] [{level}] {msg}"
    print(line)
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(os.path.join(LOGS_DIR, "a2e_dispatcher.log"), "a") as f:
        f.write(line + "\n")

# ---------- 任务模型 ----------
class ApprovalTask:
    """审批通过后的待执行任务"""
    def __init__(self, data: dict):
        self.task_id = data.get("task_id", "")
        self.title = data.get("title", "")
        self.executor_type = data.get("executor_type", "")  # e1-e6
        self.action = data.get("action", "")                 # 操作类型
        self.params = data.get("params", {})                 # 执行参数
        self.approval_id = data.get("approval_id", "")       # 飞书审批单号
        self.approved_by = data.get("approved_by", "")
        self.risk_level = data.get("risk_level", "low")      # low/mid/high
        self.dry_run_only = data.get("dry_run_only", False)  # 仅预检不执行
        self.created_at = data.get("created_at", now_str())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    def validate(self) -> list:
        """返回错误列表，空=通过"""
        errors = []
        if not self.task_id:
            errors.append("task_id 缺失")
        if not self.executor_type:
            errors.append("executor_type 缺失")
        if not self.approval_id:
            errors.append("approval_id 缺失（必须来自飞书审批）")
        return errors

    def is_high_risk(self) -> bool:
        return self.risk_level == "high" or self.action in HIGH_RISK_ACTIONS

# ---------- 预检引擎 ----------
class PrecheckEngine:
    """L2 预检: 评估变更影响，生成风险报告"""
    def __init__(self, task: ApprovalTask):
        self.task = task

    def run(self) -> dict:
        report = {
            "task_id": self.task.task_id,
            "precheck_status": "PASS" if not self.task.is_high_risk() else "NEED_REVIEW",
            "risk_level": self.task.risk_level,
            "estimated_impact": self._estimate_impact(),
            "rollback_plan": "snapshot_auto" if self.task.is_high_risk() else "none",
            "checked_at": now_str(),
        }
        # 高危任务必须验证回滚参数
        if self.task.is_high_risk():
            backup_path = self.task.params.get("backup_path") or self.task.params.get("snapshot_path")
            if not backup_path:
                report["precheck_status"] = "BLOCKED"
                report["block_reason"] = "高危任务缺少 backup_path/snapshot_path 回滚参数"
        return report

    def _estimate_impact(self) -> str:
        return f"{self.task.action} 作用于 {self.task.params.get('target', 'unknown')}"

# ---------- 快照与回滚 ----------
class SnapshotManager:
    """L3 回滚保护: 执行前快照, 失败自动回滚"""
    def __init__(self, task: ApprovalTask):
        self.task = task
        self.snapshot_dir = os.path.join(SNAPSHOTS_DIR, self.task.task_id)

    def create_snapshot(self) -> str:
        """对目标路径做快照副本"""
        target = self.task.params.get("backup_path") or self.task.params.get("target")
        if not target or not os.path.exists(target):
            log(f"快照跳过: 目标不存在 {target}", "WARN")
            return ""
        os.makedirs(self.snapshot_dir, exist_ok=True)
        dest = os.path.join(self.snapshot_dir, os.path.basename(target) + f".{int(time.time())}")
        if os.path.isdir(target):
            shutil.copytree(target, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(target, dest)
        log(f"快照已创建: {dest}")
        return dest

    def rollback(self, snapshot: str) -> bool:
        if not snapshot or not os.path.exists(snapshot):
            log("回滚失败: 无快照", "ERROR")
            return False
        target = self.task.params.get("backup_path") or self.task.params.get("target")
        if not target:
            return False
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(snapshot, target, dirs_exist_ok=True)
        else:
            shutil.copy2(snapshot, target)
        log(f"已回滚: {target} <- {snapshot}")
        return True

# ---------- 执行器路由 ----------
class ExecutorRouter:
    """按 executor_type 路由到对应执行器"""
    EXECUTOR_MAP = {
        "e1": "e1_ops",       # 运维
        "e2": "e2_deploy",    # 部署
        "e3": "e3_data",      # 数据
        "e4": "e4_config",    # 配置
        "e5": "e5_lock",      # 锁档
        "e6": "e6_notify",    # 通知
    }

    def __init__(self):
        self.executors = self._load_executors()

    def _load_executors(self) -> dict:
        """动态加载 executors/ 下的执行器模块"""
        loaded = {}
        sys.path.insert(0, EXECUTORS_DIR)
        for key, mod_name in self.EXECUTOR_MAP.items():
            try:
                mod = __import__(mod_name)
                loaded[key] = mod
            except Exception as e:
                log(f"执行器 {mod_name} 加载失败: {e}", "ERROR")
        return loaded

    def route(self, task: ApprovalTask) -> dict:
        executor = self.executors.get(task.executor_type)
        if not executor:
            return {"status": "FAILED", "reason": f"未知执行器类型 {task.executor_type}"}
        if not hasattr(executor, "execute"):
            return {"status": "FAILED", "reason": f"执行器 {task.executor_type} 缺少 execute()"}
        try:
            result = executor.execute(task.to_dict())
            return result if isinstance(result, dict) else {"status": "OK", "result": result}
        except Exception as e:
            log(f"执行器异常: {e}\n{traceback.format_exc()}", "ERROR")
            return {"status": "FAILED", "reason": str(e)}

# ---------- 审计台账 ----------
class AuditLogger:
    """执行审计: 写入 tasks.json 台账"""
    def __init__(self):
        os.makedirs(BASE_DIR, exist_ok=True)
        self.tasks_file = TASKS_FILE
        self._init_tasks()

    def _init_tasks(self):
        if not os.path.exists(self.tasks_file):
            with open(self.tasks_file, "w") as f:
                json.dump({"tasks": []}, f, ensure_ascii=False, indent=2)

    def record(self, task: ApprovalTask, result: dict, snapshot: str = ""):
        with open(self.tasks_file) as f:
            data = json.load(f)
        entry = task.to_dict()
        entry["exec_result"] = result
        entry["snapshot"] = snapshot
        entry["executed_at"] = now_str()
        entry["trace_hash"] = sha256_text(json.dumps(entry, ensure_ascii=False))
        data["tasks"].append(entry)
        with open(self.tasks_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"审计已记录: {task.task_id} -> {result.get('status')}")

# ---------- 主调度 ----------
class A2EDispatcher:
    def __init__(self):
        self.precheck = None
        self.router = ExecutorRouter()
        self.snapshot_mgr = None
        self.audit = AuditLogger()

    def dispatch(self, task_data: dict, dry_run_only: bool = False) -> dict:
        task = ApprovalTask(task_data)
        if dry_run_only:
            task.dry_run_only = True

        # 1. 任务校验
        errors = task.validate()
        if errors:
            return {"status": "REJECTED", "errors": errors}

        # 2. L1 权限: 必须有飞书审批单号
        if not task.approval_id or not task.approved_by:
            return {"status": "REJECTED", "reason": "缺少审批人/审批单，拒绝执行"}

        # 3. L2 预检
        self.precheck = PrecheckEngine(task)
        report = self.precheck.run()
        log(f"预检: {task.task_id} -> {report['precheck_status']}")
        if report["precheck_status"] == "BLOCKED":
            self.audit.record(task, {"status": "BLOCKED", "precheck": report})
            return {"status": "BLOCKED", "precheck": report}
        if report["precheck_status"] == "NEED_REVIEW":
            # 高危任务: 此处由调度策略决定——本版本要求高危任务必须带显式 force=1
            if not task.params.get("force"):
                self.audit.record(task, {"status": "NEED_REVIEW", "precheck": report})
                return {"status": "NEED_REVIEW", "reason": "高危操作需 force=1 确认", "precheck": report}

        # 4. L3 快照
        snapshot = ""
        if task.is_high_risk():
            self.snapshot_mgr = SnapshotManager(task)
            snapshot = self.snapshot_mgr.create_snapshot()

        # 5. dry-run 模式: 不真实执行
        if task.dry_run_only:
            result = {"status": "DRY_RUN_OK", "precheck": report, "would_execute": task.action}
            self.audit.record(task, result, snapshot)
            return result

        # 6. 正式执行
        log(f"开始执行: {task.task_id} [{task.executor_type}] {task.action}")
        result = self.router.route(task)
        if result.get("status") == "FAILED" and snapshot:
            # 7. 失败自动回滚
            rollback_ok = self.snapshot_mgr.rollback(snapshot)
            result["rollback"] = "OK" if rollback_ok else "FAILED"
        result["executor_type"] = task.executor_type
        self.audit.record(task, result, snapshot)
        return result

# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(description="A2E 审批→执行闭环调度器")
    parser.add_argument("--task", help="任务JSON文件路径")
    parser.add_argument("--status", help="查询任务状态")
    parser.add_argument("--list", action="store_true", help="列出可用执行器")
    parser.add_argument("--dry-run", action="store_true", help="仅预检不执行")
    args = parser.parse_args()

    dispatcher = A2EDispatcher()

    if args.list:
        print("可用执行器:")
        for k, v in ExecutorRouter.EXECUTOR_MAP.items():
            print(f"  {k}: {v}")
        return

    if args.status:
        with open(TASKS_FILE) as f:
            data = json.load(f)
        for t in data["tasks"]:
            if t.get("task_id") == args.status:
                print(json.dumps(t, ensure_ascii=False, indent=2))
                return
        print(f"未找到任务 {args.status}")
        return

    if args.task:
        with open(args.task) as f:
            task_data = json.load(f)
        result = dispatcher.dispatch(task_data, dry_run_only=args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    parser.print_help()

if __name__ == "__main__":
    main()
