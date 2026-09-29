#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 三域记忆网关 Memory-Gateway V1.0
轻量HTTP服务，按锚定条件定点拉取记忆，替代全量扫描。
端口: 8077 | 鉴权: HMAC-SHA256 | DID-BR-000002
"""
import json, os, hashlib, hmac, time, datetime
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# 配置
INDEX_PATH = "/opt/ZONGYUAN-ROOT/memory_index.json"
GATEWAY_SECRET = os.getenv("MEMORY_GATEWAY_SECRET", "ZONGYUAN-ROOT-SECRET-DID-BR-000002")
MAX_TOKEN_DEFAULT = 4000
DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"

app = FastAPI(title="ZONGYUAN-ROOT Memory Gateway", version="1.0")

# 内存缓存
_index_cache = None
_index_mtime = 0

def load_index() -> Dict[str, Any]:
    """加载记忆索引，带文件修改时间缓存"""
    global _index_cache, _index_mtime
    try:
        mtime = os.path.getmtime(INDEX_PATH)
        if _index_cache and mtime == _index_mtime:
            return _index_cache
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            _index_cache = json.load(f)
        _index_mtime = mtime
        return _index_cache
    except Exception as e:
        return {"index_meta": {}, "asset_entries": [], "error": str(e)}

def verify_signature(sig: str, payload: str) -> bool:
    """HMAC-SHA256签名验证"""
    expected = hmac.new(GATEWAY_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)

def extract_truth(entry: Dict[str, Any], max_token: int) -> str:
    """从资产条目提取真值摘要（裁剪）"""
    summary = entry.get("summary", "")
    tags = entry.get("tags", [])
    asset_id = entry.get("asset_id", "")
    priority = entry.get("priority", "C")
    result = f"[{priority}] {asset_id} | tags:{','.join(tags[:5])} | {summary}"
    # 简单token裁剪（按字符数近似）
    if len(result) > max_token * 2:
        result = result[:max_token * 2] + "..."
    return result

class AnchorRequest(BaseModel):
    anchor_type: str  # latest / tag / asset_id / snap_id / keyword
    anchor_value: str = ""
    extract_mode: str = "truth_only"  # truth_only / full / summary
    max_token: int = MAX_TOKEN_DEFAULT

class AnchorResponse(BaseModel):
    status: str
    did: str
    trace_mark: str
    matched_count: int
    total_index: int
    memories: List[str]
    index_update_time: str

@app.get("/memory/health")
async def health():
    idx = load_index()
    return {
        "status": "healthy",
        "service": "memory_gateway",
        "version": "1.0",
        "index_assets": len(idx.get("asset_entries", [])),
        "did": DID,
        "trace_mark": TRACE_MARK
    }

@app.get("/memory/index")
async def index_status():
    idx = load_index()
    meta = idx.get("index_meta", {})
    return {
        "total_assets": len(idx.get("asset_entries", [])),
        "latest_snap_id": meta.get("latest_snap_id", "N/A"),
        "merkle_root": str(meta.get("merkle_root", "N/A"))[:32],
        "index_update_time": meta.get("index_update_time", "N/A"),
        "efuse_status": meta.get("eFuse_status", "N/A"),
        "did": meta.get("did", DID)
    }

@app.post("/memory/anchor", response_model=AnchorResponse)
async def anchor(req: AnchorRequest, x_memory_sig: Optional[str] = Header(None)):
    """按锚定条件检索记忆"""
    # 签名验证（latest模式可放宽）
    if req.anchor_type != "latest":
        payload = f"{req.anchor_type}|{req.anchor_value}|{int(time.time())//300}"
        if not x_memory_sig or not verify_signature(x_memory_sig, payload):
            raise HTTPException(status_code=403, detail="invalid signature")

    idx = load_index()
    entries = idx.get("asset_entries", [])
    meta = idx.get("index_meta", {})
    matched = []

    if req.anchor_type == "latest" or req.anchor_value == "latest":
        # 最新快照：按优先级取前N条
        sorted_entries = sorted(entries, key=lambda x: {"S":0,"A":1,"B":2,"C":3,"D":4}.get(x.get("priority","D"),5))
        matched = sorted_entries[:20]
    elif req.anchor_type == "tag":
        matched = [e for e in entries if req.anchor_value in e.get("tags", [])]
    elif req.anchor_type == "asset_id":
        matched = [e for e in entries if e.get("asset_id") == req.anchor_value]
    elif req.anchor_type == "snap_id":
        matched = [e for e in entries if req.anchor_value in e.get("snap_id", [])]
    elif req.anchor_type == "keyword":
        kw = req.anchor_value.lower()
        matched = [e for e in entries if kw in e.get("summary", "").lower() or kw in ",".join(e.get("tags",[])).lower()]
    else:
        raise HTTPException(status_code=400, detail=f"unknown anchor_type: {req.anchor_type}")

    # 提取真值
    memories = [extract_truth(e, req.max_token) for e in matched[:15]]

    return AnchorResponse(
        status="ok",
        did=DID,
        trace_mark=TRACE_MARK,
        matched_count=len(matched),
        total_index=len(entries),
        memories=memories,
        index_update_time=meta.get("index_update_time", datetime.datetime.utcnow().isoformat())
    )

if __name__ == "__main__":
    import uvicorn
    print(f"[Memory-Gateway] starting on 0.0.0.0:8077, DID={DID}")
    uvicorn.run(app, host="0.0.0.0", port=8077, log_level="info")
