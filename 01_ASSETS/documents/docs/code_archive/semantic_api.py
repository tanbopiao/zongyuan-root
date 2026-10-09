#!/usr/bin/env python3
"""
9120语义检索API服务
运行在9121端口，通过Nginx路由到 /api/semantic/search
"""
import sys
import os
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vector_engine import get_engine, build_index_from_db, SparseVectorSearchEngine

LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/semantic_api.log"

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write("[{}] {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), msg))

class SemanticSearchHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/health":
            self._send_json({"status": "ok", "service": "semantic-search", "version": "1.0.0"})
            return

        if path == "/api/semantic/search":
            query = params.get("q", [""])[0]
            top_k = int(params.get("top_k", ["10"])[0])
            category = params.get("category", [None])[0]

            if not query:
                self._send_json({"success": False, "error": "query_required"}, 400)
                return

            try:
                engine = get_engine()
                start = time.time()
                results = engine.search(query, top_k=top_k, category_filter=category)
                elapsed = round((time.time() - start) * 1000, 1)

                self._send_json({
                    "success": True,
                    "query": query,
                    "total": len(results),
                    "elapsed_ms": elapsed,
                    "index_size": len(engine.documents),
                    "vocab_size": len(engine.vocabulary),
                    "results": results
                })
                log("检索: '{}' -> {}结果, {}ms".format(query, len(results), elapsed))
            except Exception as e:
                log("检索错误: {}".format(e))
                self._send_json({"success": False, "error": str(e)}, 500)
            return

        if path == "/api/semantic/stats":
            engine = get_engine()
            self._send_json({
                "success": True,
                "indexed_documents": len(engine.documents),
                "vocabulary_size": len(engine.vocabulary),
                "index_built": engine.built,
                "index_path": "/opt/ZONGYUAN-ROOT/engine/semantic_search/index.pkl"
            })
            return

        if path == "/api/semantic/rebuild":
            try:
                engine = SparseVectorSearchEngine()
                count = build_index_from_db(engine)
                global _engine
                _engine = engine
                self._send_json({"success": True, "rebuilt": count, "message": "索引重建完成"})
                log("索引重建完成: {}个文档".format(count))
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
            return

        self._send_json({"success": False, "error": "not_found", "path": path}, 404)

    def log_message(self, format, *args):
        pass  # 静默默认日志

def main():
    port = 9121
    server = HTTPServer(("127.0.0.1", port), SemanticSearchHandler)
    log("语义检索API服务启动: 127.0.0.1:{}".format(port))
    print("语义检索API服务运行在 127.0.0.1:{}".format(port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("服务停止")
        server.shutdown()

if __name__ == "__main__":
    main()
