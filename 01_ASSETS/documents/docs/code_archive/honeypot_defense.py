#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 蜜罐主动防御系统
- 假SSH服务监听2222端口
- 记录攻击者IP/时间/尝试的凭证
- 自动封禁攻击IP段（iptables DROP）
- 威胁情报写入9120
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import socket
import threading
import time
import json
import os
import subprocess
import urllib.request
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
LOG_FILE = os.path.join(BASE, "logs/honeypot.log")
BANNED_FILE = os.path.join(BASE, "data/honeypot_banned_ips.json")
HONEYPOT_PORT = 2222
BAN_THRESHOLD = 1  # 尝试1次即封禁

# 假SSH banner
SSH_BANNER = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5\r\n"

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write("[%s] %s\n" % (ts, msg))

def load_banned():
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE) as f:
            return json.load(f)
    return {"banned_ips": [], "total_attacks": 0}

def save_banned(data):
    os.makedirs(os.path.dirname(BANNED_FILE), exist_ok=True)
    with open(BANNED_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ban_ip(ip):
    """封禁IP（/24段）"""
    # 取/24段
    parts = ip.split('.')
    if len(parts) == 4:
        ip_range = "%s.%s.%s.0/24" % (parts[0], parts[1], parts[2])
    else:
        ip_range = ip
    
    try:
        # 检查是否已封禁
        result = subprocess.run(
            ["iptables", "-C", "INPUT", "-s", ip_range, "-j", "DROP"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            subprocess.run(
                ["iptables", "-I", "INPUT", "1", "-s", ip_range, "-j", "DROP"],
                capture_output=True
            )
            log("已封禁IP段: %s" % ip_range)
            return True
        return False
    except Exception as e:
        log("封禁失败 %s: %s" % (ip_range, e))
        return False

def report_to_gateway(ip, username, password, raw_data):
    """上报威胁情报到9120"""
    try:
        payload = {
            "key": "THREAT.IP.%s" % ip.replace(".", "_"),
            "value": json.dumps({
                "ip": ip,
                "first_seen": datetime.now().isoformat(),
                "attempted_user": username,
                "attempted_pass": password[:20] if password else "",
                "raw_data_len": len(raw_data),
                "action": "auto_banned",
                "source": "honeypot_2222"
            }, ensure_ascii=False),
            "category": "risk",
            "source": "honeypot",
            "did": "DID-BR-000002",
            "truth_type": "threat_intel",
            "confidence": 0.95
        }
        req = urllib.request.Request(
            "http://127.0.0.1:9120/api/truth/upsert",
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

def handle_client(conn, addr):
    """处理蜜罐连接"""
    ip = addr[0]
    log("蜜罐触发: %s:%d" % (ip, addr[1]))
    
    try:
        conn.settimeout(10)
        # 发送假SSH banner
        conn.send(SSH_BANNER.encode())
        
        # 接收数据（模拟SSH握手）
        raw_data = b""
        username = ""
        password = ""
        try:
            while len(raw_data) < 1024:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                raw_data += chunk
                # 简单提取可能的用户名密码（SSH协议初期是二进制，这里只做记录）
                if b"\x00" in chunk:
                    parts = chunk.split(b"\x00")
                    for p in parts:
                        if 3 < len(p) < 32 and all(32 <= b < 127 for b in p):
                            if not username:
                                username = p.decode('ascii', errors='ignore')
                            elif not password:
                                password = p.decode('ascii', errors='ignore')
        except:
            pass
        
        log("  凭证尝试: user=%s pass=%s 数据=%d字节" % (username, password, len(raw_data)))
        
        # 记录并封禁
        banned = load_banned()
        banned["total_attacks"] += 1
        if ip not in banned["banned_ips"]:
            banned["banned_ips"].append(ip)
        save_banned(banned)
        
        # 自动封禁
        ban_ip(ip)
        
        # 上报9120
        report_to_gateway(ip, username, password, raw_data)
        
        # 延迟响应（浪费攻击者时间）
        time.sleep(2)
        conn.send(b"Permission denied, please try again.\r\n")
        time.sleep(1)
        
    except Exception as e:
        log("  处理异常: %s" % e)
    finally:
        try:
            conn.close()
        except:
            pass

def main():
    log("=" * 50)
    log("蜜罐主动防御启动，监听端口 %d" % HONEYPOT_PORT)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", HONEYPOT_PORT))
    server.listen(10)
    
    while True:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.daemon = True
            t.start()
        except Exception as e:
            log("接受连接异常: %s" % e)
            time.sleep(1)

if __name__ == '__main__':
    main()
