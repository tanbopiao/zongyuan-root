#!/usr/bin/env python3
"""
种子真值提炼上报引擎 seed_truth_report.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
功能: 从 V11 种子真值卡片(00_KERNEL/truth_cards/SEED-V11-LOCKED.json)提炼 L0 结构化种子真值,
      按 RULE-005 V3.1 规范(key + 结构化value对象)上报云端中枢, 本地 experience/truth-core/ 留痕。
约束: 零成本(仅 HTTP 上报); 内容 100% 来自锁档卡片源文件, 不虚构; value 必为 JSON 对象(V3.1)。
用法: python3 00_KERNEL/scripts/seed_truth_report.py [--dry-run]
"""
import os, sys, json, time, hashlib, argparse, urllib.request, urllib.error

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
NODE = "NODE-DEV-CODEARTS-001"
VERSION = "SEED-TRUTH-REPORT-V1.0"
CENTRAL = "https://www.huodouai.com"
TOKEN = os.environ.get("ZR_CAPTURE_TOKEN", "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d")
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARD = PRJ + "/00_KERNEL/truth_cards/ZONGYUAN-YUANJI-YIHENG-SEED-V11-LOCKED.json"
OUT_DIR = PRJ + "/experience/truth-core"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

def sha256_file(path):
    h = hashlib.sha256()
    h.update(open(path, "rb").read())
    return h.hexdigest()

def post(payload, retries=2):
    body = json.dumps(payload, ensure_ascii=False).encode()
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(CENTRAL + "/api/report/truth", data=body, method="POST",
                headers={"Content-Type": "application/json", "X-DID": DID, "X-Capture-Token": TOKEN})
            with urllib.request.urlopen(req, timeout=15) as r:
                return {"http": 200, **json.loads(r.read().decode())}
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:200]
            if e.code != 400 and i < retries:
                time.sleep(2 * (i + 1)); continue
            return {"http": e.code, "error": err}
        except Exception as e:
            if i < retries:
                time.sleep(2 * (i + 1)); continue
            return {"http": 0, "error": str(e)[:200]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    card = json.load(open(CARD, encoding="utf-8"))
    card_sha = sha256_file(CARD)
    ts = now()
    base = {"did": DID, "anchor": TRACE, "source_card": os.path.relpath(CARD, PRJ),
            "card_sha256": card_sha, "card_version": card.get("system_version"), "ts": ts,
            "level": "L0-seed-truth", "extractor": VERSION}

    def entry(seq_id, name, truth_type, payload):
        return {"key": "SEED.YUANJI-V11.%s.%s" % (seq_id, now()[:10].replace("-", "")),
                "name": name, "truth_type": truth_type,
                "value": dict(base, truth_name=name, **payload)}

    # ---- 提炼: 12 条 L0 结构化种子真值(全部来自锁档卡片) ----
    rh = card["rule_hierarchy"]
    entries = [
        entry("01", "核心总真值", "meta_law",
              {"system_name": card["system_name"], "version": card["system_version"],
               "founder": card["founder"], "architecture": card["core_architecture"],
               "position": "ZONGYUAN-ROOT 全域内核: 四层规则体系 + 七层稳态自治架构, 元规则驱动/双节点主备/真值锚定/闭环自检"}),
        entry("02", "L0元宪法-只读熔断", "meta_law",
              {"layer": "L0", "read_only": True, "clauses": rh["L0_元宪法"]["items"]}),
        entry("03", "L1元公理-只读", "meta_law",
              {"layer": "L1", "read_only": True, "clauses": rh["L1_元公理"]["items"]}),
        entry("04", "L2元法则-可业务调整", "meta_law",
              {"layer": "L2", "read_only": False, "clauses": rh["L2_元法则"]["items"]}),
        entry("05", "L3元规则-动态配置", "meta_law",
              {"layer": "L3", "read_only": False, "clauses": rh["L3_元规则"]["items"]}),
        entry("06", "七层稳态自治架构", "meta_law",
              {"layers": card["seven_layer_architecture"]}),
        entry("07", "双网关通信链路", "protocol",
              {"link": card["communication_link"]}),
        entry("08", "五大核心能力", "meta_law",
              {"capabilities": card["core_capability"]}),
        entry("09", "系统边界", "risk",
              {"boundaries": card["system_boundary"]}),
        entry("10", "交付物清单", "decision",
              {"deliverables": card["deliverables"]}),
        entry("11", "当前运行状态", "data",
              {"status": card["current_status"]}),
        entry("12", "锁档指纹", "protocol",
              {"lock_id": card_sha[:32], "ease_seal": "blown_permanent_anchor",
               "locked_files": ["00_KERNEL/truth_cards/META-ROOT-0001-LOCKED.json",
                                "00_KERNEL/truth_cards/ZONGYUAN-YUANJI-YIHENG-SEED-V11-LOCKED.json"]}),
    ]

    if a.dry_run:
        print(json.dumps({"mode": "dry-run", "entries": len(entries),
                          "sample_keys": [e["key"] for e in entries[:3]]}, ensure_ascii=False))
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    results = [post({"key": e["key"], "value": e["value"], "truth_type": e["truth_type"],
                     "confidence": 1.0, "source_node": NODE}) for e in entries]
    ok = sum(1 for r in results if r.get("ok"))

    trail = {"engine": VERSION, "ts": now(), "card_sha256": card_sha,
             "total": len(entries), "reported_ok": ok, "reported_fail": len(entries) - ok,
             "results": [{"key": e["key"], "name": e["name"], "seq": r.get("seq"),
                          "ok": r.get("ok"), "truth_count": r.get("truth_count"),
                          "error": r.get("error")} for e, r in zip(entries, results)],
             "entries": entries}
    f = OUT_DIR + "/SEED-TRUTH-REPORT-%s.json" % now().replace("-", "")[:8]
    json.dump(trail, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({"reported_ok": ok, "fail": len(entries) - ok,
                      "seqs": [r.get("seq") for r in results if r.get("ok")],
                      "last_truth_count": results[-1].get("truth_count"),
                      "trail": os.path.relpath(f, PRJ)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
