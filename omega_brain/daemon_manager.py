#!/usr/bin/env python3
"""
M3-1: Ω-Brainμ 内核守护进程管理器
支持 start/stop/status/restart，7×24运行，自动重启，PID管理
容器环境通用方案：nohup + PID文件 + 健康检查
"""
import os
import sys
import json
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
PID_FILE = ROOT / "omega_brain" / "omega_brain.pid"
LOG_FILE = ROOT / "logs" / "daemon.log"
SERVICE_SCRIPT = ROOT / "omega_brain" / "omega_brain_service.py"
HEALTH_URL = "http://127.0.0.1:8765/health"

def log(msg):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")

def get_pid():
    if PID_FILE.exists():
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        # 检查进程是否存活
        try:
            os.kill(pid, 0)
            return pid
        except OSError:
            return None
    return None

def is_healthy():
    """健康检查：尝试连接服务端口"""
    try:
        import urllib.request
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "healthy"
    except:
        return False

def start():
    """启动守护进程"""
    pid = get_pid()
    if pid:
        print(f"Ω-Brainμ 已在运行 (PID: {pid})")
        return

    print("启动 Ω-Brainμ 守护进程...")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 启动FastAPI服务
    cmd = [
        sys.executable, "-m", "uvicorn",
        "omega_brain_service:app",
        "--host", "0.0.0.0",
        "--port", "8765",
        "--workers", "1"
    ]

    with open(LOG_FILE, "a") as logf:
        process = subprocess.Popen(
            cmd,
            cwd=str(ROOT / "omega_brain"),
            stdout=logf,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

    log(f"守护进程启动 PID={process.pid}")

    # 等待健康检查
    print("等待服务就绪...", end="", flush=True)
    for i in range(30):
        time.sleep(1)
        if is_healthy():
            print(" OK")
            print(f"Ω-Brainμ 运行中 (PID: {process.pid}, 端口: 8765)")
            log(f"服务健康检查通过 PID={process.pid}")
            return
        print(".", end="", flush=True)

    print("\n警告: 服务启动超时，请检查日志")
    log("服务启动超时")

def stop():
    """停止守护进程"""
    pid = get_pid()
    if not pid:
        print("Ω-Brainμ 未在运行")
        return

    print(f"停止 Ω-Brainμ (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        # 等待优雅退出
        for i in range(10):
            time.sleep(1)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            # 强制杀死
            os.kill(pid, signal.SIGKILL)
            log(f"强制杀死进程 PID={pid}")
    except OSError as e:
        print(f"停止失败: {e}")
        return

    if PID_FILE.exists():
        PID_FILE.unlink()
    log(f"守护进程停止 PID={pid}")
    print("Ω-Brainμ 已停止")

def status():
    """查看状态"""
    pid = get_pid()
    if pid:
        healthy = is_healthy()
        print(f"Ω-Brainμ 状态: 运行中")
        print(f"  PID: {pid}")
        print(f"  端口: 8765")
        print(f"  健康: {'✅ 正常' if healthy else '⚠️ 异常'}")
        print(f"  健康检查: {HEALTH_URL}")
        print(f"  日志: {LOG_FILE}")
        return {"running": True, "pid": pid, "healthy": healthy}
    else:
        print("Ω-Brainμ 状态: 未运行")
        return {"running": False, "pid": None, "healthy": False}

def restart():
    """重启"""
    stop()
    time.sleep(2)
    start()

def daemon_loop():
    """守护循环：监控服务状态，异常自动重启（供nohup后台运行）"""
    log("守护监控循环启动")
    print("Ω-Brainμ 守护监控循环已启动 (Ctrl+C退出)")
    fail_count = 0
    while True:
        try:
            pid = get_pid()
            if not pid or not is_healthy():
                fail_count += 1
                log(f"检测到服务异常 (连续{fail_count}次)，尝试重启...")
                if pid:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except:
                        pass
                    if PID_FILE.exists():
                        PID_FILE.unlink()
                start()
                if is_healthy():
                    fail_count = 0
                    log("服务恢复正常")
            else:
                fail_count = 0
            time.sleep(30)  # 每30秒检查一次
        except KeyboardInterrupt:
            log("守护监控循环被用户中断")
            break
        except Exception as e:
            log(f"守护循环异常: {e}")
            time.sleep(10)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 daemon_manager.py [start|stop|status|restart|daemon]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    elif cmd == "restart":
        restart()
    elif cmd == "daemon":
        daemon_loop()
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
