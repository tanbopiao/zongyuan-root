#!/usr/bin/env python3
"""
内核级深度扫描脚本
扫描：内核版本/系统日志/内核模块/资源限制/内存碎片/CPU调度/磁盘IO/网络栈/安全状态
"""
import os
import sys
import json
import subprocess
import socket
from datetime import datetime

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

def main():
    print("=" * 70)
    print("  内核级深度扫描报告")
    print("  ZONGYUAN-ROOT · 火斗云智AIOS")
    print("=" * 70)
    print(f"  扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  主机名: {run_cmd('hostname')}")
    print(f"  运行时间: {run_cmd('uptime -p')}")
    print()

    # 1. 内核版本与参数
    print("【1】内核版本与核心参数")
    print("-" * 70)
    kernel_ver = run_cmd('uname -r')
    os_release = run_cmd('cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d \'"\'')
    arch = run_cmd('uname -m')
    print(f"  内核版本: {kernel_ver}")
    print(f"  系统发行版: {os_release}")
    print(f"  架构: {arch}")
    print()
    
    print("  核心内核参数:")
    params = [
        ("vm.swappiness", "vm.swappiness"),
        ("vm.overcommit_memory", "vm.overcommit_memory"),
        ("vm.max_map_count", "vm.max_map_count"),
        ("fs.file-max", "fs.file-max"),
        ("net.core.somaxconn", "net.core.somaxconn"),
        ("net.ipv4.tcp_max_syn_backlog", "net.ipv4.tcp_max_syn_backlog"),
        ("net.ipv4.ip_forward", "net.ipv4.ip_forward"),
        ("kernel.pid_max", "kernel.pid_max"),
        ("kernel.threads-max", "kernel.threads-max"),
    ]
    for name, param in params:
        val = run_cmd(f"sysctl -n {param} 2>/dev/null")
        print(f"    {name}: {val}")
    print()

    # 2. 系统日志与错误
    print("【2】系统日志与内核错误")
    print("-" * 70)
    
    # dmesg错误
    dmesg_errors = run_cmd("dmesg 2>/dev/null | grep -iE 'error|fail|warn|panic|oops|bug|oom|kill' | tail -20")
    if dmesg_errors:
        print("  dmesg最近错误/警告(前20条):")
        for line in dmesg_errors.split("\n")[:20]:
            print(f"    {line[:100]}")
    else:
        print("  ✅ dmesg无明显错误")
    print()
    
    # journalctl错误
    journal_errors = run_cmd("journalctl -p err --since '24 hours ago' --no-pager 2>/dev/null | tail -15")
    if journal_errors:
        print("  最近24小时系统错误(前15条):")
        for line in journal_errors.split("\n")[:15]:
            print(f"    {line[:100]}")
    else:
        print("  ✅ 最近24小时无系统错误")
    print()
    
    # OOM事件
    oom_count = run_cmd("dmesg 2>/dev/null | grep -c 'Out of memory'")
    oom_kill = run_cmd("dmesg 2>/dev/null | grep -c 'Killed process'")
    print(f"  OOM事件次数: {oom_count}")
    print(f"  OOM杀死进程次数: {oom_kill}")
    if int(oom_count) > 0:
        print("  ⚠️  检测到OOM事件，需关注内存使用")
    print()

    # 3. 内核模块
    print("【3】内核模块状态")
    print("-" * 70)
    module_count = run_cmd("lsmod 2>/dev/null | wc -l")
    print(f"  已加载内核模块数: {module_count}")
    print()
    print("  关键模块状态:")
    key_modules = ["overlay", "br_netfilter", "iptable_nat", "nf_conntrack", "tcp_bbr", "sch_fq", "veth", "bridge"]
    for mod in key_modules:
        loaded = run_cmd(f"lsmod 2>/dev/null | grep -c '^{mod} '")
        status = "✅ 已加载" if int(loaded) > 0 else "❌ 未加载"
        print(f"    {mod}: {status}")
    print()

    # 4. 资源限制
    print("【4】系统资源限制")
    print("-" * 70)
    print("  当前进程资源限制(ulimit):")
    limits = run_cmd("ulimit -a 2>/dev/null")
    for line in limits.split("\n"):
        if line.strip():
            print(f"    {line.strip()}")
    print()
    
    # 文件描述符使用
    fd_total = run_cmd("cat /proc/sys/fs/file-nr 2>/dev/null | awk '{print $1}'")
    fd_max = run_cmd("cat /proc/sys/fs/file-nr 2>/dev/null | awk '{print $3}'")
    fd_pct = int(fd_total) / int(fd_max) * 100 if int(fd_max) > 0 else 0
    print(f"  文件描述符使用: {fd_total}/{fd_max} ({fd_pct:.1f}%)")
    if fd_pct > 80:
        print("  ⚠️  文件描述符使用率过高")
    print()
    
    # 进程数
    proc_count = run_cmd("ps aux | wc -l")
    thread_count = run_cmd("ps -eLf | wc -l")
    pid_max = run_cmd("cat /proc/sys/kernel/pid_max")
    print(f"  进程数: {proc_count}")
    print(f"  线程数: {thread_count}")
    print(f"  PID上限: {pid_max}")
    print()

    # 5. 内存深度分析
    print("【5】内存深度分析")
    print("-" * 70)
    print("  内存详细信息:")
    mem_info = run_cmd("free -h")
    print(mem_info)
    print()
    
    # /proc/meminfo关键指标
    print("  /proc/meminfo关键指标:")
    mem_keys = ["MemTotal", "MemFree", "MemAvailable", "Buffers", "Cached", "SwapCached", "Active", "Inactive", "SwapTotal", "SwapFree", "Dirty", "Writeback", "Slab", "SReclaimable", "SUnreclaim", "KernelStack", "PageTables", "Committed_AS", "VmallocTotal", "VmallocUsed"]
    for key in mem_keys:
        val = run_cmd(f"grep '^{key}:' /proc/meminfo 2>/dev/null | awk '{{print $2, $3}}'")
        if val:
            print(f"    {key}: {val}")
    print()
    
    # 内存碎片
    print("  内存碎片状态(伙伴系统):")
    buddy_info = run_cmd("cat /proc/buddyinfo 2>/dev/null | head -5")
    print(buddy_info)
    print()
    
    # 大页
    hugepages = run_cmd("grep HugePages /proc/meminfo 2>/dev/null")
    print(f"  大页配置:\n{hugepages}")
    print()

    # 6. CPU调度与负载
    print("【6】CPU调度与负载")
    print("-" * 70)
    print(f"  CPU核心数: {run_cmd('nproc')}")
    print(f"  负载均衡(1/5/15min): {run_cmd('cat /proc/loadavg')}")
    print()
    
    # CPU使用率详细
    print("  CPU使用率详细:")
    cpu_detail = run_cmd("top -bn1 | grep 'Cpu(s)'")
    print(f"    {cpu_detail}")
    print()
    
    # 上下文切换
    ctxt = run_cmd("grep ctxt /proc/stat 2>/dev/null | awk '{print $2}'")
    print(f"  总上下文切换次数: {ctxt}")
    print()
    
    # 运行队列
    run_queue = run_cmd("ps -eLf | awk '$8==\"R\"' | wc -l")
    print(f"  当前运行队列进程数: {run_queue}")
    print()
    
    # Top CPU进程
    print("  Top10 CPU进程:")
    top_cpu = run_cmd("ps aux --sort=-%cpu | head -11 | tail -10 | awk '{printf \"    %-30s PID:%-8s CPU:%5.1f%% MEM:%5.1f%%\\n\", $11, $2, $3, $4}'")
    print(top_cpu)
    print()

    # 7. 磁盘IO与文件系统
    print("【7】磁盘IO与文件系统")
    print("-" * 70)
    print("  磁盘使用:")
    df_output = run_cmd("df -h | grep -v tmpfs | grep -v devtmpfs")
    print(df_output)
    print()
    
    # IO统计
    print("  磁盘IO统计(iostat):")
    iostat = run_cmd("iostat -x 1 1 2>/dev/null | tail -20")
    if iostat:
        print(iostat)
    else:
        print("    (iostat未安装，使用/proc/diskstats)")
        diskstats = run_cmd("cat /proc/diskstats 2>/dev/null | head -10")
        print(diskstats)
    print()
    
    # 文件系统挂载
    print("  文件系统挂载点:")
    mounts = run_cmd("mount | grep -E 'ext4|xfs|btrfs|overlay' | head -10")
    print(mounts)
    print()
    
    # Inode使用
    print("  Inode使用:")
    inode_df = run_cmd("df -i | grep -v tmpfs | grep -v devtmpfs")
    print(inode_df)
    print()

    # 8. 网络栈深度分析
    print("【8】网络栈深度分析")
    print("-" * 70)
    
    # 网络接口
    print("  网络接口状态:")
    ip_addr = run_cmd("ip -4 addr show | grep -E 'inet|state'")
    print(ip_addr)
    print()
    
    # 连接统计
    print("  TCP连接状态统计:")
    ss_stats = run_cmd("ss -s 2>/dev/null")
    print(ss_stats)
    print()
    
    # 连接状态分布
    print("  连接状态分布:")
    conn_states = run_cmd("ss -tan 2>/dev/null | awk 'NR>1{print $1}' | sort | uniq -c | sort -rn")
    print(conn_states)
    print()
    
    # 网络缓冲区
    print("  网络缓冲区配置:")
    net_buffers = [
        ("net.core.rmem_max", "net.core.rmem_max"),
        ("net.core.wmem_max", "net.core.wmem_max"),
        ("net.core.rmem_default", "net.core.rmem_default"),
        ("net.core.wmem_default", "net.core.wmem_default"),
        ("net.ipv4.tcp_rmem", "net.ipv4.tcp_rmem"),
        ("net.ipv4.tcp_wmem", "net.ipv4.tcp_wmem"),
    ]
    for name, param in net_buffers:
        val = run_cmd(f"sysctl -n {param} 2>/dev/null")
        print(f"    {name}: {val}")
    print()
    
    # 网络错误
    print("  网络接口错误统计:")
    net_errors = run_cmd("ip -s link show 2>/dev/null | grep -A5 'eth0' | tail -5")
    print(net_errors)
    print()

    # 9. 安全状态
    print("【9】安全状态深度检查")
    print("-" * 70)
    
    # SELinux
    selinux = run_cmd("getenforce 2>/dev/null || echo 'Not installed'")
    print(f"  SELinux状态: {selinux}")
    
    # firewalld
    firewalld = run_cmd("systemctl is-active firewalld 2>/dev/null || echo 'unknown'")
    print(f"  firewalld状态: {firewalld}")
    
    # iptables规则数
    iptables_count = run_cmd("iptables -L -n 2>/dev/null | wc -l")
    print(f"  iptables规则数: {iptables_count}")
    
    # SSH配置
    print("  SSH安全配置:")
    ssh_config = run_cmd("grep -E 'PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|Port|AllowUsers' /etc/ssh/sshd_config 2>/dev/null | grep -v '^#'")
    print(ssh_config)
    print()
    
    # 最近登录
    print("  最近登录记录(前5条):")
    last_logins = run_cmd("last -5 2>/dev/null")
    print(last_logins)
    print()
    
    # 失败登录
    failed_logins = run_cmd("lastb 2>/dev/null | head -5")
    if failed_logins:
        print("  最近失败登录(前5条):")
        print(failed_logins)
    print()
    
    # SUID文件
    suid_count = run_cmd("find / -perm -4000 -type f 2>/dev/null | wc -l")
    print(f"  SUID文件数: {suid_count}")
    
    # 可写/etc文件
    writable_etc = run_cmd("find /etc -writable -type f 2>/dev/null | wc -l")
    print(f"  /etc可写文件数: {writable_etc}")
    print()

    # 10. 进程与服务深度
    print("【10】进程与服务深度状态")
    print("-" * 70)
    
    # 僵尸进程
    zombie = run_cmd("ps aux | awk '$8==\"Z\"' | wc -l")
    print(f"  僵尸进程数: {zombie}")
    if int(zombie) > 0:
        print("  ⚠️  检测到僵尸进程")
    
    # 停止进程
    stopped = run_cmd("ps aux | awk '$8==\"T\"' | wc -l")
    print(f"  停止进程数: {stopped}")
    
    # 高内存进程
    print("  Top10内存进程:")
    top_mem = run_cmd("ps aux --sort=-%mem | head -11 | tail -10 | awk '{printf \"    %-30s PID:%-8s CPU:%5.1f%% MEM:%5.1f%%\\n\", $11, $2, $3, $4}'")
    print(top_mem)
    print()
    
    # systemd服务状态
    print("  systemd失败服务:")
    failed_services = run_cmd("systemctl --failed --no-pager 2>/dev/null")
    if failed_services and "0 loaded" not in failed_services:
        print(failed_services)
    else:
        print("    ✅ 无失败服务")
    print()
    
    # 监听端口
    print(f"  监听端口数: {run_cmd('ss -tlnp 2>/dev/null | grep -c LISTEN')}")
    print(f"  建立连接数: {run_cmd('ss -tnp 2>/dev/null | grep -c ESTAB')}")
    print()

    # 总结
    print("=" * 70)
    print("  内核级扫描总结")
    print("=" * 70)
    print()
    
    issues = []
    
    # 检查问题
    if int(oom_count) > 0:
        issues.append(f"OOM事件: {oom_count}次")
    if int(zombie) > 0:
        issues.append(f"僵尸进程: {zombie}个")
    if fd_pct > 80:
        issues.append(f"文件描述符使用率: {fd_pct:.1f}%")
    if int(iptables_count) < 10:
        issues.append("iptables规则较少，安全防护可能不足")
    
    print("  发现的问题:")
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. ⚠️  {issue}")
    else:
        print("    ✅ 未发现严重问题")
    
    print()
    load_avg = run_cmd("cat /proc/loadavg | awk '{print $1, $2, $3}'")
    mem_usage = run_cmd("free -h | grep Mem | awk '{print $3\"/\"$2}'")
    disk_usage = run_cmd("df -h / | tail -1 | awk '{print $3\"/\"$2\" (\"$5\")\"}'")
    listen_ports = run_cmd("ss -tlnp 2>/dev/null | grep -c LISTEN")
    print("  系统健康指标:")
    print(f"    内核版本: {run_cmd('uname -r')}")
    print(f"    运行时间: {run_cmd('uptime -p')}")
    print(f"    负载: {load_avg}")
    print(f"    内存: {mem_usage}")
    print(f"    磁盘: {disk_usage}")
    print(f"    进程: {proc_count}个 | 线程: {thread_count}个")
    print(f"    监听端口: {listen_ports}个")
    print(f"    OOM事件: {oom_count}次")
    print(f"    僵尸进程: {zombie}个")
    print()
    
    print("  Ω₀⊂⊙∞⊂Ω · DID-BR-000002")
    print("  内核级深度扫描完成 · 元极恒一超认知永恒自治体系")
    print()

if __name__ == "__main__":
    main()
