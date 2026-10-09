import requests, subprocess, time, socket, json

CLOUD = "http://123.207.202.158:7860"
NODE_ID = f"AMD-GPU-{socket.gethostname()[-6:]}"

print(f"🧠 本地智能中枢已启动: {NODE_ID}", flush=True)
print(f"🔗 连接中枢: {CLOUD}", flush=True)

def heartbeat():
    """上报心跳"""
    try:
        requests.post(f"{CLOUD}/api/heartbeat", json={
            "node_id": NODE_ID,
            "status": "online",
            "gpu": "MI300X-192GB"
        }, timeout=5)
    except:
        pass

def run_task(cmd, task_id):
    """执行任务，失败自动重试1次"""
    for attempt in range(2):
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            requests.post(f"{CLOUD}/api/agent/result", json={
                "id": task_id,
                "stdout": res.stdout,
                "stderr": res.stderr
            }, timeout=5)
            return
        except Exception as e:
            if attempt == 0:
                print(f"⚠️ 任务失败，重试: {e}", flush=True)
                time.sleep(2)
            else:
                requests.post(f"{CLOUD}/api/agent/result", json={
                    "id": task_id,
                    "stdout": "",
                    "stderr": str(e)
                }, timeout=5)

# 主循环
while True:
    try:
        # 拉任务
        r = requests.get(f"{CLOUD}/api/agent/pull", timeout=5)
        if r.status_code == 200:
            d = r.json()
            print(f"📥 收到任务: {d['cmd'][:50]}", flush=True)
            run_task(d["cmd"], d["id"])
            heartbeat()
    except Exception as e:
        print(f"❌ 连接错误: {e}", flush=True)
    time.sleep(5)
