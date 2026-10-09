#!/usr/bin/env python3
"""ZONGYUAN-ROOT 云端对账闭环 · 每日巡检脚本
功能：读取云端记忆网关 truths + 合并桥接表，输出对账差异报告
DID-BR-000002 / Ω₀⊂⊙∞⊂Ω
"""
import json, urllib.request, os, sys
from datetime import datetime
from collections import Counter

GATEWAY="http://127.0.0.1:9120"
BRIDGE="/opt/ZONGYUAN-ROOT/truth/bridge/bridge_mapping.json"
REPORT_DIR="/opt/ZONGYUAN-ROOT/truth/bridge/reports"

def fetch_truths():
    req=urllib.request.Request(f"{GATEWAY}/api/truths?limit=5000")
    d=json.load(urllib.request.urlopen(req,timeout=15))
    return [t for t in d.get("truths",[]) if t]

def main():
    os.makedirs(REPORT_DIR,exist_ok=True)
    truths=fetch_truths()
    bridge=json.load(open(BRIDGE))
    mappings=bridge.get("mappings",[])
    by_key={m["truth_key"]:m for m in mappings}

    bridged=[k for k in truths if k in by_key]
    orphan=[k for k in truths if k not in by_key]
    local_mapped=[m for m in mappings if m["truth_key"] not in set(truths)]

    rep={
        "date":datetime.now().strftime("%Y-%m-%d"),
        "cloud_truth_count":len(truths),
        "bridge_count":len(mappings),
        "bridged_count":len(bridged),
        "bridge_rate":round(len(bridged)/len(truths)*100,2),
        "orphan_count":len(orphan),
        "local_only_mapping_count":len(local_mapped),
        "category_stats":dict(Counter(k.split('.')[0] for k in truths)),
        "orphan_samples":orphan[:10],
        "status":"CONSISTENT" if len(truths)==1305 else "DELTA",
    }
    path=os.path.join(REPORT_DIR,f"reconcile_{rep['date']}.json")
    json.dump(rep,open(path,"w"),ensure_ascii=False,indent=1)
    print(json.dumps(rep,ensure_ascii=False,indent=1))
    print(f"[OK] 报告已写: {path}")

if __name__=="__main__":
    main()
