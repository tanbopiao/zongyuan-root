#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT AI Experience Center V1.1 (Port 8046)
AI体验中心·完整功能版
DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
功能:
  - 4个工作流模板(决策/熔断/真值/短剧)可执行
  - 智能体动态注册/接入/健康检查
  - 工作流实例运行状态机(created->running->done/failed)
  - 数据持久化
"""
import json, os, time, uuid, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8046
START_TS = time.time()
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'ec_data.json')
LOCK = threading.Lock()

DEFAULT_DATA = {"agents": {}, "workflows": {}, "instances": []}

TEMPLATES = {
    "wf-decision": {"name": "三维稳态决策", "desc": "利益40%/风险35%/成本25%加权评分", "steps": ["输入方案", "权重计算", "输出评分"]},
    "wf-fuse": {"name": "熔断自愈模拟", "desc": "检测死循环→触发熔断→自愈恢复", "steps": ["健康检测", "熔断判定", "自愈执行"]},
    "wf-truth": {"name": "真值提炼蒸馏", "desc": "多轮交叉验证+来源锚定+冲突消解", "steps": ["碎片输入", "交叉验证", "蒸馏输出"]},
    "wf-drama": {"name": "短剧分镜产线", "desc": "大纲→分镜→关键帧→视频生成", "steps": ["大纲", "分镜表", "关键帧", "成片"]},
}

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

def execute_workflow(tpl_key, payload):
    """工作流执行引擎：按模板步骤模拟执行并返回结果"""
    tpl = TEMPLATES.get(tpl_key, {})
    result = {"template": tpl_key, "name": tpl.get('name', tpl_key), "steps_done": [], "output": {}}
    if tpl_key == 'wf-decision':
        opts = payload.get('options', [])
        scores = []
        for o in opts:
            s = round(0.4 * o.get('benefit', 0) + 0.35 * (100 - o.get('risk', 0)) + 0.25 * (100 - o.get('cost', 0)), 1)
            scores.append({"name": o.get('name', ''), "score": s})
        scores.sort(key=lambda x: -x['score'])
        result['steps_done'] = tpl.get('steps', [])
        result['output'] = {"scores": scores, "recommended": scores[0]['name'] if scores else None}
    elif tpl_key == 'wf-fuse':
        loop_detected = payload.get('loop_detected', True)
        result['steps_done'] = tpl.get('steps', [])
        result['output'] = {"loop_detected": loop_detected,
                            "action": "熔断隔离" if loop_detected else "正常",
                            "recovery": "自愈机制已触发" if loop_detected else "无需处理"}
    elif tpl_key == 'wf-truth':
        fragments = payload.get('fragments', [])
        verified = [f for f in fragments if f.get('cross_verified', False)]
        result['steps_done'] = tpl.get('steps', [])
        result['output'] = {"input_fragments": len(fragments), "verified": len(verified),
                            "purity_score": round(90 + len(verified) * 2, 1) if verified else 0}
    elif tpl_key == 'wf-drama':
        script = payload.get('script', '')
        result['steps_done'] = tpl.get('steps', [])
        result['output'] = {"script_len": len(script), "shots_planned": max(1, len(script) // 100),
                            "keyframes": "待生成", "status": "分镜规划完成"}
    return result

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
            self._send(200, {"status": "healthy", "service": "experience-center",
                             "port": PORT, "version": "V1.1",
                             "uptime": round(time.time()-START_TS, 1),
                             "agent_count": len(data['agents']), "templates": len(TEMPLATES),
                             "instance_count": len(data['instances']),
                             "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω"})
        elif p == '/api/agents':
            self._send(200, {"agents": data['agents']})
        elif p == '/api/templates':
            self._send(200, {"templates": TEMPLATES})
        elif p == '/api/instances':
            self._send(200, {"instances": data['instances']})
        elif p == '/api/workflows':
            self._send(200, {"workflows": data['workflows'], "templates": TEMPLATES})
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
        if p == '/api/agents/register':
            name = j.get('name') or f"agent-{uuid.uuid4().hex[:8]}"
            with LOCK:
                data['agents'][name] = {"status": "connected", "endpoint": j.get('endpoint', ''),
                                        "capabilities": j.get('capabilities', []),
                                        "last_seen": time.strftime('%Y-%m-%d %H:%M:%S'),
                                        "ts": time.time()}
                save_data(data)
            self._send(200, {"status": "ok", "agent": name, "count": len(data['agents']), "dynamic": True})
        elif p == '/api/workflows/run':
            tpl_key = j.get('template', 'wf-decision')
            if tpl_key not in TEMPLATES:
                self._send(400, {"status": "error", "msg": f"unknown template: {tpl_key}"})
                return
            inst_id = uuid.uuid4().hex[:12]
            inst = {"id": inst_id, "template": tpl_key, "name": TEMPLATES[tpl_key]['name'],
                    "status": "running", "payload": j.get('payload', {}),
                    "created": time.strftime('%Y-%m-%d %H:%M:%S')}
            with LOCK:
                data['instances'].insert(0, inst)
                save_data(data)
            # 异步执行
            def _run():
                time.sleep(0.5)
                result = execute_workflow(tpl_key, j.get('payload', {}))
                with LOCK:
                    for i in data['instances']:
                        if i['id'] == inst_id:
                            i['status'] = 'done'
                            i['result'] = result
                            i['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
                    save_data(data)
            threading.Thread(target=_run, daemon=True).start()
            self._send(200, {"status": "running", "instance_id": inst_id, "template": tpl_key})
        elif p == '/api/workflows/instantiate':
            tpl_key = j.get('template', 'wf-decision')
            with LOCK:
                data['workflows'][tpl_key] = {"template": tpl_key, "status": "ready",
                                              "instantiated": time.strftime('%Y-%m-%d %H:%M:%S')}
                save_data(data)
            self._send(200, {"status": "ok", "workflow": tpl_key, "ready": True})
        else:
            self._send(404, {"status": "not_found"})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"[experience-center-v1.1] starting on :{PORT} {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
