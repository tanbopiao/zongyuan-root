"""稳态通用全能中台 API v1.1
新增：流式输出(SSE)、多轮对话上下文管理、RAG重排序、Prometheus指标
"""
import json, os, requests, hashlib, time, asyncio
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI(title="ZONGYUAN-ROOT 稳态通用全能中台", version="v1.1")
app.add_middleware(CORSMiddleware, allow_origins=["https://www.huodouai.com","https://huodouai.com","http://127.0.0.1:8010"], allow_methods=["*"], allow_headers=["*"])

CONFIG = {
    "doubao_api_key": os.environ.get("DOUBAO_API_KEY", "6f8c69a7-d613-41d6-9db3-5c929a9a49e4"),
    "doubao_endpoint": os.environ.get("DOUBAO_ENDPOINT", "ep-m-20260325114252-xcd64"),
    "doubao_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    "admin_key": "36f55bdd86407a1fc12f27240ed9736ac0c5cfb33e7b89ee9c9f7d8594e0c242",
    "truth_file": "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json",
    "scenes_file": "/opt/ZONGYUAN-ROOT/gov-ai/gov-scene-templates.json",
}

# 多轮对话上下文管理（内存级，最大20轮）
CONVERSATIONS = {}
MAX_HISTORY = 20

# Prometheus指标
METRICS = {"requests_total": 0, "chat_total": 0, "rag_total": 0, "errors_total": 0, "avg_latency_ms": 0}

def verify_key(api_key: str):
    if api_key == CONFIG["admin_key"]: return True
    lic_file = "/opt/ZONGYUAN-ROOT/.license"
    if os.path.exists(lic_file):
        with open(lic_file) as f:
            lic = json.load(f)
        if lic.get("license_key") == api_key: return True
    return False

def get_conversation(conv_id: str):
    if conv_id not in CONVERSATIONS:
        CONVERSATIONS[conv_id] = {"messages": [], "created_at": datetime.now().isoformat()}
    return CONVERSATIONS[conv_id]

def add_message(conv_id: str, role: str, content: str):
    conv = get_conversation(conv_id)
    conv["messages"].append({"role": role, "content": content, "ts": datetime.now().isoformat()})
    if len(conv["messages"]) > MAX_HISTORY:
        conv["messages"] = conv["messages"][-MAX_HISTORY:]
    return conv

# ─── 1. 智能问答（支持流式+多轮）───
@app.post("/api/v1/chat/completions")
async def chat_completions(request: Request, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    conv_id = body.get("conversation_id", hashlib.md5(str(time.time()).encode()).hexdigest()[:12])
    
    METRICS["chat_total"] += 1
    METRICS["requests_total"] += 1
    start = time.time()
    
    # 多轮上下文：如果传入conv_id，合并历史
    if conv_id:
        conv = get_conversation(conv_id)
        if conv["messages"]:
            # 系统消息 + 历史 + 当前
            sys_msg = next((m for m in messages if m["role"]=="system"), None)
            user_msgs = [m for m in messages if m["role"]!="system"]
            merged = []
            if sys_msg: merged.append(sys_msg)
            merged.extend(conv["messages"][-10:])
            merged.extend(user_msgs)
            messages = merged
    
    # 真值前置召回
    truth_context = "[真值约束] 元极恒一，三态收敛，符号涌现。回答须逻辑自洽、信息准确、能量充沛。"
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] += "\n" + truth_context
    else:
        messages.insert(0, {"role": "system", "content": truth_context})
    
    try:
        if stream:
            async def generate():
                resp = requests.post(CONFIG["doubao_url"],
                    headers={"Authorization": f"Bearer {CONFIG['doubao_api_key']}", "Content-Type": "application/json"},
                    json={"model": CONFIG["doubao_endpoint"], "messages": messages, "stream": True},
                    timeout=120, stream=True)
                full_content = ""
                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data = line_str[6:]
                            if data == '[DONE]':
                                # 记录助手回复
                                add_message(conv_id, "assistant", full_content)
                                yield f"data: {json.dumps({'conversation_id': conv_id, 'done': True})}\n\n"
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices",[{}])[0].get("delta",{}).get("content","")
                                full_content += delta
                                yield line_str + "\n\n"
                            except: pass
            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            resp = requests.post(CONFIG["doubao_url"],
                headers={"Authorization": f"Bearer {CONFIG['doubao_api_key']}", "Content-Type": "application/json"},
                json={"model": CONFIG["doubao_endpoint"], "messages": messages}, timeout=60)
            result = resp.json()
            # 记录对话
            user_msg = next((m["content"] for m in body.get("messages",[]) if m["role"]=="user"), "")
            ai_msg = result.get("choices",[{}])[0].get("message",{}).get("content","")
            add_message(conv_id, "user", user_msg)
            add_message(conv_id, "assistant", ai_msg)
            result["conversation_id"] = conv_id
            METRICS["avg_latency_ms"] = (METRICS["avg_latency_ms"] + (time.time()-start)*1000) / 2
            return result
    except Exception as e:
        METRICS["errors_total"] += 1
        return {"error": str(e), "conversation_id": conv_id}

# 对话历史查询


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "platform", "version": "v2.0"}

@app.get("/status")
async def status():
    return {"service": "platform", "version": "v2.0", "status": "running"}
@app.get("/api/v1/chat/history/{conv_id}")
async def chat_history(conv_id: str, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    conv = CONVERSATIONS.get(conv_id)
    if not conv: return {"conversation_id": conv_id, "messages": [], "status": "not_found"}
    return {"conversation_id": conv_id, "messages": conv["messages"], "count": len(conv["messages"])}

# ─── 2. 知识库RAG（重排序优化）───
@app.get("/api/v1/knowledge/search")
async def knowledge_search(q: str, top_k: int = 5, rerank: bool = True, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    METRICS["rag_total"] += 1
    METRICS["requests_total"] += 1
    
    # 从真值库关键词粗筛
    with open(CONFIG["truth_file"]) as f:
        truths = json.load(f).get("truths", [])
    
    # 简单BM25风格评分
    query_terms = set(q.lower().split())
    scored = []
    for t in truths:
        content = (t.get("content","") + " " + t.get("id","")).lower()
        score = sum(1 for term in query_terms if term in content)
        if score > 0:
            scored.append((score, t))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [t for _, t in scored[:top_k]]
    
    # 重排序：基于内容相关性二次评分
    if rerank and results:
        for r in results:
            r["rerank_score"] = round(len(set(q.lower().split()) & set(r.get("content","").lower().split())) / max(len(query_terms),1), 3)
        results.sort(key=lambda x: x.get("rerank_score",0), reverse=True)
    
    return {"query": q, "results": results, "total": len(results), "rerank": rerank, "mode": "bm25+rerank"}

@app.post("/api/v1/knowledge/ingest")
async def knowledge_ingest(request: Request, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    body = await request.json()
    content = body.get("content", "")
    if not content: return {"status": "error", "message": "content不能为空"}
    
    # 追加到真值库
    with open(CONFIG["truth_file"]) as f:
        data = json.load(f)
    new_truth = {
        "id": f"TRUTH-INGEST-{int(time.time())}",
        "type": "config",
        "level": "L2",
        "content": content[:500],
        "source": "platform_ingest",
        "created_at": datetime.now().isoformat()
    }
    data.setdefault("truths", []).append(new_truth)
    with open(CONFIG["truth_file"], "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {"status": "success", "truth_id": new_truth["id"], "total_truths": len(data["truths"])}

# ─── 3. 文档处理 ───
@app.post("/api/v1/document/summarize")
async def doc_summarize(request: Request, x_api_key: str = Header(None)):
    if not verify_key(x_api_key or ""): raise HTTPException(401, "无效API Key")
    body = await request.json()
    text = body.get("text", "")
    max_length = body.get("max_length", 500)
    METRICS["requests_total"] += 1
    try:
        resp = requests.post(CONFIG["doubao_url"],
            headers={"Authorization": f"Bearer {CONFIG['doubao_api_key']}"},
            json={"model": CONFIG["doubao_endpoint"], "messages": [
                {"role": "system", "content": "你是文档摘要专家，生成简洁准确的结构化摘要。"},
                {"role": "user", "content": f"请摘要以下文本（不超过{max_length}字）：\n{text[:8000]}"}
            ]}, timeout=60)
        return {"summary": resp.json()["choices"][0]["message"]["content"], "original_length": len(text)}
    except Exception as e:
        return {"error": str(e)}

# ─── 4. 场景模板 ───
@app.get("/api/v1/scenes")
async def list_scenes(category: str = None):
    with open(CONFIG["scenes_file"]) as f:
        scenes = json.load(f)
    if isinstance(scenes, dict): scenes = scenes.get("scenes", scenes.get("templates", []))
    if category:
        scenes = [s for s in scenes if s.get("category","") == category or category in s.get("name","")]
    return {"scenes": scenes, "total": len(scenes), "categories": list(set(s.get("category","通用") for s in scenes))}

# ─── 5. 真值管理 ───
@app.get("/api/v1/truth")
async def list_truth(level: str = None, type: str = None, limit: int = 50):
    with open(CONFIG["truth_file"]) as f:
        data = json.load(f)
    truths = data.get("truths", [])
    if level: truths = [t for t in truths if t.get("level","").startswith(level)]
    if type: truths = [t for t in truths if t.get("type") == type]
    return {"truths": truths[:limit], "total": len(truths), "version": data.get("version"), "levels": {"L0":len([t for t in truths if t.get("level","").startswith("L0")]),"L1":len([t for t in truths if t.get("level","").startswith("L1")]),"L2":len([t for t in truths if t.get("level","").startswith("L2")])}}

@app.get("/api/v1/truth/{truth_id}")
async def get_truth(truth_id: str):
    with open(CONFIG["truth_file"]) as f:
        truths = json.load(f).get("truths", [])
    truth = next((t for t in truths if t.get("id") == truth_id), None)
    if not truth: raise HTTPException(404, "真值不存在")
    return truth

# ─── 6. 元秩序 ───
@app.get("/api/v1/meta/health")
async def meta_health():
    try:
        resp = requests.get("http://127.0.0.1:8009/api/v1/meta/health", timeout=5)
        return resp.json()
    except Exception as e:
        return {"status": "degraded", "error": str(e)}

@app.get("/api/v1/meta/stability")
async def meta_stability():
    try:
        resp = requests.get("http://127.0.0.1:8009/api/v1/meta/stability", timeout=5)
        return resp.json()
    except: return {"overall_stability": 0, "grade": "unknown", "logic_state": 0, "info_state": 0, "energy_state": 0, "recommendation": "元秩序API未响应"}

# ─── 7. Prometheus指标 ───
@app.get("/api/v1/metrics")
async def metrics():
    return {
        "platform_requests_total": METRICS["requests_total"],
        "platform_chat_total": METRICS["chat_total"],
        "platform_rag_total": METRICS["rag_total"],
        "platform_errors_total": METRICS["errors_total"],
        "platform_avg_latency_ms": round(METRICS["avg_latency_ms"], 2),
        "active_conversations": len(CONVERSATIONS),
        "service_status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# ─── 8. 平台信息 ───
@app.get("/api/v1/platform/info")
async def platform_info():
    return {
        "name": "ZONGYUAN-ROOT 稳态通用全能中台",
        "version": "v1.1",
        "kernel": "v9.11-META-ORDER-FORMAL",
        "capabilities": ["智能问答(流式)","知识库RAG(重排序)","文档处理","场景模板","真值管理","元秩序监控","多轮对话","Prometheus指标"],
        "api_format": "OpenAI兼容 + SSE流式",
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
