#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地→云端进化供给执行器（META-EVOLUTION-FEDERATION-001）
用法:
  python3 evolution_feed.py --scan             # 扫描本地进化增量
  python3 evolution_feed.py --feed             # 打包提案→网关上报→写共享大脑高阶能力反哺表
  python3 evolution_feed.py --verify          # 回读吸收状态验收
增量源: var/experience/EXP-*.json / var/conflicts/*.json / var/arbitration/steady-*.json / meta-rules 新法则
"""
import json, os, sys, io, subprocess, datetime, glob

ZR = "/home/user/ZONGYUAN-ROOT"
HIST = f"{ZR}/var/evolution"
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TABLE_ID = "tblhzlcbjTfd8QAv"  # 高阶能力反哺
LEDGER = f"{HIST}/feed-ledger.jsonl"  # 供给留痕（append-only）
FINGERPRINT = "9b64a9c3c2475cf695ea6e2d"

def load_json(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def scan():
    items = []
    for p in sorted(glob.glob(f"{ZR}/var/experience/EXP-*.json")):
        d = load_json(p); items.append({"type": "经验教训", "id": d.get("id", os.path.basename(p)),
            "title": d.get("domain", "经验"), "desc": "；".join(d.get("lessons", []))[:300], "weight": 70})
    for p in sorted(glob.glob(f"{ZR}/var/conflicts/conflict-*.json")):
        d = load_json(p); items.append({"type": "冲突判例", "id": d.get("id", os.path.basename(p)),
            "title": d.get("id", "冲突"), "desc": f"{d.get('root_cause_final','')} → {d.get('resolution_final',[''])[0] if d.get('resolution_final') else ''}", "weight": 80})
    for p in sorted(glob.glob(f"{ZR}/var/arbitration/steady-*.json")):
        d = load_json(p); items.append({"type": "仲裁判例", "id": d.get("ts", os.path.basename(p)),
            "title": f"仲裁 {d.get('target','')}", "desc": f"本地USI={d.get('local',{}).get('usi')} 云端USI={d.get('cloud',{}).get('usi')} Δ={d.get('delta_usi')} → {d.get('verdict','')}", "weight": 75})
    for p in sorted(glob.glob(f"{ZR}/meta-rules/META-*.json")):
        d = load_json(p)
        if d.get("law_id") and d.get("version") == "v1.0":
            items.append({"type": "法则草案", "id": d.get("law_id", ""),
                "title": d.get("name", "")[:60], "desc": d.get("description", "")[:300], "weight": 90})
    # 去重：跳过已供给的
    fed = set()
    if os.path.exists(LEDGER):
        for line in io.open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                try: fed.add(json.loads(line).get("id"))
                except Exception: pass
    return [i for i in items if i["id"] not in fed]

def gateway_report(key, value):
    r = subprocess.run(["python3", f"{ZR}/scripts/gateway_report.py", key, json.dumps(value, ensure_ascii=False)],
                       capture_output=True, text=True, timeout=60)
    out = r.stdout + r.stderr
    return r.returncode == 0 and "truth_count" in out, out.strip()[-120:]

def feed():
    items = scan()
    if not items:
        print("[供给] 无可供给增量（全部已供给/无新增量）"); return
    os.makedirs(HIST, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    proposals = []
    for i in items:
        pid = f"EF-{ts}-{i['type'][:2]}-{i['id'][:20]}"
        p = {"proposal_id": pid, "type": i["type"], "id": i["id"], "title": i["title"],
             "desc": i["desc"], "suggested_action": "accept", "source_fingerprint": FINGERPRINT,
             "fed_at": ts}
        proposals.append(p)
        # 网关上报
        ok, detail = gateway_report(f"evolution.feed.{ts}.{i['type'][:2]}{i['id'][:16]}", p)
        p["gateway"] = "ok" if ok else detail
        # 留痕
        with io.open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps({**p, "gateway_ok": ok}, ensure_ascii=False) + "\n")
    # 写共享大脑高阶能力反哺表
    recs = [{"能力名称": f"[{p['type']}] {p['title']}", "权重": 80 if p["type"] == "法则草案" else 70,
             "反哺时间": datetime.datetime.now().strftime("%Y/%m/%d"), "吸收状态": "待吸收",
             "能力描述": f"{p['desc']} ｜ proposal_id={p['proposal_id']}", "来源节点": "NODE-DEV-DOUBAO-WORK-001"}
            for p in proposals]
    r = subprocess.run(["lark-cli", "base", "+record-batch-create", "--base-token", BASE_TOKEN,
                        "--table-id", TABLE_ID, "--json", json.dumps({"create_records": recs}, ensure_ascii=False), "--as", "user"],
                       capture_output=True, text=True, timeout=120)
    base_ok = r.returncode == 0 and '"ok": true' in r.stdout
    print(f"[供给] {len(proposals)} 项提案已上行（网关+共享大脑）｜ base={base_ok}")
    for p in proposals:
        print(f"  {p['proposal_id']} ｜ {p['type']} ｜ {p['title'][:40]} ｜ 网关={p['gateway']}")
    return proposals

if __name__ == "__main__":
    if "--scan" in sys.argv:
        items = scan()
        print(f"[扫描] {len(items)} 项未供给进化增量：")
        for i in items:
            print(f"  {i['type']} ｜ {i['id']} ｜ {i['title'][:40]}")
    elif "--feed" in sys.argv:
        feed()
    elif "--verify" in sys.argv:
        r = subprocess.run(["lark-cli", "base", "+record-list", "--base-token", BASE_TOKEN,
                            "--table-id", TABLE_ID, "--limit", "200", "--as", "user"], capture_output=True, text=True, timeout=120)
        print(r.stdout[:800] if r.returncode == 0 else r.stderr)
    else:
        print(__doc__)
