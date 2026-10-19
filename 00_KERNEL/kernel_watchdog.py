#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 内核看门狗 Kernel-Watchdog V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

周期巡检三项组件，发现死亡自动拉起，每次治愈写入
watchdog_heal_events.jsonl（时间/组件/旧PID/新PID/原因）。

巡检对象：
  1. kernel   - autonomous_kernel_core.py 进程
  2. scheduler - PID 文件探活（内核内嵌线程，PID 指向内核进程）
  3. gateway  - 记忆网关 8077 端口

用法:
  nohup python3 kernel_watchdog.py &        # 常驻巡检（默认 30s 周期）
  python3 kernel_watchdog.py --once         # 单次巡检（供演练/测试）
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

WATCHDOG_DIR = Path("/workspace/atomgit-mirror/zongyuan-root-sync/00_KERNEL")
HEAL_EVENTS = WATCHDOG_DIR / "watchdog_heal_events.jsonl"
WATCHDOG_PID = WATCHDOG_DIR / "watchdog.pid"
SCHEDULER_PID_FILE = Path("/workspace/evolution/scheduler.pid")

KERNEL_CMD = "python3 -u autonomous_kernel_core.py"
KERNEL_CWD = str(WATCHDOG_DIR)
GATEWAY_CMD = ["python3", "-u", "memory_gateway.py"]
GATEWAY_CWD = "/workspace/atomgit-mirror/zongyuan-root-sync"
GATEWAY_PORT = 8077

CHECK_INTERVAL = 30


def now() -> str:
    return datetime.now().isoformat()


def find_kernel_pids():
    """查找内核进程 PID 列表（严格解析 /proc/<pid>/cmdline：
    必须是 python 解释器执行 autonomous_kernel_core.py——
    pgrep -f 文本匹配会把命令行含关键字的 shell/评估脚本误报为内核）"""
    pids = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            parts = (entry / 'cmdline').read_bytes().split(b'\0')
            args = [p.decode('utf-8', 'ignore') for p in parts if p]
        except OSError:
            continue
        if not args:
            continue
        is_python = 'python' in Path(args[0]).name
        runs_kernel = any(a.endswith('autonomous_kernel_core.py') for a in args[1:])
        if is_python and runs_kernel:
            pids.append(int(entry.name))
    return pids


def scheduler_alive() -> bool:
    """调度器 PID 探活（内嵌线程，PID 文件指向内核进程）"""
    if not SCHEDULER_PID_FILE.exists():
        return False
    try:
        pid = int(SCHEDULER_PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def gateway_listening() -> bool:
    """记忆网关端口探活"""
    try:
        with socket.create_connection(('127.0.0.1', GATEWAY_PORT), timeout=2):
            return True
    except OSError:
        return False


def record_heal(component: str, action: str, old_pid, new_pid, reason: str):
    """治愈事件落盘（JSONL 单行）"""
    event = {
        'event_id': f"HEAL-{int(time.time()*1000)}",
        'component': component,
        'action': action,
        'old_pid': old_pid,
        'new_pid': new_pid,
        'reason': reason,
        'healed_at': now(),
        'watchdog_pid': os.getpid(),
        'did': 'DID-BR-000002',
    }
    with open(HEAL_EVENTS, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"[WATCHDOG] 治愈 {component}: {reason} (old={old_pid} new={new_pid})")


def heal_kernel(reason: str):
    """拉起自治内核"""
    old_pids = find_kernel_pids()
    proc = subprocess.Popen(
        KERNEL_CMD, shell=True, cwd=KERNEL_CWD,
        stdout=open('/tmp/kernel_watchdog_restart.log', 'a'),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    time.sleep(3)
    new_pids = find_kernel_pids()
    if new_pids:
        record_heal('kernel', 'restart', old_pids[0] if old_pids else None,
                    new_pids[0], reason)
        return True
    record_heal('kernel', 'restart_failed', old_pids[0] if old_pids else None,
                proc.pid, reason)
    return False


def heal_gateway(reason: str):
    """拉起记忆网关"""
    proc = subprocess.Popen(
        GATEWAY_CMD, cwd=GATEWAY_CWD,
        stdout=open('/tmp/gateway_watchdog_restart.log', 'a'),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(10):
        time.sleep(1)
        if gateway_listening():
            record_heal('memory_gateway', 'restart', None, proc.pid, reason)
            return True
    record_heal('memory_gateway', 'restart_failed', None, proc.pid, reason)
    return False


def check_once() -> dict:
    """单次巡检：返回各组件状态，死亡即治愈"""
    result = {'kernel': 'up', 'scheduler': 'up', 'memory_gateway': 'up', 'healed': []}

    # 1. 内核
    if not find_kernel_pids():
        if heal_kernel('kernel process dead'):
            result['kernel'] = 'healed'
            result['healed'].append('kernel')
        else:
            result['kernel'] = 'down'
        # 内核死亡时其内嵌调度器随之死亡，内核重启后由内核自行拉起调度线程

    # 2. 调度器（内核存活但 PID 文件失效 = 异常）
    if find_kernel_pids() and not scheduler_alive():
        result['scheduler'] = 'down'  # 需内核重启才能恢复，记录不误报治愈
        record_heal('scheduler', 'detected_down', None, None,
                    'kernel alive but scheduler pid file invalid')

    # 3. 记忆网关
    if not gateway_listening():
        if heal_gateway('gateway port 8077 not listening'):
            result['memory_gateway'] = 'healed'
            result['healed'].append('memory_gateway')
        else:
            result['memory_gateway'] = 'down'

    return result


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        print(json.dumps(check_once(), ensure_ascii=False))
        return

    WATCHDOG_PID.write_text(str(os.getpid()))
    print(f"[WATCHDOG] 启动 pid={os.getpid()} 巡检周期={CHECK_INTERVAL}s")

    def _stop(signum, frame):
        if WATCHDOG_PID.exists():
            WATCHDOG_PID.unlink()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while True:
        try:
            r = check_once()
            if r['healed']:
                print(f"[WATCHDOG] 本轮治愈: {r['healed']}")
        except Exception as e:
            print(f"[WATCHDOG] 巡检异常: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
