#!/usr/bin/env python3
"""
手脚驱动层加固4 - 执行指标采集器 (Execution Metrics)

采集手脚驱动层的全部执行指标，支持:
  - Counter: 执行总数、成功数、失败数、回滚数、熔断拦截数
  - Gauge: 当前队列长度、熔断器状态、漂移等级
  - Histogram: 执行耗时分布（P50/P95/P99）
  - Prometheus文本格式导出
  - 异常告警阈值（失败率>5%、P99耗时>30s、熔断open等）
  - 指标持久化（JSON快照）
"""

import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExecutionMetrics:
    """
    执行指标采集器

    用法:
        metrics = ExecutionMetrics()
        metrics.record_execution("cas_write", success=True, duration_ms=120.5)
        metrics.record_execution("snapshot", success=False, duration_ms=5000, error="timeout")
        alert = metrics.check_alerts()
        prom = metrics.to_prometheus()
    """

    # 告警阈值
    DEFAULT_THRESHOLDS = {
        'failure_rate_pct': 5.0,        # 失败率 > 5% 告警
        'p99_duration_ms': 30000,       # P99耗时 > 30s 告警
        'p95_duration_ms': 10000,       # P95耗时 > 10s 警告
        'circuit_breaker_open': True,   # 熔断器open告警
        'drift_level_p1': True,         # P1漂移告警
        'queue_backlog': 50,            # 队列积压 > 50 告警
        'rollback_rate_pct': 2.0,       # 回滚率 > 2% 告警
    }

    def __init__(self, metrics_file: str = None, thresholds: dict = None):
        self.metrics_file = Path(metrics_file) if metrics_file else Path(__file__).parent.parent / 'executor' / 'execution_metrics.json'
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._lock = threading.Lock()

        # Counter指标
        self.total_executions = 0
        self.success_count = 0
        self.failure_count = 0
        self.rollback_count = 0
        self.blocked_count = 0  # 熔断/权限拦截
        self.tpc_prepare_count = 0
        self.tpc_commit_count = 0

        # 按Action分组的Counter
        self.action_stats: Dict[str, dict] = {}

        # Histogram: 执行耗时（毫秒）
        self.durations: List[float] = []
        self.max_durations = 10000  # 保留最近10000条

        # Gauge
        self.queue_length = 0
        self.circuit_breaker_state = "closed"
        self.drift_level = "none"

        # 告警历史
        self.alerts: List[dict] = []
        self.max_alerts = 500

        self._load()

    def _load(self):
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    d = json.load(f)
                    self.total_executions = d.get('total_executions', 0)
                    self.success_count = d.get('success_count', 0)
                    self.failure_count = d.get('failure_count', 0)
                    self.rollback_count = d.get('rollback_count', 0)
                    self.blocked_count = d.get('blocked_count', 0)
                    self.action_stats = d.get('action_stats', {})
                    self.durations = d.get('durations', [])
                    self.alerts = d.get('alerts', [])
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump({
                    'total_executions': self.total_executions,
                    'success_count': self.success_count,
                    'failure_count': self.failure_count,
                    'rollback_count': self.rollback_count,
                    'blocked_count': self.blocked_count,
                    'action_stats': self.action_stats,
                    'durations': self.durations[-self.max_durations:],
                    'alerts': self.alerts[-self.max_alerts:],
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)
        except Exception:
            pass

    def record_execution(self, action_name: str, success: bool,
                         duration_ms: float, error: str = None,
                         rolled_back: bool = False, blocked: bool = False):
        """记录一次Action执行"""
        with self._lock:
            self.total_executions += 1

            if blocked:
                self.blocked_count += 1
            elif success:
                self.success_count += 1
            else:
                self.failure_count += 1

            if rolled_back:
                self.rollback_count += 1

            # 按Action分组
            if action_name not in self.action_stats:
                self.action_stats[action_name] = {
                    'total': 0, 'success': 0, 'failure': 0,
                    'rollback': 0, 'blocked': 0,
                    'total_duration_ms': 0, 'durations': [],
                }
            stats = self.action_stats[action_name]
            stats['total'] += 1
            if blocked:
                stats['blocked'] += 1
            elif success:
                stats['success'] += 1
            else:
                stats['failure'] += 1
            if rolled_back:
                stats['rollback'] += 1
            stats['total_duration_ms'] += duration_ms
            stats['durations'].append(duration_ms)
            if len(stats['durations']) > 1000:
                stats['durations'] = stats['durations'][-1000:]

            # 全局耗时
            self.durations.append(duration_ms)
            if len(self.durations) > self.max_durations:
                self.durations = self.durations[-self.max_durations:]

            self._save()

    def record_tpc(self, action_name: str, phase: str, success: bool):
        """记录两阶段提交"""
        with self._lock:
            if phase == 'prepare':
                self.tpc_prepare_count += 1
            elif phase == 'commit':
                self.tpc_commit_count += 1

    def set_gauge(self, queue_length: int = None, circuit_state: str = None, drift_level: str = None):
        """设置Gauge指标"""
        with self._lock:
            if queue_length is not None:
                self.queue_length = queue_length
            if circuit_state is not None:
                self.circuit_breaker_state = circuit_state
            if drift_level is not None:
                self.drift_level = drift_level

    def _percentile(self, data: List[float], pct: float) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * pct / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]

    def get_summary(self) -> dict:
        """获取指标摘要"""
        with self._lock:
            failure_rate = (self.failure_count / self.total_executions * 100) if self.total_executions > 0 else 0
            rollback_rate = (self.rollback_count / self.total_executions * 100) if self.total_executions > 0 else 0
            success_rate = (self.success_count / self.total_executions * 100) if self.total_executions > 0 else 0

            return {
                'total_executions': self.total_executions,
                'success_count': self.success_count,
                'failure_count': self.failure_count,
                'rollback_count': self.rollback_count,
                'blocked_count': self.blocked_count,
                'success_rate_pct': round(success_rate, 2),
                'failure_rate_pct': round(failure_rate, 2),
                'rollback_rate_pct': round(rollback_rate, 2),
                'tpc_prepare_count': self.tpc_prepare_count,
                'tpc_commit_count': self.tpc_commit_count,
                'duration_p50_ms': round(self._percentile(self.durations, 50), 2),
                'duration_p95_ms': round(self._percentile(self.durations, 95), 2),
                'duration_p99_ms': round(self._percentile(self.durations, 99), 2),
                'duration_avg_ms': round(sum(self.durations) / len(self.durations), 2) if self.durations else 0,
                'queue_length': self.queue_length,
                'circuit_breaker_state': self.circuit_breaker_state,
                'drift_level': self.drift_level,
                'action_count': len(self.action_stats),
                'per_action': {
                    name: {
                        'total': s['total'],
                        'success': s['success'],
                        'failure': s['failure'],
                        'success_rate': round(s['success'] / s['total'] * 100, 1) if s['total'] > 0 else 0,
                        'avg_duration_ms': round(s['total_duration_ms'] / s['total'], 1) if s['total'] > 0 else 0,
                    } for name, s in self.action_stats.items()
                },
            }

    def check_alerts(self) -> List[dict]:
        """检查告警阈值，返回当前触发的告警"""
        summary = self.get_summary()
        triggered = []

        # 失败率告警
        if summary['failure_rate_pct'] > self.thresholds['failure_rate_pct']:
            triggered.append({
                'level': 'P2',
                'type': 'high_failure_rate',
                'message': f"failure rate {summary['failure_rate_pct']}% > threshold {self.thresholds['failure_rate_pct']}%",
                'value': summary['failure_rate_pct'],
                'threshold': self.thresholds['failure_rate_pct'],
            })

        # P99耗时告警
        if summary['duration_p99_ms'] > self.thresholds['p99_duration_ms']:
            triggered.append({
                'level': 'P2',
                'type': 'high_p99_latency',
                'message': f"P99 duration {summary['duration_p99_ms']}ms > {self.thresholds['p99_duration_ms']}ms",
                'value': summary['duration_p99_ms'],
                'threshold': self.thresholds['p99_duration_ms'],
            })

        # P95耗时警告
        if summary['duration_p95_ms'] > self.thresholds['p95_duration_ms']:
            triggered.append({
                'level': 'P3',
                'type': 'high_p95_latency',
                'message': f"P95 duration {summary['duration_p95_ms']}ms > {self.thresholds['p95_duration_ms']}ms",
                'value': summary['duration_p95_ms'],
                'threshold': self.thresholds['p95_duration_ms'],
            })

        # 熔断器open
        if self.thresholds['circuit_breaker_open'] and self.circuit_breaker_state == 'open':
            triggered.append({
                'level': 'P1',
                'type': 'circuit_breaker_open',
                'message': "circuit breaker is OPEN, all mutations blocked",
            })

        # P1漂移
        if self.thresholds['drift_level_p1'] and self.drift_level in ('P1', 'P0'):
            triggered.append({
                'level': 'P0' if self.drift_level == 'P0' else 'P1',
                'type': 'system_drift',
                'message': f"system drift level: {self.drift_level}",
            })

        # 队列积压
        if self.queue_length > self.thresholds['queue_backlog']:
            triggered.append({
                'level': 'P3',
                'type': 'queue_backlog',
                'message': f"queue backlog {self.queue_length} > {self.thresholds['queue_backlog']}",
            })

        # 回滚率
        if summary['rollback_rate_pct'] > self.thresholds['rollback_rate_pct']:
            triggered.append({
                'level': 'P2',
                'type': 'high_rollback_rate',
                'message': f"rollback rate {summary['rollback_rate_pct']}% > {self.thresholds['rollback_rate_pct']}%",
            })

        # 记录告警历史
        for alert in triggered:
            alert['timestamp'] = datetime.now(timezone.utc).isoformat()
            self.alerts.append(alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        self._save()

        return triggered

    def to_prometheus(self) -> str:
        """导出为Prometheus文本格式"""
        summary = self.get_summary()
        lines = []

        # HELP和TYPE
        lines.append("# HELP limb_driver_executions_total Total action executions")
        lines.append("# TYPE limb_driver_executions_total counter")
        lines.append(f"limb_driver_executions_total {summary['total_executions']}")

        lines.append("# HELP limb_driver_executions_success Successful executions")
        lines.append("# TYPE limb_driver_executions_success counter")
        lines.append(f"limb_driver_executions_success {summary['success_count']}")

        lines.append("# HELP limb_driver_executions_failure Failed executions")
        lines.append("# TYPE limb_driver_executions_failure counter")
        lines.append(f"limb_driver_executions_failure {summary['failure_count']}")

        lines.append("# HELP limb_driver_executions_rollback Rollback executions")
        lines.append("# TYPE limb_driver_executions_rollback counter")
        lines.append(f"limb_driver_executions_rollback {summary['rollback_count']}")

        lines.append("# HELP limb_driver_executions_blocked Blocked by circuit breaker or RBAC")
        lines.append("# TYPE limb_driver_executions_blocked counter")
        lines.append(f"limb_driver_executions_blocked {summary['blocked_count']}")

        lines.append("# HELP limb_driver_success_rate Success rate percentage")
        lines.append("# TYPE limb_driver_success_rate gauge")
        lines.append(f"limb_driver_success_rate {summary['success_rate_pct']}")

        lines.append("# HELP limb_driver_duration_p50_ms P50 execution duration")
        lines.append("# TYPE limb_driver_duration_p50_ms gauge")
        lines.append(f"limb_driver_duration_p50_ms {summary['duration_p50_ms']}")

        lines.append("# HELP limb_driver_duration_p95_ms P95 execution duration")
        lines.append("# TYPE limb_driver_duration_p95_ms gauge")
        lines.append(f"limb_driver_duration_p95_ms {summary['duration_p95_ms']}")

        lines.append("# HELP limb_driver_duration_p99_ms P99 execution duration")
        lines.append("# TYPE limb_driver_duration_p99_ms gauge")
        lines.append(f"limb_driver_duration_p99_ms {summary['duration_p99_ms']}")

        lines.append("# HELP limb_driver_queue_length Current task queue length")
        lines.append("# TYPE limb_driver_queue_length gauge")
        lines.append(f"limb_driver_queue_length {summary['queue_length']}")

        lines.append("# HELP limb_driver_circuit_breaker_state Circuit breaker state (0=closed,1=open,2=half_open)")
        lines.append("# TYPE limb_driver_circuit_breaker_state gauge")
        state_map = {'closed': 0, 'open': 1, 'half_open': 2}
        lines.append(f"limb_driver_circuit_breaker_state {state_map.get(summary['circuit_breaker_state'], 0)}")

        # 按Action分组
        for action, stats in summary['per_action'].items():
            lines.append(f"# HELP limb_driver_action_{action}_total Total executions for {action}")
            lines.append(f"# TYPE limb_driver_action_{action}_total counter")
            lines.append(f"limb_driver_action_{action}_total {stats['total']}")

            lines.append(f"# HELP limb_driver_action_{action}_success_rate Success rate for {action}")
            lines.append(f"# TYPE limb_driver_action_{action}_success_rate gauge")
            lines.append(f"limb_driver_action_{action}_success_rate {stats['success_rate']}")

        return '\n'.join(lines)

    def export_snapshot(self, output_file: str = None) -> str:
        """导出指标快照"""
        summary = self.get_summary()
        alerts = self.check_alerts()
        snapshot = {
            'snapshot_time': datetime.now(timezone.utc).isoformat(),
            'metrics': summary,
            'active_alerts': alerts,
            'alert_history_count': len(self.alerts),
        }
        output = Path(output_file) if output_file else self.metrics_file.parent / 'metrics_snapshot.json'
        with open(output, 'w') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        return str(output)

    def reset(self):
        """重置所有指标（谨慎使用）"""
        with self._lock:
            self.total_executions = 0
            self.success_count = 0
            self.failure_count = 0
            self.rollback_count = 0
            self.blocked_count = 0
            self.action_stats = {}
            self.durations = []
            self._save()


# 全局单例
_global_metrics: Optional[ExecutionMetrics] = None

def get_global_metrics() -> ExecutionMetrics:
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = ExecutionMetrics()
    return _global_metrics
