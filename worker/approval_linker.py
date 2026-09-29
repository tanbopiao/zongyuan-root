#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 审批监听→自动部署衔接器 V1.0 (开发节点侧)
功能: 轮询飞书审批(AIOS阶段验收) → 发现新APPROVED实例 → 解析工单 → 上报APPROVED.DEPLOY.PENDING信号
      → 云端中枢联动器自动部署 → 验证RESULT回写 → 记录已处理(防重复)
设计: 与云端 approval_deploy_linker.py 配对, 本节点负责"审批信号上报", 云端负责"实际部署执行"
铁律: 零成本 / 最小额度消耗 / 实事求是
"""
import json, os, subprocess, sys, time, urllib.request

GATEWAY = "https://www.huodouai.com/api/report/truth"
APPROVAL_CODE = "CAC2F6DD-B206-4F27-96FF-E99BD13464F7"
STATE_FILE = os.path.join(os.path.dirname(__file__), ".approval_linker_state.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "approval_linker.log")

def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    line = f"[{now_str()}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def lark(args, timeout=60):
    r = subprocess.run(["lark-cli", "approval"] + args + ["--as", "user"],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        return {"ok": False, "err": r.stderr.strip()[:200]}
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"ok": False, "err": r.stdout[:200]}

def report(key, val, t="protocol"):
    try:
        d = {"key": key, "truth_value": val, "source_node": "NODE-CLOUD-WORKER-001",
             "confidence": 1.0, "truth_type": t}
        req = urllib.request.Request(GATEWAY, data=json.dumps(d).encode(),
                                     headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return resp.get("action")
    except Exception as e:
        return f"fail:{e}"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)

def parse_form(form_str):
    """解析审批表单, 提取阶段名/验收项/成果链接"""
    try:
        form = json.loads(form_str) if isinstance(form_str, str) else form_str
        out = {}
        for w in form:
            name = w.get("name", "")
            val = w.get("value", "")
            if "阶段" in name or "阶段" in str(name):
                out["stage"] = val
            elif "验收" in name:
                out["acceptance"] = str(val)[:500]
            elif "成果" in name or "链接" in name:
                out["link"] = val
            elif "终审" in name:
                out["final_point"] = str(val)[:300]
        return out
    except Exception as e:
        return {"err": str(e)}

def get_approved_instances():
    """查询AIOS阶段验收已通过实例(最近10条)"""
    d = lark(["instances", "initiated", "--params",
              json.dumps({"approval_code": APPROVAL_CODE, "page_size": 10})])
    if not d.get("ok"):
        log(f"查询失败: {d.get('err')}")
        return []
    insts = d.get("data", {}).get("instances", [])
    approved = [i for i in insts if i.get("instance_status") in (2, 3) or i.get("instance_status") == 2]
    return approved

def handle_approved(inst, state):
    code = inst.get("instance_code")
    if code in state["processed"]:
        return "already-processed"
    # 取详情(拿status+表单)
    detail = lark(["instances", "get", "--params", json.dumps({"instance_code": code})])
    if not detail.get("ok"):
        log(f"详情获取失败 {code}: {detail.get('err')}")
        return "detail-fail"
    data = detail.get("data", {})
    status = data.get("status")
    if status != "APPROVED":
        return "not-approved"
    form = parse_form(data.get("form", ""))
    stage = form.get("stage", "未命名阶段")
    # 从成果链接推导部署包名(取路径最后一段)
    link = form.get("link", "")
    package = "auto-deploy"
    if link:
        seg = link.rstrip("/").split("/")[-1]
        if seg and "." not in seg and " " not in seg:
            package = seg
    signal = {
        "instance": code,
        "stage": stage,
        "package": package,
        "link": link,
        "approved_at": now_str()
    }
    key = f"APPROVED.DEPLOY.PENDING.{code[:8]}"
    val = json.dumps(signal, ensure_ascii=False)
    a = report(key, val, "decision")
    log(f"✅ 审批通过信号已上报 [{stage}] {code} → {a}")
    state["processed"].append(code)
    save_state(state)
    return "signal-sent"

def main():
    log("=== 审批监听→自动部署衔接器巡检 ===")
    state = load_state()
    approved = get_approved_instances()
    if not approved:
        log("无已通过审批实例, 跳过(最小额度消耗)")
        return
    done = 0
    for inst in approved:
        r = handle_approved(inst, state)
        if r == "signal-sent":
            done += 1
    log(f"巡检完成: 新信号 {done} 个, 累计处理 {len(state['processed'])} 个")

if __name__ == "__main__":
    main()
