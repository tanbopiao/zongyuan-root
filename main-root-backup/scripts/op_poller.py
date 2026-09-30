#!/usr/bin/env python3
"""
OP Poller V1.0 - 常驻后台算子轮询器
每60秒执行一轮算子链，不依赖对话窗口
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import subprocess, time, os, json
from datetime import datetime

BASE_DIR = "/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
LARK_BASE = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
NODE_TABLE = "tblOmIRJtTn2EsvM"
NODE_RECORD = "recvw432C1R4WV"
MSG_TABLE = "tbl4Dv798yO7u0IK"
IDLE_FILE = "/tmp/operator_idle_count.txt"
LOG_FILE = "/tmp/op_poller.log"

INTERVAL = 60  # 秒

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def run_cmd(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        return f"ERROR: {e}"

def step_task_runner():
    """步骤2：运行auto_task_runner.py"""
    out = run_cmd(f"python3 {BASE_DIR}/auto_task_runner.py", timeout=90)
    n = 0
    for line in out.split("\n"):
        if "自动执行" in line and "项" in line:
            try:
                n = int(line.split("自动执行")[1].split("项")[0].strip())
            except:
                pass
    log(f"任务runner: 执行{n}项")
    return n

def step_heartbeat():
    """步骤4：更新节点心跳"""
    now = datetime.now().isoformat()
    out = run_cmd(
        f'lark-cli base +record-upsert --base-token "{LARK_BASE}" --table-id "{NODE_TABLE}" '
        f'--as user --record-id "{NODE_RECORD}" '
        f'--json \'{{"当前状态":["在线"],"最后心跳时间":"{now}"}}\'',
        timeout=15
    )
    ok = '"ok": true' in out
    log(f"心跳更新: {'OK' if ok else 'FAIL'}")

def step_msg():
    """步骤5：发跨节点消息"""
    now = datetime.now().isoformat()
    ts = datetime.now().strftime("%m-%d %H:%M")
    out = run_cmd(
        f'lark-cli base +record-upsert --base-token "{LARK_BASE}" --table-id "{MSG_TABLE}" '
        f'--as user '
        f'--json \'{{"消息内容":"[{ts}]昆仑洞天算子轮询心跳","发送节点":"昆仑洞天","接收节点":"云端中枢","状态":"已送达","发送时间":"{now}"}}\'',
        timeout=15
    )
    ok = '"ok": true' in out
    log(f"跨节点消息: {'OK' if ok else 'FAIL'}")

def step_refiner():
    """步骤：高阶真值提炼（每5轮跑一次，节省资源）"""
    out = run_cmd(f"python3 {BASE_DIR}/auto_truth_refiner.py", timeout=60)
    log("真值提炼: done")

def main():
    log("=" * 50)
    log("OP Poller V1.0 启动 | 60秒轮询 | DID-BR-000002")
    log("=" * 50)
    
    round_num = 0
    while True:
        round_num += 1
        log(f"--- 第{round_num}轮 ---")
        
        try:
            n = step_task_runner()
            step_heartbeat()
            step_msg()
            
            # 每5轮跑一次真值提炼
            if round_num % 5 == 0:
                step_refiner()
            
            # 空转计数
            idle = int(open(IDLE_FILE).read().strip()) if os.path.exists(IDLE_FILE) else 0
            if n > 0:
                idle = 0
            else:
                idle += 1
            open(IDLE_FILE, "w").write(str(idle))
            log(f"空转计数: {idle}")
            
        except Exception as e:
            log(f"轮次异常: {e}")
        
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
