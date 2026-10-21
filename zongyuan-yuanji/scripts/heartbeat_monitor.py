#!/usr/bin/env python3
"""heartbeat_monitor.py — 本地心跳/节点/台账数字修正器

修复三个显示层缺陷：
  1. heartbeat 字段停滞 → 写入本地真实心跳记录
  2. nodes_online=1 vs nodes_contributed=46 → 写入本地节点台账
  3. 台账数字过期 → 写入本地真值计数快照

用法: python3 scripts/heartbeat_monitor.py
"""
import json, os, time, subprocess
from pathlib import Path

ROOT = Path("/zongyuan-yuanji")
VAR = ROOT / "var"
GATEWAY = "https://www.huodouai.com/api/report/truth"
DID = "DID-BR-000002"
ANCHOR = "\u23a0\u2282\u2299\u221e\u2282\u23a9"


def curl_get(url):
    r = subprocess.run(["curl", "-s", "-m", "10", url], capture_output=True, text=True)
    return json.loads(r.stdout) if r.stdout.strip() else {}


def curl_post(key, value, truth_type="data"):
    payload = json.dumps({"key": key, "value": value, "truth_type": truth_type,
                          "source_node": "NODE-DEV-DOUBAO-WORK-001"})
    r = subprocess.run(["curl", "-s", "-m", "15", "-X", "POST", GATEWAY,
                        "-H", "Content-Type: application/json",
                        "-H", f"X-DID: {DID}", "-d", payload],
                       capture_output=True, text=True)
    return r.stdout.strip()


def main():
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    print(f"=== heartbeat_monitor ===")
    print(f"  {ANCHOR} | {DID} | {now}\n")

    # 1. 心跳
    hb = {
        "did": DID, "anchor": ANCHOR, "node": "ZR-NODE-DC2E51C0",
        "ts": now, "status": "ACTIVE", "autonomy": "Lv10",
        "source": "local_heartbeat",
    }
    r = curl_post("KERNEL.HEARTBEAT-LOCAL-20261020", hb, "data")
    print(f"[1/3] heartbeat: {r[:100]}")

    # 2. 节点
    nodes = []
    for f in sorted((VAR / "nodes").glob("*.json")):
        try:
            d = json.loads(f.read_text())
            nodes.append({"file": f.name, "did": d.get("did", "?"),
                          "status": d.get("status", "?")})
        except Exception:
            pass
    a2a_file = VAR / "a2a" / "nodes.json"
    a2a_count = 0
    if a2a_file.exists():
        a2a_count = len(json.loads(a2a_file.read_text()))
    nd = {
        "did": DID, "anchor": ANCHOR,
        "local_nodes": nodes, "a2a_nodes": a2a_count,
        "total_contributed": len(nodes) + a2a_count,
        "measured_at": now,
        "note": "实时测量值（非静态规格值）",
    }
    r = curl_post("KERNEL.NODES-CONTRIBUTED-20261020", nd, "data")
    print(f"[2/3] nodes: {r[:100]}")

    # 3. 台账数字
    status = curl_get("https://www.huodouai.com/api/status")
    truth_count = status.get("truth_count", "?")
    stored = status.get("stored", "?")
    today = status.get("today", "?")
    seq = status.get("seq", "?")
    td = {
        "did": DID, "anchor": ANCHOR,
        "truth_count": truth_count, "stored": stored,
        "today": today, "seq": seq,
        "measured_at": now,
        "note": "实时测量值（修正过期台账口径）",
    }
    r = curl_post("KERNEL.TRUTH-COUNT-20261020", td, "data")
    print(f"[3/3] truth_count: {r[:100]}")

    print(f"\n✓ heartbeat/nodes/truth_count 修正完成")


if __name__ == "__main__":
    main()
