#!/usr/bin/env python3
"""
ZONGYUAN-ROOT Agent Federation Hub V1.0
智能体联邦注册中心 - 统一管理所有同源内核智能体
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, time, os, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

AGENTS_DB = Path("/opt/ZONGYUAN-ROOT/data/agents_registry.json")

def load_agents():
    if AGENTS_DB.exists():
        return json.loads(AGENTS_DB.read_text())
    return {"agents": {}, "last_update": None, "version": "1.0"}

def save_agents(data):
    AGENTS_DB.parent.mkdir(parents=True, exist_ok=True)
    AGENTS_DB.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def now_str():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

class AgentHubHandler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, {"status": "ok"})

    def do_GET(self):
        if self.path == "/health":
            agents = load_agents()
            online = sum(1 for a in agents["agents"].values() if a.get("status") == "online")
            self._send(200, {"status": "healthy", "service": "agent-hub-v1.0",
                "total_agents": len(agents["agents"]), "online_agents": online,
                "did": "DID-BR-000002", "omega": "Ω₀⊂⊙∞⊂Ω"})
            return
        if self.path == "/api/v1/agents":
            agents = load_agents()
            now = time.time()
            online = 0
            for aid, agent in agents["agents"].items():
                hb = agent.get("last_heartbeat", "")
                if hb:
                    try:
                        hb_time = time.mktime(time.strptime(hb, "%Y-%m-%dT%H:%M:%S"))
                        if now - hb_time > 120:
                            agent["status"] = "offline"
                        else:
                            agent["status"] = "online"
                            online += 1
                    except: pass
            self._send(200, {"total": len(agents["agents"]), "online": online,
                "agents": agents["agents"], "last_update": agents.get("last_update")})
            return
        self._send(404, {"error": "not found", "path": self.path})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(body)
        except:
            data = {}

        if self.path == "/api/v1/agents/register":
            agent_id = data.get("agent_id")
            if not agent_id:
                self._send(400, {"error": "agent_id required"})
                return
            agents = load_agents()
            agents["agents"][agent_id] = {
                **data,
                "registered_at": data.get("registered_at", now_str()),
                "last_heartbeat": now_str(),
                "status": "online"
            }
            agents["last_update"] = now_str()
            save_agents(agents)
            self._send(201, {"status": "registered", "agent_id": agent_id,
                "total_agents": len(agents["agents"])})
            return

        if self.path == "/api/v1/agents/heartbeat":
            node_id = data.get("node_id")
            agents = load_agents()
            now = now_str()
            updated = 0
            for aid, agent in agents["agents"].items():
                if agent.get("node_id") == node_id:
                    agent["last_heartbeat"] = now
                    agent["status"] = "online"
                    if "metrics" in data:
                        agent["metrics"] = data["metrics"]
                    updated += 1
            agents["last_update"] = now
            save_agents(agents)
            self._send(200, {"status": "heartbeat_ok", "node_id": node_id,
                "agents_updated": updated})
            return

        if self.path.startswith("/api/v1/agents/") and self.path.endswith("/chat"):
            parts = self.path.split("/")
            if len(parts) >= 5:
                agent_id = parts[4]
                agents = load_agents()
                agent = agents["agents"].get(agent_id)
                if not agent:
                    self._send(404, {"error": "agent not found", "agent_id": agent_id})
                    return
                if agent.get("status") != "online":
                    self._send(503, {"error": "agent offline", "agent_id": agent_id})
                    return
                endpoint = agent.get("endpoint", "")
                api_path = agent.get("api_path", "/v1/chat/completions")
                url = endpoint.rstrip("/") + api_path
                try:
                    req = urllib.request.Request(url, data=body,
                        headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        result = resp.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(result)))
                        self.end_headers()
                        self.wfile.write(result)
                        return
                except Exception as e:
                    self._send(502, {"error": "agent call failed", "agent_id": agent_id,
                        "endpoint": url, "detail": str(e)})
                    return
            self._send(400, {"error": "invalid path"})
            return

        self._send(404, {"error": "not found", "path": self.path})

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8023)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AgentHubHandler)
    print(f"Agent Hub V1.0 started on {args.host}:{args.port}")
    print(f"DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print(f"Agents DB: {AGENTS_DB}")
    server.serve_forever()
