#!/usr/bin/env python3
"""飞书协同治理 · Base 注册表对账 v1.0 —— 本地资产清单 vs 多维表格记录比对
纯标准库；未配置真实 lark 凭证时从本地模拟 base_records.json 读取远端记录。

用法:
  python3 scripts/base_reconcile.py --local-inventory <inventory.json> \
                                    --base-records <base_records.json> [--did <DID>]
"""
import sys, json, argparse, time
from pathlib import Path


def load_json(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser(description="Base 注册表对账：本地清单 vs 多维表格记录")
    ap.add_argument("--local-inventory", required=True, help="本地资产清单 JSON（{title: {sha256,size,tags}}）")
    ap.add_argument("--base-records", required=True, help="Base 记录 JSON（[{record_id, fields:{...}}]）")
    ap.add_argument("--title-field", default="title", help="Base 中标题字段名（默认 title）")
    ap.add_argument("--sha-field", default="sha256", help="Base 中哈希字段名（默认 sha256）")
    ap.add_argument("--did", default="<YOUR_DID>")
    args = ap.parse_args()

    inv = load_json(Path(args.local_inventory), {})
    raw = load_json(Path(args.base_records), [])
    if isinstance(raw, dict):
        raw = raw.get("records", [])

    local_map = {}
    for k, v in inv.items():
        if isinstance(v, dict):
            local_map[v.get("title", k)] = {"key": k, **v}
        else:
            local_map[k] = {"key": k, "title": k, "note": v}

    base_map = {}
    for r in raw:
        f = r.get("fields", r) if isinstance(r, dict) else {}
        t = f.get(args.title_field, "")
        if t:
            base_map[t] = {"record_id": r.get("record_id", ""), **f}

    local_t = set(local_map)
    base_t = set(base_map)

    only_local = sorted(local_t - base_t)        # 本地有、Base 缺 → 待补录
    only_base = sorted(base_t - local_t)        # Base 有、本地缺 → 待归档/清理
    changed = []                                  # 双端都有但 sha256 不一致
    matched = []
    for t in sorted(local_t & base_t):
        l_sha = local_map[t].get("sha256", "")
        b_sha = base_map[t].get(args.sha_field, "")
        if l_sha and b_sha and l_sha != b_sha:
            changed.append({"title": t, "local_sha256": l_sha, "base_sha256": b_sha,
                            "record_id": base_map[t]["record_id"]})
        else:
            matched.append(t)

    report = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "did": args.did,
        "local_total": len(local_map),
        "base_total": len(base_map),
        "matched": matched,
        "only_local_pending_push": only_local,
        "only_base_pending_archive": only_base,
        "changed": changed,
        "drift": len(only_local) + len(only_base) + len(changed),
        "status": "CONVERGED" if (not only_local and not only_base and not changed) else "DRIFT",
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["status"] == "CONVERGED" else 1


if __name__ == "__main__":
    sys.exit(main())
