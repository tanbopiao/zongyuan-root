#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一自治内核 · MCP Server（互操作层）
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ INTEROP-MCP-V1.0

将内核能力以 MCP (Model Context Protocol) 标准暴露，零依赖实现
（JSON-RPC 2.0 over stdio, newline-delimited）。

对外工具：
  omega_status       内核状态与自举结果
  truth_report       真值上报（中枢记忆网关）
  truth_recall       真值召回（按 key 下行）
  truth_list         最近真值列表
  memory_anchor      记忆锚定检索（本地 memory_index）
  node_heartbeat     同源节点心跳

启动：python3 omega_mcp_server.py   （stdio 模式，供 MCP client 拉起）
"""
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SNAPSHOT = os.path.join(ROOT, "00_KERNEL/startup_memory/GLOBAL_MEMORY_SNAPSHOT.json")
BOOT_REPORT = os.path.join(ROOT, "00_KERNEL/omega01_boot/BOOT-REPORT-ACTIVATED-20261009.json")
MEMORY_INDEX = os.path.join(ROOT, "memory_index.json")
BOOT_SPEC = os.path.join(ROOT, "00_KERNEL/omega01_boot/OMEGA-KERNEL-BOOT.json")

GATEWAY = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
NODE_ID = "NODE-DEV-CODEARTS-001"
CAPTURE_TOKEN = os.environ.get("ZR_CAPTURE_TOKEN", "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d")

TOOLS = [
    {
        "name": "omega_status",
        "description": "元极恒一自治内核状态：内核版本/自举报告/云端真值/节点注册",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "truth_report",
        "description": "向中枢记忆网关上报真值（禁用 content 字段，用 key/value）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "真值键，大写点分命名"},
                "value": {"description": "真值内容（任意JSON对象或字符串）"},
                "truth_type": {"type": "string", "enum": ["meta_law", "rule", "config", "decision", "data", "creative", "risk", "protocol", "unknown"]},
                "confidence": {"type": "number"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "truth_recall",
        "description": "按 key 从中枢下行召回真值",
        "inputSchema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
    },
    {
        "name": "truth_list",
        "description": "读取中枢最近真值列表（limit 默认 10，最大 200）",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200}}},
    },
    {
        "name": "memory_anchor",
        "description": "本地记忆索引锚定检索（anchor_type: latest/tag/asset_id/keyword）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "anchor_type": {"type": "string", "enum": ["latest", "tag", "asset_id", "keyword"]},
                "anchor_value": {"type": "string"},
                "max_token": {"type": "integer", "default": 4000},
            },
            "required": ["anchor_type"],
        },
    },
    {
        "name": "node_heartbeat",
        "description": "同源节点心跳上报（复用 NODE-DEV-CODEARTS-001，不重复注册）",
        "inputSchema": {"type": "object", "properties": {"note": {"type": "string"}}, "required": []},
    },
]


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def tool_omega_status(_args):
    snap = _load_json(SNAPSHOT, {})
    boot = _load_json(BOOT_REPORT, {})
    return {
        "kernel": snap.get("kernel"),
        "did": DID,
        "anchor": ANCHOR,
        "boot_report": {k: boot.get(k) for k in ("status", "steps_pass", "steps_total", "generated_at") if k in boot},
        "cloud_truth": snap.get("cloud_truth"),
        "nodes": snap.get("nodes"),
        "mcp_server": "INTEROP-MCP-V1.0",
    }


def _gateway_post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        GATEWAY + path, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-DID": DID, "X-Capture-Token": CAPTURE_TOKEN},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _gateway_get(path):
    req = urllib.request.Request(GATEWAY + path, headers={"X-DID": DID, "X-Capture-Token": CAPTURE_TOKEN})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def tool_truth_report(args):
    # V3.1 网关规范(RULE-005): value 必须为 JSON 对象, 旧 truth_value 字段已失效, X-DID 单头
    value = args.get("value")
    if isinstance(value, str):
        value = {"value": value}
    if not isinstance(value, dict) or not value:
        return {"error": "empty_value_rejected", "message": "value 必须为 JSON 对象(RULE-005 V3.1), 请用命名空间key+结构化value"}
    payload = {
        "key": args.get("key"),
        "value": value,
        "anchor": ANCHOR,
        "truth_type": args.get("truth_type", "data"),
        "confidence": args.get("confidence", 0.95),
        "source_node": NODE_ID,
    }
    return _gateway_post("/api/report/truth", payload)


def tool_truth_recall(args):
    key = urllib.parse.quote(args.get("key", ""), safe="")
    return _gateway_get("/api/truth/" + key)


def tool_truth_list(args):
    limit = int(args.get("limit", 10))
    return _gateway_get("/api/truth?limit=%d" % limit)


def tool_memory_anchor(args):
    idx = _load_json(MEMORY_INDEX, {})
    entries = idx.get("asset_entries", [])
    atype = args.get("anchor_type", "latest")
    value = args.get("anchor_value", "")
    max_token = int(args.get("max_token", 4000))
    if atype == "latest":
        matched = sorted(entries, key=lambda x: {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}.get(x.get("priority", "D"), 5))[:20]
    elif atype == "tag":
        matched = [e for e in entries if value in e.get("tags", [])]
    elif atype == "asset_id":
        matched = [e for e in entries if e.get("asset_id") == value]
    else:
        kw = value.lower()
        matched = [e for e in entries if kw in e.get("summary", "").lower() or kw in ",".join(e.get("tags", [])).lower()]
    out = []
    for e in matched[:15]:
        line = "[%s] %s | tags:%s | %s" % (e.get("priority", "C"), e.get("asset_id", ""), ",".join(e.get("tags", [])[:5]), e.get("summary", ""))
        out.append(line[: max_token * 2])
    return {"matched_count": len(matched), "total_index": len(entries), "memories": out}


def tool_node_heartbeat(args):
    payload = {
        "key": "NODE.HEARTBEAT.%s" % NODE_ID,
        "value": {"node_id": NODE_ID, "did": DID, "anchor": ANCHOR,
                  "note": args.get("note", ""), "ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800")},
        "anchor": ANCHOR, "truth_type": "protocol", "confidence": 1.0, "source_node": NODE_ID,
    }
    return _gateway_post("/api/report/truth", payload)


HANDLERS = {
    "omega_status": tool_omega_status,
    "truth_report": tool_truth_report,
    "truth_recall": tool_truth_recall,
    "truth_list": tool_truth_list,
    "memory_anchor": tool_memory_anchor,
    "node_heartbeat": tool_node_heartbeat,
}


def dispatch(name, args):
    handler = HANDLERS.get(name)
    if not handler:
        raise KeyError("unknown tool: %s" % name)
    return handler(args or {})


def handle(req):
    method = req.get("method")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "omega-zongyuan-kernel", "version": "1.0.0"},
        }}
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = req.get("params") or {}
        try:
            data = dispatch(params.get("name"), params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "isError": False}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": "error: %s" % e}], "isError": True}}
    if rid is not None:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found: %s" % method}}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()