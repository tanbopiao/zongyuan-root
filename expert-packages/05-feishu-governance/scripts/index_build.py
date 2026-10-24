#!/usr/bin/env python3
"""飞书协同治理 · 统一资产索引构建 v1.0 —— 按标题/标签/类型聚合本地+远端资产，生成可检索索引
纯标准库。

用法:
  python3 scripts/index_build.py --local-inventory <inv.json> [--remote-sim <sim.json>] \
                                --out <index.json> [--did <DID>]
"""
import sys, json, argparse, time
from pathlib import Path
from collections import defaultdict


def load_json(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser(description="统一资产索引构建")
    ap.add_argument("--local-inventory", required=True)
    ap.add_argument("--remote-sim", default="", help="可选：模拟远端状态 JSON")
    ap.add_argument("--out", required=True, help="输出 index.json 路径")
    ap.add_argument("--did", default="<YOUR_DID>")
    args = ap.parse_args()

    inv = load_json(Path(args.local_inventory), {})
    sim = load_json(Path(args.remote_sim), {}) if args.remote_sim else {}

    by_title = {}
    by_tag = defaultdict(list)
    by_type = defaultdict(list)

    # 本地条目
    for k, v in inv.items():
        if not isinstance(v, dict):
            v = {"title": k, "note": v}
        t = v.get("title", k)
        by_title.setdefault(t, {"title": t, "sources": []})
        by_title[t]["sources"].append({"channel": "local", "key": k,
                                       "sha256": v.get("sha256", ""),
                                       "size": v.get("size", 0)})
        for tag in v.get("tags", []):
            by_tag[tag].append(t)
        by_type[v.get("type", "markdown")].append(t)

    # 远端三端条目
    for ch, key_field in [("wiki_nodes", "node_token"),
                          ("drive_files", "file_token"),
                          ("base_records", "record_id")]:
        for item in sim.get(ch, []):
            f = item.get("fields", item) if ch == "base_records" else item
            t = f.get("title") or f.get("name") or ""
            if not t:
                continue
            by_title.setdefault(t, {"title": t, "sources": []})
            channel = {"wiki_nodes": "wiki", "drive_files": "drive",
                       "base_records": "base"}[ch]
            by_title[t]["sources"].append({
                "channel": channel,
                "key": item.get(key_field, ""),
                "sha256": f.get("sha256", ""),
                "size": f.get("size", 0),
                "url": item.get("url", ""),
            })
            for tag in f.get("tags", []):
                by_tag[tag].append(t)
            by_type[channel].append(t)

    index = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "did": args.did,
        "stats": {
            "titles": len(by_title),
            "tags": len(by_tag),
            "channels": {k: len(set(v)) for k, v in by_type.items()},
        },
        "by_title": by_title,
        "by_tag": {k: sorted(set(v)) for k, v in by_tag.items()},
        "by_type": {k: sorted(set(v)) for k, v in by_type.items()},
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "OK", "out": args.out,
                      "titles": index["stats"]["titles"],
                      "tags": index["stats"]["tags"],
                      "channels": index["stats"]["channels"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
