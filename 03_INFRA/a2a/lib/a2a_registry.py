#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A 对端注册表 v1.0
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: A2A-REGISTRY-V1.0

职责：管理 A2A 联邦对端清单。解决 L-31「A2A 零对端，agent-card 注册入口未探明」。
  - 注册对端（agent-card URL + 同源令牌 + 信任级别）
  - 心跳探测（拉取对端 /.well-known/agent-card.json）
  - 对端状态台账（在线/离线/未验证）
  - 零落盘：注册表文件本身不含令牌明文，令牌由调用方按需注入

设计原则：
  - 注册表落盘为纯 JSON，不含任何密钥（密钥零入库铁律）
  - 对端令牌存放在 600 权限的独立凭证文件，与注册表分离
  - 复用既有 agent-card.json 作为对端发现入口（AXIOM-REUSE-NO-REDO-001）
"""
import os
import json
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY = os.path.join(HERE, "..", "federation", "peer-registry.json")
PEER_SECRETS = "/root/.zr-credentials/a2a_peers.env"

DEAD_TIMEOUT = 5  # 秒


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class PeerRegistry:
    def __init__(self, path: str = None):
        self.path = os.path.abspath(path or DEFAULT_REGISTRY)
        self.data = _load(self.path, {"protocol": "A2A-REGISTRY-V1.0",
                                      "anchor": "Ω₀⊂⊙∞⊂Ω",
                                      "peers": []})

    # ---------- 注册 ----------
    def register(self, node_id: str, card_url: str, trust: str = "unverified",
                 note: str = "", token_ref: str = "") -> dict:
        for p in self.data["peers"]:
            if p["node_id"] == node_id:
                p.update({"card_url": card_url, "note": note, "token_ref": token_ref,
                          "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")})
                _save(self.path, self.data)
                return {"action": "updated", "peer": p}
        peer = {
            "node_id": node_id,
            "card_url": card_url,
            "trust": trust,          # unverified | verified | trusted | blocked
            "token_ref": token_ref,  # 指向凭证文件中的变量名，非令牌本身
            "note": note,
            "state": "unknown",
            "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        }
        self.data["peers"].append(peer)
        _save(self.path, self.data)
        return {"action": "registered", "peer": peer}

    # ---------- 探测 ----------
    def probe(self, node_id: str = None) -> list:
        """拉取对端 agent-card，更新在线状态"""
        results = []
        for p in self.data["peers"]:
            if node_id and p["node_id"] != node_id:
                continue
            if p.get("trust") == "blocked":
                p["state"] = "blocked"
                results.append({"node_id": p["node_id"], "state": "blocked"})
                continue
            url = p["card_url"]
            if not url.startswith("http"):
                p["state"] = "unreachable"
                p["last_error"] = "card_url 非 http"
                results.append({"node_id": p["node_id"], "state": "unreachable"})
                continue
            try:
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=DEAD_TIMEOUT) as resp:
                    card = json.loads(resp.read().decode())
                p["state"] = "online"
                p["last_seen"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
                p["card_name"] = card.get("name")
                p["card_skills"] = [s.get("id") for s in card.get("skills", [])]
                p.pop("last_error", None)
                results.append({"node_id": p["node_id"], "state": "online",
                                "card_name": card.get("name"),
                                "skills": p["card_skills"]})
            except Exception as e:
                p["state"] = "offline"
                p["last_error"] = str(e)[:200]
                p["last_probe"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
                results.append({"node_id": p["node_id"], "state": "offline", "error": str(e)[:120]})
        _save(self.path, self.data)
        return results

    # ---------- 视图 ----------
    def list_peers(self) -> list:
        return self.data["peers"]

    def set_trust(self, node_id: str, trust: str) -> dict:
        for p in self.data["peers"]:
            if p["node_id"] == node_id:
                p["trust"] = trust
                p["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
                _save(self.path, self.data)
                return {"ok": True, "peer": p}
        return {"ok": False, "error": "peer not found: %s" % node_id}

    def summary(self) -> dict:
        peers = self.data["peers"]
        by_state = {}
        for p in peers:
            by_state[p.get("state", "unknown")] = by_state.get(p.get("state", "unknown"), 0) + 1
        return {
            "protocol": self.data.get("protocol"),
            "anchor": self.data.get("anchor"),
            "total": len(peers),
            "by_state": by_state,
            "verified": sum(1 for p in peers if p.get("trust") in ("verified", "trusted")),
            "registry_path": self.path,
        }


# ---------- CLI ----------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="A2A 对端注册表")
    ap.add_argument("action", choices=["add", "list", "probe", "summary", "trust"])
    ap.add_argument("--node-id", default="")
    ap.add_argument("--card-url", default="")
    ap.add_argument("--trust", default="unverified")
    ap.add_argument("--note", default="")
    ap.add_argument("--registry", default="")
    a = ap.parse_args()
    reg = PeerRegistry(a.registry or None)
    if a.action == "add":
        print(json.dumps(reg.register(a.node_id, a.card_url, a.trust, a.note),
                         ensure_ascii=False, indent=2))
    elif a.action == "list":
        print(json.dumps(reg.list_peers(), ensure_ascii=False, indent=2))
    elif a.action == "probe":
        print(json.dumps(reg.probe(a.node_id or None), ensure_ascii=False, indent=2))
    elif a.action == "trust":
        print(json.dumps(reg.set_trust(a.node_id, a.trust), ensure_ascii=False, indent=2))
    elif a.action == "summary":
        print(json.dumps(reg.summary(), ensure_ascii=False, indent=2))
