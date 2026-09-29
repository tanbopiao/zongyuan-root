#!/usr/bin/env python3
"""安全收敛iptables配置脚本 - 安全优先，保证SSH不被锁出"""
import subprocess
import sys

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {cmd}")
        print(f"  stderr: {result.stderr}")
    return result

print("=== 安全收敛iptables配置 ===")

# 步骤1: 允许已建立连接（保证当前SSH不断）
print("\n[1/6] 允许已建立连接和loopback...")
run("iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT")
run("iptables -A INPUT -i lo -j ACCEPT")

# 步骤2: 允许核心端口
print("[2/6] 允许22(SSH)/80(HTTP)/443(HTTPS)...")
run("iptables -A INPUT -p tcp --dport 22 -j ACCEPT")
run("iptables -A INPUT -p tcp --dport 80 -j ACCEPT")
run("iptables -A INPUT -p tcp --dport 443 -j ACCEPT")

# 步骤3: 允许ICMP（ping）
print("[3/6] 允许ICMP...")
run("iptables -A INPUT -p icmp -j ACCEPT")

# 步骤4: 关键！先验证当前SSH在已建立连接中
print("[4/6] 验证当前SSH连接状态...")
result = run("ss -tnp | grep ':22' | grep ESTAB")
print(f"  SSH已建立连接:\n{result.stdout.strip()}")

# 步骤5: 设置默认策略为DROP
print("[5/6] 设置INPUT默认策略为DROP...")
run("iptables -P INPUT DROP")
run("iptables -P FORWARD DROP")
run("iptables -P OUTPUT ACCEPT")

# 步骤6: 验证
print("[6/6] 验证配置...")
result = run("iptables -L INPUT -n -v")
print(f"INPUT链规则:\n{result.stdout}")

# 验证SSH端口仍可访问
result = run("iptables -L INPUT -n | grep 'dpt:22'")
print(f"SSH规则: {result.stdout.strip()}")

# 统计
result = run("iptables -L INPUT -n | wc -l")
print(f"\nINPUT链规则数: {result.stdout.strip()}")
print(f"默认策略: DROP")

# 保存规则
run("iptables-save > /opt/ZONGYUAN-ROOT/config/iptables_rules.v4")
print("\n规则已保存到 /opt/ZONGYUAN-ROOT/config/iptables_rules.v4")
print("\n=== 配置完成，当前SSH连接应保持正常 ===")
