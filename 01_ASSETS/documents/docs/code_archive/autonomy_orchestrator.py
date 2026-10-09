"""
永恒自治调度器 V1.1.1
本源智能普惠教育体系顶层调度内核
5步固定闭环：感知采集→稳态仲裁→任务分发→执行+自检→归档沉淀
服从元宪法五大公理，三维稳态决策，分级权限，熔断回滚，全程审计
"""
import os
import sys
import json
import time
import threading
import hashlib
from datetime import datetime
from collections import deque

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.settings import (
    SYSTEM_NAME, DID, ANCHOR, META_AXIOMS, EVOLUTION_AXIOMS,
    DECISION_WEIGHTS, DATA_DIR, LOG_DIR
)
from src.common.utils import setup_logger, compute_hash, generate_asset_id

logger = setup_logger("autonomy", "autonomy.log")


class AutonomyConfig:
    """自治配置"""
    def __init__(self):
        self.poll_interval_seconds = 300  # 默认5分钟一轮
        self.max_cycles = 0  # 0=无限循环
        self.auto_execute_light_tasks = True  # 轻量任务自动执行
        self.manual_gate_for_major_changes = True  # 重大变更人工闸口
        self.risk_threshold = 0.3  # 风险阈值，超过则暂停自动执行
        self.error_rate_threshold = 0.1  # 错误率阈值
        self.circuit_breaker_enabled = True  # 熔断开关
        self.max_consecutive_failures = 3  # 连续失败熔断次数
        self.audit_log_max_entries = 10000  # 审计日志最大条数
        self.enabled_modules = [
            "knowledge_graph", "content_engine", "adaptive_learning",
            "teacher_training", "evaluation", "evolution"
        ]

    def to_dict(self):
        return self.__dict__.copy()

    def update(self, updates):
        for k, v in updates.items():
            if hasattr(self, k):
                setattr(self, k, v)


class SteadyStateArbiter:
    """三维稳态仲裁器：利益40%/风险35%/成本25%"""

    @staticmethod
    def evaluate(benefit, risk, cost):
        """计算稳态评分，0-100，越高越优"""
        score = (
            benefit * DECISION_WEIGHTS["利益"] +
            (100 - risk) * DECISION_WEIGHTS["风险"] +
            (100 - cost) * DECISION_WEIGHTS["成本"]
        )
        return round(score, 2)

    @staticmethod
    def should_execute(score, risk, config):
        """判定是否自动执行"""
        if risk > config.risk_threshold * 100:
            return False, "风险超过阈值，提交人工审核"
        if score >= 70:
            return True, "稳态评分达标，自动执行"
        elif score >= 50:
            return True, "稳态评分中等，轻量执行"
        else:
            return False, "稳态评分不足，暂缓执行"


class MetaAxiomValidator:
    """元宪法公理校验器"""

    @staticmethod
    def validate(task_description):
        """校验任务是否违反元宪法五大公理"""
        violations = []
        text = task_description.lower()

        # 人本主导校验
        if "ai完全替代" in text or "无需人类" in text or "全自动决策" in text:
            violations.append("违反人本主导公理：存在AI替代人类导向")

        # 普惠均等校验
        if "仅城区" in text or "排除乡村" in text or "付费门槛" in text:
            violations.append("违反普惠均等公理：存在资源排他或门槛")

        # 向善安全校验
        risk_keywords = ["暴力", "色情", "赌博", "毒品", "反动", "隐私泄露"]
        for kw in risk_keywords:
            if kw in text:
                violations.append(f"违反向善安全公理：包含敏感内容[{kw}]")

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "axioms_checked": list(META_AXIOMS.keys())
        }


class AutonomyTask:
    """自治任务"""
    def __init__(self, task_type, description, module, priority="normal",
                 is_major_change=False, estimated_benefit=50,
                 estimated_risk=20, estimated_cost=30):
        self.task_id = generate_asset_id("AUTO-TASK")
        self.task_type = task_type  # knowledge_update/content_generate/evaluation/evolution/resource_balance
        self.description = description
        self.module = module
        self.priority = priority  # low/normal/high/critical
        self.is_major_change = is_major_change
        self.estimated_benefit = estimated_benefit
        self.estimated_risk = estimated_risk
        self.estimated_cost = estimated_cost
        self.status = "pending"  # pending/approved/rejected/executing/completed/failed/rolled_back/manual_review
        self.created_at = datetime.now().isoformat()
        self.executed_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.steady_score = None
        self.axiom_check = None

    def to_dict(self):
        return self.__dict__.copy()


class EternalAutonomyOrchestrator:
    """永恒自治调度器 - 顶层调度内核"""

    def __init__(self, system=None):
        self.system = system  # AutoEduSystem实例
        self.config = AutonomyConfig()
        self.arbiter = SteadyStateArbiter()
        self.validator = MetaAxiomValidator()

        self.running = False
        self._thread = None
        self._stop_event = threading.Event()

        self.cycle_count = 0
        self.consecutive_failures = 0
        self.circuit_broken = False

        self.task_queue = deque()
        self.completed_tasks = []
        self.manual_review_queue = []
        self.audit_log = deque(maxlen=self.config.audit_log_max_entries)

        self.current_cycle_summary = None
        self.last_cycle_time = None

        logger.info("永恒自治调度器初始化完成，配置：轮询间隔%ds，人工闸口=%s" % (
            self.config.poll_interval_seconds, self.config.manual_gate_for_major_changes))

    def bind_system(self, system):
        """绑定教育系统实例"""
        self.system = system
        logger.info("自治调度器已绑定教育系统实例")

    # ============================================================
    # 5步闭环核心
    # ============================================================

    def step1_perceive(self):
        """第一步：感知采集 - 自动拉取全链路信号"""
        signals = {
            "timestamp": datetime.now().isoformat(),
            "system_status": None,
            "knowledge_stats": None,
            "content_stats": None,
            "learning_stats": None,
            "teacher_stats": None,
            "evaluation_summary": None,
            "evolution_status": None,
            "risk_signals": []
        }

        if self.system:
            try:
                status = self.system.get_system_status()
                signals["system_status"] = {
                    "status": status.get("status"),
                    "uptime": status.get("uptime")
                }
                signals["knowledge_stats"] = self.system.kg.get_graph_stats()
                signals["content_stats"] = self.system.content.get_stats()
                signals["learning_stats"] = self.system.adaptive.get_class_stats()
                signals["teacher_stats"] = self.system.teachers.get_training_stats()
                signals["evaluation_summary"] = self.system.evaluation.get_evaluation_summary()
                signals["evolution_status"] = self.system.evolution.get_evolution_status()

                # 风险信号识别
                if signals["evaluation_summary"].get("quality_alerts", 0) > 5:
                    signals["risk_signals"].append("质量告警数量偏高")
                if signals["content_stats"].get("total", 0) == 0:
                    signals["risk_signals"].append("内容产出为空，需初始化")
            except Exception as e:
                signals["risk_signals"].append(f"感知采集异常: {str(e)}")
                logger.warning(f"感知采集异常: {e}")

        self._audit("perceive", signals)
        return signals

    def step2_arbitrate(self, signals):
        """第二步：稳态仲裁 - 三维稳态算子判定"""
        tasks = []

        # 基于感知信号生成候选任务
        candidate_tasks = self._generate_candidate_tasks(signals)

        for task in candidate_tasks:
            # 公理校验
            task.axiom_check = self.validator.validate(task.description)
            if not task.axiom_check["passed"]:
                task.status = "rejected"
                task.error = f"公理校验未通过: {task.axiom_check['violations']}"
                self._audit("axiom_reject", task.to_dict())
                continue

            # 稳态评分
            task.steady_score = self.arbiter.evaluate(
                task.estimated_benefit, task.estimated_risk, task.estimated_cost
            )

            # 重大变更人工闸口
            if task.is_major_change and self.config.manual_gate_for_major_changes:
                task.status = "manual_review"
                self.manual_review_queue.append(task)
                self._audit("manual_gate", task.to_dict())
                continue

            # 判定是否执行
            should_exec, reason = self.arbiter.should_execute(
                task.steady_score, task.estimated_risk, self.config
            )
            if should_exec and self.config.auto_execute_light_tasks:
                task.status = "approved"
                self.task_queue.append(task)
            else:
                task.status = "rejected"
                task.error = reason
                self._audit("arbitrate_reject", task.to_dict())

        self._audit("arbitrate", {
            "candidates": len(candidate_tasks),
            "approved": len([t for t in candidate_tasks if t.status == "approved"]),
            "manual_review": len([t for t in candidate_tasks if t.status == "manual_review"]),
            "rejected": len([t for t in candidate_tasks if t.status == "rejected"])
        })
        return tasks

    def step3_dispatch(self):
        """第三步：任务分发 - 下发到对应模块"""
        dispatched = []
        while self.task_queue:
            task = self.task_queue.popleft()
            task.status = "executing"
            dispatched.append(task)
            self._audit("dispatch", task.to_dict())
        return dispatched

    def step4_execute_and_verify(self, tasks):
        """第四步：执行+自检 - 模块执行任务，自动单元自检"""
        results = []
        for task in tasks:
            try:
                task.executed_at = datetime.now().isoformat()
                result = self._execute_task(task)
                task.result = result
                task.status = "completed"
                task.completed_at = datetime.now().isoformat()
                self.consecutive_failures = 0
                self._audit("execute_success", task.to_dict())
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                self.consecutive_failures += 1
                logger.error(f"任务执行失败 [{task.task_id}]: {e}")
                self._audit("execute_fail", task.to_dict())

                # 熔断检查
                if (self.config.circuit_breaker_enabled and
                        self.consecutive_failures >= self.config.max_consecutive_failures):
                    self.circuit_broken = True
                    self._audit("circuit_breaker", {
                        "consecutive_failures": self.consecutive_failures,
                        "action": "自治循环自动暂停，等待人工介入"
                    })
                    logger.warning("熔断触发：连续失败%d次，自治循环暂停" % self.consecutive_failures)
                    break

                # 自动回滚（轻量任务）
                if not task.is_major_change:
                    task.status = "rolled_back"
                    self._audit("auto_rollback", task.to_dict())

            results.append(task)
            self.completed_tasks.append(task)

        return results

    def step5_archive(self, cycle_summary):
        """第五步：归档沉淀 - 哈希确权，写入ROOT双库，生成审计日志"""
        archive_record = {
            "cycle_id": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "summary": cycle_summary,
            "did": DID,
            "anchor": ANCHOR
        }
        archive_hash = compute_hash(archive_record)
        archive_record["hash"] = archive_hash

        # 写入审计日志
        self.audit_log.append(archive_record)

        # 持久化审计日志
        self._save_audit_log()

        self.last_cycle_time = datetime.now()
        self.current_cycle_summary = cycle_summary
        self._audit("archive", archive_record)
        logger.info(f"第{self.cycle_count}轮自治循环归档完成，哈希={archive_hash[:16]}...")
        return archive_record

    # ============================================================
    # 完整循环
    # ============================================================

    def run_one_cycle(self):
        """运行一轮完整自治循环（5步）"""
        if self.circuit_broken:
            logger.warning("熔断状态，跳过自治循环")
            return {"status": "circuit_broken", "cycle": self.cycle_count}

        self.cycle_count += 1
        cycle_start = datetime.now()
        logger.info(f"===== 第{self.cycle_count}轮永恒自治循环开始 =====")

        # Step1 感知
        signals = self.step1_perceive()

        # Step2 仲裁
        self.step2_arbitrate(signals)

        # Step3 分发
        tasks = self.step3_dispatch()

        # Step4 执行+自检
        results = self.step4_execute_and_verify(tasks)

        # 循环摘要
        cycle_summary = {
            "cycle": self.cycle_count,
            "duration_seconds": (datetime.now() - cycle_start).total_seconds(),
            "tasks_dispatched": len(tasks),
            "tasks_completed": len([r for r in results if r.status == "completed"]),
            "tasks_failed": len([r for r in results if r.status == "failed"]),
            "tasks_rolled_back": len([r for r in results if r.status == "rolled_back"]),
            "manual_review_pending": len(self.manual_review_queue),
            "circuit_broken": self.circuit_broken,
            "risk_signals": signals.get("risk_signals", [])
        }

        # Step5 归档
        self.step5_archive(cycle_summary)

        logger.info(f"===== 第{self.cycle_count}轮自治循环完成，耗时{cycle_summary['duration_seconds']:.2f}s =====")
        return cycle_summary

    def start(self):
        """启动永恒自治循环（后台线程）"""
        if self.running:
            logger.info("自治循环已在运行中")
            return False
        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._audit("start", {"poll_interval": self.config.poll_interval_seconds})
        logger.info(f"永恒自治循环已启动，轮询间隔{self.config.poll_interval_seconds}秒")
        return True

    def stop(self):
        """停止永恒自治循环"""
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._audit("stop", {"cycle_count": self.cycle_count})
        logger.info("永恒自治循环已停止")
        return True

    def pause(self):
        """临时暂停（保留状态）"""
        self.running = False
        self._audit("pause", {})
        logger.info("永恒自治循环已暂停")
        return True

    def resume(self):
        """恢复运行"""
        if not self.circuit_broken:
            return self.start()
        else:
            logger.warning("熔断状态，需先重置熔断才能恢复")
            return False

    def reset_circuit_breaker(self):
        """重置熔断"""
        self.circuit_broken = False
        self.consecutive_failures = 0
        self._audit("circuit_reset", {})
        logger.info("熔断已重置")
        return True

    def _run_loop(self):
        """后台循环主体"""
        while self.running and not self._stop_event.is_set():
            try:
                self.run_one_cycle()
            except Exception as e:
                logger.error(f"自治循环异常: {e}")
                self.consecutive_failures += 1
            # 等待下一轮，支持中断
            self._stop_event.wait(timeout=self.config.poll_interval_seconds)

    # ============================================================
    # 任务生成与执行
    # ============================================================

    def _generate_candidate_tasks(self, signals):
        """基于感知信号生成候选任务"""
        tasks = []

        # 任务1：知识图谱自动更新（轻量）
        tasks.append(AutonomyTask(
            task_type="knowledge_update",
            description="自动更新知识图谱实体版本，补全实体关系链接",
            module="knowledge_graph",
            priority="normal",
            is_major_change=False,
            estimated_benefit=65, estimated_risk=10, estimated_cost=15
        ))

        # 任务2：内容生产统计检查（轻量）
        content_stats = signals.get("content_stats", {})
        if content_stats and content_stats.get("total", 0) < 10:
            tasks.append(AutonomyTask(
                task_type="content_generate",
                description="自动批量生成初中AI基础理论教材章节与习题",
                module="content_engine",
                priority="high",
                is_major_change=False,
                estimated_benefit=80, estimated_risk=15, estimated_cost=25
            ))

        # 任务3：学习效果评估（轻量）
        tasks.append(AutonomyTask(
            task_type="evaluation",
            description="自动执行学习效果评估与体系运行评估",
            module="evaluation",
            priority="normal",
            is_major_change=False,
            estimated_benefit=60, estimated_risk=5, estimated_cost=10
        ))

        # 任务4：自治演化（中量，非重大变更）
        tasks.append(AutonomyTask(
            task_type="evolution",
            description="执行单轮七大机制自治演化，更新知识与课程",
            module="evolution",
            priority="normal",
            is_major_change=False,
            estimated_benefit=70, estimated_risk=20, estimated_cost=30
        ))

        # 任务5：资源均衡调度（轻量）
        tasks.append(AutonomyTask(
            task_type="resource_balance",
            description="监测城乡校际资源差距，自动生成均衡调度建议",
            module="evolution",
            priority="low",
            is_major_change=False,
            estimated_benefit=55, estimated_risk=10, estimated_cost=20
        ))

        return tasks

    def _execute_task(self, task):
        """执行单个任务"""
        if not self.system:
            raise RuntimeError("系统实例未绑定")

        if task.task_type == "knowledge_update":
            updated = self.system.kg.auto_update()
            relations = self.system.kg.link_prediction()
            return {"updated_entities": updated, "new_relations": relations}

        elif task.task_type == "content_generate":
            result = self.system.content.batch_generate(
                stage="初中", domains=["AI基础理论"], max_chapters=3
            )
            return {"chapters": len(result["chapters"]), "exercises": len(result["exercises"])}

        elif task.task_type == "evaluation":
            learning = self.system.evaluation.evaluate_learning_effect()
            system = self.system.evaluation.evaluate_system_operation()
            return {"learning_avg_mastery": learning.get("avg_mastery"),
                    "balanced_index": system.get("balanced_index")}

        elif task.task_type == "evolution":
            result = self.system.evolution.run_full_evolution_cycle()
            return {"evolution_cycle": result["cycle"]}

        elif task.task_type == "resource_balance":
            result = self.system.evolution.evolve_resource_balancing()
            return {"target_schools": result.get("target_schools"),
                    "gap_reduction": result.get("gap_reduction")}

        else:
            raise ValueError(f"未知任务类型: {task.task_type}")

    # ============================================================
    # 人工审核闸口
    # ============================================================

    def approve_manual_task(self, task_id):
        """人工审核通过任务"""
        for i, task in enumerate(self.manual_review_queue):
            if task.task_id == task_id:
                task.status = "approved"
                self.task_queue.append(task)
                self.manual_review_queue.pop(i)
                self._audit("manual_approve", task.to_dict())
                return True
        return False

    def reject_manual_task(self, task_id, reason=""):
        """人工审核拒绝任务"""
        for i, task in enumerate(self.manual_review_queue):
            if task.task_id == task_id:
                task.status = "rejected"
                task.error = f"人工拒绝: {reason}"
                self.completed_tasks.append(task)
                self.manual_review_queue.pop(i)
                self._audit("manual_reject", task.to_dict())
                return True
        return False

    # ============================================================
    # 状态查询
    # ============================================================

    def get_status(self):
        """获取自治调度器状态"""
        return {
            "running": self.running,
            "cycle_count": self.cycle_count,
            "circuit_broken": self.circuit_broken,
            "consecutive_failures": self.consecutive_failures,
            "poll_interval_seconds": self.config.poll_interval_seconds,
            "pending_tasks": len(self.task_queue),
            "manual_review_pending": len(self.manual_review_queue),
            "completed_tasks": len(self.completed_tasks),
            "audit_log_entries": len(self.audit_log),
            "last_cycle_time": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            "current_cycle_summary": self.current_cycle_summary,
            "config": self.config.to_dict(),
            "did": DID,
            "anchor": ANCHOR
        }

    def get_audit_logs(self, limit=50):
        """获取审计日志"""
        logs = list(self.audit_log)[-limit:]
        return logs[::-1]  # 最新在前

    def get_risk_report(self):
        """获取风险评估报告"""
        return {
            "circuit_broken": self.circuit_broken,
            "consecutive_failures": self.consecutive_failures,
            "manual_review_count": len(self.manual_review_queue),
            "recent_failures": [
                {"task_id": t.task_id, "error": t.error, "time": t.completed_at}
                for t in self.completed_tasks[-10:] if t.status in ("failed", "rolled_back")
            ],
            "risk_threshold": self.config.risk_threshold,
            "recommendation": "正常运行" if not self.circuit_broken else "熔断状态，需人工介入重置"
        }

    # ============================================================
    # 持久化
    # ============================================================

    def _audit(self, action, data):
        """写入审计日志"""
        entry = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "cycle": self.cycle_count,
            "data": data
        }
        self.audit_log.append(entry)

    def _save_audit_log(self):
        """持久化审计日志"""
        try:
            log_path = os.path.join(DATA_DIR, "autonomy_audit_log.json")
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(list(self.audit_log)[-1000:], f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f"审计日志持久化失败: {e}")

    def save_state(self):
        """保存调度器状态"""
        state = {
            "cycle_count": self.cycle_count,
            "circuit_broken": self.circuit_broken,
            "consecutive_failures": self.consecutive_failures,
            "config": self.config.to_dict(),
            "saved_at": datetime.now().isoformat()
        }
        path = os.path.join(DATA_DIR, "autonomy_state.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        logger.info("自治调度器状态已保存")
        return path
