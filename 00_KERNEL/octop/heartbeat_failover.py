#!/usr/bin/env python3
"""
ZR内核 元运维心跳巡检 v2
由定时任务触发：云端主备+OCTOP桥接器全链路状态检测+自动切换+持续上报
纳入：OCTOP桥接器运行状态(登录/Agent/Provider/模型推理/真值上报)作为心跳的一部分
"""
import sys, os, time, json, urllib.request, urllib.error, socket
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone, timedelta
from zr_octop_bridge import (octop_login, get_token, octop_health,
    octop_list_agents, octop_list_providers, octop_chat, report_truth,
    check_cloud_connectivity, degraded_mode_check, OCTOP_BASE, CLOUD_TRUTH_MAIN,
    CLOUD_TRUTH_BACKUP, CAPTURE_TOKEN, DID, NODE_ID, TOKEN_CACHE)
from wear_sdk import wear_monitor, _report_error as wear_report_error, _report_healthy as wear_report_healthy

STATE_FILE = "/root/.octop/federation/failover_state.json"
CST = timezone(timedelta(hours=8))

# 元运维关键目录清单（OCTOP端执行运维任务时必须存在，缺失即报错找不到目录）
REQUIRED_DIRS = [
    os.path.expanduser("~/.octop"),
    os.path.expanduser("~/.octop/truth_queue"),
    os.path.expanduser("~/.octop/logs"),
    os.path.expanduser("~/.octop/snapshots"),
    "/root/.octop/federation",
]

def check_dirs():
    """元运维关键目录存在性自检：缺失自动创建并记录，返回检查结果"""
    result = {"total": len(REQUIRED_DIRS), "ok": 0, "missing": [], "created": [], "all_ok": True}
    for d in REQUIRED_DIRS:
        if os.path.isdir(d):
            result["ok"] += 1
        else:
            result["missing"].append(d)
            result["all_ok"] = False
            try:
                os.makedirs(d, exist_ok=True)
                result["created"].append(d)
                result["ok"] += 1
            except Exception as e:
                result["created"].append(f"{d}(创建失败:{e})")
    return result

def log(m): print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] {m}", flush=True)

def http_status(url, timeout=6):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e: return e.code
    except Exception: return 0

def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"failover_mode": False, "since": None, "recover": False}

def save_state(st):
    json.dump(st, open(STATE_FILE,"w"), ensure_ascii=False, indent=2)

def check_bridge():
    """OCTOP桥接器运行状态检测（心跳的一部分）"""
    st = {"login":False,"token_valid":False,"health":False,"agents":0,
          "providers":0,"model_infer":False,"token_cache":False}
    # token缓存
    st["token_cache"] = os.path.exists(TOKEN_CACHE)
    # 登录/刷新
    token = get_token()
    st["login"] = token is not None
    st["token_valid"] = token is not None
    # 健康
    h = octop_health()
    st["health"] = h is not None
    # agents/providers
    try:
        st["agents"] = len(octop_list_agents() or [])
    except: pass
    try:
        st["providers"] = len(octop_list_providers() or [])
    except: pass
    # 模型推理快检（GLM-4-Flash，超时保护）
    try:
        r = octop_chat("答：正常", model="GLM-4-Flash")
        st["model_infer"] = bool(r)
    except: st["model_infer"] = False
    return st

def main():
    log("=== ZR元运维心跳巡检 v2（含OCTOP桥接器状态+目录自检）===")
    state = load_state()

    # 0. 元运维关键目录自检（缺失自动创建，防止OCTOP端报找不到目录）
    dirs = check_dirs()
    if dirs["all_ok"]:
        log(f"📁 目录自检: {dirs['ok']}/{dirs['total']} 全部存在 ✅")
    else:
        log(f"📁 目录自检: 缺失{len(dirs['missing'])}个 → 已自动创建{len(dirs['created'])}个 ⚠️")
        for d in dirs["created"]:
            log(f"   自愈: {d}")
        # WEAR上报：目录缺失已自愈
        try:
            class _DirErr(Exception): pass
            wear_report_error(
                "heartbeat_failover", "cron",
                _DirErr(f"missing dirs: {','.join(dirs['missing'])}"),
                "dir_missing_self_healed",
                context={"missing": dirs["missing"], "created": dirs["created"]},
                self_heal_attempted=True,
                self_heal_result=(True, f"auto_created {len(dirs['created'])} dirs")
            )
        except Exception: pass

    # 1. 云端主备探测
    cloud_main = http_status(CLOUD_TRUTH_MAIN.replace("/api/report/truth","/api/status"))
    cloud_bak  = http_status(CLOUD_TRUTH_BACKUP.replace("/api/report/truth","/api/status"))
    cloud_ok = cloud_main == 200 or cloud_bak == 200
    log(f"云端: 主={cloud_main} 备={cloud_bak} → {'在线' if cloud_ok else '断联'}")

    # 2. OCTOP 桥接器全链路状态
    bridge = check_bridge()
    octop_ok = bridge["health"]
    log(f"OCTOP: 健康={'✅' if octop_ok else '❌'} 登录={'✅' if bridge['login'] else '❌'} "
        f"Agent={bridge['agents']} Provider={bridge['providers']} 模型推理={'✅' if bridge['model_infer'] else '❌'}")

    # 3. 判定切换
    ts = datetime.now(CST).isoformat()
    if cloud_ok:
        mode = "normal"
        action = "云端正常，无需切换"
        if state.get("failover_mode"):
            state = {"failover_mode":False,"since":None,"recover":True,"recover_ts":ts}
            action = "云端恢复，已切回主执行端"
        log(f"✅ {action}")
    elif octop_ok:
        mode = "failover"
        if not state.get("failover_mode"):
            state = {"failover_mode":True,"since":ts,"recover":False}
            action = "⚠️ 云端断联，OCTOP在线 → 已自动切换OCTOP执行端"
        else:
            action = f"⚠️ 持续降级中(自 {state.get('since','?')})，保持OCTOP执行端"
        log(action)
    else:
        mode = "offline"
        action = "🔴 云端+OCTOP均不可达，全离线（本地闭环）"
        log(action)

    # 4. 上报完整心跳真值（含桥接器运行状态+目录自检）
    truth = {"event":"heartbeat_metaops_v2","mode":mode,
             "cloud_main":cloud_main,"cloud_bak":cloud_bak,
             "octop_bridge":bridge, "dir_check":dirs, "state":state, "ts":ts,
             "did":DID, "node":NODE_ID,
             "ts_iso":datetime.now(CST).isoformat()}
    hb_key = f"HB.METAOPS.{datetime.now(CST).strftime('%Y%m%d-%H%M')}"
    r = report_truth(hb_key, truth)
    log(f"📤 心跳真值 {hb_key} → {'主备双通' if r else '上报异常'}")
    save_state(state)

    # WEAR健康上报（沉默≠正常）
    try:
        wear_report_healthy("heartbeat_failover", "cron",
                            context={"mode": mode, "cloud_ok": cloud_ok, "octop_ok": octop_ok})
    except Exception: pass

    # 5. 退出码
    return {"mode":mode,"state":state,"bridge":bridge}

if __name__ == "__main__":
    try:
        r = main()
        sys.exit(0 if r["mode"]=="normal" else (2 if r["mode"]=="failover" else 3))
    except Exception as exc:
        # 未预期异常 → WEAR自动捕获上报
        import traceback
        try:
            wear_report_error("heartbeat_failover", "cron", exc, traceback.format_exc(),
                              context={"fatal": True})
        except Exception: pass
        print(f"[WEAR] 致命异常已上报: {exc}", flush=True)
        sys.exit(3)
