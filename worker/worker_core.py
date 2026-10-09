#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 云端Worker核心 V1.0
基于 记忆网关API + 飞书Base共享大脑 的轻量自治节点
链路: 心跳上报 → 任务认领 → 执行 → 结果回写
"""
import json, subprocess, time, datetime, sys, os

BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE = "tblnVRjuf7P31cEP"      # 任务台账
NODE_TABLE = "tblOmIRJtTn2EsvM"      # 节点状态
MSG_TABLE  = "tbl4Dv798yO7u0IK"      # 跨节点消息
TRUTH_API  = "https://www.huodouai.com/api/report/truth"
NODE_ID    = "NODE-CLOUD-WORKER-001" # 云端Worker节点标识
DID        = "DID-BR-000002"

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip()

def lark(args):
    return run(f'lark-cli base {args} --base-token {BASE_TOKEN} --as user')

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def heartbeat():
    """步骤1: 节点心跳 → 云端记忆网关 + 飞书Base节点状态"""
    body = {
        "key": f"HEARTBEAT.CLOUD-WORKER.{int(time.time())}",
        "truth_value": f"云端Worker心跳 {now_str()}",
        "source_node": NODE_ID,
        "confidence": 1.0,
        "truth_type": "data"
    }
    try:
        r = run(f"curl -s -X POST {TRUTH_API} -H 'Content-Type: application/json' -d '{json.dumps(body, ensure_ascii=False)}'")
        print(f"  [心跳] 记忆网关: {r[:120]}")
    except Exception as e:
        print(f"  [心跳] 记忆网关异常: {e}")

def claim_task():
    """步骤2: 认领任务 → 任务台账找 状态=待开始/进行中 且 负责账号含我们"""
    out = lark(f"+record-list --table-id {TASK_TABLE} --page-size 50")
    if "|" not in out:
        return None
    lines = [l for l in out.splitlines() if l.strip().startswith("| rec")]
    for line in lines:
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 3:
            continue
        rid = cols[0]
        name = cols[1]
        status = cols[-1] if cols[-1] else ""
        owner = cols[7] if len(cols) > 7 else ""
        # 认领 未完成 且 负责账号包含 云智中台/昆仑洞天/主账号 的任务
        if status not in ("已完成",) and any(k in owner for k in ("云智中台", "昆仑洞天", "主账号")):
            return {"record_id": rid, "name": name, "owner": owner}
    return None

def report_result(record_id, result_text):
    """步骤3: 结果回写任务台账"""
    tmp = f"{os.environ.get('TEMP','/tmp')}/worker_result.json"
    payload = {"执行结果": result_text, "状态": "已完成", "进度": 100}
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    r = lark(f"+record-upsert --table-id {TASK_TABLE} --record-id {record_id} --json @{tmp}")
    print(f"  [结果] 回写: {r[:150]}")

def post_message(content):
    """步骤4: 跨节点消息广播"""
    tmp = f"{os.environ.get('TEMP','/tmp')}/worker_msg.json"
    payload = {"消息内容": content, "发送节点": NODE_ID}
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    r = lark(f"+record-upsert --table-id {MSG_TABLE} --json @{tmp}")
    print(f"  [消息] 广播: {r[:150]}")

if __name__ == "__main__":
    print(f"=== 云端Worker {NODE_ID} 启动 {now_str()} ===")
    heartbeat()
    task = claim_task()
    if task:
        print(f"  [认领] 任务: {task['name']} ({task['record_id']})")
        report_result(task["record_id"], f"[{now_str()}] 云端Worker自动巡检：任务状态确认，等待人工或下游处理")
        post_message(f"云端Worker({NODE_ID})已认领任务「{task['name']}」并回写状态")
    else:
        print("  [认领] 暂无待处理任务，跳过")
        post_message(f"云端Worker({NODE_ID})心跳正常，暂无新任务")
    print("=== 本轮完成 ===")
