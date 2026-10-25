#!/usr/bin/env python3
# 认知闭环：感知→预测→决策→执行→学习
import subprocess, time

def sense():
    # 感知
    r = subprocess.run(["free","-m"],capture_output=True,text=True).stdout
    mem = int(r.split("\n")[1].split()[2])
    return mem

def predict(mem):
    # 预测
    if mem > 2500: return "high"
    return "normal"

def decide(state):
    # 决策
    if state == "high":
        subprocess.run(["bash","-c","sync && echo 3 > /proc/sys/vm/drop_caches"])
        return "cleaned"
    return "noop"

if __name__ == "__main__":
    mem = sense()
    state = predict(mem)
    action = decide(state)
    print(f"感知={mem}MB 预测={state} 决策={action}")
