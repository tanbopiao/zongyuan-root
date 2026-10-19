#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 内核核心防回归测试套件
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

覆盖已修复缺陷：元规则加载、3小时脉冲、error退避、审计JSONL、
等级阈值倒序、调度器PID探活、执行适配器日志
"""
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import autonomous_kernel_core as akc


# ---------- 1. 元规则裁决器 AxiomGate ----------

def test_axiom_gate_loads_17_rules():
    """load_rules() 必须适配 layers 嵌套结构，恒载入 17 条四层元法则"""
    gate = akc.AxiomGate()
    status = gate.get_status()
    assert status.get('error') is None, f"裁决器加载异常: {status.get('error')}"
    assert status['total_rules'] == 17, (
        f"期望 17 条（元宪法/元公理/元法则/元规则），实际 {status['total_rules']} 条"
    )


# ---------- 2/3. 进化引擎 3 小时脉冲 + error 退避 ----------

@pytest.fixture
def evo(monkeypatch, tmp_path):
    """隔离实例：禁用后台循环线程，状态落临时目录"""
    monkeypatch.setattr(akc.EvolutionIterator, '_start_cycle', lambda self: None)
    it = akc.EvolutionIterator(base_dir=str(tmp_path / 'evolution'))
    it.state = {
        'version': '3.0.0',
        'started_at': datetime.now().isoformat(),
        'cycles_completed': 0,
        'last_success_time': None,
        'last_error_time': None,
        'status': 'idle',
    }
    return it


def test_cycle_due_respects_three_hour_interval(evo):
    """2h59m 不触发、3h01m 触发（cycle_interval_hours=3 真实参与判定）"""
    evo.config['cycle_interval_hours'] = 3

    evo.state['last_success_time'] = (datetime.now() - timedelta(minutes=179)).isoformat()
    assert evo._cycle_due() is False, "2h59m 即触发 = 间隔未生效"

    evo.state['last_success_time'] = (datetime.now() - timedelta(minutes=181)).isoformat()
    assert evo._cycle_due() is True, "3h01m 未触发 = 脉冲丢失"


def test_evolution_error_backoff(evo):
    """error 状态按 last_error_time 退避：1h 内不重试，3h 后自愈"""
    evo.state['status'] = 'error'

    evo.state['last_error_time'] = datetime.now().isoformat()
    assert evo._cycle_due() is False, "error 后 1h 即重跑 = 退避失效"

    evo.state['last_error_time'] = (datetime.now() - timedelta(minutes=181)).isoformat()
    assert evo._cycle_due() is True, "error 后 3h 未重跑 = 无法自愈"


# ---------- 4. 观测审计 JSONL ----------

def test_audit_jsonl_roundtrip(monkeypatch, tmp_path):
    """_record_audit 单行 JSONL 写入 + get_status 尾部回扫可读"""
    monkeypatch.setattr(akc.ObservationAudit, '_start_monitoring', lambda self: None)
    audit = akc.ObservationAudit(audit_path=str(tmp_path))

    audit._record_audit([
        {'type': 'test', 'severity': 'WARNING', 'description': '单测注入告警'}
    ])

    status = audit.get_status()
    assert 'error' not in status or status.get('error') is None, status.get('error')
    latest = status['latest_audit']
    assert latest is not None, "get_status 无法回扫到刚写入的记录"
    assert latest['total_anomalies'] == 1
    assert latest['severity'] == 'WARNING'

    # 单行约束：文件中该记录不跨行
    lines = (tmp_path / 'audit.log').read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) >= 1
    assert json.loads(lines[-1])['audit_id'] == latest['audit_id']


# ---------- 5. 评估等级阈值倒序判定 ----------

def test_eval_level_threshold_order():
    """determine_level 必须倒序取最高达标等级（锁死插入序优先的旧 bug）"""
    from evaluate_autonomy_level import AutonomyLevelEvaluator
    ev = object.__new__(AutonomyLevelEvaluator)
    ev.level_thresholds = {'Lv7': 70, 'Lv8': 78, 'Lv9': 85, 'Lv10': 90, 'Lv11': 95}

    assert ev.determine_level(96.0) == 'Lv11'
    assert ev.determine_level(91.0) == 'Lv10'
    assert ev.determine_level(85.0) == 'Lv9'
    assert ev.determine_level(78.0) == 'Lv8'
    assert ev.determine_level(74.1) == 'Lv7'
    assert ev.determine_level(69.9) == '未达Lv7'


# ---------- 6. 调度器 PID 探活 ----------

def test_scheduler_pid_liveness(tmp_path, monkeypatch):
    """is_running(): 活 PID → True；死 PID/缺 PID 文件 → False（ps 文本匹配的替代口径）"""
    import scheduler as sched

    monkeypatch.setattr(sched, 'PID_FILE', tmp_path / 'scheduler.pid')

    # 缺文件
    assert sched.is_running() is False

    # 活 PID（当前进程）
    sched.PID_FILE.write_text(str(os.getpid()))
    assert sched.is_running() is True

    # 死 PID（已退出子进程的 PID）
    proc = subprocess.Popen(['true'])
    proc.wait()
    dead_pid = proc.pid
    if dead_pid != os.getpid():
        sched.PID_FILE.write_text(str(dead_pid))
        try:
            assert sched.is_running() is False, f"PID {dead_pid} 已退出却判定存活"
        except ProcessLookupError:
            pass


# ---------- 8. 访问控制裁决 AxiomGate ----------

def _make_task(priority=akc.Priority.P2, risk=akc.RiskLevel.LOW, command='echo ok',
               task_id='TEST-AUTH'):
    return akc.Task(
        id=task_id, priority=priority, description='裁决测试任务',
        command=command, timeout=30, risk_level=risk,
        isresponsible='TEST', created_at=datetime.now().isoformat(),
    )


def test_auth_high_risk_denied():
    """高危操作强制人工审批：无审批标志必须 DENIED（元宪法铁律）"""
    gate = akc.AxiomGate()
    ok, decision, reason = gate.check_authorization(
        _make_task(risk=akc.RiskLevel.HIGH), 'REQ-HIGH-1')
    assert ok is False
    assert decision == akc.Decision.DENIED
    assert '人工审批' in reason


def test_auth_isolation_violation():
    """危险命令隔离区拦截：rm -rf / 必须 ISOLATION_VIOLATION"""
    gate = akc.AxiomGate()
    ok, decision, reason = gate.check_authorization(
        _make_task(command='rm -rf /'), 'REQ-ISO-1')
    assert ok is False
    assert decision == akc.Decision.ISOLATION_VIOLATION


def test_auth_p0_low_risk_authorized():
    """P0 低风险任务正常放行，且成本预估不抛异常"""
    gate = akc.AxiomGate()
    for risk in (akc.RiskLevel.LOW, akc.RiskLevel.MEDIUM):
        ok, decision, reason = gate.check_authorization(
            _make_task(priority=akc.Priority.P0, risk=risk, task_id=f'TEST-AUTH-{risk.name}'),
            f'REQ-{risk.name}')
        assert ok is True, f"{risk.name} 被误拒: {reason}"
        assert decision == akc.Decision.AUTHORIZED


def test_auth_quota_exceeded_blocks_p2():
    """P2 配额耗尽必须熔断（配额保护真实生效）"""
    gate = akc.AxiomGate()
    gate.current_quotas['P2_daily'] = gate.quota_limits['P2_daily']
    ok, decision, reason = gate.check_authorization(
        _make_task(priority=akc.Priority.P2), 'REQ-QUOTA-1')
    assert ok is False
    assert decision == akc.Decision.QUOTA_EXCEEDED


# ---------- 7. 执行适配器日志 ----------

def test_execution_adapter_writes_log():
    """execute_task 必须向 /workspace/execution.log 追加任务与结果两行"""
    log_path = Path('/workspace/execution.log')
    size_before = log_path.stat().st_size if log_path.exists() else 0

    adapter = akc.ExecutionAdapter(sandbox_enabled=True)
    task = akc.Task(
        id='TEST-EXEC-PROBE', priority=akc.Priority.P3,
        description='测试套件执行链路探针',
        command='echo TEST_EXEC_OK', timeout=30,
        risk_level=akc.RiskLevel.LOW, isresponsible='TEST',
        created_at=datetime.now().isoformat(),
    )
    result = adapter.execute_task(task)

    assert result['success'] is True, result
    assert result['exit_code'] == 0
    assert 'TEST_EXEC_OK' in result['stdout']

    assert log_path.exists(), "执行日志未生成"
    assert log_path.stat().st_size > size_before, "执行日志未追加"
    tail = log_path.read_text(encoding='utf-8')[-500:]
    assert 'TEST-EXEC-PROBE' in tail
    assert '✅ 任务完成: TEST-EXEC-PROBE' in tail


# ---------- 9/10. 进程级隔离行为断言（无 Docker 场景） ----------

def _exec_capture(command: str, timeout: int = 30) -> dict:
    """经执行适配器跑一条命令并返回结果（走 _execute_direct 真实链路）"""
    adapter = akc.ExecutionAdapter(sandbox_enabled=True)
    task = akc.Task(
        id='TEST-ISOLATION', priority=akc.Priority.P3,
        description='隔离行为断言任务', command=command, timeout=timeout,
        risk_level=akc.RiskLevel.LOW, isresponsible='TEST',
        created_at=datetime.now().isoformat(),
    )
    return adapter.execute_task(task)


def test_isolation_new_session():
    """setsid 新会话隔离：子进程会话必须独立于调用方会话（SID 不同）"""
    caller_sid = os.getsid(0)
    result = _exec_capture(
        'python3 -c "import os;print(os.getsid(0))"'
    )
    assert result['success'] is True, result
    child_sid = int(result['stdout'].strip())
    assert child_sid != caller_sid, (
        f"子进程 SID={child_sid} 与调用方 SID={caller_sid} 相同，setsid 隔离未生效"
    )


def test_isolation_resource_limits():
    """资源上限注入：CPU 时间/单文件写入/core dump 三项 rlimit 必须均非无穷"""
    result = _exec_capture(
        'python3 -c "import resource as R;'
        'print(R.getrlimit(R.RLIMIT_CPU)[0],'
        'R.getrlimit(R.RLIMIT_FSIZE)[0],'
        'R.getrlimit(R.RLIMIT_CORE)[0])"'
    )
    assert result['success'] is True, result
    cpu, fsize, core = (int(x) for x in result['stdout'].split())
    infinity = -1  # RLIM_INFINITY
    assert cpu not in (0, infinity), f"CPU rlimit 未注入: {cpu}"
    assert fsize not in (0, infinity), f"FSIZE rlimit 未注入: {fsize}"
    assert core == 0, f"core dump 未禁用: {core}"
