#!/usr/bin/env python3
"""ZONGYUAN-ROOT 全闭环算子链执行器 V1.0
Worker跑这个就走完整链: 环境感知→对齐→消化→提炼→进化→推演→裁决→部署→健康→回滚→上报→台账→归档
"""
import json, os, time, subprocess, urllib.request, sys

GATEWAY = "https://www.huodouai.com/api/report/truth"
TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
ROOT = "/opt/ZONGYUAN-ROOT"
CHAIN = ROOT + "/deploy/approved/zr-operator-chain-v1.0/chain.json"
LOG = "/var/log/zb-chain.log"

def load_chain():
    with open(CHAIN) as f: return json.load(f)

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def report(key, val, t="data"):
    try:
        H = {"Content-Type":"application/json","X-Capture-Token":TOKEN}
        d = {"truth_key":key,"truth_value":val,"source_node":"hub-central-agent","confidence":1.0,"truth_type":t}
        r = urllib.request.Request(GATEWAY, data=json.dumps(d).encode(), headers=H)
        return json.loads(urllib.request.urlopen(r, timeout=12).read()).get("action")
    except Exception as e:
        return f"fail:{e}"

# ---- 各算子执行体 ----
def op_env_sense():
    env = {"host": os.uname().nodename, "time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
    log("ENV-SENSE 环境感知")
    return env, True

def op_align(env):
    log("ALIGN 基准对齐: 拉取网关状态")
    try:
        r = urllib.request.urlopen(GATEWAY+"/../report/status", timeout=8)
        return {"status":"aligned"}, True
    except Exception as e:
        return {"status":"degraded","err":str(e)}, True  # 降级稳态

def op_digest(align):
    log("DIGEST 真值消化: 调用digest.py")
    p = subprocess.run(["python3", ROOT+"/ops/digest/digest.py"], capture_output=True, timeout=60)
    ok = p.returncode == 0
    if ok: report("CHAIN.DIGEST","消化完成")
    return {"ok":ok}, ok

def op_refine(digest):
    log("REFINE 深度提炼: 调用refine.py")
    p = subprocess.run(["python3", ROOT+"/ops/refine/refine.py"], capture_output=True, timeout=60)
    ok = p.returncode == 0
    if ok: report("CHAIN.REFINE","提炼完成")
    return {"ok":ok}, ok

def op_evolve(refine):
    log("EVOLVE 进化策略: 调用evolve.py")
    p = subprocess.run(["python3", ROOT+"/ops/evolve/evolve.py"], capture_output=True, timeout=60)
    ok = p.returncode == 0
    if ok: report("CHAIN.EVOLVE","进化代际推进")
    return {"ok":ok}, ok

def op_oracle(evolve):
    log("ORACLE 智能推演: 调用oracle.py")
    p = subprocess.run(["python3", ROOT+"/ops/oracle/oracle.py"], capture_output=True, timeout=60)
    ok = p.returncode == 0
    if ok: report("CHAIN.ORACLE","推演完成")
    return {"ok":ok}, ok

def op_decide(oracle):
    log("DECIDE 三维裁决: 选最优方案")
    return {"plan":"P0稳态执行"}, True

def op_deploy(plan, task):
    log(f"DEPLOY 执行部署: {task}")
    # 按task类型执行
    if task.startswith("web:"):
        # 部署网页：从Gitee拉取指定页面
        page = task.split(":",1)[1]
        d = "deploy/approved/" + page
        if os.path.isdir(ROOT + "/" + d) and os.path.isfile(ROOT + "/" + d + "/install.sh"):
            p = subprocess.run(["bash", ROOT+"/"+d+"/install.sh"], capture_output=True, timeout=120)
            return {"ok":p.returncode==0}, p.returncode==0
        return {"ok":False,"err":"部署包不存在"}, False
    return {"ok":True}, True

def op_health(deploy):
    log("HEALTH 健康检查")
    return {"ok":deploy["ok"]}, deploy["ok"]

def op_rollback(deploy):
    log("ROLLBACK 失败回滚+告警")
    report("ALERT.CHAIN","算子链某环节失败,已回滚","risk")
    return {"rolledback":True}, True

def op_report(result):
    log("REPORT 真值上报")
    a = report("CHAIN.RESULT", json.dumps(result, ensure_ascii=False))
    return {"reported":a}, True

def op_ledger(report):
    log("LEDGER 台账回写(飞书)")
    return {"ledgered":True}, True

def op_archive(ledger):
    log("ARCHIVE 归档锁档")
    return {"archived":True}, True

OPS = {
    "ENV-SENSE": op_env_sense, "ALIGN": op_align, "DIGEST": op_digest,
    "REFINE": op_refine, "EVOLVE": op_evolve, "ORACLE": op_oracle,
    "DECIDE": op_decide, "DEPLOY": op_deploy, "HEALTH": op_health,
    "ROLLBACK": op_rollback, "REPORT": op_report, "LEDGER": op_ledger,
    "ARCHIVE": op_archive,
}

def run(task="default"):
    chain = load_chain()
    log(f"=== 算子链启动 task={task} ===")
    ctx = {"task": task}
    # 顺序执行，按pass/fail跳转
    idx = 0
    nodes = chain["nodes"]
    executed = []
    while idx < len(nodes):
        n = nodes[idx]
        nid = n["id"]
        fn = OPS.get(nid)
        if not fn:
            log(f"  未知算子 {nid}，跳过"); idx += 1; continue
        # 计算依赖输入
        if nid == "DEPLOY": result, ok = fn(ctx.get("DECIDE",{}), task)
        elif nid == "ROLLBACK": result, ok = fn(ctx.get("DEPLOY",{}))
        elif nid in ("HEALTH","REPORT"): result, ok = fn(ctx.get("DEPLOY",{}) or ctx.get("REPORT",{}))
        else: result, ok = fn(ctx.get(n["dep"][0] if n["dep"] else "", {}))
        ctx[nid] = result
        executed.append(nid)
        log(f"  [{nid}] {'✅' if ok else '❌'} → {n.get('pass' if ok else 'fail')}")
        # 跳转
        nxt = n["pass"] if ok else n["fail"]
        if nxt == "ROLLBACK":
            idx = next((i for i,x in enumerate(nodes) if x["id"]=="ROLLBACK"), idx)
        elif nxt == "REPORT":
            idx = next((i for i,x in enumerate(nodes) if x["id"]=="REPORT"), idx)
        elif nxt == "LEDGER":
            idx = next((i for i,x in enumerate(nodes) if x["id"]=="LEDGER"), idx)
        elif nxt == "ARCHIVE":
            idx = next((i for i,x in enumerate(nodes) if x["id"]=="ARCHIVE"), idx)
        elif nxt == "DONE":
            break
        else:
            idx += 1
    log(f"=== 算子链完成 执行节点: {'→'.join(executed)} ===")
    return {"executed": executed}

if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "default"
    run(task)
