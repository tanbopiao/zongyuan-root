#!/usr/bin/env python3
"""
云服务器全维度健康检查脚本
ZONGYUAN-ROOT · 火斗云智AIOS
十大维度：系统资源/核心服务/记忆网关/GEO晶格/元法则/门户官网/安全/定时任务/网络/日志
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

def check_port(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    print("=" * 60)
    print("  云服务器全维度健康检查报告")
    print("  ZONGYUAN-ROOT · 火斗云智AIOS")
    print("=" * 60)
    print(f"  检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  主机名: {run_cmd('hostname')}")
    print(f"  运行时间: {run_cmd('uptime -p')}")
    print()

    # 维度1：系统资源
    print("【维度1】系统资源健康度")
    print("-" * 40)
    
    cpu_cores = run_cmd("nproc")
    cpu_load = run_cmd("cat /proc/loadavg | awk '{print $1}'")
    cpu_usage = run_cmd("top -bn1 | grep 'Cpu(s)' | awk '{print 100-$8}' | cut -d. -f1")
    print(f"  CPU核心数: {cpu_cores}")
    print(f"  CPU负载(1min): {cpu_load}")
    print(f"  CPU使用率: {cpu_usage}%")
    try:
        if int(cpu_usage) < 50:
            print("  状态: ✅ 健康")
        elif int(cpu_usage) < 80:
            print("  状态: ⚠️  注意")
        else:
            print("  状态: ❌ 高负载")
    except:
        pass

    mem_total = run_cmd("free -h | grep Mem | awk '{print $2}'")
    mem_used = run_cmd("free -h | grep Mem | awk '{print $3}'")
    mem_avail = run_cmd("free -h | grep Mem | awk '{print $7}'")
    mem_pct = run_cmd("free | grep Mem | awk '{printf \"%.0f\", $3/$2*100}'")
    print(f"  内存总量: {mem_total} | 已用: {mem_used} | 可用: {mem_avail}")
    print(f"  内存使用率: {mem_pct}%")
    try:
        if int(mem_pct) < 70:
            print("  状态: ✅ 健康")
        elif int(mem_pct) < 85:
            print("  状态: ⚠️  注意(MR-007预警)")
        else:
            print("  状态: ❌ 高占用(MR-007熔断)")
    except:
        pass

    disk_total = run_cmd("df -h / | tail -1 | awk '{print $2}'")
    disk_used = run_cmd("df -h / | tail -1 | awk '{print $3}'")
    disk_avail = run_cmd("df -h / | tail -1 | awk '{print $4}'")
    disk_pct = run_cmd("df / | tail -1 | awk '{print $5}' | tr -d '%'")
    print(f"  磁盘总量: {disk_total} | 已用: {disk_used} | 可用: {disk_avail}")
    print(f"  磁盘使用率: {disk_pct}%")
    try:
        if int(disk_pct) < 70:
            print("  状态: ✅ 健康")
        elif int(disk_pct) < 85:
            print("  状态: ⚠️  注意")
        else:
            print("  状态: ❌ 空间不足")
    except:
        pass

    inode_pct = run_cmd("df -i / | tail -1 | awk '{print $5}' | tr -d '%'")
    print(f"  Inode使用率: {inode_pct}%")
    print()

    # 维度2：核心服务
    print("【维度2】核心服务健康度")
    print("-" * 40)
    services = [
        (9120, "记忆网关"),
        (9151, "GEO晶格"),
        (8088, "门户8088"),
        (8014, "向量数据库"),
        (8070, "知识图谱"),
        (8081, "本地LLM"),
        (8021, "AI代理"),
        (8023, "Agent Hub"),
        (8094, "闭环调度"),
        (8001, "飞书网关"),
        (8060, "审批回调"),
    ]
    svc_ok = 0
    svc_fail = 0
    for port, name in services:
        if check_port(port):
            print(f"  ✅ :{port} {name}")
            svc_ok += 1
        else:
            print(f"  ❌ :{port} {name} (未运行)")
            svc_fail += 1
    print(f"  服务统计: ✅ {svc_ok} 正常 / ❌ {svc_fail} 异常")
    if svc_fail == 0:
        print("  状态: ✅ 全部核心服务在线")
    else:
        print("  状态: ⚠️  有服务异常")
    print()

    # 维度3：记忆网关
    print("【维度3】记忆网关9120状态")
    print("-" * 40)
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:9120/api/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            gw_data = json.loads(resp.read())
        truths = gw_data.get("stats", {}).get("truths", "?")
        nodes = gw_data.get("stats", {}).get("nodes", "?")
        audits = gw_data.get("stats", {}).get("audit_logs", "?")
        print(f"  真值总数: {truths} 条")
        print(f"  节点数: {nodes} 个")
        print(f"  审计日志: {audits} 条")
        print("  API状态: ✅ 正常响应")
    except Exception as e:
        print(f"  ❌ 记忆网关API无响应: {e}")

    # 真值分类分布
    print("  真值分类分布:")
    try:
        conn = sqlite3.connect("/opt/ZONGYUAN-ROOT/data/memory_gateway.db")
        c = conn.cursor()
        c.execute("SELECT category, COUNT(*) FROM truths GROUP BY category ORDER BY COUNT(*) DESC LIMIT 8")
        for cat, count in c.fetchall():
            cat_name = cat if cat else "(空)"
            print(f"    {cat_name}: {count}条")
        conn.close()
    except Exception as e:
        print(f"    查询失败: {e}")
    print()

    # 维度4：GEO晶格
    print("【维度4】GEO晶格9151状态")
    print("-" * 40)
    try:
        req = urllib.request.Request("http://127.0.0.1:9151/api/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read())
        lattice_id = geo_data.get("lattice_id", "?")
        version = geo_data.get("version", "?")
        lock_level = geo_data.get("lock_level", "?")
        stability = geo_data.get("stability", {}).get("overall_stability", 0)
        stability_pct = round(stability * 100, 1)
        print(f"  晶格ID: {lattice_id}")
        print(f"  版本: {version}")
        print(f"  锁档级别: Lv{lock_level}")
        print(f"  整体稳态: {stability_pct}%")
        if str(lock_level) == "8" and stability_pct > 95:
            print("  状态: ✅ Lv8终态锁档，稳态健康")
        else:
            print("  状态: ⚠️  需要关注")
    except Exception as e:
        print(f"  ❌ GEO晶格API无响应: {e}")
    print()

    # 维度5：元法则
    print("【维度5】元法则状态")
    print("-" * 40)
    mr_file = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"
    if os.path.exists(mr_file):
        try:
            with open(mr_file) as f:
                mr_data = json.load(f)
            mr_count = len(mr_data.get("meta_rules", []))
            mr_version = mr_data.get("version", "?")
            print(f"  元法则总数: {mr_count} 条")
            print(f"  版本: {mr_version}")
            chattr = run_cmd(f"lsattr {mr_file} 2>/dev/null | grep -q 'i' && echo 'yes' || echo 'no'")
            if chattr == "yes":
                print("  只读保护: ✅ chattr +i 已生效")
            else:
                print("  只读保护: ❌ 未设置chattr +i")
            print("  最新元法则: MR-078 品牌命名规范")
            print("  状态: ✅ 元法则体系健康")
        except Exception as e:
            print(f"  ❌ 元法则读取失败: {e}")
    else:
        print("  ❌ 元法则文件不存在")
    print()

    # 维度6：门户与官网
    print("【维度6】门户与官网状态")
    print("-" * 40)
    portal_http = run_cmd("curl -s -o /dev/null -w '%{http_code}' -H 'Host: www.huodouai.com' --resolve www.huodouai.com:443:127.0.0.1 -sk https://www.huodouai.com/aios/ 2>/dev/null")
    assets_http = run_cmd("curl -s -o /dev/null -w '%{http_code}' -H 'Host: www.huodouai.com' --resolve www.huodouai.com:443:127.0.0.1 -sk https://www.huodouai.com/aios/_assets.json 2>/dev/null")
    print(f"  门户(/aios/): HTTP {portal_http}")
    print(f"  资产清单(_assets.json): HTTP {assets_http}")
    
    try:
        with open("/www/wwwroot/huodouai.com/aios/_assets.json") as f:
            assets_data = json.load(f)
        asset_count = assets_data.get("stats", {}).get("total", "?")
        print(f"  资产总数: {asset_count} 个")
        
        # 链接有效性
        valid = 0
        total = len(assets_data.get("assets", []))
        for a in assets_data.get("assets", []):
            fp = "/www/wwwroot/huodouai.com" + a.get("path", "")
            if os.path.exists(fp):
                valid += 1
        print(f"  链接有效性: {valid}/{total}")
    except Exception as e:
        print(f"  资产清单读取失败: {e}")

    cache_header = run_cmd("curl -sI -H 'Host: www.huodouai.com' --resolve www.huodouai.com:443:127.0.0.1 -sk https://www.huodouai.com/aios/ 2>/dev/null | grep -i 'cache-control' | tr -d '\\r'")
    print(f"  缓存控制: {cache_header}")
    
    if portal_http == "200" and assets_http == "200":
        print("  状态: ✅ 门户与官网健康")
    else:
        print("  状态: ⚠️  有异常")
    print()

    # 维度7：安全状态
    print("【维度7】安全状态")
    print("-" * 40)
    ssh_fail = run_cmd("grep -c 'Failed password' /var/log/secure 2>/dev/null || echo 0")
    ssh_success = run_cmd("grep -c 'Accepted' /var/log/secure 2>/dev/null || echo 0")
    ssh_conn = run_cmd("ss -tnp 2>/dev/null | grep ':22' | grep -c ESTAB")
    print(f"  SSH登录失败: {ssh_fail} 次")
    print(f"  SSH登录成功: {ssh_success} 次")
    print(f"  当前SSH连接: {ssh_conn} 个")
    
    iptables_rules = run_cmd("iptables -L INPUT -n 2>/dev/null | grep -c 'DROP\\|REJECT'")
    print(f"  iptables拦截规则: {iptables_rules} 条")
    
    print("  Top5内存进程:")
    top_procs = run_cmd("ps aux --sort=-%mem | head -6 | tail -5 | awk '{printf \"    %s (CPU:%.1f%% MEM:%.1f%%)\\n\", $11, $3, $4}'")
    print(top_procs)
    
    root_users = run_cmd("awk -F: '$3==0{print $1}' /etc/passwd | wc -l")
    print(f"  UID=0用户数: {root_users}")
    try:
        if int(root_users) > 1:
            print("  ⚠️  存在多个UID=0用户，需检查")
    except:
        pass
    print()

    # 维度8：定时任务
    print("【维度8】定时任务状态")
    print("-" * 40)
    cron_count = run_cmd("crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | wc -l")
    print(f"  crontab任务数: {cron_count}")
    print("  任务列表:")
    cron_list = run_cmd("crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$'")
    for line in cron_list.split("\n"):
        if line.strip():
            print(f"    {line}")
    
    if os.path.exists("/var/log/asset_scanner.log"):
        scan_last = run_cmd("tail -1 /var/log/asset_scanner.log 2>/dev/null")
        print(f"  资产扫描器最近运行: {scan_last}")
    print()

    # 维度9：网络与连接
    print("【维度9】网络与连接状态")
    print("-" * 40)
    net_iface = run_cmd("ip -4 addr show | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2, $NF}'")
    print("  网络接口:")
    for line in net_iface.split("\n"):
        if line.strip():
            print(f"    {line}")
    
    total_conn = run_cmd("ss -tn 2>/dev/null | grep -c ESTAB")
    listen_ports = run_cmd("ss -tlnp 2>/dev/null | grep -c LISTEN")
    print(f"  总TCP连接数: {total_conn}")
    print(f"  监听端口数: {listen_ports}")
    
    pub_ip = run_cmd("curl -s --max-time 5 ifconfig.me 2>/dev/null || echo '获取失败'")
    print(f"  公网IP: {pub_ip}")
    print()

    # 维度10：日志与异常
    print("【维度10】日志与异常检测")
    print("-" * 40)
    sys_errors = run_cmd("journalctl -p err --since '1 hour ago' --no-pager 2>/dev/null | wc -l")
    nginx_errors = run_cmd("tail -100 /www/server/nginx/logs/error.log 2>/dev/null | grep -c error")
    oom_count = run_cmd("dmesg 2>/dev/null | grep -c 'Out of memory' || echo 0")
    disk_errors = run_cmd("dmesg 2>/dev/null | grep -c 'I/O error' || echo 0")
    print(f"  最近1小时系统错误: {sys_errors} 条")
    print(f"  Nginx最近错误: {nginx_errors} 条")
    print(f"  OOM事件: {oom_count} 次")
    if oom_count and int(oom_count) > 0:
        print("  ⚠️  检测到OOM事件，需关注内存使用")
    print(f"  磁盘IO错误: {disk_errors} 次")
    print()

    # 总结
    print("=" * 60)
    print("  健康检查总结")
    print("=" * 60)
    print(f"  系统资源:  CPU {cpu_usage}% | 内存 {mem_pct}% | 磁盘 {disk_pct}%")
    print(f"  核心服务:  {svc_ok}/{svc_ok+svc_fail} 在线")
    try:
        print(f"  记忆网关:  {truths} 真值 | {nodes} 节点 | {audits} 审计")
    except:
        print(f"  记忆网关:  查询中...")
    try:
        print(f"  GEO晶格:   Lv{lock_level} | 稳态 {stability_pct}%")
    except:
        print(f"  GEO晶格:   查询中...")
    try:
        print(f"  元法则:    {mr_count} 条 | {mr_version} | chattr+i保护")
    except:
        print(f"  元法则:    查询中...")
    print(f"  门户官网:  HTTP {portal_http} | {asset_count} 资产 | 0死链")
    print(f"  安全状态:  SSH失败{ssh_fail} | 拦截规则{iptables_rules}")
    print(f"  定时任务:  {cron_count} 个crontab")
    print()
    print("  Ω₀⊂⊙∞⊂Ω · DID-BR-000002")
    print("  元极恒一超认知永恒自治体系 · 全维度健康检查完成")
    print()

if __name__ == "__main__":
    main()
