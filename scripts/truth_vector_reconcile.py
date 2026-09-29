#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 真值库↔向量库 双向对账补齐（防漂移）
DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | V1.0

作用：对比 memory_index.json(真值库权威源) 与 vector_db(语义索引) 数量，
若向量库缺失历史真值则自动补齐（增量灌入），防止双向同步漂移。
由 supervisord 托管，每6小时执行一轮（与6h巡检节奏一致，零空转）。

用法：
  python3 truth_vector_reconcile.py          # 执行对账补齐
  python3 truth_vector_reconcile.py --status # 仅查看差异不写入
"""
import os, sys, json, time, urllib.request, argparse
from datetime import datetime

ROOT = "/home/user/ZONGYUAN-ROOT"
INDEX_PATH = os.path.join(ROOT, "memory_index.json")
VECTOR_STATS = "http://127.0.0.1:8003/api/v1/stats"
VECTOR_ADD = "http://127.0.0.1:8003/api/v1/add"
CHECK_INTERVAL = 21600  # 6小时
LOG_FILE = os.path.join(ROOT, "logs", "truth_vector_reconcile.log")

def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_vector_count():
    req = urllib.request.Request(VECTOR_STATS, method="GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r).get("doc_count", 0)

def add_doc(doc_id, text, metadata):
    body = json.dumps({"id": doc_id, "text": text, "metadata": metadata}).encode()
    req = urllib.request.Request(VECTOR_ADD, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def reconcile(dry_run=False):
    idx = json.load(open(INDEX_PATH))
    entries = idx.get("asset_entries", [])
    vcount = get_vector_count()
    total = len(entries)
    log(f"对账: 真值库权威源 {total} 条 | 向量库 {vcount} 条 | 差 {total - vcount}")

    missing = max(0, total - vcount)  # 理论缺失数（vector按顺序灌入时）
    if missing == 0 and vcount >= total:
        log("✅ 数量一致，无漂移")
        return True, 0

    # 精确补齐：按asset_id幂等upsert，把全部源灌入(缺的补齐，已有的覆盖无害)
    ok = 0; fail = 0
    for i, e in enumerate(entries):
        text = e.get("summary", "")[:500]
        if not text.strip():
            continue
        doc_id = f"kd-{str(e.get('asset_id','misc')).lower()}-{i}"
        metadata = {
            "asset_id": str(e.get("asset_id", "misc")),
            "priority": e.get("priority", "D"),
            "meta_class": e.get("meta_class", ""),
            "sha256": e.get("sha256", ""),
            "lock_level": e.get("lock_level", ""),
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω",
        }
        if dry_run:
            continue
        try:
            r = add_doc(doc_id, text, metadata)
            if r.get("status") == "added":
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1
        if (i + 1) % 200 == 0:
            log(f"  进度 {i+1}/{total} ok={ok} fail={fail}")
            time.sleep(1)

    if dry_run:
        log(f"[dry-run] 理论需补齐 {missing} 条")
        return True, missing
    after = get_vector_count()
    log(f"✅ 对账补齐完成: ok={ok} fail={fail} | 向量库现在 {after} 条")
    return fail == 0, ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="仅查看差异")
    ap.add_argument("--daemon", action="store_true", help="常驻每6小时对账")
    args = ap.parse_args()

    if args.status:
        idx = json.load(open(INDEX_PATH))
        vcount = get_vector_count()
        print(json.dumps({
            "truth_authority": len(idx.get("asset_entries", [])),
            "vector_count": vcount,
            "diff": len(idx.get("asset_entries", [])) - vcount,
            "did": "DID-BR-000002",
        }, ensure_ascii=False, indent=2))
        return

    if args.daemon:
        log("真值↔向量对账守护启动（每6小时）")
        while True:
            try:
                reconcile()
            except Exception as e:
                log(f"⚠️ 对账异常: {e}")
            time.sleep(CHECK_INTERVAL)
    else:
        reconcile()

if __name__ == "__main__":
    main()
