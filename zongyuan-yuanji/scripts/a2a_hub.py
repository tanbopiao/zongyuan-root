#!/usr/bin/env python3
"""A2A节点注册中心：自动注册/握手/心跳/发现"""
import json, time, uuid
from pathlib import Path

NODE_DIR = Path("/root/zongyuan-yuanji/var/a2a")
NODE_DIR.mkdir(parents=True, exist_ok=True)
NODES_FILE = NODE_DIR / "nodes.json"

def _load():
    if NODES_FILE.exists():
        return json.loads(NODES_FILE.read_text())
    return {}

def _save(d):
    NODES_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2))

def register(name, endpoint="", capabilities=None, api_key=""):
    nodes = _load()
    nid = f"A2A-{uuid.uuid4().hex[:8].upper()}"
    node = {
        "id": nid, "name": name, "endpoint": endpoint,
        "capabilities": capabilities or [], "api_key": api_key,
        "registered_at": int(time.time()), "last_heartbeat": int(time.time()),
        "status": "ONLINE", "heartbeats": 1
    }
    nodes[nid] = node
    _save(nodes)
    return {"ok": True, "node_id": nid, "message": "注册成功"}

def heartbeat(nid, status="ONLINE", metrics=None):
    nodes = _load()
    if nid not in nodes: return {"ok": False, "error": "节点未注册"}
    nodes[nid]["last_heartbeat"] = int(time.time())
    nodes[nid]["status"] = status
    nodes[nid]["heartbeats"] = nodes[nid].get("heartbeats",0)+1
    if metrics: nodes[nid]["metrics"] = metrics
    _save(nodes)
    return {"ok": True, "node_id": nid}

def list_nodes():
    nodes = _load()
    now = int(time.time())
    result = []
    for nid, n in nodes.items():
        alive = (now - n["last_heartbeat"]) < 300  # 5分钟无心跳=离线
        result.append({**n, "alive": alive})
    return result

def discover(capability=None):
    nodes = list_nodes()
    if capability:
        nodes = [n for n in nodes if capability in n.get("capabilities",[])]
    return [n for n in nodes if n["alive"]]
