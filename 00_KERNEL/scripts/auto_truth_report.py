#!/usr/bin/env python3
"""
全自动真值上报引擎 auto_truth_report.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω

功能: 增量扫描 ledger/chain 的 Merkle 链块, 将未上报块按 RULE-005 V3.1 规范
      (key + 结构化 value 对象) 注入云端中枢 api/report/truth; 幂等去重, 失败留待下轮重试。
约束: 零成本(仅 HTTP 上报); 内容 100% 来自链块实档, 不虚构; value 必为 JSON 对象(V3.1);
      仅真值注入(合元宪法第2条), 不修改本地任何锁档。
用法:
  python3 auto_truth_report.py --init [--keep BLK-xxx]   # 首轮基线: 现存块标记已报(--keep 除外)
  python3 auto_truth_report.py                            # 常规轮: 上报全部未报块
  python3 auto_truth_report.py --dry-run                  # 只看待报清单, 不发送
"""
import os, sys, json, time, glob, hashlib, argparse, urllib.request, urllib.error, fcntl

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
NODE = "NODE-DEV-CODEARTS-001"
VERSION = "AUTO-TRUTH-REPORT-V1.0"
CENTRALS = ["https://www.huodouai.com", "https://drama.huodouai.com"]
TOKEN = os.environ.get("ZR_CAPTURE_TOKEN", "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d")
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAIN_DIR = PRJ + "/ledger/chain"
STATE = PRJ + "/var/auto_truth_report_state.json"
TRAIL_DIR = PRJ + "/experience/truth-core"
AUDIT = PRJ + "/var/inbox/audit.jsonl"


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {"version": VERSION, "reported": {}}


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)


def post(payload, retries=2):
    """双网关上报: 主 www → 备 drama; 返回 {ok, seq, truth_count} 或 {error}"""
    body = json.dumps(payload, ensure_ascii=False).encode()
    last = {}
    for gw in CENTRALS:
        for i in range(retries + 1):
            try:
                req = urllib.request.Request(gw + "/api/report/truth", data=body, method="POST",
                    headers={"Content-Type": "application/json", "X-DID": DID, "X-Capture-Token": TOKEN})
                with urllib.request.urlopen(req, timeout=20) as r:
                    j = json.loads(r.read().decode())
                    j["gateway"] = gw
                    return j
            except urllib.error.HTTPError as e:
                last = {"gateway": gw, "http": e.code, "error": e.read().decode()[:200]}
                if e.code == 400:  # 请求本身不合法, 换网关无意义
                    return last
                time.sleep(2 * (i + 1))
            except Exception as e:
                last = {"gateway": gw, "http": 0, "error": str(e)[:200]}
                time.sleep(2 * (i + 1))
    return dict(last, ok=False)


def block_payload(b):
    """链块 → 云端真值报文(确定性 key, 重复上报可被云端按 key 归一)"""
    e = b["entry"]
    key = "PROVENANCE.MERKLE.%s" % b["block_id"].upper()
    value = {
        "block_id": b["block_id"],
        "block_hash": b["block_hash"],
        "merkle_root": b["merkle_root"],
        "prev_block_hash": b["prev_block_hash"],
        "entry_type": e.get("type"),
        "subject": e.get("subject") or e.get("ref") or e.get("record_id"),
        "report_file": e.get("report_file") or e.get("report") or e.get("seed_file"),
        "report_sha256": e.get("report_sha256") or e.get("doc_sha256") or e.get("seed_sha256"),
        "source_path": e.get("source_path"),
        "source_manifest_sha256": e.get("source_manifest_sha256"),
        "ports": e.get("ports"),
        "verification": e.get("verification"),
        "honest": e.get("honest"),
        "entry_timestamp": e.get("timestamp"),
        "local_chain": "ledger/chain/" + b["block_id"] + ".json",
        "did": DID, "anchor": TRACE, "source_node": NODE,
        "uploader": VERSION, "ts": now(),
    }
    return {"key": key, "value": value, "truth_type": e.get("truth_type", "data"),
            "confidence": 1.0, "source_node": NODE}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true", help="首轮基线: 现存块标记为已报")
    # 单实例锁: 守护循环与定时任务并发触发时防重入(防重复上报)
    lock_f = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(json.dumps({"mode": "noop", "reason": "another_instance_running"}, ensure_ascii=False))
        return
    ap.add_argument("--keep", action="append", default=[], help="基线豁免(仍待上报)的 block_id")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    blocks = {}
    for p in glob.glob(CHAIN_DIR + "/BLK-*.json"):
        b = json.load(open(p, encoding="utf-8"))
        blocks[b["block_id"]] = b
    st = load_state()

    if a.init:
        for bid in blocks:
            if bid not in a.keep and bid not in st["reported"]:
                st["reported"][bid] = {"seq": None, "ts": now(), "note": "baseline"}
        st["version"] = VERSION
        if not a.dry_run:
            save_state(st)
        print(json.dumps({"mode": "init", "baseline": len(st["reported"]),
                          "pending": sorted(set(blocks) - set(st["reported"]))}, ensure_ascii=False))
        return

    pending = sorted((b for bid, b in blocks.items() if bid not in st["reported"]),
                     key=lambda b: b["entry"].get("timestamp", ""))
    if a.dry_run:
        print(json.dumps({"mode": "dry-run", "total_blocks": len(blocks),
                          "reported": len(st["reported"]), "pending": [b["block_id"] for b in pending]},
                         ensure_ascii=False))
        return
    if not pending:
        print(json.dumps({"mode": "noop", "reported": len(st["reported"]), "pending": 0}, ensure_ascii=False))
        return

    results = []
    for b in pending:
        r = post(block_payload(b))
        ok = bool(r.get("ok"))
        if ok:
            st["reported"][b["block_id"]] = {"seq": r.get("seq"), "ts": now(),
                                             "truth_count": r.get("truth_count"),
                                             "gateway": r.get("gateway")}
        results.append({"block_id": b["block_id"], "key": block_payload(b)["key"],
                        "ok": ok, "seq": r.get("seq"), "truth_count": r.get("truth_count"),
                        "error": r.get("error")})
        time.sleep(0.3)
    save_state(st)

    # 本地留痕: 轮报告 + 审计行(仅追加)
    ok_n = sum(1 for x in results if x["ok"])
    trail = {"engine": VERSION, "ts": now(), "total": len(results), "reported_ok": ok_n,
             "reported_fail": len(results) - ok_n, "results": results}
    os.makedirs(TRAIL_DIR, exist_ok=True)
    tf = TRAIL_DIR + "/AUTO-TRUTH-REPORT-%s.json" % time.strftime("%Y%m%d")
    prev = json.load(open(tf, encoding="utf-8")) if os.path.exists(tf) else {"rounds": []}
    prev.setdefault("rounds", []).append(trail)
    json.dump(prev, open(tf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    try:
        os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
        with open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now(), "engine": VERSION, "event": "auto_truth_report",
                                "ok": ok_n, "fail": len(results) - ok_n,
                                "seqs": [x["seq"] for x in results if x["ok"]]}, ensure_ascii=False) + "\n")
    except Exception:
        pass

    print(json.dumps({"reported_ok": ok_n, "fail": len(results) - ok_n,
                      "seqs": [x["seq"] for x in results if x["ok"]],
                      "pending_left": [x["block_id"] for x in results if not x["ok"]],
                      "trail": os.path.relpath(tf, PRJ)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
