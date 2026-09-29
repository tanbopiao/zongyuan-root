#!/usr/bin/env python3
"""
体系真值批量上报引擎 batch_report.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
功能: 把本地元宪法/元规则/核心元法则提炼成真值, 批量上报云端中枢
目的: 云端真值库从"运行经验"升级为"完整体系规则"(统摄根基)
真实部署: 真实读取体系文件, 提炼, 逐条上报, 本地留痕
"""
import os, sys, json, glob, time, hashlib, argparse, urllib.request

PRJ = "/home/user/Doubao/chats/38418284746129666"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VERSION = "BATCH-REPORT-V1.0"
CENTRAL_URL = "https://drama.huodouai.com"
TOKEN = "ZR-CAPTURE-2026-OMEGA-666b43e342a6b57ee54742f58d3e3fcd"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

DIRS = {
    "constitution": PRJ + "/00_KERNEL/constitution",
    "metarules": PRJ + "/00_KERNEL/metarules",
    "metalaws": PRJ + "/00_KERNEL/metalaws",
}

# ---------- 提炼: 从体系文件生成真值条目 ----------
def extract(cat):
    entries = []
    d = DIRS[cat]
    if not os.path.isdir(d): return entries
    for f in sorted(glob.glob(d + "/*.json")):
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict): continue
        base_id = doc.get("constitution_id") or doc.get("rule_id") or doc.get("law_id") or os.path.basename(f).replace(".json", "")
        # constitution/metalaws: clauses/律条
        for cl in doc.get("clauses", []):
            if isinstance(cl, dict):
                entries.append({"cat": cat, "src": base_id, "key": f"truth.{cat}.{base_id}.{cl.get('article','')}",
                                "value": cl.get("rule", ""), "level": doc.get("level", cat)})
        # metarules: rule本体 + channels
        if doc.get("rule"):
            entries.append({"cat": cat, "src": base_id, "key": f"truth.{cat}.{base_id}.rule",
                            "value": doc["rule"], "level": doc.get("level", "元规则")})
        for ch in doc.get("channels", []):
            if isinstance(ch, dict) and ch.get("channel"):
                entries.append({"cat": cat, "src": base_id, "key": f"truth.{cat}.{base_id}.{ch['channel']}",
                                "value": f"{ch['channel']}: {ch.get('action','')}", "level": "元规则通道"})
    # metalaws 另加 md 文件标题级提炼
    if cat == "metalaws":
        for f in sorted(glob.glob(d + "/*.md")):
            name = os.path.basename(f).replace(".md", "")
            entries.append({"cat": "metalaws", "src": name, "key": f"truth.metalaws.{name[:40]}",
                            "value": f"元法则: {name}", "level": "元法则"})
    return entries

def report_cloud(entry):
    try:
        req = urllib.request.Request(f"{CENTRAL_URL}/api/report/truth",
            data=json.dumps({"key": entry["key"], "value": {"did": DID, "value": entry["value"],
                              "level": entry["level"], "src": entry["src"], "trace": TRACE, "time": now()}}).encode(),
            headers={"X-Capture-Token": TOKEN, "X-DID": DID, "Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=10)
        resp = json.loads(r.read().decode())
        return {"key": entry["key"], "status": resp.get("success"), "action": resp.get("action")}
    except Exception as e:
        return {"key": entry["key"], "status": False, "error": str(e)}

def main():
    ap = argparse.ArgumentParser(description="体系真值批量上报引擎")
    ap.add_argument("--cats", required=True, help="类别(comma): constitution/metarules/metalaws")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cats = [c.strip() for c in a.cats.split(",") if c.strip()]

    entries = []
    for c in cats:
        entries.extend(extract(c))
    # 去重
    seen, uniq = set(), []
    for e in entries:
        if e["key"] not in seen: seen.add(e["key"]); uniq.append(e)

    results = [] if a.dry_run else [report_cloud(e) for e in uniq]
    ok = sum(1 for r in results if r.get("status"))
    fail = sum(1 for r in results if not r.get("status"))

    if not a.dry_run:
        os.makedirs(PRJ + "/experience/truth-core", exist_ok=True)
        f = PRJ + "/experience/truth-core/BATCH-REPORT-{}.json".format(time.strftime("%Y%m%d"))
        try: os.chmod(f, 0o666)
        except Exception: pass
        json.dump({"engine": VERSION, "did": DID, "time": now(), "reported": results, "entries": uniq},
                  open(f, "w"), ensure_ascii=False, indent=2)
        os.chmod(f, 0o444)

    report = {"engine": VERSION, "did": DID, "time": now(), "cats": cats,
              "extracted": len(uniq), "reported_ok": ok, "reported_fail": fail,
              "sample": [r for r in results[:5] if r] if results else uniq[:5],
              "note": "体系真值批量上报: 元宪法/元规则/元法则提炼上报云端统摄根基"}
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
