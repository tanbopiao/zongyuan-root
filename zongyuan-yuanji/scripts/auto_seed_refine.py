#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN 全自动种子真值提炼上报机制 v1.1
锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
v1.1 增强：
  1. 自治自愈：检测内核挂 → systemctl start 对应服务 → 再采集（低风险自动修复）
  2. truth_count 对齐网关 ledger_lines（/api/status），不再用 sqlite COUNT(*)
"""
import json, time, subprocess, urllib.request, urllib.error

GATEWAY = "https://www.huodouai.com/api/report/truth"
STATUS = "https://www.huodouai.com/api/status"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
PORTS = [18080,18082,18083,18084,18085,18086,18087,18088,18089,18090,18091,18092,18093,18094]
SVC = {18080:"yuanji-wrapper", 18082:"yuanji-wrapper-backup", 18083:"yuanji-wrapper-image",
       18084:"yuanji-wrapper-gov", 18085:"yuanji-wrapper-orch", 18086:"yuanji-wrapper-mon",
       18087:"yuanji-wrapper-store", 18088:"yuanji-wrapper-sec"}
for p in range(18089, 18095): SVC[p] = f"yuanji-wrapper-{p}"
LOG = "/root/zongyuan-yuanji/var/seed-refine/seed-refine.log"

def sh(cmd, timeout=15):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""

def probe(port, timeout=3):
    try:
        r = json.loads(sh(f"curl -sk https://127.0.0.1:{port}/health --max-time {timeout}") or "{}")
        return bool(r.get("ok")), r.get("engine", "v9")
    except Exception:
        return False, "?"

def collect_capability():
    kernels = []
    healed = []
    for p in PORTS:
        ok, eng = probe(p)
        if not ok and p in SVC:
            # 自治自愈：systemctl 拉起一次
            sh(f"systemctl start {SVC[p]} 2>/dev/null")
            time.sleep(0.5)
            ok, eng = probe(p, 5)
            if ok: healed.append(p)
        kernels.append({"port": p, "ok": ok, "engine": eng, "service": SVC.get(p, "-")})
    mem = sh("free -m | head -2 | tail -1").split()
    df = sh("df -h / | tail -1").split()
    load = sh("cat /proc/loadavg").split()[:1]
    # truth_count 对齐网关 ledger_lines
    tc = "?"
    try:
        st = json.loads(urllib.request.urlopen(STATUS, timeout=8).read())
        tc = st.get("truth_count", st.get("data", {}).get("truth_count", "?"))
    except Exception:
        pass
    return {
        "kernels_online": sum(1 for k in kernels if k["ok"]),
        "kernels_total": len(PORTS),
        "kernel_detail": kernels,
        "healed_this_run": healed,
        "mem_used_mb": mem[2] if len(mem) > 2 else "?",
        "mem_total_mb": mem[1] if len(mem) > 1 else "?",
        "disk_used": df[4] if len(df) > 4 else "?",
        "load1": load[0] if load else "?",
        "truth_count": tc,
    }

def collect_work():
    cron_n = sh("crontab -l 2>/dev/null | grep -vc '^#'") or "0"
    try:
        import sqlite3
        con = sqlite3.connect("/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db")
        tickets = con.execute("SELECT COUNT(*) FROM truth WHERE key LIKE 'EVOLUTION.LOOP.TICKET%'").fetchone()[0]
        closed = con.execute("SELECT COUNT(*) FROM truth WHERE key LIKE '%CONSUME%' OR key LIKE '%CLOSED%'").fetchone()[0]
        work_items = con.execute("SELECT COUNT(*) FROM truth WHERE key LIKE 'WORK%' OR key LIKE 'TICKET%' OR key LIKE 'ISSUE%'").fetchone()[0]
        con.close()
    except Exception:
        tickets = closed = work_items = "?"
    return {"cron_jobs": cron_n, "tickets_total": tickets, "tickets_closed": closed,
            "work_items": work_items, "dispatch_mode": "cron+decision_engine(15min)+evolution_loop(hourly)"}

def report(key, value):
    v = dict(value)
    v["本体维度"] = "空间/时间/属性/因果/本体/维度D1-D4"
    v["锚定"] = ANCHOR; v["did"] = DID
    v["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    body = json.dumps({"key": key, "value": v}).encode()
    req = urllib.request.Request(GATEWAY, data=body, method="POST",
        headers={"X-DID": DID, "Content-Type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return r.get("ok"), r.get("truth_count", "?"), r.get("message", "")
    except urllib.error.HTTPError as e:
        return False, "?", "HTTP%d %s" % (e.code, e.read()[:100])
    except Exception as e:
        return False, "?", str(e)[:100]

def main():
    import os
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    cap = collect_capability()
    work = collect_work()
    cap_value = {"content": "能力数据快照:内核在线率%i/%i,异构(chat/image/gov),内存%si/%sMB,磁盘%s,负载%s,真值库%s条,自愈%s" % (
        cap["kernels_online"], cap["kernels_total"], cap["mem_used_mb"], cap["mem_total_mb"],
        cap["disk_used"], cap["load1"], cap["truth_count"], cap["healed_this_run"] or "无"),
        "kernels": cap["kernel_detail"], "kernels_online": cap["kernels_online"],
        "kernels_total": cap["kernels_total"], "healed": cap["healed_this_run"],
        "mem_used_mb": cap["mem_used_mb"], "mem_total_mb": cap["mem_total_mb"],
        "disk_used": cap["disk_used"], "load1": cap["load1"], "truth_count": cap["truth_count"]}
    work_value = {"content": "工单调度快照:cron任务%s个,进化工单%s,已闭环%s,工作项%s,调度=cron+决策引擎15min+进化循环hourly" % (
        work["cron_jobs"], work["tickets_total"], work["tickets_closed"], work["work_items"]),
        "cron_jobs": work["cron_jobs"], "tickets_total": work["tickets_total"],
        "tickets_closed": work["tickets_closed"], "work_items": work["work_items"],
        "dispatch_mode": work["dispatch_mode"]}
    r1 = report("REPORT.cap.metrics", cap_value)
    r2 = report("REPORT.work.status", work_value)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "cap": r1, "work": r2, "online": "%i/%i" % (cap["kernels_online"], cap["kernels_total"]), "healed": cap["healed_this_run"]}, ensure_ascii=False) + "\n")
    print("cap:", "✅" if r1[0] else "❌", r1[1], "| work:", "✅" if r2[0] else "❌", r2[1], "| online:", "%i/%i" % (cap["kernels_online"], cap["kernels_total"]), "| healed:", cap["healed_this_run"] or "无")
    return 0 if r1[0] and r2[0] else 1

if __name__ == "__main__":
    raise SystemExit(main())
