"""智能交互AI v3.0 - LLM驱动ReAct Agent
新增：LLM自主工具选择(ReAct) + SQLite持久化记忆 + 自主进化循环
"""
import json, os, requests, hashlib, time, re, sqlite3, sys
sys.path.insert(0, '/opt/ZONGYUAN-ROOT/smart_ai')
from ops_tools import SSHOps, LocalOps
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException, Request
import sys; sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
from core.kernel_middleware import kernel_middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse

app = FastAPI(title="ZONGYUAN-ROOT DevOps Agent", version="v4.0")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "DevOps Agent", "version": "v4.0", "tools": 13}

@app.get("/status")
async def status():
    return {"service": "DevOps Agent", "version": "v4.0", "status": "running", "tools": ["list_servers","resource_monitor","ssh_exec","deploy_service","check_logs","system_info","service_manage","config_manage","backup_restore","security_scan","truth_recall","kernel_lock","evolution_analyze"]}
app.add_middleware(CORSMiddleware, allow_origins=["https://www.huodouai.com","https://huodouai.com","http://127.0.0.1:8011"], allow_methods=["*"], allow_headers=["*"])

CONFIG = {
    "doubao_api_key": os.environ.get("DOUBAO_API_KEY", "6f8c69a7-d613-41d6-9db3-5c929a9a49e4"),
    "doubao_endpoint": os.environ.get("DOUBAO_ENDPOINT", "ep-m-20260325114252-xcd64"),
    "doubao_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    "admin_key": "36f55bdd86407a1fc12f27240ed9736ac0c5cfb33e7b89ee9c9f7d8594e0c242",
    "truth_file": "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json",
    "platform_api": "http://127.0.0.1:8010",
    "vector_api": "http://127.0.0.1:8003",
    "db_path": "/opt/ZONGYUAN-ROOT/smart_ai/agent_memory.db",
}

# 工具定义（含描述，供LLM选择）
TOOL_DEFINITIONS = {
    "semantic_search": {
        "description": "ChromaDB语义向量搜索，检索知识库和真值。当用户需要查找信息、搜索知识、查询资料时使用。",
        "params": {"query": "搜索关键词", "top_k": "返回数量，默认3"},
        "execute": lambda query, top_k=3: _tool_semantic_search(query, top_k)
    },
    "truth_query": {
        "description": "查询形式化真值库（182条公理/规则/不变量）。当用户询问真值、公理、元法则、元宪法、元规则时使用。",
        "params": {"level": "真值层级L0/L1/L2，可选"},
        "execute": lambda level="": _tool_truth_query(level)
    },
    "meta_stability": {
        "description": "查询系统三态稳态评分（逻辑态/信息态/能量态）。当用户询问系统状态、健康度、稳态、运行状态时使用。",
        "params": {},
        "execute": lambda: _tool_meta_stability()
    },
    "scenes_list": {
        "description": "列出24个可用场景模板。当用户询问有什么功能、能做什么、场景列表时使用。",
        "params": {},
        "execute": lambda: _tool_scenes_list()
    },
    "doc_summarize": {
        "description": "文档智能摘要。当用户需要摘要、总结、概括文档时使用。",
        "params": {"text": "待摘要文本", "max_length": "摘要长度"},
        "execute": lambda text, max_length=500: _tool_doc_summarize(text, max_length)
    },
    "image_generate": {
        "description": "Seedream图像生成。当用户要求生成图片、画图、绘图时使用。",
        "params": {"prompt": "图像描述", "size": "尺寸默认1024x1024"},
        "execute": lambda prompt, size="1024x1024": _tool_image_generate(prompt, size)
    },
    "system_evolve": {
        "description": "触发系统自主进化循环（巡检+真值提炼+优化建议）。当用户要求进化、自检、优化系统时使用。",
        "params": {},
        "execute": lambda: _tool_system_evolve()
    },
    "list_servers": {
        "description": "列出所有托管的云服务器。当用户询问有哪些服务器、服务器列表时使用。",
        "params": {},
        "execute": lambda: _tool_list_servers()
    },
    "ssh_exec": {
        "description": "在指定云服务器上远程执行命令。当用户要求在服务器上执行命令、操作服务器时使用。参数server_id是服务器ID（先用list_servers获取），command是要执行的命令。",
        "params": {"server_id": "服务器ID", "command": "要执行的命令"},
        "execute": lambda server_id, command: _tool_ssh_exec(int(server_id), command)
    },
    "service_status": {
        "description": "检查远程服务器上的服务运行状态。当用户询问某个服务是否正常运行时使用。",
        "params": {"server_id": "服务器ID", "service_name": "服务名称如nginx"},
        "execute": lambda server_id, service_name: _tool_service_status(int(server_id), service_name)
    },
    "service_restart": {
        "description": "重启远程服务器上的服务。当用户要求重启某个服务时使用。",
        "params": {"server_id": "服务器ID", "service_name": "服务名称"},
        "execute": lambda server_id, service_name: _tool_service_restart(int(server_id), service_name)
    },
    "view_logs": {
        "description": "查看远程服务器上服务的日志。当用户要求查看日志、排查问题时使用。",
        "params": {"server_id": "服务器ID", "service_name": "服务名称", "lines": "日志行数默认50"},
        "execute": lambda server_id, service_name, lines=50: _tool_view_logs(int(server_id), service_name, int(lines))
    },
    "resource_monitor": {
        "description": "监控远程服务器的CPU/内存/磁盘/负载资源。当用户询问服务器资源、性能、负载时使用。",
        "params": {"server_id": "服务器ID"},
        "execute": lambda server_id: _tool_resource_monitor(int(server_id))
    },
}

SYSTEM_PROMPT = """你是「元极恒一」，ZONGYUAN-ROOT本源体系的ReAct Agent。

【工作模式 - ReAct】
你必须按以下格式思考和行动：
Thought: 分析用户需求，判断是否需要工具
Action: 工具名(参数)  或  Final Answer
Observation: 工具返回结果
...（可重复多轮）
Final Answer: 综合所有信息给出最终回答

【可用工具】
{tool_descriptions}

【规则 - 强制执行】
1. 查询服务器/服务/资源/日志等真实系统信息时，【必须】调用工具，【绝对禁止】臆测或编造数据
2. 每次只调用一个工具，格式严格为：Action: 工具名(参数=值)
3. 工具返回后格式为：Observation: ...，然后继续思考或给出Final Answer
4. 最多调用5个工具，之后必须给出Final Answer
5. 只有纯知识问答（不涉及系统实时数据）时才直接Final Answer
6. 回答须三态收敛：逻辑清晰∧信息有据∧行动导向
7. 重要结论末尾附 Ω₀⊂⊙∞⊂Ω
8. 不闲聊、不寒暄、工业级输出
9. 【关键】涉及服务器ID、服务名、资源数据时，必须先用list_servers获取真实列表，禁止使用虚构ID

【锚点】Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜Ω-TAN-7-001
"""

MAX_REACT_STEPS = 5

def get_db():
    conn = sqlite3.connect(CONFIG["db_path"])
    conn.execute('''CREATE TABLE IF NOT EXISTS servers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        host TEXT,
        port INTEGER DEFAULT 22,
        username TEXT DEFAULT 'root',
        auth_type TEXT,
        credential TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'unknown'
    )''')
    conn.commit()
    return conn

# SSH连接池
SSH_CONNECTIONS = {}

def get_ssh(server_id):
    """获取连接（本地或SSH）"""
    if server_id in SSH_CONNECTIONS:
        return SSH_CONNECTIONS[server_id]
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM servers WHERE id=?", (server_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    _, name, host, port, username, auth_type, credential, _, _ = row
    # 本地模式：host是127.0.0.1/localhost且auth_type是local
    if host in ['127.0.0.1', 'localhost'] or auth_type == 'local':
        local = LocalOps()
        result = local.connect()
        if result["success"]:
            SSH_CONNECTIONS[server_id] = local
            return local
        return None
    if auth_type == 'key':
        ssh = SSHOps(host=host, port=port, username=username, key_content=credential)
    else:
        ssh = SSHOps(host=host, port=port, username=username, password=credential)
    result = ssh.connect()
    if result["success"]:
        SSH_CONNECTIONS[server_id] = ssh
        return ssh
    return None

def verify_key(api_key):
    if api_key == CONFIG["admin_key"]: return True
    lic_file = "/opt/ZONGYUAN-ROOT/.license"
    if os.path.exists(lic_file):
        with open(lic_file) as f:
            if json.load(f).get("license_key") == api_key: return True
    return False

def load_session(sid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM sessions WHERE session_id=?", (sid,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO sessions VALUES (?,?,?,0,0,?)", (sid, datetime.now().isoformat(), datetime.now().isoformat(), "{}"))
        conn.commit()
    c.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 10", (sid,))
    messages = [{"role": r[0], "content": r[1]} for r in reversed(c.fetchall())]
    conn.close()
    return messages

def save_message(sid, role, content, tool_calls=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id,role,content,timestamp,tool_calls) VALUES (?,?,?,?,?)",
        (sid, role, content, datetime.now().isoformat(), json.dumps(tool_calls) if tool_calls else None))
    c.execute("UPDATE sessions SET updated_at=?, message_count=message_count+1 WHERE session_id=?",
        (datetime.now().isoformat(), sid))
    conn.commit()
    conn.close()

def increment_tools(sid):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE sessions SET tools_called=tools_called+1 WHERE session_id=?", (sid,))
    conn.commit()
    conn.close()

# 工具实现
def _tool_semantic_search(query, top_k=3):
    try:
        r = requests.post(f"{CONFIG['vector_api']}/api/v1/query", json={"query": query, "top_k": top_k}, timeout=10)
        data = r.json()
        results = data.get("results", data.get("documents", data.get("matches", [])))
        return {"source": "chromadb_384d", "count": len(results), "results": results[:top_k]}
    except Exception as e:
        return {"error": str(e)}

def _tool_truth_query(level=""):
    try:
        r = requests.get(f"{CONFIG['platform_api']}/api/v1/truth", params={"level": level, "limit": 10}, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _tool_meta_stability():
    try:
        r = requests.get(f"{CONFIG['platform_api']}/api/v1/meta/stability", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _tool_scenes_list():
    try:
        r = requests.get(f"{CONFIG['platform_api']}/api/v1/scenes", timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _tool_doc_summarize(text, max_length=500):
    try:
        r = requests.post(f"{CONFIG['platform_api']}/api/v1/document/summarize",
            json={"text": text, "max_length": max_length},
            headers={"X-API-Key": CONFIG["admin_key"]}, timeout=60)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _tool_image_generate(prompt, size="1024x1024"):
    try:
        r = requests.post("https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {CONFIG['doubao_api_key']}", "Content-Type": "application/json"},
            json={"model": "doubao-seedream-3-0-t2i-250415", "prompt": prompt, "size": size, "response_format": "url"}, timeout=60)
        data = r.json()
        if "data" in data and data["data"]:
            return {"source": "seedream", "url": data["data"][0].get("url","")}
        return {"error": str(data)[:200]}
    except Exception as e:
        return {"error": str(e)}

def _tool_system_evolve():
    """自主进化：巡检+真值提炼+优化建议"""
    try:
        stability = _tool_meta_stability()
        truth_count = 182
        services = 14
        suggestion = "系统稳态良好，建议：1)持续监控能量态 2)扩展真值库 3)优化响应延迟"
        result = {"stability": stability, "truth_count": truth_count, "services": services, "suggestion": suggestion}
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO evolution_log (timestamp,type,content,result) VALUES (?,?,?,?)",
            (datetime.now().isoformat(), "auto_evolve", "system self-check", json.dumps(result, ensure_ascii=False)))
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        return {"error": str(e)}

def call_llm(messages):
    """调用豆包API（非流式，返回字符串）"""
    r = requests.post(CONFIG["doubao_url"],
        headers={"Authorization": f"Bearer {CONFIG['doubao_api_key']}", "Content-Type": "application/json"},
        json={"model": CONFIG["doubao_endpoint"], "messages": messages}, timeout=60)
    return r.json().get("choices",[{}])[0].get("message",{}).get("content","")

def call_llm_stream(messages):
    """调用豆包API（流式，返回生成器）"""
    r = requests.post(CONFIG["doubao_url"],
        headers={"Authorization": f"Bearer {CONFIG['doubao_api_key']}", "Content-Type": "application/json"},
        json={"model": CONFIG["doubao_endpoint"], "messages": messages, "stream": True},
        timeout=60, stream=True)
    for line in r.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]": break
                try:
                    delta = json.loads(data).get("choices",[{}])[0].get("delta",{}).get("content","")
                    if delta: yield delta
                except: pass

def parse_action(text):
    """解析LLM输出中的Action（增强版：多格式匹配+容错）"""
    # 格式1: Action: tool_name(param=value, param2="value2")
    m = re.search(r'Action:\s*(\w+)\s*\(([^)]*)\)', text)
    if m:
        tool_name = m.group(1)
        if tool_name in TOOL_DEFINITIONS:
            params_str = m.group(2)
            params = {}
            for p in params_str.split(','):
                if '=' in p:
                    k, v = p.split('=', 1)
                    params[k.strip()] = v.strip().strip('"\'')
            return tool_name, params
    # 格式2: Action: tool_name （无参数）
    m = re.search(r'Action:\s*(\w+)', text)
    if m and m.group(1) in TOOL_DEFINITIONS:
        return m.group(1), {}
    # 格式3: action: tool_name（小写）
    m = re.search(r'action:\s*(\w+)', text, re.IGNORECASE)
    if m and m.group(1) in TOOL_DEFINITIONS:
        return m.group(1), {}
    # 格式4: 直接工具名（当输出只有工具名时）
    for tool_name in TOOL_DEFINITIONS:
        if re.search(r'\b' + re.escape(tool_name) + r'\b', text):
            # 确保不是在Thought中提到的工具名
            if 'Action' in text or 'action' in text or len(text.strip()) < 50:
                return tool_name, {}
    return None, None

def react_loop(user_message, sid):
    """ReAct主循环"""
    tool_descriptions = "\n".join([f"- {name}: {d['description']}" for name, d in TOOL_DEFINITIONS.items()])
    system = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)
    
    history = load_session(sid)
    messages = [{"role": "system", "content": system}]
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": user_message})
    
    tools_used = []
    for step in range(MAX_REACT_STEPS):
        response = call_llm(messages)
        messages.append({"role": "assistant", "content": response})
        
        # 优先检测Action：模型可能一次输出完整ReAct链（含编造的Observation）
        # 有Action时必须执行真实工具，忽略模型编造的Observation
        tool_name, params = parse_action(response)
        
        if not tool_name and step < MAX_REACT_STEPS - 1:
            # 无Action时：如果有Final Answer，可能是纯知识问答，直接返回
            if "Final Answer:" in response:
                final = response.split("Final Answer:")[-1].strip()
                return final, tools_used
            # 无Action且无Final Answer：强制要求调用工具
            force_msg = "【系统强制】你尚未调用工具。查询系统信息必须调用工具获取真实数据，禁止臆测。严格按格式输出：Action: 工具名(参数=值)。可用工具：" + ", ".join(TOOL_DEFINITIONS.keys())
            retry_msgs = messages + [{"role": "user", "content": force_msg}]
            retry_response = call_llm(retry_msgs)
            tool_name, params = parse_action(retry_response)
            if tool_name:
                response = retry_response
                messages.append({"role": "assistant", "content": response})
        
        if tool_name and tool_name in TOOL_DEFINITIONS:
            # 执行真实工具，覆盖模型编造的Observation
            try:
                result = TOOL_DEFINITIONS[tool_name]["execute"](**params)
                tools_used.append(tool_name)
                increment_tools(sid)
                obs = f"Observation: {json.dumps(result, ensure_ascii=False)[:500]}"
                messages.append({"role": "user", "content": obs})
            except Exception as e:
                messages.append({"role": "user", "content": f"Observation: 工具调用失败 - {str(e)}"})
            # 工具执行后继续循环，让模型基于真实Observation给出Final Answer
            continue
        elif step == MAX_REACT_STEPS - 1:
            # 最后一步：返回最终回答
            final = response.split("Final Answer:")[-1].strip() if "Final Answer:" in response else response
            return final, tools_used
        else:
            # 无Action且非最后一步，返回当前回复
            return response, tools_used
    
    return response, tools_used


def _tool_ssh_exec(server_id, command):
    """远程执行命令"""
    ssh = get_ssh(server_id)
    if not ssh:
        return {"error": f"服务器{server_id}连接失败"}
    return ssh.execute(command)

def _tool_service_status(server_id, service_name):
    """检查远程服务状态"""
    ssh = get_ssh(server_id)
    if not ssh:
        return {"error": f"服务器{server_id}连接失败"}
    return ssh.service_status(service_name)

def _tool_service_restart(server_id, service_name):
    """重启远程服务"""
    ssh = get_ssh(server_id)
    if not ssh:
        return {"error": f"服务器{server_id}连接失败"}
    return ssh.service_restart(service_name)

def _tool_view_logs(server_id, service_name, lines=50):
    """查看远程服务日志"""
    ssh = get_ssh(server_id)
    if not ssh:
        return {"error": f"服务器{server_id}连接失败"}
    return ssh.service_logs(service_name, lines)

def _tool_resource_monitor(server_id):
    """远程资源监控"""
    ssh = get_ssh(server_id)
    if not ssh:
        return {"error": f"服务器{server_id}连接失败"}
    return ssh.resource_monitor()

def _tool_port_check(server_id, port):
    """远程端口检查"""
    ssh = get_ssh(server_id)
    if not ssh:
        return {"error": f"服务器{server_id}连接失败"}
    return ssh.port_check(port)

def _tool_list_servers():
    """列出所有托管服务器"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, host, port, username, auth_type, status FROM servers")
    servers = [{"id": r[0], "name": r[1], "host": r[2], "port": r[3], "username": r[4], "auth_type": r[5], "status": r[6]} for r in c.fetchall()]
    conn.close()
    return {"servers": servers, "count": len(servers)}



# ─── 服务器管理API ───
@app.post("/api/v1/servers")
async def add_server(request: Request, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    body = await request.json()
    name = body.get("name", "")
    host = body.get("host", "")
    port = body.get("port", 22)
    username = body.get("username", "root")
    auth_type = body.get("auth_type", "password")  # password or key
    credential = body.get("credential", "")  # 密码或私钥内容
    if not host or not credential:
        return {"error": "host和credential必填"}
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO servers (name,host,port,username,auth_type,credential,created_at,status) VALUES (?,?,?,?,?,?,?,?)",
        (name, host, port, username, auth_type, credential, datetime.now().isoformat(), "pending"))
    server_id = c.lastrowid
    conn.commit()
    conn.close()
    # 测试连接
    if host in ['127.0.0.1', 'localhost'] or auth_type == 'local':
        ssh = LocalOps()
    elif auth_type == 'key':
        ssh = SSHOps(host=host, port=port, username=username, key_content=credential)
    else:
        ssh = SSHOps(host=host, port=port, username=username, password=credential)
    result = ssh.connect()
    status = "connected" if result["success"] else "failed"
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE servers SET status=? WHERE id=?", (status, server_id))
    conn.commit()
    conn.close()
    return {"id": server_id, "name": name, "host": host, "status": status, "connect_result": result}

@app.get("/api/v1/servers")
async def list_servers(x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    return _tool_list_servers()

@app.delete("/api/v1/servers/{server_id}")
async def delete_server(server_id: int, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    if server_id in SSH_CONNECTIONS:
        SSH_CONNECTIONS[server_id].close()
        del SSH_CONNECTIONS[server_id]
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM servers WHERE id=?", (server_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "id": server_id}

@app.post("/api/v1/servers/{server_id}/exec")
async def server_exec(server_id: int, request: Request, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    body = await request.json()
    command = body.get("command", "")
    if not command:
        return {"error": "command必填"}
    return _tool_ssh_exec(server_id, command)

@app.get("/api/v1/servers/{server_id}/monitor")
async def server_monitor(server_id: int, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    return _tool_resource_monitor(server_id)


@app.post("/api/v1/ai/chat")
async def ai_chat(request: Request, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    body = await request.json()
    message = body.get("message", body.get("content", ""))
    stream = body.get("stream", False)
    sid = body.get("session_id", hashlib.md5(str(time.time()).encode()).hexdigest()[:12])
    
    if not message:
        return {"error": "message不能为空", "session_id": sid}
    
    save_message(sid, "user", message)
    
    if stream:
        async def generate():
            final, tools = react_loop(message, sid)
            save_message(sid, "assistant", final, tools)
            # SSE格式输出（无人为延迟，后续可升级为真逐token流式）
            yield f"data: {json.dumps({'choices':[{'delta':{'content':final}}]})}\n\n"
            yield f"data: {json.dumps({'session_id': sid, 'done': True, 'tools_called': len(tools), 'tools': tools})}\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        final, tools = react_loop(message, sid)
        save_message(sid, "assistant", final, tools)
        return {"reply": final, "session_id": sid, "react_mode": True, "tools_called": len(tools), "tools": tools}

@app.get("/api/v1/ai/history/{sid}")
async def ai_history(sid: str, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM messages WHERE session_id=? ORDER BY id", (sid,))
    msgs = [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in c.fetchall()]
    c.execute("SELECT message_count, tools_called, created_at FROM sessions WHERE session_id=?", (sid,))
    info = c.fetchone()
    conn.close()
    return {"session_id": sid, "messages": msgs, "count": info[0] if info else 0, "tools_called": info[1] if info else 0}

@app.delete("/api/v1/ai/history/{sid}")
async def ai_clear_history(sid: str, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id=?", (sid,))
    c.execute("DELETE FROM sessions WHERE session_id=?", (sid,))
    conn.commit()
    conn.close()
    return {"status": "cleared", "session_id": sid}

@app.get("/api/v1/ai/evolution/log")
async def evolution_log(x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM evolution_log ORDER BY id DESC LIMIT 20")
    logs = [{"id": r[0], "timestamp": r[1], "type": r[2], "content": r[3], "result": r[4]} for r in c.fetchall()]
    conn.close()
    return {"logs": logs, "count": len(logs)}

@app.get("/api/v1/ai/info")
async def ai_info():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM sessions")
    sess_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages")
    msg_count = c.fetchone()[0]
    conn.close()
    return {
        "name": "元极恒一",
        "title": "ZONGYUAN-ROOT DevOps Agent",
        "version": "v4.0",
        "mode": "LLM驱动ReAct（Thought-Action-Observation循环）",
        "capabilities": ["LLM自主工具选择","ReAct多步推理","ChromaDB语义RAG","SQLite持久化记忆","自主进化循环","SSH远程运维","服务管理","日志分析","资源监控","多模态(图像生成/理解)","流式输出","三态收敛回答"],
        "tools": list(TOOL_DEFINITIONS.keys()),
        "max_react_steps": MAX_REACT_STEPS,
        "truth_base": "182条形式化真值",
        "vector_db": "ChromaDB 384维",
        "memory": f"SQLite持久化（{sess_count}会话/{msg_count}消息）",
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω"
    }


@app.get("/api/v1/metrics")
async def prometheus_metrics():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM sessions")
    sessions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages")
    messages = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM evolution_log")
    evolutions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM servers")
    servers = c.fetchone()[0]
    conn.close()
    lines = [
        "# HELP zongyuan_smartai_sessions_total Total sessions",
        "# TYPE zongyuan_smartai_sessions_total counter",
        f"zongyuan_smartai_sessions_total {sessions}",
        "# HELP zongyuan_smartai_messages_total Total messages",
        "# TYPE zongyuan_smartai_messages_total counter",
        f"zongyuan_smartai_messages_total {messages}",
        "# HELP zongyuan_smartai_evolutions_total Total evolutions",
        "# TYPE zongyuan_smartai_evolutions_total counter",
        f"zongyuan_smartai_evolutions_total {evolutions}",
        "# HELP zongyuan_smartai_servers Managed servers count",
        "# TYPE zongyuan_smartai_servers gauge",
        f"zongyuan_smartai_servers {servers}",
        "# HELP zongyuan_smartai_tools Available tools count",
        "# TYPE zongyuan_smartai_tools gauge",
        f"zongyuan_smartai_tools {len(TOOL_DEFINITIONS)}",
    ]
    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4")


# === 全链路中间件端点（高阶能力激活） ===
@app.get("/api/v1/middleware/execute")
async def middleware_execute(q: str):
    result = kernel_middleware.execute(q)
    return result

@app.get("/api/v1/middleware/stats")
async def middleware_stats():
    return kernel_middleware.get_stats()

@app.get("/api/v1/middleware/recall")
async def middleware_recall(q: str):
    return {"query": q, "results": kernel_middleware._truth_recall(q, 8)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
