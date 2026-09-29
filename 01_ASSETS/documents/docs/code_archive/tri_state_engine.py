#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜三态驱动引擎 (Tri-State Engine)
三态：逻辑态(Logic State) → 信息态(Info State) → 能量态(Energy State)
完整链路：逻辑态裁决 → 信息态解析 → 能量态分配 → 执行 → 三态闭环反馈
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR / "config"))

try:
    from config_loader import config as _config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False

def _cfg(key, default):
    if _CONFIG_AVAILABLE:
        return _config.get(key, default)
    return default


class LogicState:
    """逻辑态：裁决与决策层
    负责：权限校验、规则匹配、优先级排序、冲突检测、熔断裁决
    """

    # 裁决结果常量
    ALLOW = "allow"
    DENY = "deny"
    DEFER = "defer"  # 暂缓，需人工审批

    def __init__(self):
        self.rules = self._load_rules()
        self.decision_log = []

    def _load_rules(self):
        """加载逻辑态规则"""
        return {
            "allowed_actions": _cfg("three_state.logic_state.allowed_actions", [
                "SCAN_ASSET", "RUN_PIPELINE", "CROSS_VERIFY",
                "RELOAD_META_RULE", "SYNC_LEDGER", "STOP_WORKER",
                "TRUTH_REPORT", "BACKUP_NOW", "RESTORE_NOW"
            ]),
            "priority_levels": {"critical": 0, "high": 1, "normal": 2, "low": 3},
            "require_approval": _cfg("three_state.logic_state.require_approval", []),
            "max_concurrent_tasks": _cfg("three_state.logic_state.max_concurrent_tasks", 5),
        }

    def adjudicate(self, cmd_package):
        """逻辑态裁决：对指令包进行完整裁决

        裁决维度：
        1. 动作合法性校验
        2. 来源权限校验
        3. 优先级评定
        4. 冲突检测
        5. 熔断裁决

        Returns:
            dict: {decision, priority, reason, requires_approval, rule_trace}
        """
        logic_state = cmd_package.get("logic_state", {})
        info_state = cmd_package.get("info_state", {})
        action = info_state.get("action", "UNKNOWN")
        source = logic_state.get("source", "unknown")
        priority_hint = logic_state.get("priority", "normal")

        trace = []

        # 1. 动作合法性校验
        if action not in self.rules["allowed_actions"]:
            trace.append(f"动作{action}不在允许列表中")
            return self._decision(self.DENY, priority_hint, "非法动作，熔断拦截", trace)
        trace.append(f"动作{action}合法")

        # 2. 来源权限校验
        allowed_sources = _cfg("three_state.logic_state.allowed_sources",
                               ["MASTER", "worker", "system", "manual"])
        if source not in allowed_sources:
            trace.append(f"来源{source}无权限")
            return self._decision(self.DENY, priority_hint, f"来源{source}无执行权限", trace)
        trace.append(f"来源{source}权限验证通过")

        # 3. 优先级评定
        priority = self.rules["priority_levels"].get(priority_hint, 2)
        trace.append(f"优先级评定: {priority_hint}(level {priority})")

        # 4. 人工审批检测
        requires_approval = action in self.rules["require_approval"]
        if requires_approval:
            trace.append(f"动作{action}需人工审批")

        # 5. 显式熔断检测
        if not logic_state.get("allow_execute", True):
            trace.append("逻辑态显式标记allow_execute=False")
            return self._decision(self.DENY, priority_hint, "逻辑态裁决不通过，熔断拦截", trace)

        # 裁决通过
        self._log_decision(action, source, self.ALLOW, priority)
        return self._decision(self.ALLOW, priority_hint, "逻辑态裁决通过", trace,
                              requires_approval=requires_approval)

    def _decision(self, decision, priority, reason, trace, requires_approval=False):
        return {
            "decision": decision,
            "priority": priority,
            "priority_level": self.rules["priority_levels"].get(priority, 2),
            "reason": reason,
            "requires_approval": requires_approval,
            "rule_trace": trace,
            "timestamp": time.time(),
        }

    def _log_decision(self, action, source, decision, priority):
        self.decision_log.append({
            "action": action,
            "source": source,
            "decision": decision,
            "priority": priority,
            "timestamp": time.time(),
        })
        # 只保留最近1000条
        if len(self.decision_log) > 1000:
            self.decision_log = self.decision_log[-1000:]


class InfoState:
    """信息态：数据与真值载荷层
    负责：载荷验证、真值校验、元数据提取、Merkle锚定、内容哈希
    """

    def __init__(self):
        self.processed_payloads = []

    def parse(self, cmd_package):
        """信息态解析：验证并解析指令载荷

        解析维度：
        1. 载荷完整性校验
        2. 真值置信度评估
        3. 元数据提取
        4. 内容哈希计算
        5. Merkle锚定准备

        Returns:
            dict: {valid, action, payload, metadata, content_hash, confidence, merkle_anchor}
        """
        info_state = cmd_package.get("info_state", {})
        action = info_state.get("action", "UNKNOWN")
        payload = info_state.get("payload", {})

        # 1. 载荷完整性校验
        valid = self._validate_payload(action, payload)

        # 2. 真值置信度评估
        confidence = info_state.get("confidence", 0.5)
        if confidence < 0:
            confidence = 0.0
        elif confidence > 1:
            confidence = 1.0

        # 3. 元数据提取
        metadata = {
            "action": action,
            "source": cmd_package.get("logic_state", {}).get("source", "unknown"),
            "timestamp": info_state.get("timestamp", time.time()),
            "payload_size": len(json.dumps(payload, ensure_ascii=False)),
            "payload_keys": list(payload.keys()) if isinstance(payload, dict) else [],
        }

        # 4. 内容哈希计算
        content_str = json.dumps({"action": action, "payload": payload},
                                  sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        # 5. Merkle锚定准备
        merkle_anchor = {
            "leaf_hash": content_hash,
            "action": action,
            "timestamp": metadata["timestamp"],
            "ready_for_append": valid,
        }

        result = {
            "valid": valid,
            "action": action,
            "payload": payload,
            "metadata": metadata,
            "content_hash": content_hash,
            "confidence": confidence,
            "merkle_anchor": merkle_anchor,
        }

        self.processed_payloads.append({
            "content_hash": content_hash,
            "action": action,
            "valid": valid,
            "confidence": confidence,
            "timestamp": time.time(),
        })

        return result

    def _validate_payload(self, action, payload):
        """验证载荷完整性"""
        # 基础验证：payload必须是dict
        if not isinstance(payload, dict):
            return False

        # 特定动作的必需参数
        required_params = {
            "RUN_PIPELINE": ["asset_path"],
            "TRUTH_REPORT": ["truth_key", "truth_value"],
            "RESTORE_NOW": ["backup_path"],
        }

        if action in required_params:
            for param in required_params[action]:
                if param not in payload:
                    return False

        return True


class EnergyState:
    """能量态：资源配额与执行层
    负责：资源采集、阈值裁决、配额分配、执行预算、熔断保护
    """

    def __init__(self):
        self.energy_history = []
        self.fuse_events = []

    def collect(self):
        """采集宿主机能量态指标"""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(str(BASE_DIR))

            energy_data = {
                "cpu_percent": round(cpu_percent, 1),
                "cpu_count": psutil.cpu_count(),
                "mem_percent": round(mem.percent, 1),
                "mem_total_gb": round(mem.total / (1024**3), 2),
                "mem_available_gb": round(mem.available / (1024**3), 2),
                "disk_percent": round(disk.percent, 1),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "load_avg": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0],
                "timestamp": time.time(),
            }
        except ImportError:
            energy_data = {
                "cpu_percent": 0, "mem_percent": 0, "disk_percent": 0,
                "timestamp": time.time(),
            }

        self.energy_history.append(energy_data)
        if len(self.energy_history) > 3600:  # 保留1小时
            self.energy_history = self.energy_history[-3600:]

        return energy_data

    def adjudicate(self, energy_data, cmd_energy_state=None):
        """能量态裁决：根据当前资源状态决定是否允许执行

        裁决维度：
        1. CPU阈值检查
        2. 内存阈值检查
        3. 磁盘阈值检查
        4. 执行预算分配
        5. 熔断级别判定

        Returns:
            dict: {allow, fuse_level, reason, resource_quota, energy_snapshot}
        """
        cmd_energy_state = cmd_energy_state or {}

        # 阈值配置（支持热加载）
        cpu_warn = _cfg("worker.energy_cpu_warning", 80.0)
        cpu_crit = _cfg("worker.energy_cpu_critical", 95.0)
        mem_warn = _cfg("worker.energy_mem_warning", 80.0)
        mem_crit = _cfg("worker.energy_mem_critical", 95.0)
        disk_warn = _cfg("worker.energy_disk_warning", 85.0)
        disk_crit = _cfg("worker.energy_disk_critical", 95.0)

        cpu = energy_data.get("cpu_percent", 0)
        mem = energy_data.get("mem_percent", 0)
        disk = energy_data.get("disk_percent", 0)

        # 熔断级别判定
        fuse_level = "normal"
        reasons = []

        if cpu >= cpu_crit or mem >= mem_crit or disk >= disk_crit:
            fuse_level = "critical"
            reasons.append(f"资源临界: CPU={cpu}%, MEM={mem}%, DISK={disk}%")
            allow = False
        elif cpu >= cpu_warn or mem >= mem_warn or disk >= disk_warn:
            fuse_level = "warning"
            reasons.append(f"资源告警: CPU={cpu}%, MEM={mem}%, DISK={disk}%")
            # 告警级别只允许高优先级任务
            priority = cmd_energy_state.get("priority_level", 2)
            allow = priority <= 1  # critical/high允许
        else:
            fuse_level = "normal"
            allow = True

        # 执行预算分配
        resource_quota = self._allocate_quota(energy_data, fuse_level, cmd_energy_state)

        if fuse_level != "normal":
            self.fuse_events.append({
                "level": fuse_level,
                "reasons": reasons,
                "energy_snapshot": energy_data,
                "timestamp": time.time(),
            })

        return {
            "allow": allow,
            "fuse_level": fuse_level,
            "reason": "; ".join(reasons) if reasons else "资源充足，允许执行",
            "resource_quota": resource_quota,
            "energy_snapshot": energy_data,
            "thresholds": {
                "cpu_warn": cpu_warn, "cpu_crit": cpu_crit,
                "mem_warn": mem_warn, "mem_crit": mem_crit,
                "disk_warn": disk_warn, "disk_crit": disk_crit,
            },
        }

    def _allocate_quota(self, energy_data, fuse_level, cmd_energy_state):
        """分配执行资源配额"""
        # 根据熔断级别动态调整配额
        quota_factors = {
            "normal": 1.0,
            "warning": 0.5,
            "critical": 0.0,
        }
        factor = quota_factors.get(fuse_level, 1.0)

        # 基础配额
        base_quota = cmd_energy_state.get("base_quota", {
            "cpu_budget_percent": 20,
            "mem_budget_mb": 512,
            "timeout_seconds": 300,
            "max_retries": 3,
        })

        return {
            "cpu_budget_percent": int(base_quota["cpu_budget_percent"] * factor),
            "mem_budget_mb": int(base_quota["mem_budget_mb"] * factor),
            "timeout_seconds": int(base_quota["timeout_seconds"] * factor),
            "max_retries": base_quota["max_retries"],
            "quota_factor": factor,
        }


class TriStateEngine:
    """三态驱动引擎：整合逻辑态→信息态→能量态完整链路

    完整执行流程：
    1. 逻辑态裁决 (LogicState.adjudicate)
    2. 信息态解析 (InfoState.parse)
    3. 能量态分配 (EnergyState.adjudicate)
    4. 执行任务
    5. 三态闭环反馈 (结果回写三态状态)
    """

    def __init__(self):
        self.logic = LogicState()
        self.info = InfoState()
        self.energy = EnergyState()
        self.execution_log = []
        self.stats = {
            "total_commands": 0,
            "allowed": 0,
            "denied_logic": 0,
            "denied_energy": 0,
            "executed": 0,
            "failed": 0,
            "fuse_events": 0,
        }

    def route(self, cmd_package, executor=None):
        """三态路由：完整执行三态驱动链路

        Args:
            cmd_package: 指令包，包含logic_state/info_state/energy_state
            executor: 可选的执行函数，签名为 executor(task_result) -> result

        Returns:
            dict: 完整的三态路由结果，包含各阶段裁决和执行结果
        """
        self.stats["total_commands"] += 1
        route_id = hashlib.sha256(f"{time.time()}-{self.stats['total_commands']}".encode()).hexdigest()[:16]

        result = {
            "route_id": route_id,
            "timestamp": time.time(),
            "stages": {},
        }

        # 阶段1：逻辑态裁决
        logic_result = self.logic.adjudicate(cmd_package)
        result["stages"]["logic_state"] = logic_result

        if logic_result["decision"] != LogicState.ALLOW:
            self.stats["denied_logic"] += 1
            result["final_status"] = "denied_by_logic"
            result["reason"] = logic_result["reason"]
            return result

        # 阶段2：信息态解析
        info_result = self.info.parse(cmd_package)
        result["stages"]["info_state"] = info_result

        if not info_result["valid"]:
            self.stats["denied_logic"] += 1
            result["final_status"] = "invalid_payload"
            result["reason"] = "信息态载荷验证失败"
            return result

        # 阶段3：能量态采集与裁决
        energy_data = self.energy.collect()
        energy_result = self.energy.adjudicate(energy_data, cmd_package.get("energy_state", {}))
        result["stages"]["energy_state"] = energy_result

        if energy_result["fuse_level"] == "critical":
            self.stats["denied_energy"] += 1
            self.stats["fuse_events"] += 1
            result["final_status"] = "denied_by_energy"
            result["reason"] = energy_result["reason"]
            return result

        # 阶段4：执行（如果提供了executor）
        self.stats["allowed"] += 1
        if executor:
            try:
                task_result = {
                    "task": info_result["action"],
                    "params": info_result["payload"],
                    "resource_quota": energy_result["resource_quota"],
                    "route_id": route_id,
                }
                exec_result = executor(task_result)
                result["stages"]["execution"] = {
                    "status": "success" if exec_result.get("ok") else "failed",
                    "result": exec_result,
                }
                if exec_result.get("ok"):
                    self.stats["executed"] += 1
                else:
                    self.stats["failed"] += 1
                result["final_status"] = "executed"
            except Exception as e:
                self.stats["failed"] += 1
                result["stages"]["execution"] = {"status": "error", "error": str(e)}
                result["final_status"] = "execution_error"
                result["reason"] = f"执行异常: {str(e)}"
        else:
            result["final_status"] = "routed"
            result["reason"] = "三态路由完成，等待外部执行"

        # 阶段5：三态闭环反馈
        result["feedback"] = self._generate_feedback(result)

        # 记录执行日志
        self.execution_log.append({
            "route_id": route_id,
            "action": info_result["action"],
            "final_status": result["final_status"],
            "logic_decision": logic_result["decision"],
            "energy_fuse": energy_result["fuse_level"],
            "timestamp": time.time(),
        })
        if len(self.execution_log) > 10000:
            self.execution_log = self.execution_log[-10000:]

        return result

    def _generate_feedback(self, route_result):
        """生成三态闭环反馈"""
        return {
            "logic_feedback": {
                "decision": route_result["stages"]["logic_state"]["decision"],
                "rule_trace_count": len(route_result["stages"]["logic_state"]["rule_trace"]),
            },
            "info_feedback": {
                "content_hash": route_result["stages"]["info_state"]["content_hash"],
                "confidence": route_result["stages"]["info_state"]["confidence"],
                "merkle_ready": route_result["stages"]["info_state"]["merkle_anchor"]["ready_for_append"],
            },
            "energy_feedback": {
                "fuse_level": route_result["stages"]["energy_state"]["fuse_level"],
                "quota_factor": route_result["stages"]["energy_state"]["resource_quota"]["quota_factor"],
            },
            "final_status": route_result["final_status"],
            "feedback_timestamp": time.time(),
        }

    def get_stats(self):
        """获取引擎统计信息"""
        return {
            **self.stats,
            "logic_decision_log_size": len(self.logic.decision_log),
            "info_processed_count": len(self.info.processed_payloads),
            "energy_history_size": len(self.energy.energy_history),
            "fuse_event_count": len(self.energy.fuse_events),
            "execution_log_size": len(self.execution_log),
            "config_hot_reload": _CONFIG_AVAILABLE,
        }

    def reload_config(self):
        """重新加载配置（热加载）"""
        if _CONFIG_AVAILABLE:
            _config.reload()
            self.logic.rules = self.logic._load_rules()
        return {"reloaded": True, "config_available": _CONFIG_AVAILABLE}


# 全局单例
_engine = None

def get_engine():
    """获取三态驱动引擎单例"""
    global _engine
    if _engine is None:
        _engine = TriStateEngine()
    return _engine


if __name__ == "__main__":
    # 测试三态驱动引擎
    print("=" * 60)
    print("元极恒一｜三态驱动引擎测试")
    print("=" * 60)

    engine = get_engine()

    # 测试1：合法指令
    print("\n--- 测试1: 合法SCAN_ASSET指令 ---")
    cmd1 = {
        "logic_state": {"allow_execute": True, "source": "MASTER", "priority": "normal"},
        "info_state": {"action": "SCAN_ASSET", "payload": {}, "confidence": 0.9},
        "energy_state": {},
    }
    result1 = engine.route(cmd1)
    print(f"  最终状态: {result1['final_status']}")
    print(f"  逻辑裁决: {result1['stages']['logic_state']['decision']}")
    print(f"  能量熔断: {result1['stages']['energy_state']['fuse_level']}")
    print(f"  内容哈希: {result1['stages']['info_state']['content_hash'][:16]}...")

    # 测试2：非法动作
    print("\n--- 测试2: 非法动作 ---")
    cmd2 = {
        "logic_state": {"allow_execute": True, "source": "MASTER"},
        "info_state": {"action": "INVALID_ACTION", "payload": {}},
        "energy_state": {},
    }
    result2 = engine.route(cmd2)
    print(f"  最终状态: {result2['final_status']}")
    print(f"  拒绝原因: {result2.get('reason', 'N/A')}")

    # 测试3：逻辑态熔断
    print("\n--- 测试3: 逻辑态熔断 ---")
    cmd3 = {
        "logic_state": {"allow_execute": False, "source": "MASTER"},
        "info_state": {"action": "SCAN_ASSET", "payload": {}},
        "energy_state": {},
    }
    result3 = engine.route(cmd3)
    print(f"  最终状态: {result3['final_status']}")
    print(f"  拒绝原因: {result3.get('reason', 'N/A')}")

    # 统计
    print("\n--- 引擎统计 ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("三态驱动引擎测试完成")
    print("=" * 60)
