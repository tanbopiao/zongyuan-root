#!/usr/bin/env python3
# 决策引擎：综合状态→自动决策
import subprocess, json

def get_state():
    r = subprocess.run(["free","-m"],capture_output=True,text=True).stdout
    mem = int(r.split("\n")[1].split()[2])
    r2 = subprocess.run(["df","-h","/"],capture_output=True,text=True).stdout
    disk = int(r2.split("\n")[1].split()[4].replace("%",""))
    return {"mem":mem,"disk":disk}

def decide(s):
    actions = []
    if s["mem"] > 2500:
        actions.append("清缓存")
    if s["disk"] > 85:
        actions.append("清日志")
    if not actions:
        actions.append("无事")
    return actions

if __name__ == "__main__":
    s = get_state()
    print("状态:", s)
    print("决策:", decide(s))
