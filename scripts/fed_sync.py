#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fed_sync.py · 本地↔云端双向同步权威算子 (ZONGYUAN-ROOT)
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | NODE-DEV-DOUBAO-WORK-001

机制:
  握手      : GET  /api/status                        取云端锚点(seq/truth_count/autonomy)
  本地→云端  : 逐条 GET /api/truth?key= 查重 → 缺失即 POST /api/report/truth (幂等增量)
  云端→本地  : 云端锚点+可拉取真值回写联邦索引(更新 last_cloud_seq/sync 记录)
  启动记忆  : 刷新 runtime/memory_index.json 的 built_at + sync 锚点
  回执      : truth/reconcile/RECONCILE-SYNC-<date>.json
用法:
  python3 fed_sync.py [--git] [--key-prefix KERNEL.SEED]
"""
import json, os, sys, datetime, urllib.request, urllib.parse

ROOT = "/home/user/ZONGYUAN-ROOT"
HOST = "https://www.huodouai.com"
HDRS = {"Content-Type": "application/json",
        "X-DID": "DID-BR-000002",
        "X-Trace": "%CE%A9",
        "X-Source": "NODE-DEV-DOUBAO-WORK-001"}
LEDGER = f"{ROOT}/truth/federal-index/index_ledger.json"
MEMIDX = f"{ROOT}/runtime/memory_index.json"
RECON_DIR = f"{ROOT}/truth/reconcile"


def now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S+0800")


def http(url, method="GET", headers=None, body=None, timeout=25):
    req = urllib.request.Request(url, data=body, method=method,
                                 headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def handshake():
    try:
        s = http(HOST + "/api/status", headers={"X-DID": "DID-BR-000002"})
        return {"status": "ONLINE", "autonomy": s.get("autonomy"),
                "truth_count": s.get("truth_count"), "seq": s.get("seq"),
                "heartbeat": s.get("heartbeat")}
    except Exception as e:
        return {"status": "OFFLINE", "err": str(e)[:40]}


def cloud_has(key):
    url = HOST + "/api/truth?" + urllib.parse.urlencode({"key": key})
    try:
        d = http(url, headers={"X-DID": "DID-BR-000002"})
        return bool(d.get("count"))
    except Exception:
        return None  # 探测失败


def cloud_post(key, val):
    body = json.dumps({"key": key, "value": val,
                       "source_node": "NODE-DEV-DOUBAO-WORK-001",
                       "confidence": 0.99,
                       "truth_type": val.get("_truth_type", "meta_rule")}).encode("utf-8")
    d = http(HOST + "/api/report/truth", "POST", HDRS, body)
    return d


def build_key(entry, prefix):
    sha = entry.get("sha256", "")[:8]
    date = entry.get("timestamp", "")[:10].replace("-", "")
    return f"{prefix}.{date}.{sha}"


def main():
    prefix = "KERNEL.SEED"
    if "--key-prefix" in sys.argv:
        prefix = sys.argv[sys.argv.index("--key-prefix") + 1]
    use_git = "--git" in sys.argv

    led = json.load(open(LEDGER, encoding="utf-8"))
    entries = led.get("entries", [])

    # 1. 握手
    hs = handshake()

    # 2. 本地→云端 增量上报 (幂等)
    reported, skipped, failed = [], 0, []
    for e in entries:
        p = f"{ROOT}/{e.get('path', '')}"
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
            if isinstance(d, list):
                d = d[0] if d and isinstance(d[0], dict) else {}
        except Exception:
            continue
        if not isinstance(d, dict) or not d:
            continue
        key = build_key(e, prefix)
        has = cloud_has(key)
        if has is None:
            failed.append(key + ":probe"); continue
        if has:
            skipped += 1; continue
        val = {"concept": d.get("concept") or d.get("title") or d.get("text"),
               "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω",
               "ts": d.get("ts") or d.get("timestamp"), "sha256": e.get("sha256", ""),
               "path": e.get("path", ""), "source_node": "NODE-DEV-DOUBAO-WORK-001",
               "_truth_type": d.get("type") or "seed_truth"}
        try:
            r = cloud_post(key, val)
            reported.append((key, r.get("seq")))
        except Exception as ex:
            failed.append(key + ":" + str(ex)[:20])

    # 3. 云端→本地: 更新联邦索引锚点 + 同步元信息
    led["last_cloud_seq"] = hs.get("seq")
    led["cloud_truth_count"] = hs.get("truth_count")
    led["cloud_autonomy"] = hs.get("autonomy")
    led["last_sync_ts"] = now()
    led["last_sync"] = {"reported": len(reported), "skipped_dup": skipped,
                        "failed": failed, "handshake": hs}
    json.dump(led, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 4. 刷新启动记忆(云端同步锚点)
    if os.path.exists(MEMIDX):
        m = json.load(open(MEMIDX, encoding="utf-8"))
    else:
        m = {"index_version": "V3D-1.0", "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω"}
    m["built_at"] = now()
    m["cloud_sync"] = {"last_sync": now(), "cloud_autonomy": hs.get("autonomy"),
                       "cloud_seq": hs.get("seq"), "cloud_truth_count": hs.get("truth_count"),
                       "reported_this_round": len(reported),
                       "ledger_entry_count": led["entry_count"]}
    json.dump(m, open(MEMIDX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 5. 回执
    os.makedirs(RECON_DIR, exist_ok=True)
    date = now()[:10].replace("-", "")
    rec = {"receipt": f"RECONCILE-SYNC-{date}", "did": "DID-BR-000002",
           "trace": "Ω₀⊂⊙∞⊂Ω", "ts": now(), "handshake": hs,
           "push": {"candidates": len(entries), "reported": len(reported),
                    "skipped_duplicate": skipped, "failed": failed,
                    "seq_range": [r[1] for r in reported] or None},
           "pull": {"cloud_anchor_seq": hs.get("seq"), "cloud_truth_count": hs.get("truth_count")},
           "ledger_updated": True, "memindex_updated": True}
    rec_path = f"{RECON_DIR}/RECONCILE-SYNC-{date}.json"
    json.dump(rec, open(rec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 6. git 双副本
    if use_git:
        os.system(f"cd {ROOT} && git add -A && git commit -m 'feat(sync): 本地↔云端双向同步 [DID-BR-000002] Ω₀⊂⊙∞⊂Ω' -q && git push gitee master 2>&1")

    print(json.dumps({"ok": True, "handshake": hs,
                      "reported": len(reported), "skipped_dup": skipped,
                      "failed": failed, "receipt": rec_path},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
