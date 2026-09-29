#!/usr/bin/env python3
"""
内部结构化优化扫描脚本
扫描：真值分类/crontab/端口/进程/目录结构
"""
import os
import sys
import json
import sqlite3
import subprocess
import socket
from datetime import datetime

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except:
        return ""

def main():
    print("=" * 60)
    print("  内部结构化优化 - 详细扫描报告")
    print("=" * 60)
    print(f"  扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 真值分类扫描
    print("【1】真值分类详细扫描")
    print("-" * 40)
    try:
        conn = sqlite3.connect("/opt/ZONGYUAN-ROOT/data/memory_gateway.db")
        c = conn.cursor()
        c.execute("SELECT category, COUNT(*) FROM truths GROUP BY category ORDER BY COUNT(*) DESC")
        print("  全部分类统计:")
        total = 0
        empty_count = 0
        for cat, count in c.fetchall():
            cat_name = cat if cat else "(空/NULL)"
            print(f"    {cat_name}: {count}条")
            total += count
            if not cat or cat == "" or cat == "unclassified":
                empty_count += count
        print(f"    总计: {total}条")
        print(f"    待分类(空+unclassified): {empty_count}条")
        
        print("\n  空分类真值示例(前5条):")
        c.execute("SELECT truth_key, substr(truth_value,1,60) FROM truths WHERE category IS NULL OR category = '' OR category = 'unclassified' LIMIT 5")
        for key, value in c.fetchall():
            print(f"    {key}: {value[:50]}...")
        conn.close()
    except Exception as e:
        print(f"  ❌ 真值扫描失败: {e}")
    print()

    # 2. crontab扫描
    print("【2】crontab详细扫描")
    print("-" * 40)
    cron_list = run_cmd("crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$'")
    cron_tasks = [line for line in cron_list.split("\n") if line.strip()]
    print(f"  总任务数: {len(cron_tasks)}")
    
    # 按频率统计
    every_min = sum(1 for t in cron_tasks if t.startswith("* *"))
    every_5 = sum(1 for t in cron_tasks if t.startswith("*/5"))
    every_30 = sum(1 for t in cron_tasks if t.startswith("*/30") or t.startswith("30 *") or t.startswith("0,30"))
    every_hour = sum(1 for t in cron_tasks if t.startswith("0 *"))
    print(f"    每分钟: {every_min}")
    print(f"    每5分钟: {every_5}")
    print(f"    每30分钟: {every_30}")
    print(f"    每小时: {every_hour}")
    print(f"    每天/每周: {len(cron_tasks) - every_min - every_5 - every_30 - every_hour}")
    
    # 检测重复任务
    print("\n  重复/相似任务检测(按脚本名):")
    script_names = []
    for task in cron_tasks:
        # 提取脚本名
        if ".py" in task:
            idx = task.find(".py")
            start = task.rfind("/", 0, idx) + 1
            script_names.append(task[start:idx+3])
        elif ".sh" in task:
            idx = task.find(".sh")
            start = task.rfind("/", 0, idx) + 1
            script_names.append(task[start:idx+3])
    from collections import Counter
    duplicates = {k: v for k, v in Counter(script_names).items() if v > 1}
    if duplicates:
        for name, count in duplicates.items():
            print(f"    ⚠️  {name}: 出现{count}次")
    else:
        print("    ✅ 无明显重复任务")
    print()

    # 3. 端口扫描
    print("【3】端口详细扫描")
    print("-" * 40)
    listen_ports = run_cmd("ss -tlnp 2>/dev/null | grep LISTEN")
    port_lines = [line for line in listen_ports.split("\n") if line.strip()]
    print(f"  监听端口总数: {len(port_lines)}")
    
    print("\n  公网暴露端口(0.0.0.0):")
    public_ports = run_cmd("ss -tlnp 2>/dev/null | grep '0.0.0.0' | awk '{print $4}'")
    for port in public_ports.split("\n"):
        if port.strip():
            print(f"    {port}")
    
    local_count = run_cmd("ss -tlnp 2>/dev/null | grep -c '127.0.0.1'")
    print(f"\n  仅本地监听端口数: {local_count}")
    print()

    # 4. 进程与内存扫描
    print("【4】进程与内存详细扫描")
    print("-" * 40)
    top_procs = run_cmd("ps aux --sort=-%mem | head -11 | tail -10 | awk '{printf \"%s (PID:%s CPU:%.1f%% MEM:%.1f%%)\\n\", $11, $2, $3, $4}'")
    print("  Top10内存进程:")
    print(top_procs)
    
    python_count = run_cmd("ps aux | grep -c '[p]ython3'")
    node_count = run_cmd("ps aux | grep -c '[n]ode'")
    nginx_count = run_cmd("ps aux | grep -c '[n]ginx'")
    print(f"  python3进程数: {python_count}")
    print(f"  node进程数: {node_count}")
    print(f"  nginx进程数: {nginx_count}")
    print()

    # 5. 目录结构扫描
    print("【5】目录结构扫描")
    print("-" * 40)
    print("  /opt/ZONGYUAN-ROOT 顶层目录:")
    zy_dirs = run_cmd("ls -la /opt/ZONGYUAN-ROOT/ 2>/dev/null | grep '^d' | awk '{print $9}'")
    for d in zy_dirs.split("\n"):
        if d.strip() and d not in [".", ".."]:
            size = run_cmd(f"du -sh /opt/ZONGYUAN-ROOT/{d} 2>/dev/null | awk '{{print $1}}'")
            print(f"    {d}/ ({size})")
    
    print("\n  /www/wwwroot/huodouai.com 顶层目录:")
    www_dirs = run_cmd("ls -la /www/wwwroot/huodouai.com/ 2>/dev/null | grep '^d' | awk '{print $9}'")
    for d in www_dirs.split("\n"):
        if d.strip() and d not in [".", ".."]:
            size = run_cmd(f"du -sh /www/wwwroot/huodouai.com/{d} 2>/dev/null | awk '{{print $1}}'")
            print(f"    {d}/ ({size})")
    
    print("\n  备份/归档目录:")
    backup_dirs = run_cmd("find /opt/ZONGYUAN-ROOT -maxdepth 2 -type d \\( -name '*backup*' -o -name '*archive*' -o -name '*bak*' \\) 2>/dev/null | head -10")
    for d in backup_dirs.split("\n"):
        if d.strip():
            size = run_cmd(f"du -sh '{d}' 2>/dev/null | awk '{{print $1}}'")
            print(f"    {d} ({size})")
    
    print("\n  日志目录大小:")
    log_size = run_cmd("du -sh /opt/ZONGYUAN-ROOT/logs/ 2>/dev/null | awk '{print $1}'")
    print(f"    /opt/ZONGYUAN-ROOT/logs/: {log_size}")
    var_log_size = run_cmd("du -sh /var/log/ 2>/dev/null | awk '{print $1}'")
    print(f"    /var/log/: {var_log_size}")
    print()

    # 6. 优化建议
    print("=" * 60)
    print("  内部结构化优化建议")
    print("=" * 60)
    print()
    print("  【真值分类优化】")
    print(f"    - 待分类真值: {empty_count}条 (空+unclassified)")
    print("    - 建议: 批量重新分类，按内容关键词自动归类")
    print()
    print("  【crontab精简】")
    print(f"    - 总任务数: {len(cron_tasks)}个")
    if duplicates:
        print(f"    - 重复任务: {len(duplicates)}个脚本重复")
        print("    - 建议: 合并重复任务，清理失效任务")
    else:
        print("    - 无明显重复，建议定期审计")
    print()
    print("  【端口安全】")
    print(f"    - 监听端口: {len(port_lines)}个")
    print(f"    - 公网暴露: {len(public_ports.split())}个")
    print("    - 建议: 非必要端口改为127.0.0.1监听，公网只暴露80/443")
    print()
    print("  【内存优化】")
    print(f"    - python3进程: {python_count}个")
    print("    - 建议: 检查高内存python进程，非核心服务按需启停")
    print()
    print("  【目录整理】")
    print("    - 建议: 清理旧备份/归档，日志轮转，空目录清理")
    print()
    print("  Ω₀⊂⊙∞⊂Ω · DID-BR-000002")
    print("  内部结构化优化扫描完成")
    print()

if __name__ == "__main__":
    main()
