#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU实例心跳监控与自动重连 V3.0
用Python实现，避免shell引号和grep匹配问题
"""
import subprocess
import time
import os
from datetime import datetime

LOG_FILE = "/var/log/gpu_instance_heartbeat.log"
PID_DIR = "/var/run"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)

def check_port_listen(port):
    rc, out, err = run_cmd(f"ss -tlnp | grep :{port}")
    return rc == 0 and port in out

def check_http_health(url, timeout=8):
    rc, out, err = run_cmd(f"curl -s --connect-timeout {timeout} --max-time {timeout} {url}", timeout=timeout+2)
    if rc == 0 and "ok" in out.lower():
        return True, out
    return False, out or err

def check_ssh_tunnel():
    if check_port_listen("22022"):
        rc, out, err = run_cmd("ssh -p 22022 -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@127.0.0.1 'hostname'", timeout=8)
        if rc == 0 and "dsw" in out:
            return True
    return False

def restart_ssh_tunnel():
    log("SSH隧道断开，尝试重连...")
    cmd = "ssh -p 22022 -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@127.0.0.1 \""
    cmd += "if [ -f /tmp/ssh_reverse_tunnel.pid ]; then "
    cmd += "OLD_PID=$(cat /tmp/ssh_reverse_tunnel.pid 2>/dev/null); "
    cmd += "[ -n \\\"$OLD_PID\\\" ] && kill $OLD_PID 2>/dev/null; "
    cmd += "rm -f /tmp/ssh_reverse_tunnel.pid; fi; "
    cmd += "nohup ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -N -R 22022:127.0.0.1:22 root@123.207.202.158 > /tmp/ssh_reverse_tunnel.log 2>&1 & "
    cmd += "echo $! > /tmp/ssh_reverse_tunnel.pid\""
    run_cmd(cmd, timeout=15)
    time.sleep(8)
    return check_ssh_tunnel()

def check_gpu_brain():
    ok, out = check_http_health("http://127.0.0.1:7861/health")
    return ok

def restart_gpu_brain():
    log("GPU大脑7B服务异常，尝试恢复...")
    pid_file = f"{PID_DIR}/gpu_brain_forward.pid"
    forward_ok = False
    if os.path.exists(pid_file):
        pid = open(pid_file).read().strip()
        if pid and run_cmd(f"kill -0 {pid}")[0] == 0:
            forward_ok = True
    if not forward_ok:
        log("重建7861端口转发...")
        if os.path.exists(pid_file):
            pid = open(pid_file).read().strip()
            if pid:
                run_cmd(f"kill {pid} 2>/dev/null; kill -9 {pid} 2>/dev/null")
            os.remove(pid_file)
        run_cmd("nohup ssh -p 22022 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -L 7861:127.0.0.1:7861 root@127.0.0.1 > /tmp/gpu_brain_forward.log 2>&1 &")
        time.sleep(1)
        rc, out, err = run_cmd("pgrep -f 'ssh.*-L 7861.*root@127.0.0.1' | head -1")
        if out:
            with open(pid_file, "w") as f:
                f.write(out.strip())
    rc, out, err = run_cmd("ssh -p 22022 -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@127.0.0.1 'curl -s --connect-timeout 3 http://127.0.0.1:7861/health 2>/dev/null'", timeout=10)
    if "ok" not in (out or "").lower():
        log("启动GPU实例端GPU大脑服务...")
        cmd = "ssh -p 22022 -o StrictHostKeyChecking=no root@127.0.0.1 \""
        cmd += "if [ -f /tmp/gpu_brain_v3.pid ]; then "
        cmd += "OLD_PID=$(cat /tmp/gpu_brain_v3.pid 2>/dev/null); "
        cmd += "[ -n \\\"$OLD_PID\\\" ] && kill $OLD_PID 2>/dev/null; "
        cmd += "rm -f /tmp/gpu_brain_v3.pid; fi; "
        cmd += "cd /mnt/workspace; "
        cmd += "nohup python3 gpu_brain_v3.py > /tmp/gpu_brain_v3.log 2>&1 & "
        cmd += "echo $! > /tmp/gpu_brain_v3.pid\""
        run_cmd(cmd, timeout=15)
        time.sleep(20)
    return check_gpu_brain()

def check_05b_model():
    ok, out = check_http_health("http://127.0.0.1:7862/health", timeout=5)
    return ok

def restart_05b_model():
    log("0.5B模型服务异常，尝试恢复...")
    pid_file = f"{PID_DIR}/gpu_05b_forward.pid"
    forward_ok = False
    if os.path.exists(pid_file):
        pid = open(pid_file).read().strip()
        if pid and run_cmd(f"kill -0 {pid}")[0] == 0:
            forward_ok = True
    if not forward_ok:
        log("重建7862端口转发...")
        if os.path.exists(pid_file):
            pid = open(pid_file).read().strip()
            if pid:
                run_cmd(f"kill {pid} 2>/dev/null")
            os.remove(pid_file)
        run_cmd("nohup ssh -p 22022 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -L 7862:127.0.0.1:7862 root@127.0.0.1 > /tmp/llama_05b_forward.log 2>&1 &")
        time.sleep(1)
        rc, out, err = run_cmd("pgrep -f 'ssh.*-L 7862.*root@127.0.0.1' | head -1")
        if out:
            with open(pid_file, "w") as f:
                f.write(out.strip())
    rc, out, err = run_cmd("ssh -p 22022 -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@127.0.0.1 'curl -s --connect-timeout 3 http://127.0.0.1:7862/health > /dev/null 2>&1 && echo ok'", timeout=10)
    if "ok" not in (out or ""):
        log("启动GPU实例端0.5B服务...")
        cmd = "ssh -p 22022 -o StrictHostKeyChecking=no root@127.0.0.1 \""
        cmd += "if [ -f /tmp/llama_server_05b.pid ]; then "
        cmd += "OLD_PID=$(cat /tmp/llama_server_05b.pid 2>/dev/null); "
        cmd += "[ -n \\\"$OLD_PID\\\" ] && kill $OLD_PID 2>/dev/null; "
        cmd += "rm -f /tmp/llama_server_05b.pid; fi; "
        cmd += "cd /mnt/workspace; "
        cmd += "nohup ./llama.cpp/build/bin/llama-server -m /mnt/workspace/zongyuan-0.5B-q4_0.gguf --host 0.0.0.0 --port 7862 -c 2048 -n 512 > /tmp/llama_server_0.5b.log 2>&1 & "
        cmd += "echo $! > /tmp/llama_server_05b.pid\""
        run_cmd(cmd, timeout=15)
        time.sleep(8)
    return check_05b_model()

def main():
    log("=== GPU实例心跳检查开始 ===")
    if check_ssh_tunnel():
        ssh_status = "OK"
    else:
        ssh_status = "OK" if restart_ssh_tunnel() else "FAIL"
    if check_gpu_brain():
        brain_status = "OK"
    else:
        brain_status = "OK" if restart_gpu_brain() else "FAIL"
    if check_05b_model():
        model_status = "OK"
    else:
        model_status = "OK" if restart_05b_model() else "FAIL"
    status = f"SSH:{ssh_status} | GPU_BRAIN:{brain_status} | 0.5B:{model_status}"
    log(f"心跳检查结果: {status}")
    print(status)

if __name__ == "__main__":
    main()
