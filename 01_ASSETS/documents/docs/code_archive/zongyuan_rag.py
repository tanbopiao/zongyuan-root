#!/usr/bin/env python3
"""
ZONGYUAN-ROOT RAG增强本地推理服务
整合：9120真值库 + 向量数据库(8014) + 本地LLM(8081)
端口：8085
"""
import json
import hashlib
import time
import sqlite3
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# 配置
PORT = 8085
GATEWAY_URL = "http://127.0.0.1:9120"
VECTOR_URL = "http://127.0.0.1:8014"
LLM_URL = "http://127.0.0.1:8081"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"

def search_gateway(query, limit=5):
    """从9120真值库SQLite直接检索相关真值"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM truths WHERE truth_key LIKE ? OR truth_value LIKE ? ORDER BY updated_at DESC LIMIT 50",
                     (f'%{query}%', f'%{query}%'))
        truths = [dict(row) for row in cursor.fetchall()]
        conn.close()
        # 按匹配度排序
        query_chars = set(query.lower())
        scored = []
        for t in truths:
            val = (str(t.get('truth_value', '')) + str(t.get('truth_key', ''))).lower()
            score = sum(1 for w in query_chars if w in val)
            scored.append((score, t))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]
    except Exception as e:
        return []

def search_vector(query, limit=3):
    """从向量数据库语义检索"""
    try:
        payload = json.dumps({"query": query, "limit": limit}).encode()
        req = urllib.request.Request(
            f"{VECTOR_URL}/api/v1/semantic_search",
            data=payload,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get('results', data.get('documents', []))
    except:
        return []

def call_local_llm(prompt, max_tokens=512):
    """调用本地LLM生成回答"""
    try:
        payload = json.dumps({
            "model": "/opt/models/qwen2.5-0.5b-instruct-q4_k_m.gguf",
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "stream": False
        }).encode()
        req = urllib.request.Request(
            f"{LLM_URL}/v1/completions",
            data=payload,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data.get('choices', [{}])[0].get('text', '').strip()
    except Exception as e:
        return f"[本地LLM调用失败: {e}]"

def build_context(gateway_results, vector_results):
    """构建上下文"""
    context_parts = []
    if gateway_results:
        context_parts.append("【真值库检索结果】")
        for i, t in enumerate(gateway_results[:5], 1):
            key = t.get('truth_key', t.get('key', '?'))
            val = str(t.get('truth_value', t.get('value', '')))[:200]
            cat = t.get('category', t.get('truth_type', '?'))
            context_parts.append(f"{i}. [{cat}] {key}: {val}")
    if vector_results:
        context_parts.append("\n【语义检索结果】")
        for i, r in enumerate(vector_results[:3], 1):
            content = r.get('content', r.get('text', ''))[:200]
            context_parts.append(f"{i}. {content}")
    return "\n".join(context_parts) if context_parts else "（无相关上下文）"

class RAGHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "zongyuan-rag", "port": PORT}).encode())
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == '/ask':
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length))
            query = body.get('query', '')
            if not query:
                self.send_response(400)
                self.end_headers()
                return

            start = time.time()
            # 1. 检索
            gw_results = search_gateway(query)
            vec_results = search_vector(query)
            context = build_context(gw_results, vec_results)

            # 2. 构建prompt
            prompt = f"""你是ZONGYUAN-ROOT元极恒一自治体系的智能助手。请基于以下上下文回答用户问题。如果上下文中没有答案，请如实说明。

{context}

用户问题：{query}

回答："""

            # 3. 调用本地LLM
            answer = call_local_llm(prompt)
            elapsed = round(time.time() - start, 2)

            # 4. 返回
            result = {
                "query": query,
                "answer": answer,
                "context_sources": {
                    "gateway_truths": len(gw_results),
                    "vector_docs": len(vec_results)
                },
                "elapsed_seconds": elapsed,
                "model": "qwen2.5-0.5b-local",
                "did": DID,
                "anchor": ANCHOR
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
            return

        self.send_response(404)
        self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), RAGHandler)
    print(f"ZONGYUAN-ROOT RAG服务启动，端口{PORT}")
    print(f"依赖: 9120真值库 + 8014向量库 + 8081本地LLM")
    server.serve_forever()
