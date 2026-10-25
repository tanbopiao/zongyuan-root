#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量上报结构化种子真值到云端中枢。

用法:
    python3 report_seeds.py seeds.json [--retry 3] [--wait 90]

seeds.json: 列表，每项 { "key": "...", "value": {...}, "truth_type": "data", "confidence": 0.95 }
可选字段: source_node / anchor / did / extracted_at（缺省自动补齐）
"""
import json
import sys
import time
from pathlib import Path

SERVICES_DIR = Path("/workspace/scripts/services")
sys.path.insert(0, str(SERVICES_DIR))

from seed_extraction_engine import report_truth, DID  # noqa: E402

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
NODE = "NODE-ID"


def fill_defaults(item: dict) -> dict:
    val = item.get("value")
    if not isinstance(val, dict) or len(val) < 2:
        raise ValueError(f"value 必须为字段数>=2 的对象: {item.get('key')}")
    val.setdefault("anchor", ANCHOR)
    val.setdefault("did", DID)
    val.setdefault("source_node", item.get("source_node", NODE))
    val.setdefault("extracted_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    return {
        "key": item["key"],
        "value": val,
        "source_node": item.get("source_node", NODE),
        "confidence": item.get("confidence", 0.95),
        "truth_type": item.get("truth_type", "data"),
    }


def run_batch(payloads: list) -> tuple:
    ok, seqs, failed = 0, [], []
    for p in payloads:
        r = report_truth(p)
        if r.get("ok"):
            ok += 1
            seqs.append(r.get("seq"))
            print(f"OK  seq={r.get('seq')} key={p['key']}")
        else:
            failed.append(p)
            print(f"FAIL key={p['key']} err={str(r.get('error', r))[:160]}")
        time.sleep(0.3)
    return ok, seqs, failed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    seeds = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    retry = int(sys.argv[sys.argv.index("--retry") + 1]) if "--retry" in sys.argv else 3
    wait = int(sys.argv[sys.argv.index("--wait") + 1]) if "--wait" in sys.argv else 90

    payloads = [fill_defaults(s) for s in seeds]
    total_ok, all_seqs, failed = 0, [], payloads
    for attempt in range(1, retry + 1):
        print(f"=== 第 {attempt} 轮上报: {len(failed)} 条 ===")
        ok, seqs, failed = run_batch(failed)
        total_ok += ok
        all_seqs.extend(seqs)
        if not failed:
            break
        if attempt < retry:
            print(f"等待 {wait}s 后重试（云端写锁通常由批量任务持有）...")
            time.sleep(wait)

    print(f"\n汇总: 成功{total_ok} 失败{len(failed)}")
    print(f"seqs: {all_seqs}")
    if failed:
        print("失败key: " + ", ".join(p["key"] for p in failed))
        sys.exit(2)


if __name__ == "__main__":
    main()
