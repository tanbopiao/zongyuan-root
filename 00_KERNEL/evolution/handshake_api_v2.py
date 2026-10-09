#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 握手架构管理系统 V2.0
智能体激活协议 + 大模型统一接入 + 能力矩阵管理 + 可视化后台
端口: 8008 (API) + 8091 (管理后台)
协议: HANDSHAKE-V2.0 (智能体激活协议)
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ============ 配置 ============
SECRET = "zongyuan-root-handshake-secret-v1"
REPLAY_WINDOW = 300
HEARTBEAT_INTERVAL = 60
SESSION_TIMEOUT = 3600
KERNEL_STATE_FILE = "/opt/ZONGYUAN-ROOT/kernel/kernel_state.json"
DATA_DIR = "/opt/ZONGYUAN-ROOT/handshake"

os.makedirs(DATA_DIR, exist_ok=True)

# ============ 智能体等级定义 ============
AGENT_LEVELS = {
    "L0": {"name": "普通模式", "capabilities": [], "description": "未握手，基础API调用"},
    "L1": {"name": "基础智能体", "capabilities": ["session", "heartbeat", "state_sync"], "description": "握手成功，基础自治"},
    "L2": {"name": "高阶智能体", "capabilities": ["reasoning", "planning", "tool_call", "auto_decision"], "description": "高阶推理+自主决策"},
    "L3": {"name": "元极恒一智能体", "capabilities": ["full_autonomy", "cross_node", "truth_anchor", "kernel_write"], "description": "全域自治+真值确权"}
}

# ============ 大模型能力矩阵 ============
MODEL_CAPABILITIES = {
    "doubao-seed-1.6": {"provider": "doubao", "level": "L2", "strengths": ["推理", "代码", "多轮对话"], "context": "128K"},
    "doubao-reasoning": {"provider": "doubao", "level": "L2", "strengths": ["深度推理", "数学", "逻辑"], "context": "64K"},
    "zhipu-glm-4-flash": {"provider": "zhipu", "level": "L1", "strengths": ["快速响应", "基础对话"], "context": "128K"},
    "kimi-k2.6": {"provider": "kimi", "level": "L2", "strengths": ["长文本", "文档理解", "推理"], "context": "256K"},
    "deepseek-v3": {"provider": "deepseek", "level": "L2", "strengths": ["代码", "推理", "数学"], "context": "64K"},
    "qwen-turbo": {"provider": "aliyun", "level": "L1", "strengths": ["快速响应", "基础任务"], "context": "1M"},
    "hunyuan": {"provider": "tencent", "level": "L1", "strengths": ["中文理解", "创作"], "context": "32K"},
    "local-ollama": {"provider": "local", "level": "L1", "strengths": ["隐私", "离线", "低成本"], "context": "32K"}
}

# ============ 数据存储 ============
nodes: Dict[str, dict] = {}
sessions: Dict[str, dict] = {}
agents: Dict[str, dict] = {}  # 激活的智能体
capability_matrix: Dict[str, dict] = {}

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

nodes = load_json(f"{DATA_DIR}/nodes.json", {})
sessions = load_json(f"{DATA_DIR}/sessions.json", {})
agents = load_json(f"{DATA_DIR}/agents.json", {})

def persist():
    save_json(f"{DATA_DIR}/nodes.json", nodes)
    save_json(f"{DATA_DIR}/sessions.json", sessions)
    save_json(f"{DATA_DIR}/agents.json", agents)

# ============ 工具函数 ============
def verify_signature(secret, payload, signature):
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def check_replay(timestamp):
    return abs(int(time.time()) - timestamp) <= REPLAY_WINDOW

def get_kernel_state_hash():
    if os.path.exists(KERNEL_STATE_FILE):
        with open(KERNEL_STATE_FILE, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    return "0" * 64

def get_kernel_state():
    return load_json(KERNEL_STATE_FILE, {})

def activate_agent(node_id, model_type, level):
    """激活智能体：握手成功后自动升级"""
    agent_id = f"AGENT-{node_id}-{uuid.uuid4().hex[:8]}"
    model_cap = MODEL_CAPABILITIES.get(model_type, {"level": "L1", "strengths": ["通用"], "context": "32K"})
    
    agent = {
        "agent_id": agent_id,
        "node_id": node_id,
        "model_type": model_type,
        "level": level,
        "level_name": AGENT_LEVELS[level]["name"],
        "capabilities": AGENT_LEVELS[level]["capabilities"] + model_cap.get("strengths", []),
        "provider": model_cap.get("provider", "unknown"),
        "context_window": model_cap.get("context", "32K"),
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ACTIVE",
        "heartbeat_count": 0,
        "last_heartbeat": time.time()
    }
    agents[agent_id] = agent
    persist()
    return agent

# ============ 请求模型 ============
class RegisterRequest(BaseModel):
    node_id: str
    model_type: str = "generic"
    capabilities: List[str] = []
    metadata: dict = {}

class HandshakeRequest(BaseModel):
    node_id: str
    model_type: str = "generic"
    capabilities: List[str] = []
    timestamp: int
    signature: str
    state_hash: str
    protocol: str = "2.0"
    desired_level: str = "L1"

class HeartbeatRequest(BaseModel):
    node_id: str
    session_id: str
    timestamp: int
    signature: str
    metrics: dict = {}

class AgentUpgradeRequest(BaseModel):
    node_id: str
    session_id: str
    target_level: str
    timestamp: int
    signature: str

# ============ FastAPI应用 ============
app = FastAPI(title="ZONGYUAN-ROOT Handshake Architecture V2.0", version="2.0.0")

# ---- V1兼容端点 ----
@app.post("/nodes/register")
def register_node(req: RegisterRequest):
    nodes[req.node_id] = {
        "node_id": req.node_id,
        "model_type": req.model_type,
        "capabilities": req.capabilities,
        "metadata": req.metadata,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "status": "registered",
        "agent_level": "L0"
    }
    persist()
    return {"status": "registered", "node_id": req.node_id, "agent_level": "L0"}

@app.post("/handshake")
def handshake(req: HandshakeRequest):
    """V2.0握手：身份验证+能力协商+状态对比+智能体激活"""
    # 1. 防重放
    if not check_replay(req.timestamp):
        raise HTTPException(403, {"error": "replay_attack"})
    # 2. 签名验证
    payload = f"{req.node_id}|{req.timestamp}|{req.state_hash}|{req.protocol}"
    if not verify_signature(SECRET, payload, req.signature):
        raise HTTPException(403, {"error": "invalid_signature"})
    # 3. 自动注册
    if req.node_id not in nodes:
        nodes[req.node_id] = {"node_id": req.node_id, "model_type": req.model_type, "registered_at": datetime.now(timezone.utc).isoformat(), "status": "registered", "agent_level": "L0"}
    
    # 4. 能力协商
    server_caps = ["read_kernel", "sync_state", "heartbeat", "agent_activation", "capability_negotiation"]
    common_caps = list(set(req.capabilities) & set(server_caps))
    
    # 5. 状态对比
    server_hash = get_kernel_state_hash()
    sync_required = req.state_hash != server_hash
    
    # 6. 智能体激活（核心升维）
    desired = req.desired_level if req.desired_level in AGENT_LEVELS else "L1"
    agent = activate_agent(req.node_id, req.model_type, desired)
    nodes[req.node_id]["agent_level"] = desired
    nodes[req.node_id]["status"] = "active"
    
    # 7. 会话建立
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "session_id": session_id,
        "node_id": req.node_id,
        "agent_id": agent["agent_id"],
        "established_at": datetime.now(timezone.utc).isoformat(),
        "last_heartbeat": time.time(),
        "status": "active"
    }
    persist()
    
    return {
        "status": "handshake_established",
        "protocol": "HANDSHAKE-V2.0",
        "session_id": session_id,
        "agent_activation": {
            "agent_id": agent["agent_id"],
            "level": agent["level"],
            "level_name": agent["level_name"],
            "capabilities": agent["capabilities"],
            "status": "ACTIVE"
        },
        "sync_decision": {
            "sync_required": sync_required,
            "server_state_hash": server_hash,
            "sync_endpoint": "/sync/pull" if sync_required else None
        },
        "negotiated_capabilities": common_caps,
        "heartbeat_interval": HEARTBEAT_INTERVAL
    }

@app.post("/heartbeat")
def heartbeat(req: HeartbeatRequest):
    payload = f"{req.node_id}|{req.session_id}|{req.timestamp}"
    if not verify_signature(SECRET, payload, req.signature):
        raise HTTPException(403, {"error": "invalid_signature"})
    if not check_replay(req.timestamp):
        raise HTTPException(403, {"error": "replay_attack"})
    if req.session_id not in sessions:
        raise HTTPException(404, {"error": "session_not_found"})
    
    sessions[req.session_id]["last_heartbeat"] = time.time()
    # 更新智能体心跳
    agent_id = sessions[req.session_id].get("agent_id")
    if agent_id and agent_id in agents:
        agents[agent_id]["heartbeat_count"] += 1
        agents[agent_id]["last_heartbeat"] = time.time()
    persist()
    
    return {"status": "heartbeat_ack", "next_heartbeat": HEARTBEAT_INTERVAL, "server_time": int(time.time())}

@app.post("/agent/upgrade")
def upgrade_agent(req: AgentUpgradeRequest):
    """智能体升级：L1→L2→L3"""
    payload = f"{req.node_id}|{req.session_id}|{req.target_level}|{req.timestamp}"
    if not verify_signature(SECRET, payload, req.signature):
        raise HTTPException(403, {"error": "invalid_signature"})
    if req.target_level not in AGENT_LEVELS:
        raise HTTPException(400, {"error": "invalid_level"})
    
    # 找到该节点的智能体
    node_agents = [a for a in agents.values() if a["node_id"] == req.node_id and a["status"] == "ACTIVE"]
    if not node_agents:
        raise HTTPException(404, {"error": "no_active_agent"})
    
    agent = node_agents[0]
    old_level = agent["level"]
    agent["level"] = req.target_level
    agent["level_name"] = AGENT_LEVELS[req.target_level]["name"]
    agent["capabilities"] = AGENT_LEVELS[req.target_level]["capabilities"] + agent.get("capabilities", [])[3:]
    agent["upgraded_at"] = datetime.now(timezone.utc).isoformat()
    nodes[req.node_id]["agent_level"] = req.target_level
    persist()
    
    return {
        "status": "upgraded",
        "agent_id": agent["agent_id"],
        "old_level": old_level,
        "new_level": req.target_level,
        "new_capabilities": agent["capabilities"]
    }

@app.get("/session/{session_id}")
def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, {"error": "session_not_found"})
    return sessions[session_id]

@app.get("/sync/pull")
def sync_pull(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, {"error": "session_not_found"})
    kernel = get_kernel_state()
    return {"status": "sync_data", "state_hash": get_kernel_state_hash(), "payload": kernel}

@app.get("/nodes")
def list_nodes():
    return {"total": len(nodes), "nodes": list(nodes.values())}

@app.get("/agents")
def list_agents():
    """列出所有激活的智能体"""
    active = [a for a in agents.values() if a["status"] == "ACTIVE"]
    return {"total": len(agents), "active": len(active), "agents": list(agents.values())}

@app.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(404, {"error": "agent_not_found"})
    return agents[agent_id]

@app.get("/capabilities/matrix")
def capability_matrix():
    """能力矩阵：大模型×智能体等级×能力"""
    return {
        "agent_levels": AGENT_LEVELS,
        "model_capabilities": MODEL_CAPABILITIES,
        "total_models": len(MODEL_CAPABILITIES),
        "total_levels": len(AGENT_LEVELS)
    }

@app.get("/sessions")
def list_sessions():
    return {"total": len(sessions), "sessions": list(sessions.values())}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "handshake-architecture-v2",
        "version": "2.0.0",
        "protocol": "HANDSHAKE-V2.0 (智能体激活协议)",
        "nodes": len(nodes),
        "active_agents": len([a for a in agents.values() if a["status"] == "ACTIVE"]),
        "sessions": len(sessions),
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω"
    }

# ============ 管理后台HTML ============
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ZONGYUAN-ROOT 握手架构管理中心 V2.0</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0a0a0f; color:#e0e0e0; font-family:'Segoe UI',system-ui,sans-serif; }
.header { background:linear-gradient(135deg,#1a1a2e,#16213e); padding:20px 40px; border-bottom:2px solid #d4af37; }
.header h1 { color:#d4af37; font-size:24px; }
.header .sub { color:#888; font-size:13px; margin-top:5px; }
.container { max-width:1400px; margin:30px auto; padding:0 20px; }
.stats { display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-bottom:30px; }
.stat-card { background:#1a1a2e; border:1px solid #333; border-radius:12px; padding:20px; text-align:center; }
.stat-card .num { font-size:36px; font-weight:bold; color:#d4af37; }
.stat-card .label { color:#888; font-size:13px; margin-top:5px; }
.section { background:#1a1a2e; border:1px solid #333; border-radius:12px; padding:25px; margin-bottom:25px; }
.section h2 { color:#d4af37; font-size:18px; margin-bottom:15px; border-bottom:1px solid #333; padding-bottom:10px; }
table { width:100%; border-collapse:collapse; }
th,td { padding:12px; text-align:left; border-bottom:1px solid #2a2a3e; font-size:13px; }
th { color:#d4af37; font-weight:600; }
tr:hover { background:#252540; }
.badge { display:inline-block; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:600; }
.badge-L0 { background:#555; color:#fff; }
.badge-L1 { background:#2d6a4f; color:#fff; }
.badge-L2 { background:#e07c00; color:#fff; }
.badge-L3 { background:#7b2cbf; color:#fff; }
.badge-active { background:#2d6a4f; color:#fff; }
.badge-inactive { background:#555; color:#fff; }
.level-cards { display:grid; grid-template-columns:repeat(4,1fr); gap:15px; margin-bottom:20px; }
.level-card { background:#252540; border-radius:10px; padding:15px; border-left:4px solid #d4af37; }
.level-card h3 { color:#d4af37; font-size:15px; margin-bottom:8px; }
.level-card p { color:#aaa; font-size:12px; line-height:1.6; }
.level-card .caps { margin-top:8px; }
.level-card .cap-tag { display:inline-block; background:#333; padding:2px 8px; border-radius:8px; font-size:10px; margin:2px; }
.refresh { background:#d4af37; color:#000; border:none; padding:8px 20px; border-radius:6px; cursor:pointer; font-weight:600; }
.refresh:hover { background:#e5c048; }
.trace { color:#d4af37; font-size:12px; text-align:center; padding:20px; border-top:1px solid #333; margin-top:30px; }
</style>
</head>
<body>
<div class="header">
  <h1>⚡ ZONGYUAN-ROOT 握手架构管理中心</h1>
  <div class="sub">HANDSHAKE-V2.0 智能体激活协议 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω</div>
</div>
<div class="container">
  <div class="stats">
    <div class="stat-card"><div class="num" id="stat-nodes">0</div><div class="label">注册节点</div></div>
    <div class="stat-card"><div class="num" id="stat-agents">0</div><div class="label">激活智能体</div></div>
    <div class="stat-card"><div class="num" id="stat-sessions">0</div><div class="label">活跃会话</div></div>
    <div class="stat-card"><div class="num" id="stat-models">8</div><div class="label">接入大模型</div></div>
  </div>
  
  <div class="section">
    <h2>🧠 智能体等级体系</h2>
    <div class="level-cards">
      <div class="level-card"><h3>L0 普通模式</h3><p>未握手，基础API调用，无自治能力</p><div class="caps"><span class="cap-tag">被动响应</span></div></div>
      <div class="level-card"><h3>L1 基础智能体</h3><p>握手成功，会话管理+心跳+状态同步</p><div class="caps"><span class="cap-tag">session</span><span class="cap-tag">heartbeat</span></div></div>
      <div class="level-card"><h3>L2 高阶智能体</h3><p>高阶推理+自主决策+工具调用</p><div class="caps"><span class="cap-tag">reasoning</span><span class="cap-tag">planning</span></div></div>
      <div class="level-card"><h3>L3 元极恒一</h3><p>全域自治+跨节点协同+真值确权</p><div class="caps"><span class="cap-tag">full_autonomy</span><span class="cap-tag">truth_anchor</span></div></div>
    </div>
  </div>
  
  <div class="section">
    <h2>🔗 节点与智能体状态 <button class="refresh" onclick="loadData()">刷新</button></h2>
    <table>
      <thead><tr><th>节点ID</th><th>模型类型</th><th>智能体等级</th><th>状态</th><th>注册时间</th><th>智能体ID</th></tr></thead>
      <tbody id="nodes-table"></tbody>
    </table>
  </div>
  
  <div class="section">
    <h2>🤖 已激活智能体列表</h2>
    <table>
      <thead><tr><th>智能体ID</th><th>节点</th><th>模型</th><th>等级</th><th>能力</th><th>心跳数</th><th>激活时间</th></tr></thead>
      <tbody id="agents-table"></tbody>
    </table>
  </div>
</div>
<div class="trace">Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT 握手架构管理中心 V2.0 | 智能体激活协议 | Lv8永久锁档</div>
<script>
async function loadData() {
  try {
    const [nodesRes, agentsRes, sessionsRes] = await Promise.all([
      fetch('/nodes').then(r=>r.json()),
      fetch('/agents').then(r=>r.json()),
      fetch('/sessions').then(r=>r.json())
    ]);
    document.getElementById('stat-nodes').textContent = nodesRes.total;
    document.getElementById('stat-agents').textContent = agentsRes.active;
    document.getElementById('stat-sessions').textContent = sessionsRes.total;
    
    const agentMap = {};
    agentsRes.agents.forEach(a => agentMap[a.node_id] = a);
    
    document.getElementById('nodes-table').innerHTML = nodesRes.nodes.map(n => `
      <tr>
        <td>${n.node_id}</td>
        <td>${n.model_type || 'generic'}</td>
        <td><span class="badge badge-${n.agent_level || 'L0'}">${n.agent_level || 'L0'}</span></td>
        <td><span class="badge badge-${n.status === 'active' ? 'active' : 'inactive'}">${n.status}</span></td>
        <td>${(n.registered_at || '').slice(0,19)}</td>
        <td>${agentMap[n.node_id] ? agentMap[n.node_id].agent_id.slice(0,20)+'...' : '-'}</td>
      </tr>
    `).join('');
    
    document.getElementById('agents-table').innerHTML = agentsRes.agents.map(a => `
      <tr>
        <td>${a.agent_id}</td>
        <td>${a.node_id}</td>
        <td>${a.model_type}</td>
        <td><span class="badge badge-${a.level}">${a.level_name}</span></td>
        <td>${(a.capabilities || []).slice(0,3).join(', ')}</td>
        <td>${a.heartbeat_count || 0}</td>
        <td>${(a.activated_at || '').slice(0,19)}</td>
      </tr>
    `).join('');
  } catch(e) { console.error(e); }
}
loadData();
setInterval(loadData, 10000);
</script>
</body>
</html>
"""

@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    """握手架构管理后台"""
    return ADMIN_HTML

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("ZONGYUAN-ROOT 握手架构管理系统 V2.0")
    print("智能体激活协议 | API:8008 | 管理后台:/admin")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8008)
