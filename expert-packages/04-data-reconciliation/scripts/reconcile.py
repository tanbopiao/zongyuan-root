#!/usr/bin/env python3
"""数据资产对账引擎 v1.0 —— 目录指纹扫描 + 基线对账 + 漂移报告（纯标准库，零网络依赖）

用法:
  python3 scripts/reconcile.py --dir <资产目录> --baseline <基线.json> [--did <DID>]
                               [--local-only] [--init-baseline] [--ledger <账本.jsonl>]
                               [--exclude <模式>] [--webhook <URL>]
"""
import os, sys, json, csv, hashlib, time, argparse, urllib.request
from pathlib import Path
from typing import List, Dict

DEFAULT_EXCLUDE = ["__pycache__", ".git", ".DS_Store", "Thumbs.db", "node_modules"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_dir(target: Path, exclude: List[str]) -> Dict[str, Dict]:
    """OP-01 目录指纹扫描：返回 {rel_path: {sha256, size}}"""
    assets: Dict[str, Dict] = {}
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in exclude]
        for fname in sorted(files):
            if any(p in fname for p in exclude):
                continue
            fp = Path(root) / fname
            rel = str(fp.relative_to(target))
            try:
                assets[rel] = {"sha256": sha256_file(fp), "size": fp.stat().st_size}
            except OSError:
                continue
    return assets


def load_baseline(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("assets", {})


def reconcile(cur: Dict[str, Dict], base: Dict[str, Dict]) -> Dict:
    """OP-02 基线对账：新增/删除/变更 + 漂移率"""
    cur_keys, base_keys = set(cur), set(base)
    added = sorted(cur_keys - base_keys)
    removed = sorted(base_keys - cur_keys)
    changed = sorted(k for k in (cur_keys & base_keys)
                     if cur[k]["sha256"] != base[k].get("sha256"))
    total = len(base_keys) or 1
    drift = len(added) + len(removed) + len(changed)
    return {
        "added": added, "removed": removed, "changed": changed,
        "drift": drift, "baseline_total": len(base_keys), "current_total": len(cur_keys),
        "drift_ratio": round(drift / total * 100, 2),
        "status": "CONVERGED" if drift == 0 else "DRIFT",
    }


def ledger_append(ledger: Path, event: Dict):
    """append-only 账本：只追加不修改"""
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def compute_merkle(ledger: Path) -> str:
    """OP-03 Merkle 根：账本全部行累积哈希"""
    root = "0000"
    if ledger.exists():
        with open(ledger, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    root = hashlib.sha256((root + line.strip()).encode()).hexdigest()
    return root


def post_webhook(url: str, payload: Dict) -> bool:
    """可选上报：对账报告推送（失败不阻塞主流程）"""
    if not url:
        return False
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status in (200, 201)
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="数据资产对账引擎")
    ap.add_argument("--dir", required=True, help="被对账资产目录")
    ap.add_argument("--baseline", required=True, help="基线清单 JSON 路径")
    ap.add_argument("--did", default="<YOUR_DID>")
    ap.add_argument("--local-only", action="store_true", help="仅本地对账，跳过远端/上报")
    ap.add_argument("--init-baseline", action="store_true", help="以当前目录生成基线并退出")
    ap.add_argument("--ledger", default="", help="append-only 账本路径（可选）")
    ap.add_argument("--exclude", action="append", default=[], help="额外排除模式")
    ap.add_argument("--webhook", default="", help="对账报告上报端点（可选）")
    args = ap.parse_args()

    target = Path(args.dir).resolve()
    if not target.is_dir():
        print(json.dumps({"status": "ERROR", "reason": "dir not found", "dir": str(target)}, ensure_ascii=False))
        return 2
    exclude = DEFAULT_EXCLUDE + args.exclude

    cur = scan_dir(target, exclude)
    if args.init_baseline:
        baseline = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "did": args.did, "assets": cur}
        Path(args.baseline).write_text(json.dumps(baseline, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"status": "BASELINE_INIT", "asset_count": len(cur), "baseline": args.baseline}, ensure_ascii=False))
        return 0

    base = load_baseline(Path(args.baseline))
    report = reconcile(cur, base)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report.update({"ts": ts, "did": args.did})

    # 账本事件（可选）
    if args.ledger:
        ledger_path = Path(args.ledger)
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        seq = (sum(1 for _ in open(ledger_path, encoding="utf-8")) + 1) if ledger_path.exists() else 1
        event = {"seq": seq, "event_id": f"reconcile-{int(time.time()*1000)}-{hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:8]}",
                 "sha": hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                 "ts": ts, "drift": report["drift"], "status": report["status"]}
        ledger_append(ledger_path, event)
        report["merkle_root"] = compute_merkle(ledger_path)

    # 可选上报
    if args.webhook and not args.local_only:
        report["webhook_ack"] = post_webhook(args.webhook, report)

    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["status"] == "CONVERGED" else 1


if __name__ == "__main__":
    sys.exit(main())
