#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH临时接入管理
- 申请临时接入：自动放行IP 30分钟
- 查询当前放行列表
- 手动放行/取消放行
- 自动清理过期放行
"""
import os
import json
import time
import subprocess
from datetime import datetime

ACCESS_FILE = "/opt/ZONGYUAN-ROOT/data/ssh_controller/temp_access.json"

def load_access():
    try:
        if os.path.exists(ACCESS_FILE):
            with open(ACCESS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"granted": [], "history": []}

def save_access(data):
    try:
        os.makedirs(os.path.dirname(ACCESS_FILE), exist_ok=True)
        with open(ACCESS_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("保存失败:", e)

def grant_access(ip, duration_minutes=30, reason="", requested_by=""):
    data = load_access()
    for item in data["granted"]:
        if item["ip"] == ip and item["expires_at"] > time.time():
            return {"success": False, "message": "IP " + ip + " 已在放行列表中"}
    expires_at = time.time() + duration_minutes * 60
    access_item = {
        "ip": ip,
        "granted_at": time.time(),
        "expires_at": expires_at,
        "duration_minutes": duration_minutes,
        "reason": reason,
        "requested_by": requested_by,
        "status": "active",
    }
    data["granted"].append(access_item)
    data["history"].append(access_item)
    if len(data["history"]) > 100:
        data["history"] = data["history"][-100:]
    try:
        subprocess.run(
            ["iptables", "-I", "INPUT", "1", "-s", ip, "-p", "tcp", "--dport", "22", "-j", "ACCEPT"],
            capture_output=True, timeout=5
        )
    except Exception as e:
        print("iptables放行失败:", e)
    save_access(data)
    return {"success": True, "message": "IP " + ip + " 已放行 " + str(duration_minutes) + " 分钟"}

def revoke_access(ip):
    data = load_access()
    found = False
    for item in data["granted"]:
        if item["ip"] == ip:
            item["status"] = "revoked"
            found = True
            try:
                subprocess.run(
                    ["iptables", "-D", "INPUT", "-s", ip, "-p", "tcp", "--dport", "22", "-j", "ACCEPT"],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
    if found:
        data["granted"] = [x for x in data["granted"] if x["ip"] != ip]
        save_access(data)
        return {"success": True, "message": "IP " + ip + " 已取消放行"}
    return {"success": False, "message": "IP " + ip + " 不在放行列表中"}

def cleanup_expired():
    data = load_access()
    expired = []
    for item in data["granted"]:
        if item["expires_at"] < time.time():
            expired.append(item["ip"])
            try:
                subprocess.run(
                    ["iptables", "-D", "INPUT", "-s", item["ip"], "-p", "tcp", "--dport", "22", "-j", "ACCEPT"],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
    if expired:
        data["granted"] = [x for x in data["granted"] if x["ip"] not in expired]
        save_access(data)
        print("已清理过期放行:", expired)
    return expired

def list_active():
    data = load_access()
    return [x for x in data["granted"] if x["expires_at"] > time.time()]

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: ssh_temp_access.py [list|grant|revoke|cleanup]")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "list":
        active = list_active()
        print("当前放行IP:", len(active), "个")
        for item in active:
            remaining = int(item["expires_at"] - time.time())
            print("  -", item["ip"], "| 剩余", remaining//60, "分", remaining%60, "秒 |", item.get("reason",""))
    elif cmd == "grant":
        if len(sys.argv) < 3:
            print("用法: grant <ip> [minutes] [reason]")
            sys.exit(1)
        ip = sys.argv[2]
        minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        reason = sys.argv[4] if len(sys.argv) > 4 else ""
        result = grant_access(ip, minutes, reason, "central-brain")
        print(result["message"])
    elif cmd == "revoke":
        if len(sys.argv) < 3:
            print("用法: revoke <ip>")
            sys.exit(1)
        result = revoke_access(sys.argv[2])
        print(result["message"])
    elif cmd == "cleanup":
        expired = cleanup_expired()
        print("已清理", len(expired), "个过期放行")
