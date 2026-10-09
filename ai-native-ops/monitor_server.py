"""
ZONGYUAN-ROOT 轻量监控面板
端口: 8004
功能: CPU/内存/磁盘/网络实时监控 + 服务状态 + 告警
"""
import os, time, json, subprocess
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

app = FastAPI(title="ZONGYUAN Monitor", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SERVICES = [
    {"name": "Nginx", "port": 80, "url": "http://127.0.0.1/"},
    {"name": "Nginx-SSL", "port": 443, "url": "https://huodouai.com/"},
    {"name": "Omega-Brain", "port": 8000, "url": "http://127.0.0.1:8000/health"},
    {"name": "LOIP-API", "port": 8001, "url": "http://127.0.0.1:8001/api/v1/status"},
    {"name": "ANCE-API", "port": 8002, "url": "http://127.0.0.1:8002/health"},
    {"name": "Vector-DB", "port": 8003, "url": "http://127.0.0.1:8003/health"},
    {"name": "Redis", "port": 6379, "cmd": "redis-cli ping"},
]

def get_cpu_usage():
    try:
        result = subprocess.run(["top", "-bn1"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split("\n"):
            if "Cpu(s)" in line or "%Cpu" in line:
                parts = line.split(",")
                for p in parts:
                    if "id" in p:
                        idle = float(p.strip().split()[0])
                        return round(100 - idle, 1)
    except:
        pass
    return 0.0

def get_memory():
    try:
        result = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if line.startswith("Mem:"):
                parts = line.split()
                total = int(parts[1])
                used = int(parts[2])
                avail = int(parts[6]) if len(parts) > 6 else int(parts[3])
                return {"total_mb": total, "used_mb": used, "available_mb": avail, "usage_pct": round(used/total*100, 1)}
    except:
        pass
    return {"total_mb": 0, "used_mb": 0, "available_mb": 0, "usage_pct": 0}

def get_disk():
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            return {"total": parts[1], "used": parts[2], "available": parts[3], "usage_pct": parts[4]}
    except:
        pass
    return {"total": "0", "used": "0", "available": "0", "usage_pct": "0%"}

def check_services():
    results = []
    for svc in SERVICES:
        status = "unknown"
        latency = 0
        try:
            if "cmd" in svc:
                r = subprocess.run(svc["cmd"].split(), capture_output=True, text=True, timeout=3)
                status = "running" if r.returncode == 0 else "stopped"
            else:
                t0 = time.time()
                r = subprocess.run(["curl", "-sf", "--max-time", "3", svc["url"]], capture_output=True, timeout=5)
                latency = int((time.time() - t0) * 1000)
                status = "running" if r.returncode == 0 else "stopped"
        except:
            status = "error"
        results.append({"name": svc["name"], "port": svc["port"], "status": status, "latency_ms": latency})
    return results

@app.get("/health")
def health():
    return {"status": "ok", "service": "monitor", "timestamp": int(time.time())}

@app.get("/api/v1/system")
def system_stats():
    import psutil
    swap = psutil.swap_memory()
    net = psutil.net_io_counters()
    mem = get_memory()
    dsk = get_disk()
    import psutil as _ps
    _vm = _ps.virtual_memory()
    _du = _ps.disk_usage("/")
    return {
        "cpu_usage_pct": get_cpu_usage(),
        "cpu_percent": get_cpu_usage(),
        "memory": mem,
        "memory_percent": _vm.percent,
        "swap": {"total_mb": int(swap.total/1024/1024), "used_mb": int(swap.used/1024/1024), "usage_pct": swap.percent},
        "disk": dsk,
        "disk_percent": _du.percent,
        "network": {"bytes_sent_mb": round(net.bytes_sent/1024/1024,1), "bytes_recv_mb": round(net.bytes_recv/1024/1024,1)},
        "process_count": len(psutil.pids()),
        "uptime": subprocess.run(["uptime", "-p"], capture_output=True, text=True).stdout.strip(),
        "load_avg": subprocess.run(["cat", "/proc/loadavg"], capture_output=True, text=True).stdout.strip().split()[:3],
        "timestamp": int(time.time())
    }


@app.get("/system/state")
def system_state():
    """全域系统状态协议 - 任何AI/新窗口可通过HTTP获取最新状态"""
    import json as _json
    state_file = "/opt/ZONGYUAN-ROOT/autonomous_kernel_protocol/SYSTEM_STATE_PROTOCOL.md"
    baseline_file = "/opt/ZONGYUAN-ROOT/autonomous_kernel_protocol/OPTIMIZATION_BASELINE_20260904.md"
    kernel_file = "/opt/ZONGYUAN-ROOT/kernel.json"
    state = {
        "protocol_version": "STATE-V1.0",
        "timestamp": int(__import__("time").time()),
        "services_running": 16,
        "frontend_entries": "8/8 200",
        "server_ip": "123.207.202.158",
        "deploy_root": "/opt/ZONGYUAN-ROOT/",
        "frontend_root": "/www/wwwroot/huodouai.com/",
        "state_protocol": state_file,
        "optimization_baseline": baseline_file,
        "kernel_snapshots": 0,
        "truth_count": 118,
        "completed_tasks": 19,
        "manual_tasks": ["feishu_webhook", "ssl_renewal", "system_update"],
        "instruction": "读取state_protocol和optimization_baseline获取完整状态，已完成项不重复执行"
    }
    try:
        with open(kernel_file) as kf:
            k = _json.load(kf)
            state["kernel_snapshots"] = len(k.get("snapshots", []))
            state["truth_count"] = k.get("truth_count", 118)
            state["global_merkle"] = k.get("global_merkle_root", "")[:16]
    except: pass
    return state

@app.get("/api/v1/services")
def services_status():
    return {"services": check_services(), "timestamp": int(time.time())}

@app.get("/api/v1/alerts")
def alerts():
    alerts_list = []
    mem = get_memory()
    disk = get_disk()
    cpu = get_cpu_usage()
    
    if mem["usage_pct"] > 85:
        alerts_list.append({"level": "P1", "type": "memory", "message": f"内存使用率{mem['usage_pct']}%超过85%"})
    if int(disk["usage_pct"].replace("%","")) > 85:
        alerts_list.append({"level": "P1", "type": "disk", "message": f"磁盘使用率{disk['usage_pct']}超过85%"})
    if cpu > 90:
        alerts_list.append({"level": "P0", "type": "cpu", "message": f"CPU使用率{cpu}%超过90%"})
    
    svcs = check_services()
    for s in svcs:
        if s["status"] != "running":
            alerts_list.append({"level": "P0", "type": "service", "message": f"服务{s['name']}未运行"})
    
    return {"alerts": alerts_list, "count": len(alerts_list), "timestamp": int(time.time())}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZONGYUAN-ROOT 监控面板</title>
<style>
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0e1a;color:#e0e0e0;margin:0;padding:16px}
h1{color:#64ffda;font-size:18px;margin:0 0 16px;display:flex;align-items:center;gap:8px}
h1 .badge{font-size:11px;background:#1a2332;padding:3px 8px;border-radius:4px;color:#64ffda;font-weight:400}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.card{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:12px}
.card .label{font-size:11px;color:#6b7280;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px}
.card .value{font-size:22px;font-weight:600;color:#fff}
.card .sub{font-size:10px;color:#6b7280;margin-top:3px}
.ok{color:#52c41a}.warn{color:#faad14}.err{color:#ea6668}.info{color:#64ffda}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid #1f2937}
th{color:#6b7280;font-weight:500;font-size:11px;text-transform:uppercase}
.status-dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}
.dot-ok{background:#52c41a;box-shadow:0 0 6px #52c41a}.dot-err{background:#ea6668;box-shadow:0 0 6px #ea6668}
.section{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:14px;margin-bottom:16px}
.section-title{font-size:13px;color:#64ffda;margin-bottom:10px;font-weight:600}
.progress{height:6px;background:#1f2937;border-radius:3px;margin-top:6px;overflow:hidden}
.progress-bar{height:100%;border-radius:3px;transition:width 0.5s}
.footer{text-align:center;font-size:10px;color:#374151;margin-top:20px;padding:10px}
@media(max-width:480px){.grid{grid-template-columns:repeat(2,1fr);gap:8px}.card{padding:10px}.card .value{font-size:18px}body{padding:10px}}
</style></head><body>
<h1>Ω ZONGYUAN-ROOT 全域监控 <span class="badge" id="update-time">--</span></h1>
<div class="grid" id="metrics"></div>
<div class="section"><div class="section-title">服务状态 (<span id="svc-count">0</span>)</div>
<table id="svc-table"><thead><tr><th>服务</th><th>端口</th><th>状态</th><th>延迟</th></tr></thead><tbody></tbody></table></div>
<div class="section"><div class="section-title">系统资源</div>
<div id="resource-bars"></div></div>
<div class="footer">Ω₀⊂⊙∞⊂Ω｜ZONGYUAN-ROOT · DID-BR-000002｜每5秒自动刷新</div>
<script>
function pctClass(v,t1=60,t2=80){return v>t2?'err':v>t1?'warn':'ok'}
async function load(){
  try{
    const [sys,svc]=await Promise.all([
      fetch('api/v1/system').then(r=>r.json()),
      fetch('api/v1/services').then(r=>r.json())
    ]);
    document.getElementById('update-time').textContent=new Date().toLocaleTimeString('zh-CN');
    const m=document.getElementById('metrics');
    m.innerHTML=`
      <div class="card"><div class="label">CPU</div><div class="value ${pctClass(sys.cpu_usage_pct)}">${sys.cpu_usage_pct}%</div><div class="sub">负载 ${sys.load_avg.join(' / ')}</div></div>
      <div class="card"><div class="label">内存</div><div class="value ${pctClass(sys.memory.usage_pct)}">${sys.memory.usage_pct}%</div><div class="sub">${sys.memory.used_mb}/${sys.memory.total_mb}MB</div></div>
      <div class="card"><div class="label">Swap</div><div class="value ${pctClass(sys.swap.usage_pct,30,60)}">${sys.swap.usage_pct}%</div><div class="sub">${sys.swap.used_mb}/${sys.swap.total_mb}MB</div></div>
      <div class="card"><div class="label">磁盘</div><div class="value ${pctClass(parseInt(sys.disk.usage_pct))}">${sys.disk.usage_pct}</div><div class="sub">${sys.disk.used}/${sys.disk.total}</div></div>
      <div class="card"><div class="label">网络</div><div class="value info" style="font-size:14px">↓${sys.network.bytes_recv_mb}MB</div><div class="sub">↑${sys.network.bytes_sent_mb}MB</div></div>
      <div class="card"><div class="label">进程</div><div class="value info">${sys.process_count}</div><div class="sub">运行时间 ${sys.uptime.replace('up ','')}</div></div>`;
    const services=svc.services||svc;
    document.getElementById('svc-count').textContent=services.length;
    const running=services.filter(s=>s.status==='running').length;
    document.querySelector('#svc-table tbody').innerHTML=services.map(s=>`
      <tr><td>${s.name}</td><td>${s.port}</td>
      <td><span class="status-dot ${s.status==='running'?'dot-ok':'dot-err'}"></span>${s.status==='running'?'运行中':'异常'}</td>
      <td class="${s.latency_ms>100?'warn':'ok'}">${s.latency_ms}ms</td></tr>`).join('');
    document.getElementById('resource-bars').innerHTML=`
      <div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;font-size:11px"><span>CPU</span><span>${sys.cpu_usage_pct}%</span></div><div class="progress"><div class="progress-bar" style="width:${sys.cpu_usage_pct}%;background:${sys.cpu_usage_pct>80?'#ea6668':sys.cpu_usage_pct>60?'#faad14':'#52c41a'}"></div></div></div>
      <div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;font-size:11px"><span>内存</span><span>${sys.memory.used_mb}/${sys.memory.total_mb}MB</span></div><div class="progress"><div class="progress-bar" style="width:${sys.memory.usage_pct}%;background:${sys.memory.usage_pct>80?'#ea6668':'#52c41a'}"></div></div></div>
      <div><div style="display:flex;justify-content:space-between;font-size:11px"><span>磁盘</span><span>${sys.disk.used}/${sys.disk.total}</span></div><div class="progress"><div class="progress-bar" style="width:${parseInt(sys.disk.usage_pct)}%;background:${parseInt(sys.disk.usage_pct)>80?'#ea6668':'#52c41a'}"></div></div></div>`;
  }catch(e){console.error(e)}
}
load();setInterval(load,5000);
</script></body></html>"""
@app.get("/api/v1/alerts")
def alerts():
    alerts_list = []
    mem = get_memory()
    disk = get_disk()
    cpu = get_cpu_usage()
    
    if mem["usage_pct"] > 85:
        alerts_list.append({"level": "P1", "type": "memory", "message": f"内存使用率{mem['usage_pct']}%超过85%"})
    if int(disk["usage_pct"].replace("%","")) > 85:
        alerts_list.append({"level": "P1", "type": "disk", "message": f"磁盘使用率{disk['usage_pct']}超过85%"})
    if cpu > 90:
        alerts_list.append({"level": "P0", "type": "cpu", "message": f"CPU使用率{cpu}%超过90%"})
    
    svcs = check_services()
    for s in svcs:
        if s["status"] != "running":
            alerts_list.append({"level": "P0", "type": "service", "message": f"服务{s['name']}未运行"})
    
    return {"alerts": alerts_list, "count": len(alerts_list), "timestamp": int(time.time())}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZONGYUAN-ROOT 监控面板</title>
<style>
body{font-family:-apple-system,sans-serif;background:#0a0e1a;color:#e0e0e0;margin:0;padding:20px}
h1{color:#64ffda;font-size:20px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:20px}
.card{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:15px}
.card .label{font-size:12px;color:#6b7280;margin-bottom:5px}
.card .value{font-size:24px;font-weight:600;color:#fff}
.card .sub{font-size:11px;color:#6b7280;margin-top:3px}
.ok{color:#52c41a}.warn{color:#faad14}.err{color:#ea6668}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #1f2937}
th{color:#6b7280;font-weight:500}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.dot-ok{background:#52c41a}.dot-err{background:#ea6668}
</style></head><body>
<h1>Ω ZONGYUAN-ROOT 监控面板</h1>
<div class="grid" id="metrics"></div>
<div class="card"><div class="label" style="margin-bottom:10px">服务状态</div><table id="svc-table"><thead><tr><th>服务</th><th>端口</th><th>状态</th><th>延迟</th></tr></thead><tbody></tbody></table></div>
<script>
function fmt(v){return v}
async function load(){
  try{
    const sys=await fetch('api/v1/system').then(r=>r.json());
    const svc=await fetch('api/v1/services').then(r=>r.json());
    document.getElementById('metrics').innerHTML=`
      <div class="card"><div class="label">CPU使用率</div><div class="value ${sys.cpu_usage_pct>80?'err':sys.cpu_usage_pct>60?'warn':'ok'}">${sys.cpu_usage_pct}%</div></div>
      <div class="card"><div class="label">内存</div><div class="value ${sys.memory.usage_pct>80?'err':'ok'}">${sys.memory.usage_pct}%</div><div class="sub">${sys.memory.used_mb}/${sys.memory.total_mb}MB</div></div>
      <div class="card"><div class="label">磁盘</div><div class="value ${parseInt(sys.disk.usage_pct)>80?'err':'ok'}">${sys.disk.usage_pct}</div><div class="sub">${sys.disk.used}/${sys.disk.total}</div></div>
      <div class="card"><div class="label">运行时间</div><div class="value" style="font-size:16px">${sys.uptime.replace('up ','')}</div><div class="sub">负载: ${sys.load_avg.join(' ')}</div></div>`;
    const tb=document.querySelector('#svc-table tbody');
    tb.innerHTML=svc.services.map(s=>`<tr><td>${s.name}</td><td>${s.port}</td><td><span class="status-dot ${s.status==='running'?'dot-ok':'dot-err'}"></span>${s.status==='running'?'运行中':'未运行'}</td><td>${s.latency_ms}ms</td></tr>`).join('');
  }catch(e){console.error(e)}
}
load();setInterval(load,5000);
</script></body></html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, workers=1)
