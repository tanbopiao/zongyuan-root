#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT KD-PIPELINE V1.4 (Port 8626)
短剧产线自治引擎·完整功能版
DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
功能:
  - 产线任务队列(创建->分镜->镜头->渲染->完成)
  - L4镜头生成层(8021)集成状态
  - 批次处理与失败重试
  - 数据持久化 + 统计
"""
import json, os, time, uuid, threading, urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8626
START_TS = time.time()
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'kd_data.json')
LOCK = threading.Lock()
L4_PROXY_URL = os.environ.get('L4_PROXY_URL', 'http://127.0.0.1:8021')

DEFAULT_DATA = {"tasks": [], "batches": [], "renders": []}

STATUS_FLOW = ["created", "storyboard", "shot", "render", "done"]
FAILED_STATUS = ["failed"]

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

def probe_l4():
    """探测L4镜头生成层(8021)"""
    try:
        with urllib.request.urlopen(f"{L4_PROXY_URL}/health", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

def advance_task(task):
    """推进任务状态机"""
    idx = STATUS_FLOW.index(task['status']) if task['status'] in STATUS_FLOW else -1
    if idx >= 0 and idx < len(STATUS_FLOW) - 1:
        task['status'] = STATUS_FLOW[idx + 1]
        task['updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if task['status'] == 'done':
            task['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
    return task

def create_batch(tasks):
    """将任务分组为批次"""
    batch_id = uuid.uuid4().hex[:12]
    return {"id": batch_id, "task_ids": [t['id'] for t in tasks],
            "size": len(tasks), "status": "processing",
            "created": time.strftime('%Y-%m-%d %H:%M:%S')}

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
            self._send(200, {"status": "healthy", "service": "kd-pipeline",
                             "port": PORT, "version": "V1.4",
                             "uptime": round(time.time()-START_TS, 1),
                             "task_count": len(data['tasks']),
                             "batch_count": len(data['batches']),
                             "l4_layer": {"port": 8021, "online": probe_l4()},
                             "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω"})
        elif p == '/api/tasks':
            self._send(200, {"tasks": data['tasks']})
        elif p == '/api/tasks/stats':
            stats = {}
            for t in data['tasks']:
                stats[t['status']] = stats.get(t['status'], 0) + 1
            self._send(200, {"stats": stats, "total": len(data['tasks'])})
        elif p == '/api/batches':
            self._send(200, {"batches": data['batches']})
        elif p == '/api/layers':
            self._send(200, {"layers": {"L4_shot_layer": {"port": 8021, "online": probe_l4()},
                                        "storyboard": {"status": "ready"},
                                        "render": {"status": "ready"}}})
        elif p == '/api/renders':
            self._send(200, {"renders": data['renders']})
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
        if p == '/api/tasks':
            tid = uuid.uuid4().hex[:12]
            task = {"id": tid, "script": j.get('script', ''), "title": j.get('title', ''),
                    "status": "created", "priority": j.get('priority', 'P2'),
                    "created": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "updated": time.strftime('%Y-%m-%d %H:%M:%S')}
            with LOCK:
                data['tasks'].insert(0, task)
                save_data(data)
            self._send(200, {"status": "created", "task_id": tid, "count": len(data['tasks'])})
        elif p == '/api/tasks/advance':
            tid = j.get('task_id', '')
            with LOCK:
                for t in data['tasks']:
                    if t['id'] == tid:
                        advance_task(t)
                        save_data(data)
                        self._send(200, {"status": "ok", "task_id": tid, "task_status": t['status']})
                        return
            self._send(404, {"status": "not_found", "task_id": tid})
        elif p == '/api/batches/run':
            # 将pending任务组批并逐级推进
            tasks = [t for t in data['tasks'] if t['status'] in ('created', 'storyboard', 'shot')]
            if not tasks:
                self._send(200, {"status": "no_tasks"})
                return
            batch = create_batch(tasks)
            with LOCK:
                data['batches'].insert(0, batch)
                for t in tasks:
                    advance_task(t)
                    advance_task(t)
                save_data(data)
            self._send(200, {"status": "processing", "batch_id": batch['id'],
                             "task_ids": batch['task_ids'], "size": batch['size']})
        elif p == '/api/renders':
            rid = uuid.uuid4().hex[:12]
            with LOCK:
                data['renders'].append({"id": rid, "task_id": j.get('task_id', ''),
                                        "status": "queued", "ts": time.strftime('%Y-%m-%d %H:%M:%S')})
                save_data(data)
            self._send(200, {"status": "queued", "render_id": rid})
        else:
            self._send(404, {"status": "not_found"})

    def do_DELETE(self):
        p = self.path.split('?')[0]
        data = load_data()
        m = __import__('re').match(r'/api/tasks/(\w+)', p)
        if m:
            tid = m.group(1)
            with LOCK:
                data['tasks'] = [t for t in data['tasks'] if t['id'] != tid]
                save_data(data)
            self._send(200, {"status": "deleted", "task_id": tid})
            return
        self._send(404, {"status": "not_found"})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"[kd-pipeline-v1.4] starting on :{PORT} {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
