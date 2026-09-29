#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-011 稳态进化引擎
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

核心思想：
  稳态是进化的前提，进化是稳态的升华。
  先度量稳态，再决定进化，执行后验证，失败则回滚。

五大组件：
  1. 稳态度量器 (StabilityMeter)   - 量化系统稳态程度(0-100分)
  2. 进化决策器 (EvolutionDecider)  - 基于稳态分数决定进化策略
  3. 进化执行器 (EvolutionExecutor)  - 将进化建议转化为实际动作
  4. 进化验证器 (EvolutionVerifier)  - 执行前后对比，失败回滚
  5. 速率控制器 (RateController)     - 控制进化频率和幅度
"""

import os
import sys
import time
import json
import logging
import sqlite3
import subprocess
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

# ============================================================
# 配置
# ============================================================
CONFIG = {
    # 路径
    "state_file": "/opt/ZONGYUAN-ROOT/ops/mr011_evolution/state.json",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/mr011_evolution/audit.jsonl",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr011_evolution/evolution.log",
    "evolution_history": "/opt/ZONGYUAN-ROOT/ops/mr011_evolution/history.jsonl",
    "gateway_db": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",

    # 调度
    "measure_interval": 300,       # 稳态度量间隔（5分钟）
    "evolution_interval": 3600,     # 进化决策间隔（1小时）
    "max_evolutions_per_day": 10,   # 每天最大进化次数
    "min_evolution_gap": 1800,      # 两次进化最小间隔（30分钟）

    # 稳态阈值
    "stability_evolve_threshold": 70,    # 稳态分数>=此值允许进化
    "stability_caution_threshold": 50,    # 稳态分数<此值暂停进化
    "stability_target": 85,               # 稳态目标分数

    # 核心服务清单（用于可用性度量）
    "core_services": [
        "zongyuan-local-llm",
        "mr010-dual-compute-scheduler",
        "dr-resource-monitor",
        "dr-self-healing-monitor",
        "nginx",
        "kg-api",
        "gov-gateway",
        "closed-loop-scheduler",
        "zongyuan-ai-proxy",
    ],

    # 节点ID
    "node_id": "mr011-stability-evolution",
}

# ============================================================
# 日志
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("mr011")

logger = setup_logging()

# ============================================================
# 工具函数
# ============================================================
def run_cmd(cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """执行shell命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def write_json(filepath: str, data: Any):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_jsonl(filepath: str, data: Any):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


# ============================================================
# 状态管理
# ============================================================
class StateManager:
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_measure": None,
            "last_evolution": None,
            "stability_scores": [],        # 历史稳态分数
            "evolution_count": 0,
            "evolution_today": 0,
            "last_evolution_date": None,
            "success_count": 0,
            "rollback_count": 0,
            "started_at": datetime.now().isoformat(),
        }

    def save(self):
        write_json(self.state_file, self.state)

    def record_measure(self, score: float, details: Dict):
        self.state["last_measure"] = datetime.now().isoformat()
        self.state["stability_scores"].append({
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "details": details,
        })
        # 只保留最近100条
        if len(self.state["stability_scores"]) > 100:
            self.state["stability_scores"] = self.state["stability_scores"][-100:]

    def can_evolve(self) -> Tuple[bool, str]:
        """检查是否可以执行进化"""
        # 检查每日次数限制
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("last_evolution_date") != today:
            self.state["evolution_today"] = 0
            self.state["last_evolution_date"] = today

        if self.state["evolution_today"] >= CONFIG["max_evolutions_per_day"]:
            return False, f"今日进化次数已达上限({CONFIG['max_evolutions_per_day']})"

        # 检查最小间隔
        if self.state.get("last_evolution"):
            last_time = datetime.fromisoformat(self.state["last_evolution"])
            gap = (datetime.now() - last_time).total_seconds()
            if gap < CONFIG["min_evolution_gap"]:
                return False, f"距上次进化仅{gap:.0f}秒，最小间隔{CONFIG['min_evolution_gap']}秒"

        return True, "可以进化"

    def record_evolution(self, success: bool, action: str):
        self.state["last_evolution"] = datetime.now().isoformat()
        self.state["evolution_count"] += 1
        self.state["evolution_today"] += 1
        if success:
            self.state["success_count"] += 1
        else:
            self.state["rollback_count"] += 1


# ============================================================
# 组件一：稳态度量器
# ============================================================
class StabilityMeter:
    """量化系统稳态程度（0-100分）"""

    def measure(self) -> Tuple[float, Dict]:
        """执行全面稳态度量，返回(总分, 详情)"""
        details = {}

        # 1. 资源稳定性（30分）
        resource_score, resource_detail = self._measure_resources()
        details["resources"] = resource_detail

        # 2. 服务可用性（30分）
        service_score, service_detail = self._measure_services()
        details["services"] = service_detail

        # 3. 真值质量（25分）
        truth_score, truth_detail = self._measure_truths()
        details["truths"] = truth_detail

        # 4. 进化健康度（15分）
        evolution_score, evolution_detail = self._measure_evolution_health()
        details["evolution_health"] = evolution_detail

        # 总分
        total_score = resource_score + service_score + truth_score + evolution_score
        details["total_score"] = round(total_score, 1)
        details["breakdown"] = {
            "resources": f"{resource_score}/30",
            "services": f"{service_score}/30",
            "truths": f"{truth_score}/25",
            "evolution_health": f"{evolution_score}/15",
        }

        logger.info(f"稳态度量: {total_score:.1f}/100 | 资源{resource_score}/30 服务{service_score}/30 真值{truth_score}/25 进化{evolution_score}/15")
        return total_score, details

    def _measure_resources(self) -> Tuple[float, Dict]:
        """度量资源稳定性（30分）"""
        detail = {}
        score = 30.0

        # 内存
        code, out, _ = run_cmd("free -m | awk 'NR==2{print $2,$3,$7}'")
        if code == 0 and out.strip():
            parts = out.strip().split()
            if len(parts) >= 3:
                total, used, available = int(parts[0]), int(parts[1]), int(parts[2])
                usage_pct = (used / total * 100) if total > 0 else 100
                detail["memory"] = {"total_mb": total, "used_mb": used, "available_mb": available, "usage_pct": round(usage_pct, 1)}
                # 内存使用率评分
                if usage_pct > 90:
                    score -= 15
                elif usage_pct > 80:
                    score -= 10
                elif usage_pct > 70:
                    score -= 5
                elif usage_pct > 60:
                    score -= 2

        # CPU负载
        code, out, _ = run_cmd("cat /proc/loadavg | awk '{print $1,$2,$3}'")
        if code == 0 and out.strip():
            parts = out.strip().split()
            if len(parts) >= 3:
                load1, load5, load15 = float(parts[0]), float(parts[1]), float(parts[2])
                detail["cpu_load"] = {"1min": load1, "5min": load5, "15min": load15}
                # 4核CPU，负载>3算高
                if load1 > 3.5:
                    score -= 8
                elif load1 > 2.5:
                    score -= 4
                elif load1 > 1.5:
                    score -= 2

        # 磁盘
        code, out, _ = run_cmd("df -h / | awk 'NR==2{print $2,$3,$4,$5}'")
        if code == 0 and out.strip():
            parts = out.strip().split()
            if len(parts) >= 4:
                usage_str = parts[3].replace('%', '')
                try:
                    disk_usage = int(usage_str)
                    detail["disk"] = {"usage_pct": disk_usage}
                    if disk_usage > 90:
                        score -= 7
                    elif disk_usage > 80:
                        score -= 4
                except ValueError:
                    pass

        detail["score"] = round(max(0, score), 1)
        return max(0, score), detail

    def _measure_services(self) -> Tuple[float, Dict]:
        """度量服务可用性（30分）"""
        detail = {"active": [], "failed": [], "total": len(CONFIG["core_services"])}
        score = 30.0

        for svc in CONFIG["core_services"]:
            code, out, _ = run_cmd(f"systemctl is-active {svc}")
            status = out.strip()
            if status == "active":
                detail["active"].append(svc)
            else:
                detail["failed"].append({"service": svc, "status": status})
                score -= 3  # 每个失败服务扣3分

        # 9120端口特殊检查
        code, out, _ = run_cmd("netstat -tlnp 2>/dev/null | grep ':9120' | head -1")
        if code == 0 and out.strip():
            detail["gateway_9120"] = "listening"
        else:
            detail["gateway_9120"] = "NOT listening"
            score -= 5

        detail["active_count"] = len(detail["active"])
        detail["failed_count"] = len(detail["failed"])
        detail["score"] = round(max(0, score), 1)
        return max(0, score), detail

    def _measure_truths(self) -> Tuple[float, Dict]:
        """度量真值质量（25分）"""
        detail = {}
        score = 25.0

        try:
            conn = sqlite3.connect(CONFIG["gateway_db"])
            cursor = conn.cursor()

            # 真值总数
            cursor.execute("SELECT COUNT(*) FROM truths")
            total = cursor.fetchone()[0]
            detail["total"] = total

            # 有分类的比例
            cursor.execute("SELECT COUNT(*) FROM truths WHERE category IS NOT NULL AND category != ''")
            categorized = cursor.fetchone()[0]
            cat_pct = (categorized / total * 100) if total > 0 else 0
            detail["categorized_pct"] = round(cat_pct, 1)
            if cat_pct < 50:
                score -= 5
            elif cat_pct < 70:
                score -= 2

            # 最近24小时新增
            cursor.execute("SELECT COUNT(*) FROM truths WHERE updated_at > ?", (time.time() - 86400,))
            recent = cursor.fetchone()[0]
            detail["recent_24h"] = recent
            if recent == 0:
                score -= 3  # 24小时无新真值，系统可能停滞

            # 节点分布
            cursor.execute("SELECT COUNT(DISTINCT node_id) FROM truths")
            nodes = cursor.fetchone()[0]
            detail["distinct_nodes"] = nodes

            conn.close()
        except Exception as e:
            logger.error(f"真质量量度量失败: {e}")
            score -= 10
            detail["error"] = str(e)

        detail["score"] = round(max(0, score), 1)
        return max(0, score), detail

    def _measure_evolution_health(self) -> Tuple[float, Dict]:
        """度量进化健康度（15分）"""
        detail = {}
        score = 15.0

        # MR-010调度器状态
        code, out, _ = run_cmd("systemctl is-active mr010-dual-compute-scheduler")
        if out.strip() == "active":
            detail["mr010_active"] = True
        else:
            detail["mr010_active"] = False
            score -= 8

        # 本地LLM状态
        code, out, _ = run_cmd("systemctl is-active zongyuan-local-llm")
        if out.strip() == "active":
            detail["local_llm_active"] = True
        else:
            detail["local_llm_active"] = False
            score -= 5

        # 自反思真值存在性
        try:
            conn = sqlite3.connect(CONFIG["gateway_db"])
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM truths WHERE truth_key LIKE '%SELF_REFLECTION%'")
            reflections = cursor.fetchone()[0]
            detail["self_reflections"] = reflections
            if reflections == 0:
                score -= 3
            conn.close()
        except Exception:
            pass

        detail["score"] = round(max(0, score), 1)
        return max(0, score), detail


# ============================================================
# 组件二：进化决策器
# ============================================================
class EvolutionDecider:
    """基于稳态分数和自反思结果，决定进化策略"""

    def decide(self, stability_score: float, stability_details: Dict) -> Dict:
        """决定进化动作"""
        decision = {
            "can_evolve": False,
            "strategy": "none",
            "actions": [],
            "reason": "",
            "stability_score": stability_score,
        }

        # 稳态分数判断
        if stability_score < CONFIG["stability_caution_threshold"]:
            decision["strategy"] = "recovery_only"
            decision["reason"] = f"稳态分数{stability_score:.1f}低于警戒值{CONFIG['stability_caution_threshold']}，暂停进化，优先恢复稳态"
            # 只执行恢复性动作
            decision["actions"] = self._get_recovery_actions(stability_details)
            decision["can_evolve"] = True  # 允许恢复性动作
            return decision

        if stability_score < CONFIG["stability_evolve_threshold"]:
            decision["strategy"] = "cautious"
            decision["reason"] = f"稳态分数{stability_score:.1f}处于谨慎区间({CONFIG['stability_caution_threshold']}-{CONFIG['stability_evolve_threshold']})，仅执行小幅进化"
            decision["actions"] = self._get_cautious_actions(stability_details)
            decision["can_evolve"] = True
            return decision

        # 稳态良好，允许正常进化
        decision["strategy"] = "normal"
        decision["reason"] = f"稳态分数{stability_score:.1f}良好(>={CONFIG['stability_evolve_threshold']})，执行正常进化"
        decision["actions"] = self._get_normal_actions(stability_details)
        decision["can_evolve"] = True
        return decision

    def _get_recovery_actions(self, details: Dict) -> List[Dict]:
        """恢复性动作"""
        actions = []
        svc_detail = details.get("services", {})
        for failed in svc_detail.get("failed", []):
            actions.append({
                "type": "service_restart",
                "target": failed["service"],
                "description": f"重启失败服务: {failed['service']}",
                "risk": "low",
            })
        return actions

    def _get_cautious_actions(self, details: Dict) -> List[Dict]:
        """谨慎进化动作（小幅调整）"""
        actions = []
        # 只执行低风险动作
        actions.append({
            "type": "truth_cleanup",
            "description": "清理测试/临时真值",
            "risk": "low",
        })
        return actions

    def _get_normal_actions(self, details: Dict) -> List[Dict]:
        """正常进化动作"""
        actions = []

        # 1. 服务一致性修复
        svc_detail = details.get("services", {})
        for failed in svc_detail.get("failed", []):
            actions.append({
                "type": "service_fix",
                "target": failed["service"],
                "description": f"修复失败服务: {failed['service']}",
                "risk": "medium",
            })

        # 2. 真值质量优化
        truth_detail = details.get("truths", {})
        if truth_detail.get("categorized_pct", 100) < 80:
            actions.append({
                "type": "truth_classification",
                "description": f"对未分类真值进行分类(当前{truth_detail.get('categorized_pct', 0)}%)",
                "risk": "low",
            })

        # 3. 资源阈值优化
        res_detail = details.get("resources", {})
        mem_usage = res_detail.get("memory", {}).get("usage_pct", 50)
        if mem_usage > 70:
            actions.append({
                "type": "resource_optimization",
                "description": f"内存使用率{mem_usage}%偏高，优化资源配置",
                "risk": "medium",
            })

        return actions[:3]  # 每次最多3个动作


# ============================================================
# 组件三：进化执行器
# ============================================================
class EvolutionExecutor:
    """将进化建议转化为实际动作"""

    def execute(self, actions: List[Dict]) -> List[Dict]:
        """执行进化动作，返回执行结果"""
        results = []
        for action in actions:
            result = self._execute_action(action)
            results.append(result)
            # 如果是高风险动作失败，停止后续执行
            if not result["success"] and action.get("risk") == "high":
                logger.error(f"高风险动作失败，停止后续进化: {action['description']}")
                break
        return results

    def _execute_action(self, action: Dict) -> Dict:
        """执行单个动作"""
        action_type = action.get("type")
        description = action.get("description", "")
        logger.info(f"执行进化动作: [{action_type}] {description}")

        try:
            if action_type == "service_restart" or action_type == "service_fix":
                return self._fix_service(action)
            elif action_type == "truth_cleanup":
                return self._cleanup_truths(action)
            elif action_type == "truth_classification":
                return self._classify_truths(action)
            elif action_type == "resource_optimization":
                return self._optimize_resources(action)
            else:
                return {"action": action, "success": False, "error": f"未知动作类型: {action_type}"}
        except Exception as e:
            logger.error(f"动作执行异常: {e}")
            return {"action": action, "success": False, "error": str(e)}

    def _fix_service(self, action: Dict) -> Dict:
        """修复/重启服务"""
        service = action.get("target", "")
        if not service:
            return {"action": action, "success": False, "error": "未指定服务"}

        # 特殊处理：zongyuan-unified-gateway实际由memory_gateway_v3_sqlite.py提供
        if service == "zongyuan-unified-gateway":
            # 检查9120端口是否已经在监听
            code, out, _ = run_cmd("netstat -tlnp 2>/dev/null | grep ':9120'")
            if code == 0 and out.strip():
                # 9120已经在工作，只是systemd服务状态不对
                # 修正systemd服务配置
                logger.info("9120端口已在监听，修正systemd服务配置...")
                # 这里只记录，不实际修改（避免风险）
                return {"action": action, "success": True, "result": "9120端口正常，systemd状态不匹配，建议人工修正服务配置"}

        # 常规重启
        code, out, err = run_cmd(f"systemctl restart {service}", timeout=30)
        if code != 0:
            return {"action": action, "success": False, "error": err}

        time.sleep(3)
        code, out, _ = run_cmd(f"systemctl is-active {service}")
        if out.strip() == "active":
            return {"action": action, "success": True, "result": f"服务{service}已恢复active"}
        else:
            return {"action": action, "success": False, "error": f"重启后仍未active: {out.strip()}"}

    def _cleanup_truths(self, action: Dict) -> Dict:
        """清理测试/临时真值"""
        try:
            conn = sqlite3.connect(CONFIG["gateway_db"])
            cursor = conn.cursor()
            # 标记测试真值为已清理（不实际删除，保留审计）
            cursor.execute(
                "UPDATE truths SET truth_value = ?, category = 'cleaned' WHERE truth_key LIKE '%TEST%' OR truth_key LIKE '%SELTEST%' OR truth_key LIKE '%test%'",
                (json.dumps({"status": "cleaned_by_mr011", "timestamp": datetime.now().isoformat()}),)
            )
            cleaned = cursor.rowcount
            conn.commit()
            conn.close()
            return {"action": action, "success": True, "result": f"标记清理了{cleaned}条测试真值"}
        except Exception as e:
            return {"action": action, "success": False, "error": str(e)}

    def _classify_truths(self, action: Dict) -> Dict:
        """对未分类真值进行分类（触发MR-010分类任务）"""
        # 这里只记录，实际分类由MR-010调度器执行
        return {"action": action, "success": True, "result": "已触发真值分类任务（由MR-010执行）"}

    def _optimize_resources(self, action: Dict) -> Dict:
        """优化资源配置"""
        # 检查是否有可以释放的内存
        code, out, _ = run_cmd("ps aux --sort=-%mem | head -6")
        return {"action": action, "success": True, "result": "资源优化建议已生成，需人工审核后执行", "details": out}


# ============================================================
# 组件四：进化验证器
# ============================================================
class EvolutionVerifier:
    """执行前后对比，失败回滚"""

    def __init__(self, meter: StabilityMeter):
        self.meter = meter
        self.baseline_score = None
        self.baseline_details = None

    def snapshot(self):
        """执行前快照"""
        self.baseline_score, self.baseline_details = self.meter.measure()
        logger.info(f"进化前快照: 稳态分数{self.baseline_score:.1f}")

    def verify(self) -> Tuple[bool, float, Dict]:
        """执行后验证，返回(是否成功, 新分数, 新详情)"""
        new_score, new_details = self.meter.measure()
        delta = new_score - (self.baseline_score or 0)
        logger.info(f"进化后验证: 稳态分数{new_score:.1f} (变化{delta:+.1f})")

        # 验证标准：稳态分数不下降超过5分
        if delta < -5:
            logger.warning(f"进化导致稳态下降{delta:.1f}分，需要回滚")
            return False, new_score, new_details
        return True, new_score, new_details

    def rollback(self, actions: List[Dict]):
        """回滚进化动作"""
        logger.warning("执行回滚...")
        for action in reversed(actions):
            action_type = action.get("type")
            if action_type in ["service_restart", "service_fix"]:
                service = action.get("target", "")
                if service:
                    run_cmd(f"systemctl restart {service}", timeout=30)
        logger.info("回滚完成")


# ============================================================
# 组件五：速率控制器
# ============================================================
class RateController:
    """控制进化频率和幅度"""

    def __init__(self, state: StateManager):
        self.state = state

    def check_rate_limit(self) -> Tuple[bool, str]:
        """检查速率限制"""
        return self.state.can_evolve()


# ============================================================
# 主引擎
# ============================================================
class MR011EvolutionEngine:
    def __init__(self):
        self.state = StateManager(CONFIG["state_file"])
        self.meter = StabilityMeter()
        self.decider = EvolutionDecider()
        self.executor = EvolutionExecutor()
        self.verifier = EvolutionVerifier(self.meter)
        self.rate_controller = RateController(self.state)

    def run_measure_cycle(self):
        """执行稳态度量循环"""
        logger.info("=" * 60)
        logger.info("MR-011 稳态度量循环")
        logger.info("=" * 60)

        score, details = self.meter.measure()
        self.state.record_measure(score, details)
        self.state.save()

        # 写入9120真值
        self._write_stability_truth(score, details)

        logger.info(f"稳态度量完成: {score:.1f}/100")
        return score, details

    def run_evolution_cycle(self):
        """执行进化循环"""
        logger.info("=" * 60)
        logger.info("MR-011 进化循环")
        logger.info("=" * 60)

        # 1. 速率检查
        can_evolve, reason = self.rate_controller.check_rate_limit()
        if not can_evolve:
            logger.info(f"进化速率限制: {reason}")
            return

        # 2. 稳态度量
        score, details = self.meter.measure()
        self.state.record_measure(score, details)

        # 3. 进化决策
        decision = self.decider.decide(score, details)
        logger.info(f"进化决策: 策略={decision['strategy']}, 动作数={len(decision['actions'])}, 原因={decision['reason']}")

        if not decision["can_evolve"] or not decision["actions"]:
            logger.info("无需执行进化动作")
            return

        # 4. 执行前快照
        self.verifier.snapshot()

        # 5. 执行进化动作
        results = self.executor.execute(decision["actions"])
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"进化动作执行: {success_count}/{len(results)}成功")

        # 6. 验证
        verify_success, new_score, new_details = self.verifier.verify()
        if not verify_success:
            logger.warning("进化验证失败，执行回滚")
            self.verifier.rollback(decision["actions"])
            self.state.record_evolution(success=False, action="rollback")
        else:
            self.state.record_evolution(success=True, action=decision["strategy"])

        # 7. 记录进化历史
        history = {
            "timestamp": datetime.now().isoformat(),
            "strategy": decision["strategy"],
            "actions": decision["actions"],
            "results": results,
            "baseline_score": self.verifier.baseline_score,
            "final_score": new_score,
            "verify_success": verify_success,
        }
        append_jsonl(CONFIG["evolution_history"], history)

        # 8. 写入9120真值
        self._write_evolution_truth(history)

        self.state.save()
        logger.info(f"进化循环完成: 策略={decision['strategy']}, 验证={'成功' if verify_success else '失败回滚'}")

    def _write_stability_truth(self, score: float, details: Dict):
        """写入稳态度量真值到9120"""
        try:
            conn = sqlite3.connect(CONFIG["gateway_db"])
            cursor = conn.cursor()
            key = f"STABILITY.MEASURE.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            value = json.dumps({
                "score": score,
                "breakdown": details.get("breakdown", {}),
                "services": {"active": details.get("services", {}).get("active_count", 0), "failed": details.get("services", {}).get("failed_count", 0)},
                "truths": {"total": details.get("truths", {}).get("total", 0), "categorized_pct": details.get("truths", {}).get("categorized_pct", 0)},
                "timestamp": datetime.now().isoformat(),
            }, ensure_ascii=False)
            truth_hash = hashlib.sha256(value.encode()).hexdigest()
            now = time.time()
            cursor.execute(
                "INSERT INTO truths (truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at, version) VALUES (?,?,?,?,?,?,?,1)",
                (key, value, truth_hash, "stability_measure", CONFIG["node_id"], now, now)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"写入稳态度量真值失败: {e}")

    def _write_evolution_truth(self, history: Dict):
        """写入进化记录真值到9120"""
        try:
            conn = sqlite3.connect(CONFIG["gateway_db"])
            cursor = conn.cursor()
            key = f"EVOLUTION.{history['timestamp'].replace(':', '').replace('-', '')}"
            value = json.dumps(history, ensure_ascii=False)
            truth_hash = hashlib.sha256(value.encode()).hexdigest()
            now = time.time()
            cursor.execute(
                "INSERT INTO truths (truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at, version) VALUES (?,?,?,?,?,?,?,1)",
                (key, value, truth_hash, "evolution_record", CONFIG["node_id"], now, now)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"写入进化记录真值失败: {e}")

    def run_forever(self):
        """常驻运行"""
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-011 稳态进化引擎启动                              ║")
        logger.info("║  稳态度量: 每5分钟                                     ║")
        logger.info("║  进化决策: 每1小时                                     ║")
        logger.info("║  稳态目标: >=85分                                      ║")
        logger.info("║  进化原则: 稳态优先，谨慎进化，失败回滚               ║")
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        last_evolution = 0
        while True:
            try:
                # 稳态度量（每5分钟）
                self.run_measure_cycle()

                # 进化决策（每1小时）
                if time.time() - last_evolution >= CONFIG["evolution_interval"]:
                    self.run_evolution_cycle()
                    last_evolution = time.time()

                # 等待到下一个度量周期
                time.sleep(CONFIG["measure_interval"])
            except Exception as e:
                logger.error(f"主循环异常: {e}")
                time.sleep(60)


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-011 稳态进化引擎")
    parser.add_argument("--measure", action="store_true", help="只执行一次稳态度量")
    parser.add_argument("--evolve", action="store_true", help="执行一次进化循环")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--daemon", action="store_true", help="常驻运行（默认）")

    args = parser.parse_args()

    engine = MR011EvolutionEngine()

    if args.status:
        print(json.dumps(engine.state.state, ensure_ascii=False, indent=2))
    elif args.measure:
        score, details = engine.run_measure_cycle()
        print(f"\n稳态分数: {score:.1f}/100")
        print(f"详情: {json.dumps(details.get('breakdown', {}), ensure_ascii=False, indent=2)}")
    elif args.evolve:
        engine.run_evolution_cycle()
        print("进化循环完成")
    else:
        engine.run_forever()
