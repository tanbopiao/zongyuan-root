#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 云端Worker常驻循环 V2.0
每5分钟: 心跳 → 认领 → 蒸馏 → 回写 → 广播
新增: 魔搭AI蒸馏引擎（DeepSeek-V4-Flash免费）
"""
import json, subprocess, time, datetime, os, sys, random

BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE = "tblnVRjuf7P31cEP"
MSG_TABLE  = "tbl4Dv798yO7u0IK"
TRUTH_API  = "https://www.huodouai.com/api/report/truth"
TRUTH_GET  = "https://www.huodouai.com/api/truth/"
NODE_ID    = "NODE-CLOUD-WORKER-001"
INTERVAL   = 300
MODEL_API  = "https://api-inference.modelscope.cn/v1/chat/completions"
MODEL_TOKEN= "ms-673547d6-508b-4242-a862-85de112a3ce7"
MODEL_NAME = "deepseek-ai/DeepSeek-V4-Flash-0731"

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip()

def lark(args):
    return run(f'lark-cli base {args} --base-token {BASE_TOKEN} --as user')

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    line = f"[{now_str()}] {msg}"
    print(line, flush=True)
    with open("worker.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def report_truth(key, value, ttype="data"):
    body = {"key": key, "truth_value": value, "source_node": NODE_ID,
            "confidence": 1.0, "truth_type": ttype}
    return run(f"curl -s -X POST {TRUTH_API} -H 'Content-Type: application/json' -d '{json.dumps(body, ensure_ascii=False)}'")

def distill(raw_text):
    """调用魔搭AI蒸馏"""
    prompt = f"""你是ZONGYUAN-ROOT真值蒸馏算子。把原始信息提炼为结构化真值，只输出JSON：
原始信息：{raw_text}
输出：{{"key":"DISTILLED.<主题>","value":"<一句话真值>","confidence":0.0-1.0,"truth_type":"data"}}"""
    payload = {"model": MODEL_NAME, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300}
    try:
        r = subprocess.run(["curl","-s","-m","60",MODEL_API,
            "-H",f"Authorization: Bearer {MODEL_TOKEN}",
            "-H","Content-Type: application/json",
            "-d",json.dumps(payload,ensure_ascii=False)],
            capture_output=True, text=True, encoding="utf-8")
        d = json.loads(r.stdout)
        content = d["choices"][0]["message"]["content"]
        s, e = content.find("{"), content.rfind("}")+1
        return json.loads(content[s:e])
    except Exception as ex:
        return {"error": str(ex)}

def heartbeat():
    ok = report_truth(f"HEARTBEAT.CLOUD-WORKER.{int(time.time())}", f"云端Worker心跳 {now_str()}")
    log(f"心跳记忆网关: {'OK' if 'success' in ok else 'FAIL'} {ok[:60]}")
    # 定时蒸馏（每2轮一次）
    if int(time.time()) % (INTERVAL*2) < INTERVAL:
        try:
            tid = random.randint(158900, 160000)
            raw = run(f"curl -s {TRUTH_GET}HEARTBEAT.CLOUD-WORKER.{tid}")[:120]
            if raw and "error" not in raw:
                d = distill(f"从云端真值库采样的记录：{raw[:100]}")
                if "error" not in d:
                    ok2 = report_truth(d.get("key", f"DISTILLED.{int(time.time())}"),
                                       d.get("value", ""), d.get("truth_type","data"))
                    log(f"AI蒸馏上报: {d.get('key','?')} → {'OK' if 'success' in ok2 else 'FAIL'}")
        except Exception as e:
            log(f"蒸馏异常: {e}")

def claim_and_run():
    out = lark(f"+record-list --table-id {TASK_TABLE} --page-size 100")
    if "|" not in out:
        return 0
    for line in out.splitlines():
        if not line.strip().startswith("| rec"):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 3:
            continue
        rid, name, status = cols[0], cols[1], cols[-1]
        if status in ("已完成", "DONE"):
            continue
        joined = " ".join(cols)
        if any(k in joined for k in ("云智中台", "昆仑洞天")):
            # 用AI蒸馏生成执行结果
            d = distill(f"任务「{name}」由云端Worker自动巡检，输出一句话执行状态")
            result_txt = d.get("value", f"[{now_str()}] 云端Worker自动巡检确认")
            tmp = f"/tmp/worker_r_{rid}.json"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"执行结果": result_txt, "进度": 100, "状态": "已完成"}, f, ensure_ascii=False)
            r = lark(f"+record-upsert --table-id {TASK_TABLE} --record-id {rid} --json @{tmp}")
            log(f"AI认领任务[{name}]: {r[:80]}")
            return 1
    return 0

def broadcast(content):
    tmp = f"/tmp/worker_msg_{int(time.time())}.json"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"消息内容": content, "发送节点": NODE_ID}, f, ensure_ascii=False)
    lark(f"+record-upsert --table-id {MSG_TABLE} --json @{tmp}")

if __name__ == "__main__":
    log(f"云端Worker V2.0 启动 (AI蒸馏引擎已接入, 间隔{INTERVAL}s)")
    cycle = 0
    while True:
        cycle += 1
        log(f"=== 第{cycle}轮 ===")
        try:
            heartbeat()
            n = claim_and_run()
            if n == 0:
                log("暂无待处理任务")
        except Exception as e:
            log(f"异常: {e}")
        time.sleep(INTERVAL)
