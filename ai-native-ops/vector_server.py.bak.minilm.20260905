"""
轻量向量数据库服务 - 基于ChromaDB嵌入式模式
端口: 8003
用途: RAG语义召回、真值向量存储、企业知识库
"""
import os, sys, time, json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="ZONGYUAN Vector DB", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

VECTOR_DIR = "/opt/ZONGYUAN-ROOT/vector_db"
os.makedirs(VECTOR_DIR, exist_ok=True)

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv("/opt/ZONGYUAN-ROOT/.env")
except: pass

try:
    import chromadb
    from chromadb.utils import embedding_functions
    client = chromadb.PersistentClient(path=VECTOR_DIR)
    # 使用ChromaDB内置语义嵌入模型（all-MiniLM-L6-v2, 384维）
    # 豆包2560维Embedding需在火山方舟控制台单独创建接入点后启用
    ef = embedding_functions.DefaultEmbeddingFunction()
    try:
        client.delete_collection(name="zongyuan_truth")
    except: pass
    collection = client.get_or_create_collection(name="zongyuan_truth", embedding_function=ef)
    CHROMA_READY = True
    EMBEDDING_MODE = "minilm_384d_semantic"
except Exception as e:
    CHROMA_READY = False
    EMBEDDING_MODE = "error"
    print(f"ChromaDB初始化失败: {e}")

class AddDoc(BaseModel):
    id: str
    text: str
    metadata: Optional[dict] = None

class QueryDoc(BaseModel):
    query: str
    top_k: int = 5

@app.get("/health")
def health():
    return {"status": "ok" if CHROMA_READY else "degraded", "service": "vector-db", "chroma": CHROMA_READY, "embedding": EMBEDDING_MODE if CHROMA_READY else "error"}

@app.get("/api/v1/stats")
def stats():
    if not CHROMA_READY:
        return {"error": "chromadb not ready"}
    count = collection.count()
    return {"collection": "zongyuan_truth", "doc_count": count, "path": VECTOR_DIR, "embedding": EMBEDDING_MODE, "dimension": 384 if "minilm" in EMBEDDING_MODE else 256}

@app.post("/api/v1/add")
def add_doc(doc: AddDoc):
    if not CHROMA_READY:
        return {"error": "chromadb not ready"}
    collection.upsert(ids=[doc.id], documents=[doc.text], metadatas=[doc.metadata or {}])
    return {"status": "added", "id": doc.id, "total": collection.count()}

@app.post("/api/v1/query")
def query_doc(q: QueryDoc):
    if not CHROMA_READY:
        return {"error": "chromadb not ready", "results": []}
    results = collection.query(query_texts=[q.query], n_results=q.top_k)
    return {
        "query": q.query,
        "results": [
            {"id": results["ids"][0][i], "text": results["documents"][0][i], 
             "distance": results["distances"][0][i] if results.get("distances") else None,
             "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}}
            for i in range(len(results["ids"][0]))
        ]
    }

@app.delete("/api/v1/delete/{doc_id}")
def delete_doc(doc_id: str):
    if not CHROMA_READY:
        return {"error": "chromadb not ready"}
    collection.delete(ids=[doc_id])
    return {"status": "deleted", "id": doc_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, workers=1)
