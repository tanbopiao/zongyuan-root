#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜全域底层深度扫描与台账生成
功能：深度扫描本地实例实际底层环境，建立完整全域台账
维度：操作系统/硬件/存储/进程/网络/文件系统/依赖/安全/定时任务/元极恒一体系
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import os
import sys
import json
import time
import socket
import platform
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.resolve()
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"


def run_cmd(cmd, timeout=10):
    """执行shell命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def safe_int(val, default=0):
    """安全转换为整数"""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def scan_os_hardware():
    """扫描操作系统与硬件底层"""
    print("  [1/7] 扫描操作系统与硬件...")
    data = {}

    # 操作系统信息
    data["os"] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "hostname": socket.gethostname(),
        "node": platform.node(),
    }

    # 发行版信息
    try:
        with open("/etc/os-release", "r") as f:
            os_release = {}
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os_release[k] = v.strip('"')
            data["os"]["distro"] = os_release.get("PRETTY_NAME", "unknown")
            data["os"]["distro_id"] = os_release.get("ID", "unknown")
            data["os"]["distro_version"] = os_release.get("VERSION_ID", "unknown")
    except Exception:
        data["os"]["distro"] = "unknown"

    # 内核信息
    data["os"]["kernel"] = run_cmd("uname -r")
    data["os"]["kernel_version"] = run_cmd("uname -v")
    data["os"]["architecture"] = run_cmd("uname -m")

    # 启动时间和运行时长
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            data["os"]["uptime_seconds"] = round(uptime_seconds, 2)
            data["os"]["uptime_human"] = f"{days}天 {hours}小时 {minutes}分钟"
            data["os"]["boot_time"] = datetime.fromtimestamp(time.time() - uptime_seconds).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        data["os"]["uptime"] = "unknown"

    # CPU信息
    cpu_info = run_cmd("lscpu 2>/dev/null || cat /proc/cpuinfo | head -30")
    data["cpu"] = {
        "model": run_cmd("grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs"),
        "cores_logical": safe_int(run_cmd("nproc")),
        "cores_physical": safe_int(run_cmd("grep 'cpu cores' /proc/cpuinfo | head -1 | awk '{print $4}'")),
        "sockets": safe_int(run_cmd("grep 'physical id' /proc/cpuinfo | sort -u | wc -l")),
        "mhz": run_cmd("grep 'cpu MHz' /proc/cpuinfo | head -1 | awk '{print $4}'"),
        "cache_size": run_cmd("grep 'cache size' /proc/cpuinfo | head -1 | awk '{print $4, $5}'"),
        "flags": run_cmd("grep 'flags' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs | cut -c1-200"),
    }

    # 内存信息
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = {}
            for line in f:
                if ":" in line:
                    k, v = line.strip().split(":", 1)
                    meminfo[k] = v.strip()
            data["memory"] = {
                "total_kb": safe_int(meminfo.get("MemTotal", "").split()[0]),
                "free_kb": safe_int(meminfo.get("MemFree", "").split()[0]),
                "available_kb": safe_int(meminfo.get("MemAvailable", "").split()[0]),
                "buffers_kb": safe_int(meminfo.get("Buffers", "").split()[0]),
                "cached_kb": safe_int(meminfo.get("Cached", "").split()[0]),
                "swap_total_kb": safe_int(meminfo.get("SwapTotal", "0").split()[0]),
                "swap_free_kb": safe_int(meminfo.get("SwapFree", "0").split()[0]),
            }
            data["memory"]["total_gb"] = round(data["memory"]["total_kb"] / 1024 / 1024, 2)
            data["memory"]["used_gb"] = round((data["memory"]["total_kb"] - data["memory"]["available_kb"]) / 1024 / 1024, 2)
            data["memory"]["used_percent"] = round((data["memory"]["total_kb"] - data["memory"]["available_kb"]) / data["memory"]["total_kb"] * 100, 2)
    except Exception as e:
        data["memory"] = {"error": str(e)}

    # 负载信息
    try:
        with open("/proc/loadavg", "r") as f:
            load = f.read().split()
            data["load"] = {
                "load_1m": float(load[0]),
                "load_5m": float(load[1]),
                "load_15m": float(load[2]),
                "running_processes": load[3],
                "total_processes": load[4],
            }
    except Exception:
        data["load"] = {}

    return data


def scan_storage_filesystem():
    """扫描存储与文件系统"""
    print("  [2/7] 扫描存储与文件系统...")
    data = {}

    # 磁盘分区
    df_output = run_cmd("df -hT 2>/dev/null")
    partitions = []
    for line in df_output.split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 7:
            partitions.append({
                "filesystem": parts[0],
                "type": parts[1],
                "size": parts[2],
                "used": parts[3],
                "available": parts[4],
                "use_percent": parts[5],
                "mount_point": parts[6],
            })
    data["partitions"] = partitions

    # inode使用
    inode_output = run_cmd("df -i 2>/dev/null")
    inodes = []
    for line in inode_output.split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 6:
            inodes.append({
                "filesystem": parts[0],
                "inodes_total": parts[1],
                "inodes_used": parts[2],
                "inodes_free": parts[3],
                "use_percent": parts[4],
                "mount_point": parts[5],
            })
    data["inodes"] = inodes

    # 块设备
    data["block_devices"] = run_cmd("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE 2>/dev/null")

    # 关键目录统计
    key_dirs = [
        "/home/user",
        "/home/user/Doubao",
        str(BASE_DIR),
        "/tmp",
        "/var/log",
        "/opt",
        "/usr/local",
    ]
    dir_stats = []
    for d in key_dirs:
        if os.path.exists(d):
            try:
                # 文件数量
                file_count = run_cmd(f"find {d} -type f 2>/dev/null | wc -l")
                # 目录大小
                dir_size = run_cmd(f"du -sh {d} 2>/dev/null | cut -f1")
                # 最近修改
                last_modified = run_cmd(f"find {d} -type f -printf '%T@ %p\\n' 2>/dev/null | sort -rn | head -1 | awk '{{print $1}}'")
                dir_stats.append({
                    "path": d,
                    "file_count": safe_int(file_count),
                    "size": dir_size,
                    "exists": True,
                })
            except Exception:
                dir_stats.append({"path": d, "exists": True, "error": "scan failed"})
        else:
            dir_stats.append({"path": d, "exists": False})
    data["key_directories"] = dir_stats

    # 元极恒一部署目录详细统计
    deploy_stats = {}
    if BASE_DIR.exists():
        # 按子目录统计
        for subdir in sorted(BASE_DIR.iterdir()):
            if subdir.is_dir():
                file_count = run_cmd(f"find {subdir} -type f 2>/dev/null | wc -l")
                dir_size = run_cmd(f"du -sh {subdir} 2>/dev/null | cut -f1")
                deploy_stats[subdir.name] = {
                    "file_count": safe_int(file_count),
                    "size": dir_size,
                }
        # 总文件数
        total_files = run_cmd(f"find {BASE_DIR} -type f 2>/dev/null | wc -l")
        total_size = run_cmd(f"du -sh {BASE_DIR} 2>/dev/null | cut -f1")
        deploy_stats["_total"] = {
            "file_count": safe_int(total_files),
            "size": total_size,
        }
    data["deploy_directory"] = deploy_stats

    return data


def scan_process_network():
    """扫描进程与网络"""
    print("  [3/7] 扫描进程与网络...")
    data = {}

    # 进程总数
    data["process_summary"] = {
        "total_processes": safe_int(run_cmd("ps aux | wc -l")),
        "running": safe_int(run_cmd("ps aux | awk '$8 ~ /R/ {count++} END {print count}'")),
        "sleeping": safe_int(run_cmd("ps aux | awk '$8 ~ /S/ {count++} END {print count}'")),
        "zombie": safe_int(run_cmd("ps aux | awk '$8 ~ /Z/ {count++} END {print count}'")),
        "threads": safe_int(run_cmd("ps -eLf | wc -l")),
    }

    # 资源占用TOP10进程
    top_cpu = run_cmd("ps aux --sort=-%cpu | head -11")
    top_mem = run_cmd("ps aux --sort=-%mem | head -11")
    data["top_processes"] = {
        "by_cpu": top_cpu,
        "by_memory": top_mem,
    }

    # 元极恒一相关进程
    yjh_processes = run_cmd("ps aux | grep -E 'yuanjihengyi|master_core|slave_core|worker_main|dashboard|supervisord|watchdog' | grep -v grep")
    data["yuanjihengyi_processes"] = yjh_processes

    # 进程树（简化）
    data["process_tree"] = run_cmd("pstree -p 2>/dev/null | head -50 || ps -ejH | head -50")

    # 监听端口
    listening_ports = run_cmd("netstat -tlnp 2>/dev/null || ss -tlnp 2>/dev/null")
    data["listening_ports"] = listening_ports

    # 所有网络连接
    all_connections = run_cmd("netstat -tnp 2>/dev/null | head -30 || ss -tnp 2>/dev/null | head -30")
    data["network_connections"] = all_connections

    # 网络接口
    interfaces = run_cmd("ip addr show 2>/dev/null || ifconfig 2>/dev/null")
    data["network_interfaces"] = interfaces

    # 路由表
    data["routing_table"] = run_cmd("ip route show 2>/dev/null || route -n 2>/dev/null")

    # DNS配置
    data["dns_config"] = run_cmd("cat /etc/resolv.conf 2>/dev/null")

    # hosts文件
    data["hosts_file"] = run_cmd("cat /etc/hosts 2>/dev/null")

    # 端口统计
    data["port_stats"] = {
        "tcp_listening": safe_int(run_cmd("netstat -tln 2>/dev/null | wc -l")),
        "tcp_established": safe_int(run_cmd("netstat -tn 2>/dev/null | grep ESTABLISHED | wc -l")),
        "tcp_time_wait": safe_int(run_cmd("netstat -tn 2>/dev/null | grep TIME_WAIT | wc -l")),
    }

    return data


def scan_dependencies_runtime():
    """扫描依赖与运行时"""
    print("  [4/7] 扫描依赖与运行时...")
    data = {}

    # Python环境
    data["python"] = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "path": sys.path,
    }

    # Python已安装包
    pip_packages = run_cmd(f"{sys.executable} -m pip list --format=json 2>/dev/null || pip list 2>/dev/null")
    try:
        data["python_packages"] = json.loads(pip_packages) if pip_packages.startswith("[") else pip_packages
    except Exception:
        data["python_packages"] = pip_packages

    # 关键Python包版本
    key_packages = ["requests", "numpy", "flask", "psutil", "pillow", "fastapi", "uvicorn", "aiosqlite"]
    package_versions = {}
    for pkg in key_packages:
        version = run_cmd(f"{sys.executable} -m pip show {pkg} 2>/dev/null | grep Version | awk '{{print $2}}'")
        package_versions[pkg] = version if version else "not installed"
    data["key_package_versions"] = package_versions

    # 系统包管理器
    data["package_manager"] = {
        "apt": run_cmd("which apt-get 2>/dev/null"),
        "dpkg_count": safe_int(run_cmd("dpkg -l 2>/dev/null | wc -l")),
    }

    # 关键系统工具
    tools = ["python3", "pip3", "node", "npm", "git", "curl", "wget", "ffmpeg", "ffprobe",
             "sqlite3", "redis-cli", "mysql", "psql", "docker", "supervisord", "supervisorctl",
             "crontab", "rsync", "jq", "nohup", "tmux", "screen"]
    tool_versions = {}
    for tool in tools:
        path = run_cmd(f"which {tool} 2>/dev/null")
        if path:
            version = run_cmd(f"{tool} --version 2>&1 | head -1")
            tool_versions[tool] = {"path": path, "version": version[:100]}
        else:
            tool_versions[tool] = {"path": None, "version": "not installed"}
    data["system_tools"] = tool_versions

    # 环境变量（过滤敏感信息）
    env_vars = {}
    for k, v in os.environ.items():
        if any(sensitive in k.upper() for sensitive in ["PASSWORD", "SECRET", "TOKEN", "KEY", "PRIVATE"]):
            env_vars[k] = "***REDACTED***"
        else:
            env_vars[k] = v[:200]
    data["environment_variables"] = env_vars

    # 运行时限制
    data["resource_limits"] = {
        "open_files": run_cmd("ulimit -n 2>/dev/null"),
        "max_processes": run_cmd("ulimit -u 2>/dev/null"),
        "stack_size": run_cmd("ulimit -s 2>/dev/null"),
        "cpu_time": run_cmd("ulimit -t 2>/dev/null"),
    }

    return data


def scan_yuanjihengyi_system():
    """扫描元极恒一体系"""
    print("  [5/7] 扫描元极恒一体系...")
    data = {}

    # 部署根目录
    data["deploy_root"] = str(BASE_DIR)
    data["deploy_exists"] = BASE_DIR.exists()

    # 核心代码文件
    core_files = [
        "master/core/master_core.py",
        "slave/core/slave_core.py",
        "worker/worker_main.py",
        "worker/tri_state_engine.py",
        "worker/tri_state_cmd.py",
        "web/dashboard.py",
        "comm/protocol/comm_protocol.py",
        "pipeline/truth_pipeline.py",
        "operators/core_operators.py",
        "operators/extended_operators.py",
        "operators/result_persistence.py",
        "operators/operator_dispatcher.py",
        "config/meta_rules.json",
        "config/config_loader.py",
        "config/supervisord.conf",
    ]
    file_inventory = []
    for f in core_files:
        fpath = BASE_DIR / f
        if fpath.exists():
            stat = fpath.stat()
            file_inventory.append({
                "path": f,
                "size_bytes": stat.st_size,
                "size_human": f"{stat.st_size/1024:.1f}KB",
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "lines": safe_int(run_cmd(f"wc -l < {fpath} 2>/dev/null")),
                "sha256": run_cmd(f"sha256sum {fpath} 2>/dev/null | awk '{{print $1}}'")[:16],
            })
        else:
            file_inventory.append({"path": f, "exists": False})
    data["core_files"] = file_inventory

    # 数据库文件
    db_files = [
        "master/core/master_state.db",
        "db/asset_index.db",
        "db/operator_results.db",
    ]
    db_inventory = []
    for f in db_files:
        fpath = BASE_DIR / f
        if fpath.exists():
            stat = fpath.stat()
            # 表统计
            tables = run_cmd(f"sqlite3 {fpath} '.tables' 2>/dev/null")
            table_count = len(tables.split()) if tables else 0
            db_inventory.append({
                "path": f,
                "size_bytes": stat.st_size,
                "size_human": f"{stat.st_size/1024:.1f}KB",
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "tables": tables,
                "table_count": table_count,
            })
        else:
            db_inventory.append({"path": f, "exists": False})
    data["databases"] = db_inventory

    # 账本文件
    ledger_files = [
        "ledger/merkle_tree.json",
        "ledger/audit_log.jsonl",
    ]
    ledger_inventory = []
    for f in ledger_files:
        fpath = BASE_DIR / f
        if fpath.exists():
            stat = fpath.stat()
            line_count = safe_int(run_cmd(f"wc -l < {fpath} 2>/dev/null"))
            ledger_inventory.append({
                "path": f,
                "size_bytes": stat.st_size,
                "lines": line_count,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            ledger_inventory.append({"path": f, "exists": False})
    data["ledger_files"] = ledger_inventory

    # 配置文件
    config_files = run_cmd(f"find {BASE_DIR}/config -type f 2>/dev/null | sort")
    data["config_files"] = [f.replace(str(BASE_DIR) + "/", "") for f in config_files.split("\n") if f]

    # 脚本文件
    script_files = run_cmd(f"find {BASE_DIR}/scripts -type f 2>/dev/null | sort")
    data["script_files"] = [f.replace(str(BASE_DIR) + "/", "") for f in script_files.split("\n") if f]

    # 算子清单
    try:
        sys.path.insert(0, str(BASE_DIR / "operators"))
        from operator_dispatcher import get_dispatcher
        dispatcher = get_dispatcher()
        op_status = dispatcher.get_status()
        data["operators"] = {
            "total_registered": op_status.get("registered_operators", 0),
            "total_executions": op_status.get("total_executions", 0),
            "persistence_results": op_status.get("persistence", {}).get("total_results", 0),
            "operators": op_status.get("operators", []),
        }
    except Exception as e:
        data["operators"] = {"error": str(e)}

    # API端点状态
    try:
        import requests
        api_endpoints = ["/", "/api/status", "/api/tri_state", "/api/energy",
                         "/api/merkle", "/api/config", "/api/operators",
                         "/api/commands", "/api/audit"]
        api_status = []
        for ep in api_endpoints:
            try:
                resp = requests.get(f"http://localhost:8090{ep}", timeout=3)
                api_status.append({"endpoint": ep, "status_code": resp.status_code, "ok": resp.status_code == 200})
            except Exception as e:
                api_status.append({"endpoint": ep, "error": str(e), "ok": False})
        data["api_endpoints"] = api_status
    except Exception as e:
        data["api_endpoints"] = {"error": str(e)}

    # 报告文件
    report_files = run_cmd(f"find {BASE_DIR} -maxdepth 1 -name '*.md' -type f 2>/dev/null | sort")
    data["report_files"] = [os.path.basename(f) for f in report_files.split("\n") if f]

    return data


def scan_security_scheduled():
    """扫描安全与定时任务"""
    print("  [6/7] 扫描安全与定时任务...")
    data = {}

    # 用户信息
    data["current_user"] = {
        "username": run_cmd("whoami"),
        "uid": run_cmd("id -u"),
        "gid": run_cmd("id -g"),
        "groups": run_cmd("id -Gn"),
        "home": os.path.expanduser("~"),
        "shell": run_cmd("echo $SHELL"),
    }

    # sudo权限
    data["sudo_access"] = {
        "has_sudo": run_cmd("sudo -n true 2>/dev/null && echo 'yes' || echo 'no'"),
        "sudo_version": run_cmd("sudo --version 2>/dev/null | head -1"),
    }

    # 系统用户
    data["system_users"] = run_cmd("cat /etc/passwd | grep -E '/bin/(bash|sh|zsh)' | cut -d: -f1,3,6,7")

    # SSH配置
    data["ssh"] = {
        "sshd_config": run_cmd("cat /etc/ssh/sshd_config 2>/dev/null | grep -v '^#' | grep -v '^$' | head -20"),
        "authorized_keys": run_cmd(f"wc -l < ~/.ssh/authorized_keys 2>/dev/null || echo '0'"),
        "ssh_keys": run_cmd(f"ls -la ~/.ssh/ 2>/dev/null | grep -E '\\.pub|id_' | awk '{{print $9}}'"),
    }

    # 开放端口（安全视角）
    data["open_ports"] = run_cmd("netstat -tlnp 2>/dev/null | grep LISTEN | awk '{print $4, $7}' || ss -tlnp 2>/dev/null | grep LISTEN | awk '{print $4, $6}'")

    # 防火墙
    data["firewall"] = {
        "ufw_status": run_cmd("ufw status 2>/dev/null | head -5"),
        "iptables_rules": run_cmd("iptables -L -n 2>/dev/null | head -20"),
    }

    # crontab任务
    data["crontab"] = {
        "user_crontab": run_cmd("crontab -l 2>/dev/null"),
        "cron_daily": run_cmd("ls -la /etc/cron.daily/ 2>/dev/null | awk '{print $9}' | grep -v '^$'"),
        "cron_hourly": run_cmd("ls -la /etc/cron.hourly/ 2>/dev/null | awk '{print $9}' | grep -v '^$'"),
    }

    # supervisor配置
    supervisor_conf = BASE_DIR / "config" / "supervisord.conf"
    if supervisor_conf.exists():
        data["supervisor"] = {
            "config_exists": True,
            "config_path": str(supervisor_conf),
            "programs": run_cmd(f"grep '\\[program:' {supervisor_conf} | sed 's/\\[program://;s/\\]//'"),
            "groups": run_cmd(f"grep '\\[group:' {supervisor_conf} | sed 's/\\[group://;s/\\]//'"),
            "status": run_cmd(f"supervisorctl -c {supervisor_conf} status 2>/dev/null"),
        }
    else:
        data["supervisor"] = {"config_exists": False}

    # systemd服务（容器内通常不可用）
    data["systemd"] = {
        "available": run_cmd("systemctl --version 2>/dev/null | head -1 || echo 'not available'"),
        "running_services": run_cmd("systemctl list-units --type=service --state=running 2>/dev/null | head -10 || echo 'systemd not available'"),
    }

    # 登录会话
    data["login_sessions"] = run_cmd("who 2>/dev/null || w 2>/dev/null | head -10")

    # 历史命令（最近20条）
    data["recent_commands"] = run_cmd("history 2>/dev/null | tail -20 || cat ~/.bash_history 2>/dev/null | tail -20")

    return data


def generate_report(all_data):
    """生成全域台账报告"""
    print("  [7/7] 生成全域台账报告...")

    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_id = f"INVENTORY-{datetime.now().strftime('%Y%m%d_%H%M%S')}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"

    # 计算台账摘要
    summary = {
        "scan_id": scan_id,
        "scan_time": scan_time,
        "hostname": all_data["os_hardware"]["os"]["hostname"],
        "os": all_data["os_hardware"]["os"].get("distro", "unknown"),
        "kernel": all_data["os_hardware"]["os"]["kernel"],
        "uptime": all_data["os_hardware"]["os"].get("uptime_human", "unknown"),
        "cpu_cores": all_data["os_hardware"]["cpu"]["cores_logical"],
        "memory_total_gb": all_data["os_hardware"]["memory"].get("total_gb", 0),
        "memory_used_percent": all_data["os_hardware"]["memory"].get("used_percent", 0),
        "partitions": len(all_data["storage_filesystem"]["partitions"]),
        "total_processes": all_data["process_network"]["process_summary"]["total_processes"],
        "listening_ports": all_data["process_network"]["port_stats"]["tcp_listening"],
        "python_packages": len(all_data["dependencies_runtime"].get("python_packages", [])) if isinstance(all_data["dependencies_runtime"].get("python_packages"), list) else "unknown",
        "yuanjihengyi_operators": all_data["yuanjihengyi_system"].get("operators", {}).get("total_registered", 0),
        "yuanjihengyi_api_endpoints": len(all_data["yuanjihengyi_system"].get("api_endpoints", [])),
        "crontab_tasks": all_data["security_scheduled"]["crontab"]["user_crontab"].count("\n") + 1 if all_data["security_scheduled"]["crontab"]["user_crontab"] else 0,
        "did": DID,
        "trace": TRACE,
    }

    report = {
        "summary": summary,
        "os_hardware": all_data["os_hardware"],
        "storage_filesystem": all_data["storage_filesystem"],
        "process_network": all_data["process_network"],
        "dependencies_runtime": all_data["dependencies_runtime"],
        "yuanjihengyi_system": all_data["yuanjihengyi_system"],
        "security_scheduled": all_data["security_scheduled"],
    }

    # 保存JSON报告
    json_path = REPORT_DIR / f"full_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    return report, summary, json_path


def main():
    print("=" * 60)
    print("元极恒一｜全域底层深度扫描与台账生成")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"溯源: {TRACE} | {DID}")
    print("=" * 60)
    print()

    # 执行各维度扫描
    all_data = {}
    all_data["os_hardware"] = scan_os_hardware()
    all_data["storage_filesystem"] = scan_storage_filesystem()
    all_data["process_network"] = scan_process_network()
    all_data["dependencies_runtime"] = scan_dependencies_runtime()
    all_data["yuanjihengyi_system"] = scan_yuanjihengyi_system()
    all_data["security_scheduled"] = scan_security_scheduled()

    # 生成报告
    report, summary, json_path = generate_report(all_data)

    # 输出摘要
    print()
    print("=" * 60)
    print("全域台账扫描完成")
    print("=" * 60)
    print(f"  扫描ID: {summary['scan_id']}")
    print(f"  主机: {summary['hostname']}")
    print(f"  系统: {summary['os']} (内核 {summary['kernel']})")
    print(f"  运行时长: {summary['uptime']}")
    print(f"  CPU: {summary['cpu_cores']}核")
    print(f"  内存: {summary['memory_total_gb']}GB (已用 {summary['memory_used_percent']}%)")
    print(f"  分区: {summary['partitions']}个")
    print(f"  进程: {summary['total_processes']}个")
    print(f"  监听端口: {summary['listening_ports']}个")
    print(f"  元极恒一算子: {summary['yuanjihengyi_operators']}个")
    print(f"  API端点: {summary['yuanjihengyi_api_endpoints']}个")
    print(f"  crontab任务: {summary['crontab_tasks']}个")
    print(f"  JSON报告: {json_path}")
    print("=" * 60)

    return report, summary


if __name__ == "__main__":
    main()
