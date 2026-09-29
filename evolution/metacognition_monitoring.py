#!/usr/bin/env python3
"""
元认知自我监测系统 V1.0
ZONGYUAN-ROOT 全域进化第五维度

核心能力：
1. 系统运行状态自我监测
2. 缺陷与异常自我发现
3. 优化方案自我生成
4. 进化决策自我执行
5. 元认知反思与学习
6. 全局健康评分与预警
"""

import hashlib
import time
import uuid
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple
from enum import Enum


class HealthLevel(Enum):
    """健康等级"""
    EXCELLENT = "excellent"     # 优秀（90-100）
    GOOD = "good"               # 良好（75-90）
    FAIR = "fair"               # 一般（60-75）
    POOR = "poor"               # 较差（40-60）
    CRITICAL = "critical"       # 危急（<40）


class AnomalySeverity(Enum):
    """异常严重程度"""
    INFO = "info"               # 信息
    LOW = "low"                 # 低
    MEDIUM = "medium"           # 中
    HIGH = "high"               # 高
    CRITICAL = "critical"       # 危急


class AnomalyCategory(Enum):
    """异常类别"""
    PERFORMANCE = "performance"     # 性能问题
    STABILITY = "stability"         # 稳定性问题
    SECURITY = "security"           # 安全问题
    RESOURCE = "resource"           # 资源问题
    CONFIGURATION = "configuration" # 配置问题
    DEPENDENCY = "dependency"       # 依赖问题
    DATA = "data"                   # 数据问题
    UNKNOWN = "unknown"             # 未知


class OptimizationPriority(Enum):
    """优化优先级"""
    P0 = "P0"  # 紧急（立即处理）
    P1 = "P1"  # 高（24小时内）
    P2 = "P2"  # 中（本周内）
    P3 = "P3"  # 低（本月内）
    P4 = "P4"  # 极低（长期规划）


@dataclass
class SystemMetric:
    """系统指标"""
    name: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    timestamp: float = field(default_factory=time.time)
    history: List[Tuple[float, float]] = field(default_factory=list)  # (timestamp, value)

    @property
    def status(self) -> str:
        if self.value >= self.threshold_critical:
            return "critical"
        elif self.value >= self.threshold_warning:
            return "warning"
        return "normal"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "threshold_warning": self.threshold_warning,
            "threshold_critical": self.threshold_critical,
            "timestamp": self.timestamp
        }


@dataclass
class Anomaly:
    """异常记录"""
    anomaly_id: str
    category: AnomalyCategory
    severity: AnomalySeverity
    title: str
    description: str
    detected_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    status: str = "detected"  # detected, analyzing, optimizing, resolved, ignored
    root_cause: Optional[str] = None
    affected_components: List[str] = field(default_factory=list)
    optimization_plan_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "anomaly_id": self.anomaly_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "status": self.status,
            "root_cause": self.root_cause,
            "affected_components": self.affected_components,
            "optimization_plan_id": self.optimization_plan_id,
            "metadata": self.metadata
        }


@dataclass
class OptimizationPlan:
    """优化方案"""
    plan_id: str
    title: str
    description: str
    priority: OptimizationPriority
    related_anomalies: List[str] = field(default_factory=list)
    status: str = "proposed"  # proposed, approved, executing, completed, failed, cancelled
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    expected_benefit: str = ""
    estimated_effort: str = ""
    risk_level: str = "medium"  # low, medium, high
    execution_steps: List[Dict] = field(default_factory=list)
    execution_log: List[Dict] = field(default_factory=list)
    result: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "related_anomalies": self.related_anomalies,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "expected_benefit": self.expected_benefit,
            "estimated_effort": self.estimated_effort,
            "risk_level": self.risk_level,
            "execution_steps_count": len(self.execution_steps),
            "execution_log_count": len(self.execution_log),
            "result": self.result,
            "metadata": self.metadata
        }


@dataclass
class MetacognitionReflection:
    """元认知反思记录"""
    reflection_id: str
    type: str  # self_evaluation, learning, insight, decision_review
    title: str
    content: str
    created_at: float = field(default_factory=time.time)
    related_events: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class MetacognitionMonitoringSystem:
    """元认知自我监测系统"""

    def __init__(self):
        self.metrics: Dict[str, SystemMetric] = {}
        self.anomalies: Dict[str, Anomaly] = {}
        self.optimization_plans: Dict[str, OptimizationPlan] = {}
        self.reflections: List[MetacognitionReflection] = []
        self.monitoring_log: List[Dict] = []
        self.global_health_score: float = 100.0
        self.health_history: List[Tuple[float, float]] = []  # (timestamp, score)
        self.created_at = time.time()
        self.last_monitoring_cycle: Optional[float] = None

        # 初始化默认指标
        self._init_default_metrics()

    def _init_default_metrics(self):
        """初始化默认监控指标"""
        default_metrics = [
            ("cpu_usage", "CPU使用率", "%", 70, 90),
            ("memory_usage", "内存使用率", "%", 75, 90),
            ("disk_usage", "磁盘使用率", "%", 80, 95),
            ("network_latency", "网络延迟", "ms", 100, 300),
            ("service_uptime", "服务可用率", "%", 99, 95),  # 注意：这个是越低越差
            ("error_rate", "错误率", "%", 1, 5),
            ("response_time", "平均响应时间", "ms", 500, 2000),
            ("truth_conflict_rate", "真值冲突率", "%", 5, 15),
            ("sync_success_rate", "同步成功率", "%", 95, 85),  # 越低越差
            ("node_online_rate", "节点在线率", "%", 90, 75),  # 越低越差
        ]

        for metric_id, name, unit, warn, critical in default_metrics:
            self.metrics[metric_id] = SystemMetric(
                name=name,
                value=0,
                unit=unit,
                threshold_warning=warn,
                threshold_critical=critical
            )

    def update_metric(self, metric_id: str, value: float) -> Dict:
        """更新指标"""
        if metric_id not in self.metrics:
            return {"success": False, "error": f"Metric {metric_id} not found"}

        metric = self.metrics[metric_id]
        old_value = metric.value
        metric.value = value
        metric.timestamp = time.time()
        metric.history.append((time.time(), value))
        # 保留最近100条历史
        if len(metric.history) > 100:
            metric.history = metric.history[-100:]

        # 检测阈值异常
        if metric.status != "normal":
            self._detect_metric_anomaly(metric)

        self._log_event("metric_updated", {
            "metric_id": metric_id,
            "old_value": old_value,
            "new_value": value,
            "status": metric.status
        })

        return {"success": True, "metric_id": metric_id, "value": value, "status": metric.status}

    def _detect_metric_anomaly(self, metric: SystemMetric):
        """检测指标异常"""
        severity = AnomalySeverity.HIGH if metric.status == "critical" else AnomalySeverity.MEDIUM

        # 检查是否已有相同异常未解决
        existing = [a for a in self.anomalies.values()
                   if a.title == f"{metric.name}异常" and a.status in ["detected", "analyzing", "optimizing"]]
        if existing:
            return  # 已有相同异常，不重复创建

        anomaly = Anomaly(
            anomaly_id=f"ANOMALY-{uuid.uuid4().hex[:10]}",
            category=AnomalyCategory.PERFORMANCE,
            severity=severity,
            title=f"{metric.name}异常",
            description=f"{metric.name}当前值为 {metric.value}{metric.unit}，超过{'危急' if metric.status == 'critical' else '警告'}阈值（{metric.threshold_critical if metric.status == 'critical' else metric.threshold_warning}{metric.unit}）",
            affected_components=[metric.name]
        )
        self.anomalies[anomaly.anomaly_id] = anomaly
        self._log_event("anomaly_detected", {
            "anomaly_id": anomaly.anomaly_id,
            "metric": metric.name,
            "value": metric.value,
            "severity": severity.value
        })

    def detect_anomalies(self) -> List[Anomaly]:
        """主动检测异常（综合分析）"""
        new_anomalies = []

        # 1. 指标阈值检测（已在update_metric中处理）
        # 2. 趋势检测（持续恶化）
        for metric_id, metric in self.metrics.items():
            if len(metric.history) >= 5:
                recent = metric.history[-5:]
                values = [v for _, v in recent]
                # 检测持续上升趋势（对于越高越差的指标）
                if metric_id not in ["service_uptime", "sync_success_rate", "node_online_rate"]:
                    if all(values[i] < values[i+1] for i in range(len(values)-1)):
                        trend_anomaly = Anomaly(
                            anomaly_id=f"ANOMALY-TREND-{uuid.uuid4().hex[:8]}",
                            category=AnomalyCategory.PERFORMANCE,
                            severity=AnomalySeverity.MEDIUM,
                            title=f"{metric.name}持续恶化趋势",
                            description=f"{metric.name}在最近5个监测周期内持续上升，从{values[0]:.1f}上升至{values[-1]:.1f}{metric.unit}",
                            affected_components=[metric.name]
                        )
                        self.anomalies[trend_anomaly.anomaly_id] = trend_anomaly
                        new_anomalies.append(trend_anomaly)

        # 3. 服务健康检测（模拟）
        # 4. 依赖关系检测
        # 5. 配置一致性检测

        return new_anomalies

    def analyze_anomaly(self, anomaly_id: str) -> Dict:
        """分析异常根因"""
        anomaly = self.anomalies.get(anomaly_id)
        if not anomaly:
            return {"success": False, "error": "Anomaly not found"}

        anomaly.status = "analyzing"

        # 简化的根因分析（实际应结合更多数据）
        root_causes = {
            "cpu_usage异常": "可能原因：高负载任务并发、内存泄漏导致频繁GC、恶意进程占用",
            "memory_usage异常": "可能原因：内存泄漏、大对象未释放、缓存无上限、并发任务过多",
            "disk_usage异常": "可能原因：日志无轮转、临时文件未清理、备份堆积、资产无限增长",
            "error_rate异常": "可能原因：依赖服务故障、配置错误、代码缺陷、资源不足",
            "truth_conflict_rate异常": "可能原因：多节点写入冲突、真值版本不一致、共识机制故障",
        }

        for key, cause in root_causes.items():
            if key in anomaly.title:
                anomaly.root_cause = cause
                break

        if not anomaly.root_cause:
            anomaly.root_cause = "需要进一步分析，建议收集更多上下文信息"

        anomaly.status = "detected"  # 分析完成，回到已检测状态
        self._log_event("anomaly_analyzed", {
            "anomaly_id": anomaly_id,
            "root_cause": anomaly.root_cause
        })

        return {"success": True, "anomaly_id": anomaly_id, "root_cause": anomaly.root_cause}

    def generate_optimization_plan(self, anomaly_id: str) -> Dict:
        """生成优化方案"""
        anomaly = self.anomalies.get(anomaly_id)
        if not anomaly:
            return {"success": False, "error": "Anomaly not found"}

        # 根据异常类型生成优化方案
        plan_templates = {
            "cpu_usage异常": {
                "title": "CPU使用率优化方案",
                "description": "通过负载均衡、任务限流、代码优化等方式降低CPU使用率",
                "priority": OptimizationPriority.P1,
                "expected_benefit": "CPU使用率降低至70%以下，系统响应速度提升30%",
                "estimated_effort": "4-8小时",
                "risk_level": "low",
                "steps": [
                    {"step": 1, "action": "分析高CPU进程，识别热点", "status": "pending"},
                    {"step": 2, "action": "实施任务限流和优先级调度", "status": "pending"},
                    {"step": 3, "action": "优化热点代码和算法", "status": "pending"},
                    {"step": 4, "action": "验证优化效果并持续监控", "status": "pending"}
                ]
            },
            "memory_usage异常": {
                "title": "内存使用率优化方案",
                "description": "通过内存泄漏修复、缓存上限设置、对象池化等方式降低内存使用率",
                "priority": OptimizationPriority.P1,
                "expected_benefit": "内存使用率降低至75%以下，消除OOM风险",
                "estimated_effort": "6-12小时",
                "risk_level": "medium",
                "steps": [
                    {"step": 1, "action": "内存泄漏检测与定位", "status": "pending"},
                    {"step": 2, "action": "设置缓存上限和淘汰策略", "status": "pending"},
                    {"step": 3, "action": "修复内存泄漏问题", "status": "pending"},
                    {"step": 4, "action": "实施大对象池化", "status": "pending"},
                    {"step": 5, "action": "验证优化效果", "status": "pending"}
                ]
            },
            "disk_usage异常": {
                "title": "磁盘使用率优化方案",
                "description": "通过日志轮转、临时文件清理、冷数据归档等方式释放磁盘空间",
                "priority": OptimizationPriority.P2,
                "expected_benefit": "磁盘使用率降低至80%以下，释放至少20%空间",
                "estimated_effort": "2-4小时",
                "risk_level": "low",
                "steps": [
                    {"step": 1, "action": "磁盘空间分析，定位大文件", "status": "pending"},
                    {"step": 2, "action": "配置日志轮转策略", "status": "pending"},
                    {"step": 3, "action": "清理临时文件和旧日志", "status": "pending"},
                    {"step": 4, "action": "冷数据归档到对象存储", "status": "pending"},
                    {"step": 5, "action": "设置磁盘空间告警", "status": "pending"}
                ]
            }
        }

        # 匹配模板
        template = None
        for key, t in plan_templates.items():
            if key in anomaly.title:
                template = t
                break

        if not template:
            template = {
                "title": f"{anomaly.title}优化方案",
                "description": f"针对{anomaly.title}的综合优化方案",
                "priority": OptimizationPriority.P2,
                "expected_benefit": "异常消除，系统恢复正常状态",
                "estimated_effort": "4-8小时",
                "risk_level": "medium",
                "steps": [
                    {"step": 1, "action": "深入分析异常根因", "status": "pending"},
                    {"step": 2, "action": "制定具体优化措施", "status": "pending"},
                    {"step": 3, "action": "执行优化措施", "status": "pending"},
                    {"step": 4, "action": "验证优化效果", "status": "pending"}
                ]
            }

        plan = OptimizationPlan(
            plan_id=f"PLAN-{uuid.uuid4().hex[:10]}",
            title=template["title"],
            description=template["description"],
            priority=template["priority"],
            related_anomalies=[anomaly_id],
            expected_benefit=template["expected_benefit"],
            estimated_effort=template["estimated_effort"],
            risk_level=template["risk_level"],
            execution_steps=template["steps"]
        )

        self.optimization_plans[plan.plan_id] = plan
        anomaly.optimization_plan_id = plan.plan_id
        anomaly.status = "optimizing"

        self._log_event("optimization_plan_generated", {
            "plan_id": plan.plan_id,
            "anomaly_id": anomaly_id,
            "priority": plan.priority.value
        })

        return {"success": True, "plan_id": plan.plan_id, "plan": plan.to_dict()}

    def execute_optimization_plan(self, plan_id: str) -> Dict:
        """执行优化方案（模拟执行）"""
        plan = self.optimization_plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}

        plan.status = "executing"
        plan.started_at = time.time()

        # 模拟执行步骤
        for step in plan.execution_steps:
            step["status"] = "completed"
            step["completed_at"] = time.time()
            plan.execution_log.append({
                "step": step["step"],
                "action": step["action"],
                "status": "completed",
                "timestamp": time.time()
            })

        plan.status = "completed"
        plan.completed_at = time.time()
        plan.result = {
            "success": True,
            "duration_seconds": plan.completed_at - plan.started_at,
            "steps_completed": len(plan.execution_steps),
            "message": "优化方案执行完成，系统状态已改善"
        }

        # 标记相关异常为已解决
        for anomaly_id in plan.related_anomalies:
            if anomaly_id in self.anomalies:
                self.anomalies[anomaly_id].status = "resolved"
                self.anomalies[anomaly_id].resolved_at = time.time()

        self._log_event("optimization_plan_executed", {
            "plan_id": plan_id,
            "duration": plan.result["duration_seconds"],
            "success": True
        })

        return {"success": True, "plan_id": plan_id, "result": plan.result}

    def calculate_global_health(self) -> float:
        """计算全局健康评分"""
        if not self.metrics:
            return 100.0

        # 加权计算（关键指标权重更高）
        weights = {
            "service_uptime": 0.20,
            "error_rate": 0.15,
            "cpu_usage": 0.10,
            "memory_usage": 0.10,
            "disk_usage": 0.10,
            "response_time": 0.10,
            "sync_success_rate": 0.10,
            "node_online_rate": 0.10,
            "truth_conflict_rate": 0.05,
            "network_latency": 0.05,
        }

        total_score = 0.0
        total_weight = 0.0

        for metric_id, metric in self.metrics.items():
            weight = weights.get(metric_id, 0.05)
            # 计算单个指标得分（0-100）
            if metric_id in ["service_uptime", "sync_success_rate", "node_online_rate"]:
                # 越高越好的指标
                score = min(100, max(0, metric.value))
            else:
                # 越低越好的指标
                if metric.value <= metric.threshold_warning:
                    score = 100
                elif metric.value <= metric.threshold_critical:
                    score = 50
                else:
                    score = max(0, 100 - (metric.value - metric.threshold_critical) * 2)

            total_score += score * weight
            total_weight += weight

        if total_weight > 0:
            self.global_health_score = total_score / total_weight
        else:
            self.global_health_score = 100.0

        # 记录历史
        self.health_history.append((time.time(), self.global_health_score))
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]

        return self.global_health_score

    def get_health_level(self) -> HealthLevel:
        """获取健康等级"""
        score = self.global_health_score
        if score >= 90:
            return HealthLevel.EXCELLENT
        elif score >= 75:
            return HealthLevel.GOOD
        elif score >= 60:
            return HealthLevel.FAIR
        elif score >= 40:
            return HealthLevel.POOR
        return HealthLevel.CRITICAL

    def metacognition_reflect(self, reflection_type: str, title: str,
                                content: str, insights: List[str] = None,
                                action_items: List[str] = None) -> Dict:
        """元认知反思"""
        reflection = MetacognitionReflection(
            reflection_id=f"REFLECT-{uuid.uuid4().hex[:10]}",
            type=reflection_type,
            title=title,
            content=content,
            insights=insights or [],
            action_items=action_items or []
        )
        self.reflections.append(reflection)

        self._log_event("metacognition_reflection", {
            "reflection_id": reflection.reflection_id,
            "type": reflection_type,
            "title": title
        })

        return {"success": True, "reflection_id": reflection.reflection_id}

    def run_monitoring_cycle(self) -> Dict:
        """运行完整监测周期"""
        self.last_monitoring_cycle = time.time()

        # 1. 检测异常
        new_anomalies = self.detect_anomalies()

        # 2. 计算全局健康
        health_score = self.calculate_global_health()
        health_level = self.get_health_level()

        # 3. 生成元认知反思
        if health_level in [HealthLevel.POOR, HealthLevel.CRITICAL]:
            self.metacognition_reflect(
                "self_evaluation",
                "系统健康状态预警",
                f"当前系统健康评分为{health_score:.1f}，等级为{health_level.value}，需要立即关注和优化",
                insights=["系统健康状态持续下降可能导致服务不可用", "应优先处理高优先级异常"],
                action_items=["立即处理P0/P1级异常", "增加资源监控频率", "考虑扩容或优化"]
            )

        result = {
            "cycle_time": time.time(),
            "health_score": health_score,
            "health_level": health_level.value,
            "new_anomalies_detected": len(new_anomalies),
            "total_anomalies": len(self.anomalies),
            "open_anomalies": len([a for a in self.anomalies.values() if a.status in ["detected", "analyzing", "optimizing"]]),
            "total_optimization_plans": len(self.optimization_plans),
            "active_plans": len([p for p in self.optimization_plans.values() if p.status in ["proposed", "executing"]]),
            "total_reflections": len(self.reflections)
        }

        self._log_event("monitoring_cycle_completed", result)
        return result

    def get_system_status(self) -> Dict:
        """获取系统状态总览"""
        return {
            "system": "metacognition_monitoring_v1.0",
            "global_health_score": self.global_health_score,
            "health_level": self.get_health_level().value,
            "metrics": {mid: m.to_dict() for mid, m in self.metrics.items()},
            "anomalies": {
                "total": len(self.anomalies),
                "open": len([a for a in self.anomalies.values() if a.status in ["detected", "analyzing", "optimizing"]]),
                "resolved": len([a for a in self.anomalies.values() if a.status == "resolved"]),
                "by_severity": {
                    s.value: len([a for a in self.anomalies.values() if a.severity == s])
                    for s in AnomalySeverity
                }
            },
            "optimization_plans": {
                "total": len(self.optimization_plans),
                "active": len([p for p in self.optimization_plans.values() if p.status in ["proposed", "executing"]]),
                "completed": len([p for p in self.optimization_plans.values() if p.status == "completed"]),
                "by_priority": {
                    p.value: len([pl for pl in self.optimization_plans.values() if pl.priority == p])
                    for p in OptimizationPriority
                }
            },
            "reflections": len(self.reflections),
            "monitoring_cycles": len(self.monitoring_log),
            "last_cycle": self.last_monitoring_cycle,
            "created_at": self.created_at
        }

    def _log_event(self, event_type: str, data: Dict):
        """记录监测事件"""
        self.monitoring_log.append({
            "event_type": event_type,
            "timestamp": time.time(),
            "data": data
        })


# 全局元认知监测系统实例
global_metacognition_system = MetacognitionMonitoringSystem()


if __name__ == "__main__":
    print("=" * 60)
    print("ZONGYUAN-ROOT 元认知自我监测系统 V1.0 测试")
    print("=" * 60)

    system = global_metacognition_system

    # 更新指标（模拟正常状态）
    print("\n【更新系统指标（正常状态）】")
    metrics_normal = [
        ("cpu_usage", 45.2),
        ("memory_usage", 62.8),
        ("disk_usage", 68.5),
        ("network_latency", 45.3),
        ("service_uptime", 99.95),
        ("error_rate", 0.3),
        ("response_time", 230.5),
        ("truth_conflict_rate", 2.1),
        ("sync_success_rate", 98.7),
        ("node_online_rate", 95.0),
    ]
    for metric_id, value in metrics_normal:
        result = system.update_metric(metric_id, value)
        print(f"  ✅ {metric_id}: {value} ({result['status']})")

    # 计算全局健康
    print("\n【计算全局健康评分】")
    score = system.calculate_global_health()
    level = system.get_health_level()
    print(f"  全局健康评分: {score:.1f}/100")
    print(f"  健康等级: {level.value}")

    # 模拟异常状态
    print("\n【模拟异常状态（CPU和内存飙升）】")
    system.update_metric("cpu_usage", 92.5)
    system.update_metric("memory_usage", 88.3)
    system.update_metric("error_rate", 6.2)

    # 检测异常
    print("\n【检测异常】")
    anomalies = system.detect_anomalies()
    print(f"  检测到 {len(anomalies)} 个新异常")
    for anomaly in system.anomalies.values():
        print(f"    ⚠️ {anomaly.anomaly_id}: [{anomaly.severity.value}] {anomaly.title}")

    # 分析异常根因
    print("\n【分析异常根因】")
    for anomaly_id in list(system.anomalies.keys())[:2]:
        result = system.analyze_anomaly(anomaly_id)
        print(f"  ✅ {anomaly_id}: {result['root_cause'][:50]}...")

    # 生成优化方案
    print("\n【生成优化方案】")
    for anomaly_id in list(system.anomalies.keys())[:2]:
        result = system.generate_optimization_plan(anomaly_id)
        plan = result['plan']
        print(f"  ✅ {plan['plan_id']}: {plan['title']}")
        print(f"     优先级: {plan['priority']}, 预期收益: {plan['expected_benefit'][:30]}...")
        print(f"     执行步骤: {plan['execution_steps_count']}步")

    # 执行优化方案
    print("\n【执行优化方案】")
    for plan_id in list(system.optimization_plans.keys())[:1]:
        result = system.execute_optimization_plan(plan_id)
        print(f"  ✅ {plan_id}: 执行完成, 耗时{result['result']['duration_seconds']:.2f}秒")

    # 元认知反思
    print("\n【元认知反思】")
    result = system.metacognition_reflect(
        "self_evaluation",
        "系统异常处理反思",
        "本次监测周期检测到CPU和内存异常，已生成并执行优化方案。反思整个过程，发现异常检测响应及时，但根因分析深度不足，建议增加更多上下文信息收集。",
        insights=[
            "异常检测响应时间在可接受范围内",
            "根因分析需要更多上下文数据支持",
            "优化方案执行效率可以进一步提升",
            "应建立异常模式库以加速后续处理"
        ],
        action_items=[
            "增加异常上下文信息收集机制",
            "建立常见异常模式库和解决方案库",
            "优化根因分析算法，提高准确性",
            "设置异常处理SLA和超时告警"
        ]
    )
    print(f"  ✅ 反思记录: {result['reflection_id']}")

    # 恢复正常状态并重新计算健康
    print("\n【恢复正常状态并重新评估】")
    system.update_metric("cpu_usage", 50.0)
    system.update_metric("memory_usage", 65.0)
    system.update_metric("error_rate", 0.5)
    score = system.calculate_global_health()
    level = system.get_health_level()
    print(f"  全局健康评分: {score:.1f}/100")
    print(f"  健康等级: {level.value}")

    # 运行完整监测周期
    print("\n【运行完整监测周期】")
    result = system.run_monitoring_cycle()
    print(f"  健康评分: {result['health_score']:.1f}")
    print(f"  健康等级: {result['health_level']}")
    print(f"  新异常: {result['new_anomalies_detected']}")
    print(f"  总异常: {result['total_anomalies']}")
    print(f"  开放异常: {result['open_anomalies']}")
    print(f"  优化方案: {result['total_optimization_plans']}")
    print(f"  元认知反思: {result['total_reflections']}")

    # 获取系统状态总览
    print("\n【系统状态总览】")
    status = system.get_system_status()
    print(f"  系统: {status['system']}")
    print(f"  全局健康: {status['global_health_score']:.1f} ({status['health_level']})")
    print(f"  指标数: {len(status['metrics'])}")
    print(f"  异常: 总计{status['anomalies']['total']}, 开放{status['anomalies']['open']}, 已解决{status['anomalies']['resolved']}")
    print(f"  异常严重度分布: {status['anomalies']['by_severity']}")
    print(f"  优化方案: 总计{status['optimization_plans']['total']}, 活跃{status['optimization_plans']['active']}, 完成{status['optimization_plans']['completed']}")
    print(f"  优化优先级分布: {status['optimization_plans']['by_priority']}")
    print(f"  元认知反思: {status['reflections']}")
    print(f"  监测周期: {status['monitoring_cycles']}")

    print("\n" + "=" * 60)
    print("✅ 元认知自我监测系统 V1.0 测试完成")
    print("=" * 60)
