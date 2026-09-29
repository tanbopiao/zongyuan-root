#!/usr/bin/env python3
"""
昆仑洞天短剧平台 API Mock 服务 V1.0
本地开发联调用，零成本，不消耗付费额度
启动: python3 drama_api_mock.py --port 8100
"""
import json, hashlib, time, argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

MOCK_DATA = {
    "series": [
        {"series_id": "SRS-20260918-001", "title": "九天玄女传", "status": "in_production",
         "total_episodes": 12, "completed_episodes": 1, "genre": "仙侠/奇幻"}
    ],
    "episodes": {
        "SRS-20260918-001": [
            {"episode_id": "EP-001", "episode_number": 1, "title": "降世临凡", "status": "keyframe", "duration": 90},
            {"episode_id": "EP-002", "episode_number": 2, "title": "魔焰围城", "status": "storyboard", "duration": 90},
        ]
    },
    "storyboards": {
        "EP-002": [
            {"shot_id": "S02-001", "scene": "昆仑天柱全景，七方魔族合围", "duration": 10, "status": "pending"},
            {"shot_id": "S02-002", "scene": "玄女独守天柱，受伤状态", "duration": 10, "status": "pending"},
        ]
    },
    "tasks": {}
}

class MockHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/v1/series":
            self._send_json({"series": MOCK_DATA["series"], "total": len(MOCK_DATA["series"])})
        elif path.startswith("/api/v1/series/") and path.endswith("/episodes"):
            sid = path.split("/")[4]
            self._send_json({"episodes": MOCK_DATA["episodes"].get(sid, [])})
        elif path.startswith("/api/v1/episodes/") and path.endswith("/storyboard"):
            eid = path.split("/")[4]
            self._send_json({"episode_id": eid, "shots": MOCK_DATA["storyboards"].get(eid, [])})
        elif path == "/api/v1/pipeline/status":
            self._send_json({"queue_depth": {"keyframes": 5, "videos": 3}, "active_workers": {"keyframes": 2, "videos": 1}, "system_load": 0.45})
        elif path.startswith("/api/v1/keyframes/tasks/"):
            tid = path.split("/")[-1]
            task = MOCK_DATA["tasks"].get(tid, {"task_id": tid, "status": "completed", "progress": 100})
            self._send_json(task)
        else:
            self._send_json({"error": {"code": "NOT_FOUND", "message": f"Mock: {path}"}}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/api/v1/auth/token":
            self._send_json({"access_token": "mock_token_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:16], "token_type": "Bearer", "expires_in": 7200})
        elif path == "/api/v1/series":
            sid = "SRS-MOCK-" + str(int(time.time()))
            MOCK_DATA["series"].append({"series_id": sid, **body, "status": "created"})
            self._send_json({"series_id": sid, "status": "created"}, 201)
        elif path.startswith("/api/v1/episodes/") and path.endswith("/keyframes"):
            tid = "KF-TASK-MOCK-" + str(int(time.time()))
            MOCK_DATA["tasks"][tid] = {"task_id": tid, "status": "queued", "progress": 0}
            self._send_json({"task_id": tid, "status": "queued", "estimated_time": 120}, 202)
        elif path.startswith("/api/v1/episodes/") and path.endswith("/videos"):
            tid = "VID-TASK-MOCK-" + str(int(time.time()))
            MOCK_DATA["tasks"][tid] = {"task_id": tid, "status": "queued", "progress": 0}
            self._send_json({"task_id": tid, "status": "queued", "estimated_time": 300}, 202)
        else:
            self._send_json({"mock": "POST " + path, "received": body}, 200)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, format, *args):
        print(f"  [MOCK] {args[0]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8100)
    args = parser.parse_args()
    server = HTTPServer(("0.0.0.0", args.port), MockHandler)
    print(f"昆仑洞天短剧平台 API Mock 服务启动: http://localhost:{args.port}")
    print(f"确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print(f"零成本本地开发模式，不消耗付费额度")
    print("Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMock服务已停止")
