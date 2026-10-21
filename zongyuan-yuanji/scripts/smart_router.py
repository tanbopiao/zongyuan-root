#!/usr/bin/env python3
# 智能路由：根据负载分任务
import subprocess, json

KERNELS = {
    18080: {"role":"chat","load":0},
    18083: {"role":"image","load":0},
    18084: {"role":"gov","load":0},
}

def check_load(port):
    try:
        r = subprocess.run(["curl","-sk",f"https://127.0.0.1:{port}/health","--max-time","2"],
                          capture_output=True,text=True)
        return 0 if "ok" in r.stdout else 1
    except:
        return 1

def route(req_type):
    best = None
    best_load = 999
    for port, info in KERNELS.items():
        if info["role"] == req_type:
            load = check_load(port)
            if load < best_load:
                best_load = load
                best = port
    return best

if __name__ == "__main__":
    print("chat →", route("chat"))
    print("image →", route("image"))
    print("gov →", route("gov"))
