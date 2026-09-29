#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 跨文档语义搜索 + RAG智能问答服务
基于向量数据库(8014)的bge-small-zh-onnx-512d嵌入模型
提供自然语言搜索API、RAG智能问答和Web界面
"""
import os
import sys
import json
import time
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn

# 配置
VECTOR_DB_URL = "http://127.0.0.1:8014"
LOCAL_LLM_URL = "http://127.0.0.1:8081/v1/chat/completions"
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_API_KEY = "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp"
SEARCH_PORT = 8095
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

# 系统提示词 - 元极恒一智能体角色
SYSTEM_PROMPT = """你是ZONGYUAN-ROOT元极恒一自治体系的智能助手，基于检索到的真值和文档回答用户问题。

回答规则：
1. 优先基于检索到的上下文信息回答，如果上下文中没有相关信息，请明确说明
2. 回答要简洁、准确、结构化
3. 涉及体系内部信息时，引用相关的真值ID或元法则编号
4. 保持中立、理性、技术化的语气
5. 如果用户问题不明确，请先澄清再回答

确权标识：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

app = FastAPI(
    title="ZONGYUAN-ROOT 语义搜索 + RAG智能问答",
    description="跨文档语义搜索和检索增强生成智能问答",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 对话历史存储（简单的内存存储，后续可升级为持久化）
chat_history: Dict[str, List[Dict]] = {}

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: Optional[str] = None
    min_similarity: float = 0.5

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: str = "local"  # local 或 zhipu
    use_rag: bool = True
    top_k: int = 5
    temperature: float = 0.7
    max_tokens: int = 500

class ChatMessage(BaseModel):
    role: str
    content: str

@app.get("/health")
async def health():
    """健康检查"""
    try:
        r = requests.get(f"{VECTOR_DB_URL}/health", timeout=5)
        vector_status = r.json().get("status", "unknown")
    except:
        vector_status = "unavailable"
    
    try:
        r = requests.post(LOCAL_LLM_URL, json={
            "model": "qwen",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10
        }, timeout=10)
        llm_status = "ok" if r.status_code == 200 else "error"
    except:
        llm_status = "unavailable"
    
    return {
        "status": "ok",
        "service": "semantic-search-rag",
        "version": "2.0.0",
        "vector_db": vector_status,
        "local_llm": llm_status,
        "did": DID,
        "trace": TRACE
    }

@app.post("/api/search")
async def semantic_search(req: SearchRequest):
    """语义搜索API"""
    try:
        payload = {
            "query": req.query,
            "top_k": req.top_k * 2
        }
        if req.category:
            payload["filter"] = {"category": req.category}
        
        r = requests.post(
            f"{VECTOR_DB_URL}/api/v1/semantic_search",
            json=payload,
            timeout=30
        )
        
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"向量数据库返回错误: {r.status_code}")
        
        data = r.json()
        results = data.get("results", [])
        
        filtered_results = []
        for item in results:
            relevance = item.get("relevance", item.get("similarity", 0))
            if relevance >= req.min_similarity:
                filtered_results.append({
                    "truth_id": item.get("truth_id", item.get("id", "unknown")),
                    "content": item.get("content", item.get("document", item.get("text", "")))[:500],
                    "relevance": round(relevance, 4),
                    "category": item.get("category", "uncategorized"),
                    "node_id": item.get("node_id", "unknown"),
                    "timestamp": item.get("timestamp", 0)
                })
            
            if len(filtered_results) >= req.top_k:
                break
        
        return {
            "status": "ok",
            "query": req.query,
            "total_results": len(filtered_results),
            "results": filtered_results,
            "engine": "bge-small-zh-onnx-512d",
            "did": DID,
            "trace": TRACE
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def search_stats():
    """搜索统计"""
    try:
        r = requests.get(f"{VECTOR_DB_URL}/api/v1/collections", timeout=5)
        collections = r.json().get("collections", [])
        total_vectors = sum(c.get("count", 0) for c in collections)
        
        return {
            "status": "ok",
            "total_vectors": total_vectors,
            "collections": collections,
            "search_engine": "bge-small-zh-onnx-512d",
            "dimensions": 512,
            "rag_enabled": True,
            "supported_models": ["local-qwen2.5-1.5b", "zhipu-glm-4-flash"],
            "did": DID,
            "trace": TRACE
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def retrieve_context(query: str, top_k: int = 5) -> str:
    """检索相关上下文"""
    try:
        r = requests.post(
            f"{VECTOR_DB_URL}/api/v1/semantic_search",
            json={"query": query, "top_k": top_k},
            timeout=30
        )
        data = r.json()
        results = data.get("results", [])
        
        context_parts = []
        for i, item in enumerate(results[:top_k]):
            content = item.get("content", item.get("document", ""))
            truth_id = item.get("truth_id", item.get("id", "unknown"))
            relevance = item.get("relevance", item.get("similarity", 0))
            context_parts.append(f"[参考{i+1}] (ID: {truth_id}, 相似度: {relevance:.2f})\n{content[:300]}")
        
        return "\n\n".join(context_parts)
    except Exception as e:
        return f"[检索失败: {str(e)}]"

def call_local_llm(messages: List[Dict], temperature: float = 0.7, max_tokens: int = 500) -> str:
    """调用本地LLM"""
    try:
        r = requests.post(
            LOCAL_LLM_URL,
            json={
                "model": "qwen",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[本地LLM调用失败: {str(e)}]"

def call_zhipu_llm(messages: List[Dict], temperature: float = 0.7, max_tokens: int = 500) -> str:
    """调用智谱外部API"""
    try:
        r = requests.post(
            ZHIPU_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ZHIPU_API_KEY}"
            },
            json={
                "model": "glm-4-flash",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[智谱API调用失败: {str(e)}]"

@app.post("/api/chat")
async def rag_chat(req: ChatRequest):
    """RAG智能问答API"""
    try:
        # 初始化会话历史
        if req.session_id not in chat_history:
            chat_history[req.session_id] = []
        
        # 检索上下文
        context = ""
        retrieved_docs = []
        if req.use_rag:
            context = retrieve_context(req.message, req.top_k)
            # 解析检索到的文档
            try:
                r = requests.post(
                    f"{VECTOR_DB_URL}/api/v1/semantic_search",
                    json={"query": req.message, "top_k": req.top_k},
                    timeout=30
                )
                data = r.json()
                for item in data.get("results", [])[:req.top_k]:
                    retrieved_docs.append({
                        "id": item.get("truth_id", "unknown"),
                        "relevance": round(item.get("relevance", 0), 4),
                        "category": item.get("category", "uncategorized")
                    })
            except:
                pass
        
        # 构建消息
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # 添加上下文
        if context:
            messages.append({
                "role": "system",
                "content": f"以下是检索到的相关真值和文档，请基于这些信息回答用户问题：\n\n{context}"
            })
        
        # 添加历史对话（最近5轮）
        history = chat_history[req.session_id][-10:]
        messages.extend(history)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": req.message})
        
        # 调用LLM
        start_time = time.time()
        if req.model == "zhipu":
            answer = call_zhipu_llm(messages, req.temperature, req.max_tokens)
            model_used = "zhipu-glm-4-flash"
        else:
            answer = call_local_llm(messages, req.temperature, req.max_tokens)
            model_used = "local-qwen2.5-1.5b"
        
        elapsed = round(time.time() - start_time, 2)
        
        # 保存对话历史
        chat_history[req.session_id].append({"role": "user", "content": req.message})
        chat_history[req.session_id].append({"role": "assistant", "content": answer})
        
        # 限制历史长度
        if len(chat_history[req.session_id]) > 40:
            chat_history[req.session_id] = chat_history[req.session_id][-40:]
        
        return {
            "status": "ok",
            "answer": answer,
            "model": model_used,
            "rag_enabled": req.use_rag,
            "retrieved_docs": retrieved_docs,
            "session_id": req.session_id,
            "elapsed_seconds": elapsed,
            "did": DID,
            "trace": TRACE
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """获取对话历史"""
    return {
        "status": "ok",
        "session_id": session_id,
        "messages": chat_history.get(session_id, []),
        "message_count": len(chat_history.get(session_id, []))
    }

@app.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """清除对话历史"""
    if session_id in chat_history:
        del chat_history[session_id]
    return {"status": "ok", "message": f"会话 {session_id} 历史已清除"}

@app.get("/", response_class=HTMLResponse)
async def search_ui():
    """搜索+智能问答Web界面"""
    return get_web_ui()

def get_web_ui():
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZONGYUAN-ROOT 语义搜索 + RAG智能问答</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            color: #fff;
        }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; padding: 30px 0 20px; }
        .header h1 {
            font-size: 2em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }
        .header p { color: #a0a0c0; font-size: 0.95em; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            justify-content: center;
        }
        .tab {
            padding: 12px 30px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 1em;
            color: #a0a0c0;
        }
        .tab:hover { background: rgba(102,126,234,0.2); }
        .tab.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            border-color: transparent;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .search-box, .chat-box {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .search-input, .chat-input {
            width: 100%;
            padding: 14px 18px;
            font-size: 1em;
            border: 2px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            outline: none;
            transition: all 0.3s;
        }
        .search-input:focus, .chat-input:focus {
            border-color: #667eea;
            box-shadow: 0 0 20px rgba(102,126,234,0.3);
        }
        .options { display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap; align-items: center; }
        .options label { color: #a0a0c0; font-size: 0.85em; display: flex; align-items: center; gap: 6px; }
        .options select, .options input[type="number"] {
            padding: 6px 10px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            outline: none;
        }
        .options input[type="checkbox"] { width: 16px; height: 16px; cursor: pointer; }
        .btn {
            margin-top: 18px;
            padding: 12px 35px;
            font-size: 1em;
            font-weight: 600;
            color: #fff;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102,126,234,0.4); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .results { margin-top: 25px; display: none; }
        .results.show { display: block; }
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .result-header h2 { font-size: 1.2em; }
        .result-count { color: #a0a0c0; font-size: 0.85em; }
        .result-item {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
        }
        .result-item:hover { border-color: rgba(102,126,234,0.5); transform: translateX(5px); }
        .result-title {
            font-size: 1em;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 8px;
            word-break: break-all;
        }
        .result-content {
            color: #d0d0e0;
            line-height: 1.6;
            margin-bottom: 10px;
            font-size: 0.9em;
        }
        .result-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8em;
            color: #8080a0;
            flex-wrap: wrap;
        }
        .relevance-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
        }
        .relevance-high { background: rgba(34,197,94,0.2); color: #4ade80; }
        .relevance-medium { background: rgba(234,179,8,0.2); color: #facc15; }
        .relevance-low { background: rgba(239,68,68,0.2); color: #f87171; }
        .category-tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            background: rgba(102,126,234,0.2);
            color: #a5b4fc;
        }
        .chat-container {
            height: 400px;
            overflow-y: auto;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            margin-bottom: 15px;
        }
        .chat-message {
            margin-bottom: 15px;
            display: flex;
            flex-direction: column;
        }
        .chat-message.user { align-items: flex-end; }
        .chat-message.assistant { align-items: flex-start; }
        .chat-bubble {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 16px;
            line-height: 1.6;
            font-size: 0.95em;
        }
        .chat-message.user .chat-bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            border-bottom-right-radius: 4px;
        }
        .chat-message.assistant .chat-bubble {
            background: rgba(255,255,255,0.1);
            color: #e0e0f0;
            border-bottom-left-radius: 4px;
        }
        .chat-meta {
            font-size: 0.75em;
            color: #606080;
            margin-top: 4px;
        }
        .retrieved-docs {
            margin-top: 8px;
            padding: 8px 12px;
            background: rgba(102,126,234,0.1);
            border-radius: 8px;
            font-size: 0.75em;
            color: #a5b4fc;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #a0a0c0;
        }
        .loading-spinner {
            width: 30px;
            height: 30px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .quick-tags { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
        .quick-tag {
            padding: 5px 12px;
            background: rgba(102,126,234,0.15);
            border: 1px solid rgba(102,126,234,0.3);
            border-radius: 16px;
            color: #a5b4fc;
            font-size: 0.8em;
            cursor: pointer;
            transition: all 0.3s;
        }
        .quick-tag:hover { background: rgba(102,126,234,0.3); }
        .footer {
            text-align: center;
            padding: 25px;
            color: #606080;
            font-size: 0.8em;
        }
        .model-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 600;
            margin-left: 8px;
        }
        .model-local { background: rgba(34,197,94,0.2); color: #4ade80; }
        .model-zhipu { background: rgba(59,130,246,0.2); color: #60a5fa; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 ZONGYUAN-ROOT 智能检索中心</h1>
            <p>跨文档语义搜索 + RAG智能问答 · bge-small-zh-onnx-512d · 8448+ 条向量化真值</p>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('search')">🔍 语义搜索</div>
            <div class="tab" onclick="switchTab('chat')">💬 RAG智能问答</div>
        </div>
        
        <!-- 语义搜索标签页 -->
        <div class="tab-content active" id="tab-search">
            <div class="search-box">
                <input type="text" id="query" class="search-input" placeholder="输入搜索内容，例如：内存熔断、元法则、短剧生产、自治内核..." onkeypress="if(event.key==='Enter')doSearch()">
                <div class="options">
                    <label>结果数量:
                        <select id="topK">
                            <option value="5">5条</option>
                            <option value="10">10条</option>
                            <option value="20">20条</option>
                        </select>
                    </label>
                    <label>最低相似度:
                        <input type="number" id="minSim" value="0.5" min="0" max="1" step="0.1" style="width:60px">
                    </label>
                </div>
                <div class="quick-tags">
                    <span class="quick-tag" onclick="quickSearch('内存熔断机制')">内存熔断</span>
                    <span class="quick-tag" onclick="quickSearch('元法则体系')">元法则</span>
                    <span class="quick-tag" onclick="quickSearch('短剧生产流水线')">短剧生产</span>
                    <span class="quick-tag" onclick="quickSearch('自治内核保活')">自治内核</span>
                    <span class="quick-tag" onclick="quickSearch('知识图谱因果推理')">知识图谱</span>
                    <span class="quick-tag" onclick="quickSearch('蜜罐安全防御')">安全防御</span>
                </div>
                <button class="btn" id="searchBtn" onclick="doSearch()">开始搜索</button>
            </div>
            <div class="results" id="results">
                <div class="result-header">
                    <h2>搜索结果</h2>
                    <span class="result-count" id="resultCount"></span>
                </div>
                <div id="resultList"></div>
            </div>
        </div>
        
        <!-- RAG智能问答标签页 -->
        <div class="tab-content" id="tab-chat">
            <div class="chat-box">
                <div class="options" style="margin-top:0;margin-bottom:15px">
                    <label>模型:
                        <select id="chatModel">
                            <option value="local">本地 Qwen2.5-1.5B</option>
                            <option value="zhipu">智谱 GLM-4-Flash (免费)</option>
                        </select>
                    </label>
                    <label><input type="checkbox" id="useRAG" checked> 启用RAG检索</label>
                    <label>温度:
                        <input type="number" id="chatTemp" value="0.7" min="0" max="2" step="0.1" style="width:50px">
                    </label>
                    <button onclick="clearChat()" style="padding:6px 14px;background:rgba(239,68,68,0.2);border:1px solid rgba(239,68,68,0.3);border-radius:8px;color:#f87171;cursor:pointer;font-size:0.85em">清除对话</button>
                </div>
                <div class="chat-container" id="chatContainer">
                    <div class="chat-message assistant">
                        <div class="chat-bubble">
                            你好！我是ZONGYUAN-ROOT元极恒一自治体系的智能助手。我可以基于体系内的真值和文档回答你的问题。<br><br>
                            试试问我：<br>
                            • 我们的元法则体系有哪些？<br>
                            • 内存熔断机制是怎么工作的？<br>
                            • 当前系统有哪些服务在运行？<br>
                            • 知识图谱里有哪些高价值实体？
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:10px">
                    <input type="text" id="chatInput" class="chat-input" placeholder="输入你的问题..." style="flex:1" onkeypress="if(event.key==='Enter')sendChat()">
                    <button class="btn" id="chatBtn" onclick="sendChat()" style="width:auto;padding:12px 25px;margin-top:0">发送</button>
                </div>
                <div class="quick-tags">
                    <span class="quick-tag" onclick="quickChat('元法则体系有哪些？')">元法则体系</span>
                    <span class="quick-tag" onclick="quickChat('内存熔断机制怎么工作？')">内存熔断</span>
                    <span class="quick-tag" onclick="quickChat('当前系统运行状态如何？')">系统状态</span>
                    <span class="quick-tag" onclick="quickChat('知识图谱有哪些高价值实体？')">知识图谱</span>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Ω₀⊂⊙∞⊂Ω · DID-BR-000002 · ZONGYUAN-ROOT 元极恒一自治体系</p>
        </div>
    </div>
    
    <script>
        let sessionId = 'session_' + Date.now();
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }
        
        function quickSearch(q) {
            document.getElementById('query').value = q;
            doSearch();
        }
        
        async function doSearch() {
            const query = document.getElementById('query').value.trim();
            if (!query) { alert('请输入搜索内容'); return; }
            
            const btn = document.getElementById('searchBtn');
            const resultsDiv = document.getElementById('results');
            const resultList = document.getElementById('resultList');
            const resultCount = document.getElementById('resultCount');
            
            btn.disabled = true;
            btn.textContent = '搜索中...';
            resultsDiv.classList.add('show');
            resultList.innerHTML = '<div class="loading"><div class="loading-spinner"></div>正在语义搜索...</div>';
            
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: query,
                        top_k: parseInt(document.getElementById('topK').value),
                        min_similarity: parseFloat(document.getElementById('minSim').value)
                    })
                });
                
                const data = await response.json();
                
                if (data.status === 'ok' && data.results.length > 0) {
                    resultCount.textContent = `找到 ${data.total_results} 条相关结果`;
                    resultList.innerHTML = data.results.map((item, idx) => {
                        const relClass = item.relevance >= 0.8 ? 'relevance-high' : 
                                        item.relevance >= 0.6 ? 'relevance-medium' : 'relevance-low';
                        return `
                            <div class="result-item">
                                <div class="result-title">${idx + 1}. ${item.truth_id}</div>
                                <div class="result-content">${item.content.substring(0, 300)}${item.content.length > 300 ? '...' : ''}</div>
                                <div class="result-meta">
                                    <span class="relevance-badge ${relClass}">相似度: ${(item.relevance * 100).toFixed(1)}%</span>
                                    <span class="category-tag">${item.category}</span>
                                    <span>节点: ${item.node_id}</span>
                                </div>
                            </div>
                        `;
                    }).join('');
                } else {
                    resultCount.textContent = '未找到相关结果';
                    resultList.innerHTML = '<div class="loading">未找到相关结果，请尝试其他关键词或降低最低相似度阈值</div>';
                }
            } catch (error) {
                resultList.innerHTML = `<div class="loading">搜索失败: ${error.message}</div>`;
            }
            
            btn.disabled = false;
            btn.textContent = '开始搜索';
        }
        
        function quickChat(q) {
            document.getElementById('chatInput').value = q;
            sendChat();
        }
        
        async function sendChat() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if (!message) return;
            
            const btn = document.getElementById('chatBtn');
            const container = document.getElementById('chatContainer');
            
            // 添加用户消息
            addMessage('user', message);
            input.value = '';
            btn.disabled = true;
            btn.textContent = '思考中...';
            
            // 添加加载提示
            const loadingId = 'loading-' + Date.now();
            container.innerHTML += `
                <div class="chat-message assistant" id="${loadingId}">
                    <div class="chat-bubble">
                        <div class="loading-spinner" style="margin:0"></div>
                        <span style="margin-left:10px">正在检索知识库并生成回答...</span>
                    </div>
                </div>
            `;
            container.scrollTop = container.scrollHeight;
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId,
                        model: document.getElementById('chatModel').value,
                        use_rag: document.getElementById('useRAG').checked,
                        temperature: parseFloat(document.getElementById('chatTemp').value),
                        max_tokens: 500
                    })
                });
                
                const data = await response.json();
                
                // 移除加载提示
                document.getElementById(loadingId)?.remove();
                
                if (data.status === 'ok') {
                    let retrievedHtml = '';
                    if (data.retrieved_docs && data.retrieved_docs.length > 0) {
                        retrievedHtml = '<div class="retrieved-docs">📚 检索到 ' + data.retrieved_docs.length + ' 条相关真值: ' + 
                            data.retrieved_docs.map(d => d.id).join(', ') + '</div>';
                    }
                    
                    const modelClass = data.model.includes('zhipu') ? 'model-zhipu' : 'model-local';
                    addMessage('assistant', data.answer + retrievedHtml + 
                        `<div class="chat-meta">模型: ${data.model} <span class="model-badge ${modelClass}">${data.model.includes('zhipu') ? '外部' : '本地'}</span> · 耗时: ${data.elapsed_seconds}s</div>`);
                } else {
                    addMessage('assistant', '抱歉，回答生成失败，请稍后重试。');
                }
            } catch (error) {
                document.getElementById(loadingId)?.remove();
                addMessage('assistant', `请求失败: ${error.message}`);
            }
            
            btn.disabled = false;
            btn.textContent = '发送';
        }
        
        function addMessage(role, content) {
            const container = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'chat-message ' + role;
            messageDiv.innerHTML = `<div class="chat-bubble">${content}</div>`;
            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }
        
        async function clearChat() {
            if (!confirm('确定要清除当前对话历史吗？')) return;
            try {
                await fetch('/api/chat/history/' + sessionId, { method: 'DELETE' });
            } catch(e) {}
            sessionId = 'session_' + Date.now();
            document.getElementById('chatContainer').innerHTML = `
                <div class="chat-message assistant">
                    <div class="chat-bubble">对话已清除。有什么可以帮你的吗？</div>
                </div>
            `;
        }
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    print(f"启动语义搜索+RAG智能问答服务，端口: {SEARCH_PORT}")
    print(f"向量数据库: {VECTOR_DB_URL}")
    print(f"本地LLM: {LOCAL_LLM_URL}")
    uvicorn.run(app, host="127.0.0.1", port=SEARCH_PORT)
