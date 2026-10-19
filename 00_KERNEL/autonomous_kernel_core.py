#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 元极恒一自治内核核心
七层稳态架构 · 超认知永恒自治 · DID-BR-000002
溯源标识: Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import time
import hashlib
import signal
import subprocess
import threading
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# ==================== 枚举与数据结构 ====================

class TriState(Enum):
    """逻辑态-算子态-代码执行态三态"""
    LOGICAL = "LOGICAL"
    OPERATOR = "OPERATOR"
    EXECUTION = "EXECUTION"

class Priority(Enum):
    """任务优先级 P0-P3"""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class RiskLevel(Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Decision(Enum):
    """裁决结果"""
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    ISOLATION_VIOLATION = "ISOLATION_VIOLATION"

@dataclass
class Task:
    """任务工单"""
    id: str
    priority: Priority
    description: str
    command: Optional[str]
    timeout: int
    risk_level: RiskLevel
    isresponsible: str
    created_at: str
    spawned_at: Optional[str] = None
    completed_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None

@dataclass
class AxiomGuard:
    """元规则裁决 guard 状态"""
    rule_id: str
    guard_type: str
    priority_threshold: int
    quota_limit: int
    quota_used: int
    isolation_zone: str
    isactive: bool

# ==================== 元规则裁决器 AxiomGate ====================

class AxiomGate:
    """
    元规则裁决器 - AxiomGate TEE边界裁决器
    执行权限判定、配额保护、内外隔离
    """

    def __init__(self, config_path: str = "/workspace/atomgit-mirror/zongyuan-root-sync/config/meta_laws/ENG-DELIVERY-LAWS-001.json"):
        self.config_path = Path(config_path)
        self.auxiom_rules: List[Dict] = []
        self.quota_limits: Dict[str, int] = {}
        self.current_quotas: Dict[str, int] = {}
        self.load_rules()
        self._load_quotas()

    def load_rules(self):
        """加载元规则体系（真实配置为顶层 metadata + layers 四层嵌套，
        原实现取顶层中文键恒为 0 条）"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                layers = config.get('layers') if isinstance(config.get('layers'), dict) else config
                for category in ['元宪法', '元公理', '元法则', '元规则']:
                    for rule in layers.get(category, []) or []:
                        self.auxiom_rules.append(rule)

    def _load_quotas(self):
        """加载配额限制"""
        self.quota_limits = {
            'P0_daily': 10,
            'P1_daily': 50,
            'P2_daily': 200,
            'P3_daily': 1000,
            'model_call_hour': 100,
            'api_call_hour': 500
        }
        self.current_quotas = {
            'P0_daily': 0,
            'P1_daily': 0,
            'P2_daily': 0,
            'P3_daily': 0,
            'model_call_hour': 0,
            'api_call_hour': 0
        }

    def check_authorization(self, task: Task, request_id: str) -> Tuple[bool, Decision, str]:
        """
        权限判定
        返回：(is_authorized, decision, reason)
        """
        can_proceed = True
        decision = Decision.AUTHORIZED
        reasons = []

        # 1. 优先级增益测试 (Priority Gamma Test)
        if task.priority == Priority.P0:
            # P0 优先放行
            reasons.append("P0高优先级，优先执行")
        elif task.priority == Priority.P1:
            # P1 需通过限额阈值检测
            if self.current_quotas.get('P1_daily', 0) >= self.quota_limits.get('P1_daily', 50):
                can_proceed = False
                decision = Decision.QUOTA_EXCEEDED
                reasons.append(f"P1任务配额已达上限 ({self.current_quotas.get('P1_daily')}/{self.quota_limits.get('P1_daily')})")
        elif task.priority == Priority.P2:
            # P2 触发熔断 (DAL FUSE)
            if self.current_quotas.get('P2_daily', 0) >= self.quota_limits.get('P2_daily', 200):
                can_proceed = False
                decision = Decision.QUOTA_EXCEEDED
                reasons.append(f"P2任务配额超限，熔断保护")

        # 2. 风险等级检查
        if task.risk_level == RiskLevel.HIGH or task.risk_level == RiskLevel.CRITICAL:
            # 付费、高危操作强制人工审批
            can_proceed = False
            decision = Decision.DENIED
            reasons.append("高危操作，需要人工审批")

            # 检查人工审批标志
            approval_key = f"approval.{task.id}"
            if os.path.exists(approval_key):
                with open(approval_key, 'r', encoding='utf-8') as f:
                    if json.load(f).get('approved') and json.load(f).get('approver') == 'AUTHORIZED_USER':
                        can_proceed = True
                        decision = Decision.AUTHORIZED
                        reasons.append("已获人工授权")
                        os.remove(approval_key)

        # 3. 隔离区域检查
        if task.command and ('rm -rf /' in task.command or 'sudo rm' in task.command):
            can_proceed = False
            decision = Decision.ISOLATION_VIOLATION
            reasons.append("危险命令，隔离区禁止执行")

        # 4. 元宪法优先级检查
        # 风险最小 > 成本最小 > 收益最大
        if can_proceed and task.risk_level == RiskLevel.MEDIUM:
            cost = self._estimate_cost(task)
            if cost > 100:  # 成本过高
                can_proceed = False
                decision = Decision.DENIED
                reasons.append(f"成本过高 ({cost})，不符合最优原则")

        if can_proceed:
            return True, Decision.AUTHORIZED, " | ".join(reasons)
        else:
            return False, decision, " | ".join(reasons)

    def _estimate_cost(self, task: Task) -> int:
        """预估执行成本"""
        if not task.command:
            return 0

        cost = 0
        # 基础成本
        if task.priority == Priority.P0:
            cost += 10
        elif task.priority == Priority.P1:
            cost += 20
        elif task.priority == Priority.P2:
            cost += 30
        else:
            cost += 40

        # 风险加成（RiskLevel.value 为字符串标签，不可直接乘——
        # 原 cost *= value 使 int 变 str，后续 str+int 抛 TypeError，
        # 即全部 MEDIUM 风险裁决路径异常）
        risk_factor = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 4, 'CRITICAL': 8}
        cost *= risk_factor.get(task.risk_level.name, 1)

        # 命令复杂度
        cost += len(task.command.split()) // 10

        return cost

    def update_quota(self, priority: Priority, increment: int = 1):
        """更新配额使用"""
        key = f"{priority.value}_daily"
        self.current_quotas[key] = min(
            self.current_quotas.get(key, 0) + increment,
            self.quota_limits.get(key, 0)
        )

    def reset_quotas(self):
        """重置配额（每日重置）"""
        for key in self.current_quotas:
            self.current_quotas[key] = 0

    def get_status(self) -> Dict:
        """获取裁决器状态"""
        return {
            "total_rules": len(self.auxiom_rules),
            "quota_limits": self.quota_limits,
            "current_quotas": self.current_quotas,
            "is_active": True,
            "version": "1.0.0",
            "axiom_sign": "Ω₀⊂⊙∞⊂Ω"
        }

# ==================== 执行适配器 ExecutionAdapter ====================

class ExecutionAdapter:
    """
    执行适配器 - 执行任务适配
    支持多种执行环境，提供安全执行基础设施
    """

    def __init__(self, sandbox_enabled: bool = True):
        self.sandbox_enabled = sandbox_enabled
        self.sandbox_path = Path("/workspace/sandbox")
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        self.execution_log = Path("/workspace/execution.log")
        self.docker_available = False
        self._check_docker()

    def _check_docker(self):
        """检查 Docker 可用性"""
        try:
            result = subprocess.run(['docker', 'version'], capture_output=True, text=True)
            self.docker_available = result.returncode == 0
        except Exception:
            self.docker_available = False

    def execute_task(self, task: Task) -> Dict:
        """
        执行任务
        返回：{success, exit_code, stdout, stderr, execution_time}
        """
        start_time = time.time()
        result = {
            'success': False,
            'exit_code': None,
            'stdout': '',
            'stderr': '',
            'execution_time': 0
        }

        # 记录执行日志
        self._log_execution(f"[{task.priority.value}] {task.id}: {task.description}")

        try:
            if self.sandbox_enabled and self.docker_available:
                # Docker 沙箱执行（增强安全）
                result = self._execute_docker(task)
            else:
                # 直接执行（基础安全）
                result = self._execute_direct(task)

            result['execution_time'] = round(time.time() - start_time, 3)

            # 更新任务状态
            task.completed_at = datetime.now().isoformat()
            task.exit_code = result['exit_code']

            if result['success']:
                self._log_execution(f"✅ 任务完成: {task.id} (耗时: {result['execution_time']}s)")
            else:
                self._log_execution(f"❌ 任务失败: {task.id} (退出码: {result['exit_code']})")

        except subprocess.TimeoutExpired:
            self._log_execution(f"⏱️ 任务超时: {task.id}")
            result['stderr'] = '执行超时'

        except Exception as e:
            self._log_execution(f"❌ 任务异常: {task.id}, {str(e)}")
            result['stderr'] = str(e)

        return result

    def _execute_direct(self, task: Task) -> Dict:
        """直接执行命令（无 Docker 时的进程级隔离：
        1. start_new_session=True → setsid，子进程脱离调用者会话/信号域
        2. ulimit 前缀 → CPU 时间、单文件写入、core dump 三项资源上限）
        """
        if not task.command:
            return {'error': 'no command provided'}

        # 资源上限：CPU=超时+10s；单文件 8GB（ulimit -f 单位 1024B 块）；禁 core
        limits = (
            f"ulimit -t {task.timeout + 10} 2>/dev/null; "
            f"ulimit -f {8 * 1024 * 1024} 2>/dev/null; "
            f"ulimit -c 0 2>/dev/null; "
        )

        try:
            result = subprocess.run(
                limits + task.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=task.timeout,
                cwd=self.sandbox_path,
                env={**os.environ, 'TZ': 'Asia/Shanghai'},
                start_new_session=True
            )
            return {
                'success': result.returncode == 0,
                'exit_code': result.returncode,
                'stdout': result.stdout[:4096],
                'stderr': result.stderr[:4096]
            }
        except subprocess.TimeoutExpired:
            return {'error': 'timeout', 'exit_code': -1}
        except Exception as e:
            return {'error': str(e), 'exit_code': -1}

    def _execute_docker(self, task: Task) -> Dict:
        """Docker 沙箱执行"""
        # 创建隔离容器
        container_name = f"task_{task.id}_{int(time.time())}"
        try:
            # 拉取基础镜像
            subprocess.run(['docker', 'pull', 'python:3.9-slim'], capture_output=True)

            # 启动容器
            cmd = (
                f"docker run --rm --name {container_name} -i python:3.9-slim "
                f"bash -c '{task.command}'"
            )

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=task.timeout + 60  # 额外 60 秒缓冲
            )

            return {
                'success': result.returncode == 0,
                'exit_code': result.returncode,
                'stdout': result.stdout[:4096],
                'stderr': result.stderr[:4096]
            }

        except Exception as e:
            return {'error': str(e), 'exit_code': -1}

    def _log_execution(self, message: str):
        """记录执行日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        with open(self.execution_log, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def get_status(self) -> Dict:
        """获取执行器状态"""
        return {
            'sandbox_enabled': self.sandbox_enabled,
            'docker_available': self.docker_available,
            'execution_log': str(self.execution_log),
            'log_size': self.execution_log.stat().st_size if self.execution_log.exists() else 0,
            'version': '1.0.0',
            'axiom_sign': 'Ω₀⊂⊙∞⊂Ω'
        }

# ==================== 观测审计模块 ObservationAudit ====================

class ObservationAudit:
    """
    观测审计模块 - 实时巡检、异常上报
    全域持续观测，因果溯源，四维本体建模
    """

    def __init__(self, audit_path: str = "/workspace/atomgit-mirror/zongyuan-root-sync/audit_logs",
                 register_path: str = "/workspace/atomgit-mirror/zongyuan-root-sync/00_KERNEL/monitoring/east_wing_register.json"):
        self.audit_path = Path(audit_path)
        self.audit_path.mkdir(parents=True, exist_ok=True)
        self.register_path = Path(register_path)
        self.register = self._load_register()
        self.monitoring_interval = int(self.register['collection']['interval_seconds'])
        self.audit_log = self.audit_path / "audit.log"
        self.disable_list = {}
        self._start_monitoring()

    def _load_register(self) -> Dict:
        """加载东翼观测寄存器配置（缺失时回退内置默认值）"""
        default = {
            'register_id': 'EAST-WING-OBSERVATION-REGISTER',
            'collection': {'interval_seconds': 60, 'snapshot_path': 'audit_logs/east_wing_register.state.json'},
            'thresholds': {
                'memory_warn_percent': 85, 'memory_error_percent': 90,
                'disk_warn_percent': 85, 'disk_error_percent': 90,
                'load_warn_per_cpu': 1.5, 'load_error_per_cpu': 3.0,
            },
            'alert': {'enabled': True, 'min_anomalies_for_alert': 3, 'sink': 'audit_logs/east_wing_alerts.jsonl'},
        }
        try:
            with open(self.register_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            default.update(loaded)
            return default
        except Exception:
            return default

    def _start_monitoring(self):
        """启动后台监控"""
        def monitor_loop():
            while True:
                self._monitor_system()
                time.sleep(self.monitoring_interval)

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def _monitor_system(self):
        """系统监控"""
        try:
            # 1. 进程状态监控
            process_status = self._check_processes()

            # 2. 服务健康检查
            service_status = self._check_services()

            # 3. 资源使用监控
            resource_status = self._check_resources()

            # 4. 异常检测
            anomalies = self._detect_anomalies(
                process_status, service_status, resource_status
            )

            # 5. 东翼寄存器指标快照（核心指标采集落盘）
            self._write_register_snapshot(process_status, service_status, resource_status, anomalies)

            # 6. 记录审计
            self._record_audit(anomalies)

        except Exception as e:
            self._log_audit(f"监控异常: {str(e)}", "ERROR")

    def _write_register_snapshot(self, process_status: Dict, service_status: Dict,
                                 resource_status: Dict, anomalies: List[Dict]):
        """核心指标采集快照写入东翼寄存器状态文件"""
        try:
            snapshot_path = self.audit_path / Path(
                self.register.get('collection', {}).get('snapshot_path',
                                                        'audit_logs/east_wing_register.state.json')
            ).name
            snapshot = {
                'register_id': self.register.get('register_id', 'EAST-WING-OBSERVATION-REGISTER'),
                'collected_at': datetime.now().isoformat(),
                'metrics': {
                    'memory': resource_status.get('memory'),
                    'disk': resource_status.get('disk'),
                    'load': resource_status.get('load'),
                    'process_running': sum(1 for s in process_status.values() if s.get('running')),
                    'process_total': len(process_status),
                    'services_up': sum(1 for up in service_status.values() if up),
                    'services_total': len(service_status),
                },
                'anomaly_count': len(anomalies),
                'anomaly_severity': 'CLEAN' if not anomalies else 'ERROR' if any(
                    a['severity'] == 'ERROR' for a in anomalies) else 'WARNING',
                'did': 'DID-BR-000002',
                'trace_mark': 'Ω₀⊂⊙∞⊂Ω',
            }
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
        except Exception:
            # 快照落盘失败不得中断监控主链
            pass

    def _check_processes(self) -> Dict:
        """检查关键进程"""
        processes = {
            'nginx': ('pgrep -x nginx >/dev/null', 0),
            'python': ('pgrep -x python3 >/dev/null || pgrep -x python >/dev/null', 0),
            'aios_backend': ('curl -s http://127.0.0.1:8765/health | grep -q ok', 0),
            'omega_brain': ('curl -s http://127.0.0.1:8000/health | grep -q healthy', 0),
            'memory_gateway': ('curl -s http://127.0.0.1:8077/memory/health | grep -q healthy', 0)
        }

        status = {}
        for name, (cmd, expected) in processes.items():
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                status[name] = {
                    'running': result.returncode == expected,
                    'last_check': datetime.now().isoformat()
                }
            except Exception as e:
                status[name] = {
                    'error': str(e),
                    'last_check': datetime.now().isoformat()
                }

        return status

    def _check_services(self) -> Dict:
        """检查关键服务"""
        services = {}

        # 检查 OpenAPI /api/v1/sync/handshake
        try:
            result = subprocess.run(
                'curl -s http://127.0.0.1:8006/api/v1/sync/handshake | grep -q truth_version',
                shell=True,
                capture_output=True,
                text=True
            )
            services['anchor_api'] = result.returncode == 0
        except:
            services['anchor_api'] = False

        # 检查 ntfy 队列
        try:
            result = subprocess.run('ss -tlnp | grep -q 7100', shell=True)
            services['ntfy'] = result.returncode == 0
        except:
            services['ntfy'] = False

        return services

    def _check_resources(self) -> Dict:
        """检查系统资源"""
        resources = {}

        # 内存
        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                total = int(parts[1])
                used = int(parts[2])
                resources['memory'] = {
                    'total_mb': total,
                    'used_mb': used,
                    'percent': int(used * 100 / total)
                }
        except Exception as e:
            resources['memory'] = {'error': str(e)}

        # 磁盘
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                resources['disk'] = {
                    'percent': int(parts[4].replace('%', ''))
                }
        except Exception as e:
            resources['disk'] = {'error': str(e)}

        # 负载
        try:
            result = subprocess.run(['uptime'], capture_output=True, text=True)
            if 'load average:' in result.stdout:
                load_str = result.stdout.split('load average:')[1].strip().split(',')[0]
                resources['load'] = float(load_str)
        except Exception as e:
            resources['load'] = {'error': str(e)}

        return resources

    def _detect_anomalies(self, process_status, service_status, resource_status) -> List[Dict]:
        """检测异常"""
        anomalies = []
        timestamp = datetime.now().isoformat()

        # 进程异常
        for name, status in process_status.items():
            if 'running' in status and not status['running']:
                anomalies.append({
                    'type': 'process',
                    'name': name,
                    'severity': 'WARNING',
                    'description': f'进程 {name} 未运行',
                    'timestamp': timestamp
                })
            elif 'error' in status:
                # 指标采集失效必须可见（曾被 except 吞掉导致进程态静默缺失）
                anomalies.append({
                    'type': 'collection',
                    'name': name,
                    'severity': 'ERROR',
                    'description': f'进程 {name} 采集失败: {status["error"]}',
                    'timestamp': timestamp
                })

        # 服务异常
        for name, up in service_status.items():
            if not up:
                anomalies.append({
                    'type': 'service',
                    'name': name,
                    'severity': 'ERROR',
                    'description': f'服务 {name} 异常',
                    'timestamp': timestamp
                })

        # 资源异常（阈值来自东翼观测寄存器）
        th = self.register.get('thresholds', {})
        if 'memory' in resource_status:
            memory = resource_status['memory']
            if isinstance(memory, dict) and 'percent' in memory:
                if memory['percent'] > th.get('memory_error_percent', 90):
                    anomalies.append({
                        'type': 'resource', 'name': 'memory', 'severity': 'ERROR',
                        'description': f'内存使用率 {memory["percent"]}% 超错误阈值 {th.get("memory_error_percent", 90)}%',
                        'timestamp': timestamp
                    })
                elif memory['percent'] > th.get('memory_warn_percent', 85):
                    anomalies.append({
                        'type': 'resource', 'name': 'memory', 'severity': 'WARNING',
                        'description': f'内存使用率 {memory["percent"]}% 超警告阈值 {th.get("memory_warn_percent", 85)}%',
                        'timestamp': timestamp
                    })

        if 'disk' in resource_status:
            disk = resource_status['disk']
            if isinstance(disk, dict) and 'percent' in disk:
                if disk['percent'] > th.get('disk_error_percent', 90):
                    anomalies.append({
                        'type': 'resource', 'name': 'disk', 'severity': 'ERROR',
                        'description': f'磁盘使用率 {disk["percent"]}% 超错误阈值 {th.get("disk_error_percent", 90)}%',
                        'timestamp': timestamp
                    })
                elif disk['percent'] > th.get('disk_warn_percent', 85):
                    anomalies.append({
                        'type': 'resource', 'name': 'disk', 'severity': 'WARNING',
                        'description': f'磁盘使用率 {disk["percent"]}% 超警告阈值 {th.get("disk_warn_percent", 85)}%',
                        'timestamp': timestamp
                    })

        # 负载异常（每核阈值 × CPU 核数，此前完全无检测）
        if isinstance(resource_status.get('load'), (int, float)):
            try:
                cpu_count = os.cpu_count() or 1
                load = float(resource_status['load'])
                warn_line = th.get('load_warn_per_cpu', 1.5) * cpu_count
                err_line = th.get('load_error_per_cpu', 3.0) * cpu_count
                if load > err_line:
                    anomalies.append({
                        'type': 'resource', 'name': 'load', 'severity': 'ERROR',
                        'description': f'负载 {load} 超错误线 {err_line:.1f}（{cpu_count}核）',
                        'timestamp': timestamp
                    })
                elif load > warn_line:
                    anomalies.append({
                        'type': 'resource', 'name': 'load', 'severity': 'WARNING',
                        'description': f'负载 {load} 超警告线 {warn_line:.1f}（{cpu_count}核）',
                        'timestamp': timestamp
                    })
            except (TypeError, ValueError):
                pass

        return anomalies

    def _record_audit(self, anomalies: List[Dict]):
        """记录审计（JSONL 单行追加；原 indent 多行格式使 get_status 尾行解析自首版即失效）"""
        audit_record = {
            'audit_id': f"AUDIT-{int(time.time())}",
            'anomalies': anomalies,
            'total_anomalies': len(anomalies),
            'severity': ('ERROR' if any(a.get('severity') == 'ERROR' for a in anomalies)
                         else 'WARNING' if anomalies else 'CLEAN'),
            'timestamp': datetime.now().isoformat()
        }

        # 写入审计日志（单行 JSONL）
        log_entry = json.dumps(audit_record, ensure_ascii=False)
        with open(self.audit_log, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")

        # 到 ThresholdAlert()
        if len(anomalies) >= 3:
            self._threshold_alert(anomalies)

    def _threshold_alert(self, anomalies: List[Dict]):
        """触发阈值告警（落盘东翼寄存器告警槽，供人工/联邦侧消费）"""
        alert_cfg = self.register.get('alert', {})
        if not alert_cfg.get('enabled', True):
            return
        min_count = int(alert_cfg.get('min_anomalies_for_alert', 3))
        if len(anomalies) < min_count:
            return
        try:
            sink = self.audit_path / Path(
                alert_cfg.get('sink', 'audit_logs/east_wing_alerts.jsonl')
            ).name
            alert = {
                'alert_id': f"ALERT-{int(time.time())}",
                'register_id': self.register.get('register_id'),
                'trigger': f"anomalies {len(anomalies)} >= {min_count}",
                'errors': [a['description'] for a in anomalies if a['severity'] == 'ERROR'],
                'severity': 'ERROR' if any(a['severity'] == 'ERROR' for a in anomalies) else 'WARNING',
                'fired_at': datetime.now().isoformat(),
                'did': 'DID-BR-000002',
            }
            with open(sink, 'a', encoding='utf-8') as f:
                f.write(json.dumps(alert, ensure_ascii=False) + "\n")
        except Exception:
            # 告警落盘失败不得中断监控主链
            pass

    def _log_audit(self, message: str, level: str = "INFO"):
        """异常兜底日志（原被调用但未定义，监控线程二次崩溃的隐患）"""
        try:
            with open(self.audit_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'audit_id': f"AUDIT-ERR-{int(time.time())}",
                    'level': level,
                    'message': message,
                    'timestamp': datetime.now().isoformat(),
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def stop(self):
        """停止监控"""
        self.monitoring_interval = 0

    def get_status(self) -> Dict:
        """获取观测器状态（从尾部回扫找最近一条完整记录，
        兼容历史 indent 多行记录——直接解析尾行会因 '}' 或空行恒失败）"""
        try:
            latest_audit = None
            if self.audit_log.exists():
                with open(self.audit_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for line in reversed(lines[-200:]):
                    line = line.strip()
                    if not line.startswith('{'):
                        continue
                    try:
                        record = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if isinstance(record, dict) and 'audit_id' in record:
                        latest_audit = record
                        break

            log_size = self.audit_log.stat().st_size if self.audit_log.exists() else 0

            return {
                'is_active': True,
                'monitoring_interval': self.monitoring_interval,
                'audit_log_size': log_size,
                'latest_audit': latest_audit,
                'register_id': self.register.get('register_id'),
                'version': '1.0.0',
                'axiom_sign': 'Ω₀⊂⊙∞⊂Ω'
            }
        except Exception as e:
            return {'error': str(e), 'is_active': True}

# ==================== 持久化版本账本 PersistedLedger ====================

class PersistedLedger:
    """
    持久化版本账本 - 资产持久存储、哈希确权锁档
    资产持久存储 + 哈希确权锁档，Merkle-DAG 凭证
    """

    def __init__(self, ledger_path: str = "/workspace/atomgit-mirror/zongyuan-root-sync/ledger"):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.mkdir(parents=True, exist_ok=True)
        self.indices_path = self.ledger_path / "index"
        self.indices_path.mkdir(parents=True, exist_ok=True)
        self.chain_path = self.ledger_path / "chain"
        self.chain_path.mkdir(parents=True, exist_ok=True)
        self.merkle_path = self.ledger_path / "merkle"
        self.merkle_path.mkdir(parents=True, exist_ok=True)
        self.enabled = True

    def _sha256_hash(self, data: str) -> str:
        """计算 SHA256 哈希"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def _compute_merkle_root(self, nodes: List[Dict]) -> str:
        """计算 Merkle 树根"""
        if not nodes:
            return self._sha256_hash("empty")

        # 叶子节点
        leaves = [self._sha256_hash(json.dumps(node, ensure_ascii=False, sort_keys=True)) for node in nodes]

        # 构建 Merkle 树
        while len(leaves) > 1:
            if len(leaves) % 2 == 1:
                leaves.append(leaves[-1])
            next_level = []
            for i in range(0, len(leaves), 2):
                merged = leaves[i] + leaves[i + 1]
                next_level.append(self._sha256_hash(merged))
            leaves = next_level

        return leaves[0]

    def add_entry(self, entry: Dict) -> Dict:
        """
        添加记录到账本
        返回：{block_id, hash, merkle_root}
        """
        if not self.enabled:
            return {'error': 'Ledger disabled'}

        timestamp = time.time()
        entry['timestamp'] = datetime.now().isoformat()
        entry['version'] = '1.0.0'
        entry['axiom_sign'] = 'Ω₀⊂⊙∞⊂Ω'

        # 计算块哈希
        block_hash = self._sha256_hash(json.dumps(entry, ensure_ascii=False, sort_keys=True))

        # 生成块 ID
        block_id = f"BLK-{int(timestamp)}-{block_hash[:8]}"

        # 计算 Merkle 根
        merkle_root = self._compute_merkle_root([entry])

        # 保存块数据
        block_path = self.chain_path / f"{block_id}.json"
        with open(block_path, 'w', encoding='utf-8') as f:
            json.dump({
                'block_id': block_id,
                'block_hash': block_hash,
                'merkle_root': merkle_root,
                'entry': entry,
                'sorted_at': datetime.now().isoformat(),
                '溯源标识': 'Ω₀⊂⊙∞⊂Ω',
                '确权编码': 'DID-BR-000002',
                '体系基线': 'ZONGYUAN-ROOT V1.0'
            }, f, ensure_ascii=False, indent=2)

        # 更新索引
        self._update_index(block_id, entry)

        return {
            'block_id': block_id,
            'block_hash': block_hash,
            'merkle_root': merkle_root
        }

    def _update_index(self, block_id: str, entry: Dict):
        """更新索引"""
        # 按类型索引
        entry_type = entry.get('type', 'unknown')
        type_index = self.indices_path / f"{entry_type}.json"

        if type_index.exists():
            with open(type_index, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        else:
            index_data = {'type': entry_type, 'blocks': [], 'total': 0, 'merkle_root': ''}

        index_data['blocks'].append(block_id)
        index_data['total'] += 1

        # 计算新的 Merkle 根
        with open(self.chain_path / f"{block_id}.json", 'r', encoding='utf-8') as f:
            block_data = json.load(f)
        index_data['merkle_root'] = block_data.get('merkle_root', '')

        with open(type_index, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def get_ledger_status(self) -> Dict:
        """获取账本状态"""
        blocks = list(self.chain_path.glob("*.json"))
        total_blocks = len(blocks)

        # 获取最新块
        latest_hash = None
        if blocks:
            latest_block = blocks[-1]
            with open(latest_block, 'r', encoding='utf-8') as f:
                latest_data = json.load(f)
                latest_hash = latest_data.get('block_hash')

        # 计算链式验证
        chain_status = {
            'total_blocks': total_blocks,
            'latest_hash': latest_hash,
            'is_consistent': True  # TODO: 实现链式验证
        }

        return {
            'enabled': self.enabled,
            'total_blocks': total_blocks,
            'chain_status': chain_status,
            'ledger_path': str(self.ledger_path),
            'version': '1.0.0',
            'axiom_sign': 'Ω₀⊂⊙∞⊂Ω'
        }

    def verify_consistency(self, block_ids: List[str]) -> Dict:
        """验证账本一致性"""
        errors = []

        for block_id in block_ids:
            block_path = self.chain_path / f"{block_id}.json"
            if not block_path.exists():
                errors.append(f'块 {block_id} 不存在')
                continue

            with open(block_path, 'r', encoding='utf-8') as f:
                block_data = json.load(f)

            # 验证哈希
            calculated_hash = self._sha256_hash(json.dumps(block_data['entry'], ensure_ascii=False, sort_keys=True))
            if calculated_hash != block_data['block_hash']:
                errors.append(f'块 {block_id} 哈希验证失败')

        return {
            'is_consistent': len(errors) == 0,
            'errors': errors,
            'verified_blocks': len(block_ids) - len(errors),
            'timestamp': datetime.now().isoformat()
        }

# ==================== 进化迭代器 EvolutionIterator ====================

class EvolutionIterator:
    """
    进化迭代器 - 3小时云端进化脉冲循环
    CTE全闭环V2.0，全自动元进化引擎V3.0
    """

    def __init__(self, base_dir: str = "/workspace/atomgit-mirror/zongyuan-root-sync/evolution"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.base_dir / "evolution_state.json"
        self.history_dir = self.base_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.config = {
            'cycle_interval_hours': 3,
            'auto_approve_low_risk': True,
            'max_cycle_attempts': 3,
            'cloud_sync_enabled': True
        }
        self.load_state()
        self._start_cycle()

    def load_state(self):
        """加载进化状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
        else:
            self.state = {
                'version': '3.0.0',
                'started_at': datetime.now().isoformat(),
                'cycles_completed': 0,
                'suggestions_generated': 0,
                'last_check_time': datetime.now().isoformat(),
                'last_success_time': None,
                'evolution_epoch': 1,
                'current_cycle_id': None,
                'status': 'idle'
            }

    def _start_cycle(self):
        """启动进化循环（3 小时脉冲：距上次成功/失败基准点 ≥cycle_interval_hours 才进入新循环）"""
        def cycle_loop():
            while True:
                try:
                    # idle 与 error 均可进入（error 通过 last_error_time 3小时退避后自愈重试）
                    if self.state.get('status') in ('idle', 'error') and self._cycle_due():
                        self._run_evolution_cycle()
                except Exception as e:
                    # 兜底：循环本身异常不得静默退出
                    self.state['status'] = 'error'
                    self.state['last_error_time'] = datetime.now().isoformat()
                    self.save_state()
                time.sleep(60)  # 每分钟检查一次是否到达 3 小时脉冲点

        loop_thread = threading.Thread(target=cycle_loop, daemon=True)
        loop_thread.start()

    def _cycle_due(self) -> bool:
        """是否到达 3 小时进化脉冲点
        基准 = last_success/last_error 中较新者（error 由此实现 3 小时退避）；
        两者皆缺（全新状态）时才退回 started_at 立即首跑。
        """
        def parse(ref):
            if not ref:
                return None
            try:
                return datetime.fromisoformat(ref).timestamp()
            except (TypeError, ValueError):
                return None

        refs = [t for t in (parse(self.state.get('last_success_time')),
                            parse(self.state.get('last_error_time'))) if t is not None]
        if refs:
            ref_ts = max(refs)
        else:
            ref_ts = parse(self.state.get('started_at'))
        if ref_ts is None:
            return True
        return (time.time() - ref_ts) >= int(self.config['cycle_interval_hours'] * 3600)

    def _run_evolution_cycle(self):
        """执行进化循环"""
        self.state['status'] = 'running'
        self.state['current_cycle_id'] = f"EVOLUTION-CYCLE-{int(time.time())}"
        start_time = datetime.now()

        try:
            # 1. 生成建议（阶段1）- 参考 self_evolution_engine_v3.py
            suggestions = self._generate_suggestions()

            # 2. 人工确认（阶段2）
            self._request_approval(suggestions)

            # 3. 沙箱验证（阶段3）
            verified_suggestions = self._verify_suggestions(suggestions)

            # 4. 锁档归档（阶段4）
            lock_ids = self._archive_suggestions(suggestions, verified_suggestions)

            # 更新状态
            self.state['status'] = 'idle'
            self.state['cycles_completed'] += 1
            self.state['suggestions_generated'] += len(suggestions)
            self.state['last_success_time'] = datetime.now().isoformat()

            # 保存到历史
            self._save_to_history({
                'cycle_id': self.state['current_cycle_id'],
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now().isoformat(),
                'suggestions_count': len(suggestions),
                'verified_count': len(verified_suggestions),
                'locked_count': len(lock_ids),
                'lock_ids': lock_ids,
                'status': 'completed'
            })

            # 云端同步（锁档归档流程末端：脉冲摘要上报记忆网关）
            if self.config['cloud_sync_enabled']:
                self._sync_to_cloud(lock_ids=lock_ids)

        except Exception as e:
            self.state['status'] = 'error'
            self.state['last_error_time'] = datetime.now().isoformat()
            self._save_to_history({
                'cycle_id': self.state['current_cycle_id'],
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now().isoformat(),
                'error': str(e),
                'status': 'error'
            })
        finally:
            self.save_state()

    def _generate_suggestions(self) -> List[Dict]:
        """生成优化建议"""
        # 简化：返回一些示例建议
        return [
            {
                'suggestion_id': f"SUGG-{int(time.time())}-MEM",
                'type': '性能优化',
                'title': '内存使用率优化建议',
                'description': '当前内存使用率超过阈值，建议优化',
                'expected_benefit': '降低内存使用率至70%以下',
                'risk_level': 'low',
                'implementation_plan': ['检查高内存占用进程', '优化服务配置', '清理缓存文件'],
                'estimated_time': '1-2小时',
                'created_at': datetime.now().isoformat(),
                'status': 'pending'
            },
            {
                'suggestion_id': f"SUGG-{int(time.time())}-DISK",
                'type': '安全加固',
                'title': 'SSL证书到期检查',
                'description': 'SSL证书即将到期，建议续期',
                'expected_benefit': '避免证书过期导致服务中断',
                'risk_level': 'medium',
                'implementation_plan': ['检查证书到期时间', '续期证书', '验证更新'],
                'estimated_time': '30分钟',
                'created_at': datetime.now().isoformat(),
                'status': 'pending'
            }
        ]

    def _request_approval(self, suggestions: List[Dict]):
        """请求批准"""
        for sug in suggestions:
            if sug.get('risk_level') == 'low' and self.config['auto_approve_low_risk']:
                sug['status'] = 'approved'
                sug['approver'] = 'auto_system'
                sug['approved_at'] = datetime.now().isoformat()
            else:
                sug['status'] = 'pending_approval'

    def _verify_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """验证建议"""
        verified = []
        for sug in suggestions:
            if sug.get('status') == 'approved':
                # 简化：低风险建议直接验证通过
                sug['verified'] = True
                sug['verified_at'] = datetime.now().isoformat()
                verified.append(sug)
        return verified

    def _archive_suggestions(self, suggestions: List[Dict], verified: List[Dict]) -> List[str]:
        """归档建议（返回锁档 ID 列表，供云端脉冲同步）"""
        lock_ids: List[str] = []
        for sug in suggestions:
            if sug.get('verified'):
                # 计算锁档哈希
                lock_data = {
                    'suggestion': sug,
                    'locked_at': datetime.now().isoformat()
                }
                lock_hash = hashlib.sha256(json.dumps(lock_data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

                # 创建锁档记录
                lock_record = {
                    'lock_id': f"LOCK-{int(time.time())}-EVO",
                    'suggestion_id': sug['suggestion_id'],
                    'lock_hash': lock_hash,
                    'lock_type': 'self_evolution',
                    'status': 'BLOWN_PERMANENT',
                    'locked_at': datetime.now().isoformat(),
                    '溯源标识': 'Ω₀⊂⊙∞⊂Ω',
                    '确权编码': 'DID-BR-000002',
                    '体系基线': 'ZONGYUAN-ROOT V1.7',
                    'engine_version': '3.0.0'
                }

                # 保存锁档
                lock_path = self.history_dir / f"{lock_record['lock_id']}.json"
                with open(lock_path, 'w', encoding='utf-8') as f:
                    json.dump(lock_record, f, ensure_ascii=False, indent=2)

                # 更新建议状态
                sug['status'] = 'locked'
                sug['lock_id'] = lock_record['lock_id']
                sug['lock_hash'] = lock_hash

                lock_ids.append(lock_record['lock_id'])

        return lock_ids

    def _save_to_history(self, record: Dict):
        """保存到历史"""
        history_path = self.history_dir / f"HIST-{int(time.time())}.json"
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

    def _sync_to_cloud(self, lock_ids: Optional[List[str]] = None):
        """锁档归档云端同步：脉冲摘要上报记忆网关（KERNEL.* 命名空间，value 为结构化对象）"""
        payload = {
            'key': 'KERNEL.EVOLUTION.PULSE.V1',
            'value': {
                'cycle_id': self.state.get('current_cycle_id'),
                'cycles_completed': self.state.get('cycles_completed'),
                'suggestions_generated': self.state.get('suggestions_generated'),
                'evolution_epoch': self.state.get('evolution_epoch'),
                'locks_this_cycle': lock_ids or [],
                'cycle_interval_hours': self.config['cycle_interval_hours'],
                'did': 'DID-BR-000002',
                'trace_mark': 'Ω₀⊂⊙∞⊂Ω',
                'synced_at': datetime.now().isoformat(),
            },
        }
        req = urllib.request.Request(
            'https://www.huodouai.com/api/report/truth',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'X-DID': 'DID-BR-000002'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode('utf-8'))
            self.state['last_cloud_sync'] = {
                'ok': body.get('ok'), 'seq': body.get('seq'),
                'event_id': body.get('event_id'),
                'at': datetime.now().isoformat(),
            }
        except Exception as e:
            # 网关不可达不阻断本地锁档流程（风险最小优先），记录供下周期排查
            self.state['last_cloud_sync'] = {
                'ok': False, 'error': str(e),
                'at': datetime.now().isoformat(),
            }

    def save_state(self):
        """保存进化状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def get_status(self) -> Dict:
        """获取进化器状态"""
        try:
            return {
                'version': self.state.get('version', '3.0.0'),
                'cycles_completed': self.state.get('cycles_completed', 0),
                'suggestions_generated': self.state.get('suggestions_generated', 0),
                'current_cycle_id': self.state.get('current_cycle_id'),
                'status': self.state.get('status', 'idle'),
                'last_success_time': self.state.get('last_success_time'),
                'evolution_epoch': self.state.get('evolution_epoch', 1),
                'cloud_sync_enabled': self.config['cloud_sync_enabled'],
                'axiom_sign': 'Ω₀⊂⊙∞⊂Ω'
            }
        except Exception as e:
            return {'error': str(e), 'status': 'error'}

    def stop(self):
        """停止进化器（先从盘上刷新状态再置 stopped——
        防止陈旧内存 state 在退出时覆盖其他实例更新的盘上状态，造成 cycles/时间戳回滚）"""
        try:
            self.load_state()
        except Exception:
            pass
        self.state['status'] = 'stopped'
        self.state['stopped_at'] = datetime.now().isoformat()
        self.save_state()

# ==================== 自治内核主类 ====================

class AutonomousKernel:
    """
    ZONGYUAN-ROOT 元极恒一自治内核
    七层稳态架构 · 超认知永恒自治
    """

    def __init__(self):
        self.kernel_config = {
            'version': '1.0.0',
            'did': 'DID-BR-000002',
            'axiom_sign': 'Ω₀⊂⊙∞⊂Ω',
            'features': {
                'axiom_gate': True,
                'execution_adapter': True,
                'observation_audit': True,
                'persisted_ledger': True,
                'evolution_iterator': True
            }
        }

        # 初始化各组件
        self.axiom_gate = AxiomGate()
        self.execution_adapter = ExecutionAdapter()
        self.observation_audit = ObservationAudit()
        self.persisted_ledger = PersistedLedger()
        self.evolution_iterator = EvolutionIterator()

        # 组件状态注册
        self.components = {
            'axiom_gate': self.axiom_gate,
            'execution_adapter': self.execution_adapter,
            'observation_audit': self.observation_audit,
            'persisted_ledger': self.persisted_ledger,
            'evolution_iterator': self.evolution_iterator
        }

        # 调度器初始化
        self.scheduler = None
        self._load_scheduler()

        # 启动信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # 自启用
        self.enabled = True

    def _load_scheduler(self):
        """加载调度器"""
        try:
            from scheduler import TaskScheduler
            self.scheduler = TaskScheduler()
        except Exception as e:
            print(f"警告: 调度器加载失败: {e}")

    def _signal_handler(self, signum, frame):
        """信号处理：优雅退出"""
        print(f"\n接收到信号 {signum}，自治内核正在退出...")

        # 停止所有组件
        for name, component in self.components.items():
            try:
                if hasattr(component, 'stop'):
                    component.stop()
                print(f"  - {name} 已停止")
            except Exception as e:
                print(f"  - {name} 停止时出错: {e}")

        # 保存状态
        self._save_state()

        print("ZONGYUAN-ROOT 自治内核退出完成")
        sys.exit(0)

    def _save_state(self):
        """保存内核状态"""
        state = {
            'enabled': self.enabled,
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }

        for name, component in self.components.items():
            try:
                if hasattr(component, 'get_status'):
                    state['components'][name] = component.get_status()
            except Exception as e:
                state['components'][name] = {'error': str(e)}

        state_path = Path("/workspace/kernel_state.json")
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def execute_task(self, task_data: Dict) -> Dict:
        """
        执行任务
        1. 权限判定
        2. 资源配额检查
        3. 执行适配
        4. 异常上报
        5. 版本账本记录
        """
        # 转换为 Task 对象
        task = None
        try:
            # 映射 task_data 到 Task
            priority = Priority[task_data.get('priority', 'P3')]
            risk_level = RiskLevel[task_data.get('risk_level', 'MEDIUM')]

            task = Task(
                id=task_data['id'],
                priority=priority,
                description=task_data.get('description', ''),
                command=task_data.get('command'),
                timeout=task_data.get('timeout', 300),
                risk_level=risk_level,
                isresponsible=task_data.get('isresponsible', 'AUTO')
            )

        except Exception as e:
            return {
                'success': False,
                'error': f"任务解析失败: {str(e)}"
            }

        # 1. 权限判定
        authorized, decision, reasons = self.axiom_gate.check_authorization(task, task_data.get('request_id', 'AUTO'))
        if not authorized:
            # 记录裁决拒绝
            self._record_rejection(task, decision, reasons)
            return {
                'success': False,
                'authorized': False,
                'decision': decision.value,
                'reasons': reasons
            }

        # 2. 执行任务
        task_result = self.execution_adapter.execute_task(task)

        # 3. 更新配额
        if task_result.get('success'):
            self.axiom_gate.update_quota(task.priority)

        # 4. 记录到账本
        ledger_entry = {
            'type': 'task_execution',
            'task_id': task.id,
            'task_priority': task.priority.value,
            'task_risk': task.risk_level.value,
            'execution_result': task_result,
            'timestamp': datetime.now().isoformat(),
            'authorized_by': 'AXIOMGATE',
            '溯源标识': 'Ω₀⊂⊙∞⊂Ω',
            '确权编码': 'DID-BR-000002'
        }
        ledger_record = self.persisted_ledger.add_entry(ledger_entry)

        # 构建最终结果
        result = {
            'success': task_result.get('success', False),
            'task_id': task.id,
            'authorized': authorized,
            'result': task_result,
            'axiom_guard': {
                'decision': decision.value,
                'reasons': reasons
            },
            'ledger_record': ledger_record,
            'timestamp': datetime.now().isoformat(),
            'axiom_sign': 'Ω₀⊂⊙∞⊂Ω'
        }

        return result

    def _record_rejection(self, task: Task, decision: Decision, reasons: str):
        """记录裁决拒绝"""
        rejection_entry = {
            'type': 'task_rejection',
            'task': asdict(task),
            'decision': decision.value,
            'reasons': reasons,
            'timestamp': datetime.now().isoformat(),
            'axiom_sign': 'Ω₀⊂⊙∞⊂Ω'
        }
        # 保存到拒绝记录文件
        rejection_path = Path("/workspace/axiom_rejections.log")
        with open(rejection_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rejection_entry, ensure_ascii=False) + "\n")

    def get_status(self) -> Dict:
        """获取自治内核状态"""
        status = {
            'enabled': self.enabled,
            'version': self.kernel_config['version'],
            'did': self.kernel_config['did'],
            'axiom_sign': self.kernel_config['axiom_sign'],
            'features': self.kernel_config['features'].copy(),
            'components': {},
            'system_time': datetime.now().isoformat()
        }

        for name, component in self.components.items():
            try:
                if hasattr(component, 'get_status'):
                    status['components'][name] = component.get_status()
            except Exception as e:
                status['components'][name] = {'error': str(e)}

        # 确认调度器状态
        if self.scheduler:
            status['scheduler'] = 'running' if hasattr(self.scheduler, 'is_running') and self.scheduler.is_running() else 'idle'

        return status

    def start(self):
        """启动自治内核"""
        print(f"{'='*60}")
        print(f"  ZONGYUAN-ROOT 元极恒一自治内核")
        print(f"  溯源标识: {self.kernel_config['axiom_sign']}")
        print(f"  DID: {self.kernel_config['did']}")
        print(f"  版本: {self.kernel_config['version']}")
        print(f"  {'='*60}")

        # 初始化记录
        self._save_state()

        # 启动调度
        if self.scheduler:
            try:
                # 后台启动调度器
                thread = threading.Thread(target=self.scheduler.run, daemon=True)
                thread.start()
                print("  ✓ 任务调度器已启动")
            except Exception as e:
                print(f"  ✗ 任务调度器启动失败: {e}")

        # 确认组件状态
        components_status = self.get_status()
        for component, status in components_status['components'].items():
            if status.get('is_active') or status.get('enabled'):
                print(f"  ✓ {component} 已就绪")

        print(f"  {'='*60}")
        print("  自治内核启动完成")
        print(f"  {'='*60}")

    def stop(self):
        """停止自治内核"""
        print("\n正在停止自治内核...")

        # 停止各组件
        for name, component in self.components.items():
            try:
                if hasattr(component, 'stop'):
                    component.stop()
                print(f"  - {name} 已停止")
            except Exception as e:
                print(f"  - {name} 停止时出错: {e}")

        # 停止调度器
        if self.scheduler:
            try:
                self.scheduler.stop()
                print("  - 任务调度器已停止")
            except Exception as e:
                print(f"  - 任务调度器停止时出错: {e}")

        self.enabled = False
        self._save_state()
        print("\nZONGYUAN-ROOT 自治内核退出完成")

# ==================== 主程序入口 ====================

if __name__ == "__main__":
    import sys

    kernel = AutonomousKernel()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "status":
            print(json.dumps(kernel.get_status(), ensure_ascii=False, indent=2))
        else:
            print(f"未知命令: {cmd}")
            print(f"用法: {sys.argv[0]} [start|stop|status]")
    else:
        # 默认启动
        kernel.start()
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            kernel.stop()
