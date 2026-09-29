#!/usr/bin/env python3
"""
scheduler_task_validator.py
Ω-OP-SCHED 调度引擎任务报文校验模块
对接 kernel_load_meta_protocol 协议加载器，对进入任务队列/DAG/算力调度的请求执行同源校验：
  1. 强制字段完整性校验（task_schema.mandatory_fields）
  2. 双标识同源校验（meta_homo_root + asset_did）
  3. 双层校验规则分发（调度层 + Worker 层）
  4. 异源任务拦截/隔离
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 本源根 Ω-TAN-7-001
"""
import hashlib
import json
import sys
from pathlib import Path

# 将项目根加入 sys.path，支持 from kernel.kernel_load_meta_protocol import
# __file__ 位于 <根>/kernel/scripts/ 下，上溯三级得项目根
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kernel.kernel_load_meta_protocol import MetaHomoProtocolLoader

DID_ANCHOR = "DID-BR-000002"
ROOT_OMEGA_ANCHOR = "Ω-TAN-7-001"


def calc_homo_signature(task: dict) -> str:
    """计算同源签名：双标识 + 核心任务字段的SHA256"""
    canonical = json.dumps(
        {
            "meta_homo_root": task.get("meta_homo_root"),
            "asset_did": task.get("asset_did"),
            "task_id": task.get("task_id"),
            "operator_name": task.get("operator_name"),
            "trace_hash": task.get("trace_hash"),
        },
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SchedulerTaskValidator:
    def __init__(self, proto_loader):
        """proto_loader: MetaHomoProtocolLoader 已加载实例"""
        if not proto_loader.load_success:
            raise RuntimeError("协议尚未加载，调度引擎无法执行同源校验")
        self.proto_loader = proto_loader
        self.mandatory_fields = proto_loader.get_task_mandatory_fields()
        self.double_verify = proto_loader.get_verify_rule()

    def validate_task(self, task: dict) -> dict:
        """同源校验任务报文，返回校验结果"""
        result = {"valid": True, "reason": [], "signature": None}

        # 1. 字段完整性
        missing = [f for f in self.mandatory_fields if f not in task]
        if missing:
            result["valid"] = False
            result["reason"].append(f"缺失强制字段: {missing}")

        # 2. 双标识同源
        if task.get("meta_homo_root") != ROOT_OMEGA_ANCHOR:
            result["valid"] = False
            result["reason"].append("meta_homo_root 异源")
        if task.get("asset_did") != DID_ANCHOR:
            result["valid"] = False
            result["reason"].append("asset_did 异源")

        # 3. 任务签名校验
        if task.get("homo_signature"):
            sig = calc_homo_signature(task)
            if sig != task["homo_signature"]:
                result["valid"] = False
                result["reason"].append("homo_signature 校验失败")
            result["signature"] = sig

        return result

    def dispatch_layer(self, task: dict) -> str:
        """双层校验分发：返回应执行的校验层裁决"""
        r = self.validate_task(task)
        if not r["valid"]:
            return "REJECTED"          # 第一层（调度层）拒绝
        return "PASS_TO_WORKER"        # 放行至第二层（Worker 层）二次确认


def build_standard_task(operator_name: str, task_id: str, domain: str = "zongyuan-root",
                        extra: dict = None) -> dict:
    """构造符合同源协议的标准任务报文"""
    extra = extra or {}
    task = {
        "proto_version": "1.0",
        "meta_homo_root": ROOT_OMEGA_ANCHOR,
        "asset_did": DID_ANCHOR,
        "task_id": task_id,
        "domain": domain,
        "operator_name": operator_name,
        "resource_quota": extra.get("resource_quota"),
        "retry_policy": extra.get("retry_policy", "retry3"),
        "trace_hash": extra.get("trace_hash"),
    }
    task["homo_signature"] = calc_homo_signature(task)
    return task


if __name__ == "__main__":
    loader = MetaHomoProtocolLoader()
    loader.load_protocol()
    validator = SchedulerTaskValidator(loader)

    print("=== Ω-OP-SCHED 任务报文同源校验演示 ===")
    print("强制字段:", validator.mandatory_fields)
    print("双层规则:", list(validator.double_verify.keys()))

    # 合法任务
    ok_task = build_standard_task("P4真值对账算子", "TASK-0001")
    ok_r = validator.validate_task(ok_task)
    print("\n[1] 合法任务:", "✅ 通过" if ok_r["valid"] else "❌ 拒绝", "| 签名:", ok_r["signature"][:16], "…")
    print("    调度层裁决:", validator.dispatch_layer(ok_task))

    # 异源任务
    evil_task = {"meta_homo_root": "EVIL-ROOT", "asset_did": "DID-X", "task_id": "T-X"}
    evil_r = validator.validate_task(evil_task)
    print("[2] 异源任务:", "✅ 通过" if evil_r["valid"] else "❌ 拦截", "| 原因:", evil_r["reason"])
    print("    调度层裁决:", validator.dispatch_layer(evil_task))

    # 缺字段任务
    poor_task = {"meta_homo_root": "Ω-TAN-7-001", "asset_did": "DID-BR-000002", "task_id": "T-1"}
    poor_r = validator.validate_task(poor_task)
    print("[3] 缺字段任务:", "✅ 通过" if poor_r["valid"] else "❌ 拦截", "| 原因:", poor_r["reason"])
