#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT Universal Agent Executor V1.1 (Port 8029)
通用智能体网关·完整功能版
DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
功能:
  - 智能体注册/发现/心跳/注销
  - 任务调度队列(优先级P0-P3)
  - 执行结果回写
  - 数据持久化
"""
import json, os, time, uuid, threading, heapq
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8029
START_TS = time.time()
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'uag_data.json')
LOCK = threading.Lock()

DEFAULT_DATA = {"agents": {}, "tasks": [], "results": {}}
PRIORITY = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}

def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        try:
            ln = int(self.headers.get('Content-Length', 0))
            return self.rfile.read(ln) if ln else b''
        except Exception:
            return b''

    def do_GET(self):
        p = self.path.split('?')[0]
        data = load_data()
        if p in ('/health', '/healthz'):
            online = sum(1 for a in data['agents'].values() if time.time() - a.get('ts', 0) < 120)
            self._send(200, {"status": "healthy", "service": "universal-agent-executor",
                             "port": PORT, "version": "V1.1",
                             "uptime": round(time.time()-START_TS, 1),
                             "agent_count": len(data['agents']), "online_agents": online,
                             "queue_depth": len([t for t in data['tasks'] if t['status'] == 'queued']),
                             "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω"})
        elif p == '/agents':
            # 在线智能体（120秒心跳窗口）
            online = {k: v for k, v in data['agents'].items() if time.time() - v.get('ts', 0) < 120}
            self._send(200, {"agents": online, "total": len(data['agents']), "online": len(online)})
        elif p == '/agents/all':
            self._send(200, {"agents": data['agents']})
        elif p == '/tasks':
            self._send(200, {"tasks": data['tasks']})
        elif p == '/tasks/queued':
            self._send(200, {"queued": [t for t in data['tasks'] if t['status'] == 'queued']})
        else:
            self._send(404, {"status": "not_found"})

    def do_POST(self):
        p = self.path.split('?')[0]
        data = load_data()
        body = self._read_body()
        try:
            j = json.loads(body or b'{}')
        except Exception:
            j = {}
        if p == '/register':
            name = j.get('name') or f"agent-{uuid.uuid4().hex[:8]}"
            with LOCK:
                data['agents'][name] = {"status": "registered",
                                        "capabilities": j.get('capabilities', []),
                                        "endpoint": j.get('endpoint', ''),
                                        "ts": time.time(),
                                        "registered": time.strftime('%Y-%m-%d %H:%M:%S')}
                save_data(data)
            self._send(200, {"status": "ok", "agent": name, "count": len(data['agents'])})
        elif p == '/heartbeat':
            name = j.get('name', '')
            with LOCK:
                if name in data['agents']:
                    data['agents'][name]['ts'] = time.time()
                    data['agents'][name]['status'] = 'online'
                    save_data(data)
                    self._send(200, {"status": "ok", "agent": name, "heartbeat": True})
                    return
            self._send(404, {"status": "unknown_agent", "agent": name})
        elif p == '/execute':
            tid = uuid.uuid4().hex[:12]
            task = {"id": tid, "task": j.get('task') or j.get('query') or 'empty',
                    "priority": j.get('priority', 'P2'),
                    "agent": j.get('agent', 'any'),
                    "status": "queued", "created": time.strftime('%Y-%m-%d %H:%M:%S')}
            with LOCK:
                data['tasks'].insert(0, task)
                save_data(data)
            self._send(200, {"status": "queued", "task_id": tid, "priority": task['priority'],
                             "queue_depth": len([t for t in data['tasks'] if t['status'] == 'queued'])})
        elif p == '/tasks/pick':
            # 调度器取任务：优先P0，可指定agent
            target = j.get('agent', 'any')
            with LOCK:
                candidates = [t for t in data['tasks'] if t['status'] == 'queued' and
                              (target == 'any' or t['agent'] == target or t['agent'] == 'any')]
                candidates.sort(key=lambda t: PRIORITY.get(t['priority'], 3))
                if candidates:
                    t = candidates[0]
                    t['status'] = 'running'
                    t['agent_assigned'] = target
                    t['picked'] = time.strftime('%Y-%m-%d %H:%M:%S')
                    save_data(data)
                    self._send(200, {"status": "assigned", "task": t})
                else:
                    self._send(200, {"status": "empty"})
        elif p == '/tasks/complete':
            tid = j.get('task_id', '')
            with LOCK:
                for t in data['tasks']:
                    if t['id'] == tid:
                        t['status'] = 'done'
                        t['result'] = j.get('result', {})
                        t['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        save_data(data)
                        self._send(200, {"status": "ok", "task_id": tid, "done": True})
                        return
            self._send(404, {"status": "not_found", "task_id": tid})
        elif p == '/unregister':
            name = j.get('name', '')
            with LOCK:
                if name in data['agents']:
                    data['agents'][name]['status'] = 'unregistered'
                    data['agents'][name]['ts'] = 0
                    save_data(data)
                    self._send(200, {"status": "ok", "agent": name})
                    return
            self._send(404, {"status": "unknown_agent"})
        else:
            self._send(404, {"status": "not_found"})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"[universal-agent-executor-v1.1] starting on :{PORT} {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
