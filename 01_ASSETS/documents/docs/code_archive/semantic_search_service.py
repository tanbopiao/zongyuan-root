#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 跨文档语义搜索服务
基于向量数据库(8014)的bge-small-zh-onnx-512d嵌入模型
提供自然语言搜索API和Web界面
"""
import os
import sys
import json
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

# 配置
VECTOR_DB_URL = "http://127.0.0.1:8014"
SEARCH_PORT = 8090
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

app = FastAPI(
    title="ZONGYUAN-ROOT 语义搜索服务",
    description="跨文档语义搜索，基于bge-small-zh-onnx-512d嵌入模型",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: Optional[str] = None
    min_similarity: float = 0.5

class SearchResult(BaseModel):
    truth_id: str
    content: str
    relevance: float
    category: str
    node_id: str
    timestamp: float

@app.get("/health")
async def health():
    """健康检查"""
    try:
        r = requests.get(f"{VECTOR_DB_URL}/health", timeout=5)
        vector_status = r.json().get("status", "unknown")
        return {
            "status": "ok",
            "service": "semantic-search",
            "version": "1.0.0",
            "vector_db": vector_status,
            "did": DID,
            "trace": TRACE
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e), "did": DID, "trace": TRACE}

@app.post("/api/search")
async def semantic_search(req: SearchRequest):
    """语义搜索API"""
    try:
        # 调用向量数据库
        payload = {
            "query": req.query,
            "top_k": req.top_k * 2  # 多取一些，然后过滤
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
        
        # 过滤和格式化
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
            "did": DID,
            "trace": TRACE
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def search_ui():
    """搜索Web界面"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZONGYUAN-ROOT 语义搜索</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .header { text-align: center; padding: 40px 0; }
        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }
        .header p { color: #a0a0c0; font-size: 1.1em; }
        .search-box {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .search-input {
            width: 100%;
            padding: 16px 20px;
            font-size: 1.1em;
            border: 2px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            outline: none;
            transition: all 0.3s;
        }
        .search-input:focus { border-color: #667eea; box-shadow: 0 0 20px rgba(102,126,234,0.3); }
        .search-options { display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap; }
        .search-options label { color: #a0a0c0; font-size: 0.9em; display: flex; align-items: center; gap: 8px; }
        .search-options select, .search-options input {
            padding: 8px 12px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            outline: none;
        }
        .search-btn {
            margin-top: 20px;
            padding: 14px 40px;
            font-size: 1.1em;
            font-weight: 600;
            color: #fff;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
        }
        .search-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102,126,234,0.4); }
        .search-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .results { display: none; }
        .results.show { display: block; }
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .result-header h2 { font-size: 1.3em; }
        .result-count { color: #a0a0c0; font-size: 0.9em; }
        .result-item {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
        }
        .result-item:hover { border-color: rgba(102,126,234,0.5); transform: translateX(5px); }
        .result-title {
            font-size: 1.1em;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 10px;
            word-break: break-all;
        }
        .result-content {
            color: #d0d0e0;
            line-height: 1.6;
            margin-bottom: 12px;
            font-size: 0.95em;
        }
        .result-meta {
            display: flex;
            gap: 15px;
            font-size: 0.85em;
            color: #8080a0;
            flex-wrap: wrap;
        }
        .result-meta span { display: flex; align-items: center; gap: 5px; }
        .relevance-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .relevance-high { background: rgba(34,197,94,0.2); color: #4ade80; }
        .relevance-medium { background: rgba(234,179,8,0.2); color: #facc15; }
        .relevance-low { background: rgba(239,68,68,0.2); color: #f87171; }
        .category-tag {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 6px;
            background: rgba(102,126,234,0.2);
            color: #a5b4fc;
            font-size: 0.8em;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #a0a0c0;
        }
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .footer {
            text-align: center;
            padding: 30px;
            color: #606080;
            font-size: 0.85em;
        }
        .quick-tags { margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        .quick-tag {
            padding: 6px 14px;
            background: rgba(102,126,234,0.15);
            border: 1px solid rgba(102,126,234,0.3);
            border-radius: 20px;
            color: #a5b4fc;
            font-size: 0.85em;
            cursor: pointer;
            transition: all 0.3s;
        }
        .quick-tag:hover { background: rgba(102,126,234,0.3); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 ZONGYUAN-ROOT 语义搜索</h1>
            <p>跨文档自然语言搜索 · bge-small-zh-onnx-512d · 8448+ 条向量化真值</p>
        </div>
        
        <div class="search-box">
            <input type="text" id="query" class="search-input" placeholder="输入搜索内容，例如：内存熔断、元法则、短剧生产、自治内核..." onkeypress="if(event.key==='Enter')doSearch()">
            <div class="search-options">
                <label>结果数量:
                    <select id="topK">
                        <option value="5">5条</option>
                        <option value="10">10条</option>
                        <option value="20">20条</option>
                    </select>
                </label>
                <label>最低相似度:
                    <input type="number" id="minSim" value="0.5" min="0" max="1" step="0.1" style="width:70px">
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
            <button class="search-btn" id="searchBtn" onclick="doSearch()">开始搜索</button>
        </div>
        
        <div class="results" id="results">
            <div class="result-header">
                <h2>搜索结果</h2>
                <span class="result-count" id="resultCount"></span>
            </div>
            <div id="resultList"></div>
        </div>
        
        <div class="footer">
            <p>Ω₀⊂⊙∞⊂Ω · DID-BR-000002 · ZONGYUAN-ROOT 元极恒一自治体系</p>
        </div>
    </div>
    
    <script>
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
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    print(f"启动语义搜索服务，端口: {SEARCH_PORT}")
    print(f"向量数据库: {VECTOR_DB_URL}")
    uvicorn.run(app, host="127.0.0.1", port=SEARCH_PORT)
