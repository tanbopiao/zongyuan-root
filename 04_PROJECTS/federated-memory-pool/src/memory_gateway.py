#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 三域记忆网关 Memory-Gateway V1.0（开源版）
轻量HTTP服务，按锚定条件定点拉取记忆，替代全量扫描。
端口: 8077 | 鉴权: HMAC-SHA256 | 锚定: Ω₀⊂⊙∞⊂Ω
"""
import json, os, hashlib, hmac, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# ==================== 配置 ====================
INDEX_PATH = os.getenv("MEMORY_INDEX", "memory_index.json")
GATEWAY_SECRET = os.getenv("MEMORY_GATEWAY_SECRET", "CHANGE_ME_TO_YOUR_SECRET")
MAX_TOKEN_DEFAULT = 4000
DID = os.getenv("DID", "DID-BR-000002")
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"

# ==================== 记忆索引 ====================
_index_cache: Dict[str, Any] = {}
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
    except Exception:
        return {"index_meta": {}, "asset_entries": [], "error": "index_not_found"}

def verify_signature(sig: str, payload: str) -> bool:
    """HMAC-SHA256签名验证"""
    expected = hmac.new(
        GATEWAY_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig, expected)

def extract_truth(entry: Dict[str, Any], max_token: int) -> str:
    """从资产条目提取真值摘要（裁剪）"""
    summary = entry.get("summary", "")
    tags = entry.get("tags", [])
    asset_id = entry.get("asset_id", "")
    priority = entry.get("priority", "C")
    result = f"[{priority}] {asset_id} | tags:{','.join(tags[:5])} | {summary}"
    if len(result) > max_token * 2:
        result = result[:max_token * 2] + "..."
    return result

def query_memories(anchor_type: str, anchor_value: str, max_token: int) -> tuple:
    """按锚点类型过滤记忆条目"""
    idx = load_index()
    entries = idx.get("asset_entries", [])
    total = len(entries)
    matched = []

    for e in entries:
        if anchor_type == "latest":
            matched = entries[:20]  # 最近20条（索引已按时间排序）
            break
        elif anchor_type == "tag":
            tags = e.get("tags", [])
            if anchor_value in tags:
                matched.append(e)
        elif anchor_type == "asset_id":
            if e.get("asset_id") == anchor_value:
                matched.append(e)
        elif anchor_type == "keyword":
            blob = f"{e.get('asset_id','')} {e.get('summary','')} {' '.join(e.get('tags',[]))}"
            if anchor_value.lower() in blob.lower():
                matched.append(e)
        elif anchor_type == "snap_id":
            if anchor_value in e.get("snap_id", []):
                matched.append(e)

    # 按优先级排序（A > B > C > D）
    prio = {"A": 0, "B": 1, "C": 2, "D": 3}
    matched.sort(key=lambda e: prio.get(e.get("priority", "C"), 2))
    return matched, total

# ==================== HTTP 服务 ====================
class MemoryHandler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        """GET /memory/health — 健康检查"""
        if self.path == "/memory/health":
            idx = load_index()
            self._send(200, {
                "status": "healthy",
                "service": "memory_gateway",
                "version": "1.0",
                "index_assets": len(idx.get("asset_entries", [])),
                "did": DID,
                "trace_mark": TRACE_MARK
            })
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        """POST /memory/anchor — 锚点拉取记忆"""
        if self.path != "/memory/anchor":
            self._send(404, {"error": "not_found"})
            return

        # 1. 签名校验
        sig = self.headers.get("X-Memory-Sig", "")
        body_raw = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        if not verify_signature(sig, body_raw):
            self._send(401, {"error": "unauthorized", "message": "HMAC签名验证失败"})
            return

        # 2. 解析请求
        try:
            req = json.loads(body_raw)
        except Exception:
            self._send(400, {"error": "bad_json"})
            return

        anchor_type = req.get("anchor_type", "latest")
        anchor_value = req.get("anchor_value", "")
        extract_mode = req.get("extract_mode", "truth_only")
        max_token = int(req.get("max_token", MAX_TOKEN_DEFAULT))

        # 3. 查询
        matched, total = query_memories(anchor_type, anchor_value, max_token)

        # 4. 提取输出
        if extract_mode == "truth_only":
            memories = [extract_truth(e, max_token) for e in matched]
        else:
            memories = [json.dumps(e, ensure_ascii=False) for e in matched]

        self._send(200, {
            "status": "ok",
            "did": DID,
            "trace_mark": TRACE_MARK,
            "matched_count": len(matched),
            "total_index": total,
            "memories": memories,
            "query": {"anchor_type": anchor_type, "anchor_value": anchor_value}
        })

def main():
    port = int(os.getenv("MEMORY_GATEWAY_PORT", "8077"))
    print(f"[{TRACE_MARK}] Memory Gateway 启动 @ 127.0.0.1:{port} (DID={DID})")
    print(f"索引: {INDEX_PATH} | 资产: {len(load_index().get('asset_entries', []))}条")
    HTTPServer(("127.0.0.1", port), MemoryHandler).serve_forever()

if __name__ == "__main__":
    main()
