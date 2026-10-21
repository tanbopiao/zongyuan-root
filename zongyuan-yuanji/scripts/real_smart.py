#!/usr/bin/env python3
# 真智能调度：根据实时负载分配
import subprocess, json, time

def get_load(port):
    try:
        r = subprocess.run(["curl","-sk",f"https://127.0.0.1:{port}/health","--max-time","1"],
                          capture_output=True,text=True)
        return 0 if "ok" in r.stdout else 99
    except:
        return 99

def smart_route(req_type):
    # 按类型找候选，选负载最低的
    candidates = {
        "chat": [18080, 18082],
        "image": [18083],
        "gov": [18084],
    }
    best = None
    best_score = 999
    for port in candidates.get(req_type, [18080]):
        load = get_load(port)
        score = load
        if score < best_score:
            best_score = score
            best = port
    return best

if __name__ == "__main__":
    print("chat →", smart_route("chat"))
    print("image →", smart_route("image"))
    print("gov →", smart_route("gov"))
