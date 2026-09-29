#!/usr/bin/env python3
"""
跨文档语义搜索 - 归档文档向量化导入
将高价值归档文档(白皮书/报告/元法则/方案)向量化存入向量库
支持自然语言搜索定位文档段落
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import glob
import hashlib
import urllib.request
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
VECTOR_API = "http://127.0.0.1:8014/api/v1"
LOG_FILE = os.path.join(BASE, "logs/doc_vector_import.log")
STATE_FILE = os.path.join(BASE, "data/doc_vector_state.json")

# 高价值文档目录和模式
HIGH_VALUE_PATTERNS = [
    os.path.join(BASE, "*.md"),                    # 根目录白皮书
    os.path.join(BASE, "reports", "**", "*.md"),   # 报告
    os.path.join(BASE, "zero_trust", "**", "*.md"),# 零信任架构
    os.path.join(BASE, "kernel", "**", "*.json"),  # 元法则
    os.path.join(BASE, "assets", "**", "*.md"),    # 短剧剧本
]

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write("[%s] %s\n" % (ts, msg))
    print("[%s] %s" % (ts, msg))

def api_add(doc_id, text, metadata):
    """向量化添加文档"""
    payload = {
        "ids": [doc_id],
        "documents": [text[:2000]],  # 限制长度
        "metadatas": [metadata]
    }
    try:
        req = urllib.request.Request(
            VECTOR_API + "/add",
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def semantic_search(query, top_k=3):
    """语义搜索测试"""
    payload = {"query": query, "top_k": top_k}
    try:
        req = urllib.request.Request(
            VECTOR_API + "/semantic_search",
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def chunk_text(text, chunk_size=1500, overlap=200):
    """文本分块"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def run_import(limit=100):
    """执行文档导入"""
    log("=" * 50)
    log("归档文档向量化导入开始")
    
    # 收集高价值文档
    files = set()
    for pattern in HIGH_VALUE_PATTERNS:
        files.update(glob.glob(pattern, recursive=True))
    
    files = sorted(files)[:limit]
    log("发现高价值文档: %d个" % len(files))
    
    # 加载已导入状态
    imported = set()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
            imported = set(state.get("imported", []))
    else:
        state = {"imported": [], "total_chunks": 0}
    
    new_docs = 0
    new_chunks = 0
    errors = 0
    
    for filepath in files:
        # 计算文件哈希作为ID
        try:
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read()
        except:
            continue
        
        file_hash = hashlib.md5(filepath.encode()).hexdigest()[:12]
        if file_hash in imported:
            continue
        
        filename = os.path.basename(filepath)
        rel_path = os.path.relpath(filepath, BASE)
        
        # 分块导入
        chunks = chunk_text(content)
        doc_chunks = 0
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 20:
                continue
            doc_id = "%s_%d" % (file_hash, i)
            metadata = {
                "source": "archive_doc",
                "filename": filename,
                "path": rel_path,
                "chunk": i,
                "total_chunks": len(chunks),
                "did": "DID-BR-000002"
            }
            result = api_add(doc_id, chunk, metadata)
            if "error" not in result:
                doc_chunks += 1
                new_chunks += 1
            else:
                errors += 1
        
        if doc_chunks > 0:
            imported.add(file_hash)
            new_docs += 1
            log("  导入: %s (%d块)" % (filename, doc_chunks))
    
    # 保存状态
    state["imported"] = list(imported)
    state["total_chunks"] = state.get("total_chunks", 0) + new_chunks
    state["last_import"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    
    log("导入完成: %d个新文档, %d个文本块, %d个错误" % (new_docs, new_chunks, errors))
    
    # 测试语义搜索
    log("--- 语义搜索测试 ---")
    test_queries = ["内存熔断机制", "元法则安全", "短剧剧本"]
    for q in test_queries:
        result = semantic_search(q, top_k=2)
        results = result.get("results", [])
        if results:
            log("  搜索[%s]: 命中%d条, 首条=%s" % (q, len(results), results[0].get("truth_id", "?")[:40]))
    
    log("=" * 50)
    return state

if __name__ == '__main__':
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run_import(limit)
