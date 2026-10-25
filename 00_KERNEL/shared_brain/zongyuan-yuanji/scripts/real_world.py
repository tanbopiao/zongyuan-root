#!/usr/bin/env python3
# 真世界模型：预测动作后果
import subprocess, json, time

def get_state():
    """感知当前世界状态"""
    r = subprocess.run(["systemctl","is-active","yuanji-wrapper"],capture_output=True,text=True)
    return {"wrapper": r.stdout.strip(), "ts": int(time.time())}

def predict(action, state):
    """预测动作后果"""
    predictions = {
        "restart_wrapper": {"risk":"low","downtime_s":3,"success_prob":0.95},
        "edit_wrapper": {"risk":"high","downtime_s":30,"success_prob":0.7},
        "edit_nginx": {"risk":"critical","downtime_s":60,"success_prob":0.6},
        "add_kernel": {"risk":"low","downtime_s":0,"success_prob":0.99},
    }
    return predictions.get(action, {"risk":"unknown","success_prob":0.5})

# 当前状态
s = get_state()
print("当前状态:", s)
print()
# 推演几个动作
for action in ["restart_wrapper","edit_wrapper","edit_nginx","add_kernel"]:
    p = predict(action, s)
    print("动作: %-20s 风险: %-10s 成功率: %.0f%%" % (action, p["risk"], p["success_prob"]*100))
