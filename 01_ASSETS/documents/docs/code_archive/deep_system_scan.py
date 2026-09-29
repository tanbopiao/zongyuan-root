#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜底层系统深度探查
功能：全面扫描系统底层状态（内核/cgroup/文件系统/进程/网络/SQLite/安全）
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import os
import sys
import json
import time
import sqlite3
import subprocess
from pathlib import Path

BASE_DIR = Path("/home/user/Doubao/chats/1128121028098/yuanjihengyi-deploy")
REPORT = {
    "timestamp": time.time(),
    "did": "DID-BR-000002",
    "trace": "Ω₀⊂⊙∞⊂Ω",
}


def run_cmd(cmd, timeout=10):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ========== 1. 内核与系统信息 ==========
section("1. 内核与系统信息")
REPORT["kernel"] = {
    "kernel_version": run_cmd("uname -r"),
    "os": run_cmd("cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2"),
    "arch": run_cmd("uname -m"),
    "hostname": run_cmd("hostname"),
    "uptime": run_cmd("uptime -p"),
    "load_avg": run_cmd("cat /proc/loadavg"),
    "pid_1": run_cmd("ps -p 1 -o comm="),
    "container_env": os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"),
}
for k, v in REPORT["kernel"].items():
    print(f"  {k}: {v}")


# ========== 2. 内核参数（sysctl） ==========
section("2. 内核参数（关键sysctl）")
key_sysctls = [
    "fs.file-max", "fs.inotify.max_user_instances", "fs.inotify.max_user_watches",
    "net.core.somaxconn", "net.core.netdev_max_backlog", "net.core.rmem_max", "net.core.wmem_max",
    "net.ipv4.tcp_max_syn_backlog", "net.ipv4.tcp_fin_timeout", "net.ipv4.tcp_keepalive_time",
    "net.ipv4.tcp_tw_reuse", "net.ipv4.ip_local_port_range",
    "vm.swappiness", "vm.dirty_ratio", "vm.dirty_background_ratio", "vm.overcommit_memory",
    "kernel.pid_max", "kernel.threads-max", "kernel.msgmax", "kernel.shmmax",
]
REPORT["sysctl"] = {}
for s in key_sysctls:
    val = run_cmd(f"sysctl -n {s} 2>/dev/null")
    REPORT["sysctl"][s] = val
    print(f"  {s} = {val}")


# ========== 3. cgroup配置 ==========
section("3. cgroup配置")
REPORT["cgroup"] = {
    "cgroup_version": run_cmd("stat -fc %T /sys/fs/cgroup"),
    "cpu_cfs_period": run_cmd("cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo 'N/A'"),
    "memory_max": run_cmd("cat /sys/fs/cgroup/memory.max 2>/dev/null || echo 'N/A'"),
    "memory_current": run_cmd("cat /sys/fs/cgroup/memory.current 2>/dev/null || echo 'N/A'"),
    "pids_max": run_cmd("cat /sys/fs/cgroup/pids.max 2>/dev/null || echo 'N/A'"),
    "pids_current": run_cmd("cat /sys/fs/cgroup/pids.current 2>/dev/null || echo 'N/A'"),
    "io_max": run_cmd("cat /sys/fs/cgroup/io.max 2>/dev/null || echo 'N/A'"),
}
for k, v in REPORT["cgroup"].items():
    print(f"  {k}: {v}")


# ========== 4. 文件系统 ==========
section("4. 文件系统与挂载")
REPORT["filesystem"] = {
    "mounts": run_cmd("mount | grep -E 'ext4|xfs|hpvs|overlay|tmpfs' | head -10"),
    "disk_usage": run_cmd("df -h / /home/user 2>/dev/null"),
    "inode_usage": run_cmd("df -i / /home/user 2>/dev/null | tail -2"),
    "io_scheduler": run_cmd("cat /sys/block/*/queue/scheduler 2>/dev/null | head -5"),
    "read_ahead": run_cmd("cat /sys/block/*/queue/read_ahead_kb 2>/dev/null | head -5"),
    "nr_requests": run_cmd("cat /sys/block/*/queue/nr_requests 2>/dev/null | head -5"),
}
for k, v in REPORT["filesystem"].items():
    print(f"  {k}:\n{v}")


# ========== 5. 系统限制（ulimit） ==========
section("5. 系统限制（ulimit）")
REPORT["limits"] = {
    "open_files": run_cmd("ulimit -n"),
    "max_processes": run_cmd("ulimit -u"),
    "file_size": run_cmd("ulimit -f"),
    "stack_size": run_cmd("ulimit -s"),
    "cpu_time": run_cmd("ulimit -t"),
    "virtual_memory": run_cmd("ulimit -v"),
    "locked_memory": run_cmd("ulimit -l"),
    "pending_signals": run_cmd("ulimit -i"),
}
for k, v in REPORT["limits"].items():
    print(f"  {k}: {v}")


# ========== 6. 进程资源使用 ==========
section("6. 元极恒一进程资源使用")
REPORT["processes"] = []
proc_names = ["master_core", "slave_core", "worker_main", "dashboard", "watchdog", "supervisord"]
for name in proc_names:
    info = run_cmd(f"ps aux | grep {name} | grep -v grep | head -1")
    if info:
        parts = info.split()
        REPORT["processes"].append({
            "name": name,
            "pid": parts[1],
            "cpu": parts[2],
            "mem": parts[3],
            "vsz": parts[4],
            "rss": parts[5],
            "start": parts[8],
            "time": parts[9],
        })
        print(f"  {name}: PID={parts[1]}, CPU={parts[2]}%, MEM={parts[3]}%, RSS={int(parts[5])//1024}MB")

# Top 5 CPU
print(f"\n  Top 5 CPU进程:")
top_cpu = run_cmd("ps aux --sort=-%cpu | head -6")
print(top_cpu)


# ========== 7. 网络配置 ==========
section("7. 网络配置")
REPORT["network"] = {
    "interfaces": run_cmd("ip addr show | grep -E 'inet |^[0-9]' | head -10"),
    "routes": run_cmd("ip route show | head -5"),
    "listening_ports": run_cmd("ss -tlnp 2>/dev/null | head -15 || netstat -tlnp 2>/dev/null | head -15"),
    "connections": run_cmd("ss -s 2>/dev/null || echo 'N/A'"),
    "conntrack": run_cmd("cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo 'N/A'"),
}
for k, v in REPORT["network"].items():
    print(f"  {k}:\n{v}")


# ========== 8. SQLite数据库状态 ==========
section("8. SQLite数据库状态")
REPORT["sqlite"] = []
databases = [
    ("master_state", BASE_DIR / "master/core/master_state.db"),
    ("asset_index", BASE_DIR / "db/asset_index.db"),
    ("operator_results", BASE_DIR / "db/operator_results.db"),
    ("federation_state", BASE_DIR / "db/federation_state.db"),
]
for name, db_path in databases:
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            # 数据库大小
            size = db_path.stat().st_size
            # 表数量和名称
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            # 每页大小
            page_size = conn.execute("PRAGMA page_size").fetchone()[0]
            # 页数
            page_count = conn.execute("PRAGMA page_count").fetchone()[0]
            #  journal模式
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            # 同步级别
            synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
            # 缓存大小
            cache_size = conn.execute("PRAGMA cache_size").fetchone()[0]
            # 行数统计
            row_counts = {}
            for t in table_names:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
                    row_counts[t] = count
                except Exception:
                    pass
            conn.close()

            db_info = {
                "name": name,
                "path": str(db_path),
                "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 2),
                "tables": table_names,
                "table_count": len(table_names),
                "page_size": page_size,
                "page_count": page_count,
                "journal_mode": journal_mode,
                "synchronous": synchronous,
                "cache_size": cache_size,
                "row_counts": row_counts,
            }
            REPORT["sqlite"].append(db_info)
            print(f"  {name}: {db_info['size_mb']}MB, {len(table_names)}表, journal={journal_mode}, sync={synchronous}, cache={cache_size}")
            for t, c in row_counts.items():
                print(f"    {t}: {c}行")
        except Exception as e:
            print(f"  {name}: ERROR - {e}")
    else:
        print(f"  {name}: 不存在")


# ========== 9. 安全配置 ==========
section("9. 安全配置")
REPORT["security"] = {
    "aslr": run_cmd("cat /proc/sys/kernel/randomize_va_space 2>/dev/null"),
    "protected_hardlinks": run_cmd("cat /proc/sys/fs/protected_hardlinks 2>/dev/null"),
    "protected_symlinks": run_cmd("cat /proc/sys/fs/protected_symlinks 2>/dev/null"),
    "kptr_restrict": run_cmd("cat /proc/sys/kernel/kptr_restrict 2>/dev/null"),
    "dmesg_restrict": run_cmd("cat /proc/sys/kernel/dmesg_restrict 2>/dev/null"),
    "yama_ptrace_scope": run_cmd("cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null"),
    "sudo_nopasswd": run_cmd("sudo -n true 2>/dev/null && echo 'yes' || echo 'no'"),
    "root_shells": run_cmd("grep -E '^root:' /etc/passwd"),
    "suid_files": run_cmd("find /usr/bin /usr/sbin /bin /sbin -perm -4000 2>/dev/null | head -10"),
}
for k, v in REPORT["security"].items():
    print(f"  {k}: {v}")


# ========== 10. 元极恒一体系文件结构 ==========
section("10. 元极恒一体系文件结构")
REPORT["structure"] = {
    "total_size": run_cmd(f"du -sh {BASE_DIR} 2>/dev/null | cut -f1"),
    "file_count": run_cmd(f"find {BASE_DIR} -type f 2>/dev/null | wc -l"),
    "dir_count": run_cmd(f"find {BASE_DIR} -type d 2>/dev/null | wc -l"),
    "code_files": run_cmd(f"find {BASE_DIR} -name '*.py' -type f 2>/dev/null | wc -l"),
    "config_files": run_cmd(f"find {BASE_DIR} -name '*.json' -o -name '*.conf' -o -name '*.yaml' 2>/dev/null | wc -l"),
    "db_files": run_cmd(f"find {BASE_DIR} -name '*.db' -type f 2>/dev/null | wc -l"),
    "log_files": run_cmd(f"find {BASE_DIR}/logs -name '*.log' -type f 2>/dev/null | wc -l"),
    "log_size": run_cmd(f"du -sh {BASE_DIR}/logs 2>/dev/null | cut -f1"),
    "backup_size": run_cmd(f"du -sh {BASE_DIR}/backup 2>/dev/null | cut -f1"),
}
for k, v in REPORT["structure"].items():
    print(f"  {k}: {v}")


# ========== 输出JSON报告 ==========
section("11. 生成JSON报告")
report_path = BASE_DIR / "reports" / "deep_system_scan.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
print(f"  ✅ JSON报告已生成: {report_path}")
print(f"  报告大小: {report_path.stat().st_size} bytes")


# ========== 优化建议 ==========
section("12. 底层优化建议")
suggestions = []

# 内核参数优化
if REPORT["sysctl"].get("net.core.somaxconn", "128") == "128":
    suggestions.append("net.core.somaxconn: 128→1024（提高并发连接队列）")
if REPORT["sysctl"].get("vm.swappiness", "60") != "10":
    suggestions.append("vm.swappiness: 60→10（减少swap使用，优先物理内存）")
if REPORT["sysctl"].get("fs.file-max", "0") < "1000000":
    suggestions.append("fs.file-max: 提高到1000000（增加文件描述符上限）")
if REPORT["sysctl"].get("net.ipv4.tcp_fin_timeout", "60") != "15":
    suggestions.append("net.ipv4.tcp_fin_timeout: 60→15（加快TCP连接回收）")

# SQLite优化
for db in REPORT["sqlite"]:
    if db["journal_mode"] != "wal":
        suggestions.append(f"SQLite {db['name']}: journal_mode={db['journal_mode']}→wal（提高并发读写性能）")
    if db["synchronous"] != 1:
        suggestions.append(f"SQLite {db['name']}: synchronous={db['synchronous']}→1（NORMAL模式，平衡性能和安全）")
    if abs(db["cache_size"]) < 10000:
        suggestions.append(f"SQLite {db['name']}: cache_size={db['cache_size']}→-20000（20MB缓存，提高查询性能）")

# 进程优化
suggestions.append("进程优先级: master/dashboard设置nice=-10（高优先级），worker设置nice=0")
suggestions.append("OOM评分: 关键进程设置oom_score_adj=-500（降低被OOM killer杀死概率）")

# 文件系统优化
suggestions.append("文件系统: 数据库目录设置noatime（减少访问时间写入）")
suggestions.append("目录结构: 按模块分离日志/数据/配置，便于备份和迁移")

# 安全优化
suggestions.append("安全: 配置seccomp限制系统调用，减少攻击面")
suggestions.append("安全: 非root用户运行，最小权限原则")

for i, s in enumerate(suggestions, 1):
    print(f"  {i}. {s}")

print(f"\n  共 {len(suggestions)} 条优化建议")
print("\n✅ 底层系统深度探查完成！")
