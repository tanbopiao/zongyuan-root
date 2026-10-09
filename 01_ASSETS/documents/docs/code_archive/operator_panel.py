#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 算子统一管理面板
端口：8170
功能：算子状态总览、服务管理、Merkle链状态、自愈引擎状态
"""
import json
import subprocess
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = 8170
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

# 算子服务清单（名称: 描述）
OPERATOR_SERVICES = {
    "mr010-dual-compute-scheduler": "MR-010 双算力调度器",
    "mr011-stability-evolution": "MR-011 稳态进化引擎",
    "mr012-kernel-bus": "MR-012 内核总线",
    "mr013-truth-unify": "MR-013 真值统一服务",
    "mr014-metacognition": "MR-014 元认知引擎",
    "mr015-truth-generator": "MR-015 主动真值生成器",
    "mr016-thinking-evolution": "MR-016 思维进化引擎",
    "mr017-self-development": "MR-017 自我开发引擎",
    "mr018-multi-node": "MR-018 多节点协同",
    "mr019-long-term-memory": "MR-019 长期记忆",
    "mr020-meta-kernel": "MR-020 元内核终极集成",
    "dr-resource-monitor": "DR 资源监控熔断",
    "dr-self-healing-monitor": "DR 全链路自愈监控",
    "dr-truth-absorber": "DR 真值自动吸收",
    "huodouai-autonomy": "全域自治引擎",
    "huodouai-deep-healing": "全域深度自愈引擎",
    "huodouai-kernel-hub": "Kernel Hub调度器",
    "huodouai-learning": "学习反馈引擎",
    "huodouai-midplatform-healing": "中台9组件自愈",
    "huodouai-protocol-gateway": "协议网关",
    "huodouai-three-dim": "三维稳态决策",
    "self-healing-engine": "自动自愈修复引擎(8161)",
    "zongyuan-self-healing": "自组织自愈",
    "gov-operator-cluster": "政务算子集群",
    "commercial-api": "商业API网关",
    "kg-api": "知识图谱API",
    "zongyuan-unified-gateway": "统一记忆网关(9120)",
}

def get_service_status(name):
    try:
        result = subprocess.run(['systemctl', 'is-active', name], capture_output=True, text=True, timeout=3)
        return result.stdout.strip()
    except:
        return "unknown"

def get_service_enabled(name):
    try:
        result = subprocess.run(['systemctl', 'is-enabled', name], capture_output=True, text=True, timeout=3)
        return result.stdout.strip()
    except:
        return "unknown"

def get_merkle_status():
    try:
        with open('/opt/ZONGYUAN-ROOT/kernel/merkle_chain_state.json') as f:
            state = json.load(f)
        latest = state['chain'][-1] if state['chain'] else {}
        return {
            "height": latest.get('height', 0),
            "integrity": latest.get('integrity_percent', 0),
            "root": latest.get('merkle_root', '')[:24] + '...',
            "last_update": latest.get('timestamp', 'unknown')
        }
    except:
        return {"height": 0, "integrity": 0, "root": "unknown", "last_update": "unknown"}

def get_healing_status():
    try:
        req = urllib.request.Request("http://127.0.0.1:8161/api/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read())
    except:
        return {"status": "unreachable"}

def get_gateway_status():
    try:
        req = urllib.request.Request("http://127.0.0.1:9120/api/stats")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read())
    except:
        try:
            req = urllib.request.Request("http://127.0.0.1:9120/api/truths?limit=1")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                return {"truth_count": data.get('total', data.get('count', 'unknown'))}
        except:
            return {"status": "unreachable"}

class PanelHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/health':
            self._json({"status": "ok"})
            return
        if self.path == '/api/overview':
            services = []
            running = 0
            for name, desc in OPERATOR_SERVICES.items():
                status = get_service_status(name)
                enabled = get_service_enabled(name)
                if status == 'active':
                    running += 1
                services.append({"name": name, "desc": desc, "status": status, "enabled": enabled})
            data = {
                "timestamp": datetime.now().isoformat(),
                "did": DID,
                "anchor": ANCHOR,
                "total_services": len(OPERATOR_SERVICES),
                "running": running,
                "stopped": len(OPERATOR_SERVICES) - running,
                "services": services,
                "merkle": get_merkle_status(),
                "healing": get_healing_status(),
                "gateway": get_gateway_status()
            }
            self._json(data)
            return
        if self.path == '/' or self.path == '/index.html':
            self._html()
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith('/api/service/'):
            parts = self.path.split('/')
            if len(parts) >= 4:
                action = parts[3]  # start/stop/restart
                service = parts[4]
                if service in OPERATOR_SERVICES and action in ['start', 'stop', 'restart']:
                    subprocess.run(['systemctl', action, service], timeout=5)
                    self._json({"action": action, "service": service, "status": get_service_status(service)})
                    return
            self.send_response(400)
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def _json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _html(self):
        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ZONGYUAN-ROOT 算子管理面板</title>
<style>
body{font-family:monospace;background:#0a0a0a;color:#0f0;margin:20px}
h1{color:#0f0;border-bottom:1px solid #0f0}
.card{border:1px solid #333;padding:15px;margin:10px 0;border-radius:5px}
.status-running{color:#0f0}.status-stopped{color:#f00}
table{width:100%;border-collapse:collapse}
td,th{border:1px solid #333;padding:8px;text-align:left}
th{background:#111}
button{background:#111;color:#0f0;border:1px solid #0f0;padding:5px 10px;cursor:pointer;margin:2px}
button:hover{background:#0f0;color:#000}
</style></head><body>
<h1>Ω₀⊂⊙∞⊂Ω ZONGYUAN-ROOT 算子管理面板</h1>
<div id="overview" class="card">加载中...</div>
<div id="services" class="card"><h2>算子服务清单</h2><div id="list">加载中...</div></div>
<script>
function refresh(){
  fetch('/api/overview').then(r=>r.json()).then(d=>{
    document.getElementById('overview').innerHTML=
      '<h2>总览</h2>'+
      '<p>算子服务: '+d.running+'/'+d.total_services+' 运行中</p>'+
      '<p>Merkle链: 高度'+d.merkle.height+' | 完整性'+d.merkle.integrity+'% | '+d.merkle.last_update+'</p>'+
      '<p>自愈引擎: '+d.healing.status+' | 故障模式'+d.healing.fault_patterns_count+' | 待审核'+d.healing.pending_approvals+'</p>'+
      '<p>记忆网关: '+JSON.stringify(d.gateway).substring(0,100)+'</p>';
    let html='<table><tr><th>服务</th><th>描述</th><th>状态</th><th>开机自启</th><th>操作</th></tr>';
    d.services.forEach(s=>{
      html+='<tr><td>'+s.name+'</td><td>'+s.desc+'</td>'+
        '<td class="status-'+s.status+'">'+s.status+'</td><td>'+s.enabled+'</td>'+
        '<td><button onclick="act(\\'restart\\',\\''+s.name+'\\')">重启</button></td></tr>';
    });
    html+='</table>';
    document.getElementById('list').innerHTML=html;
  });
}
function act(action,service){
  if(confirm('确认'+action+' '+service+'?')){
    fetch('/api/service/'+action+'/'+service,{method:'POST'}).then(()=>refresh());
  }
}
refresh();setInterval(refresh,30000);
</script></body></html>"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), PanelHandler)
    print(f"算子管理面板启动，端口{PORT}")
    server.serve_forever()
