#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜全域可视化仪表盘 (Flask Web)
提供：节点状态、Merkle账本、指令调度、审计日志、能量态监控 的可视化与API
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""
import sys
import os
import json
import time
import socket
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "operators"))
sys.path.insert(0, str(BASE_DIR))
MASTER_DB = BASE_DIR / "master" / "core" / "master_state.db"
LEDGER_DIR = BASE_DIR / "ledger"
LOG_DIR = BASE_DIR / "logs"

# 统一数据库连接模块（自动设置PRAGMA: WAL/NORMAL/20MB缓存）
from comm.db_utils import get_connection

# 配置加载器（支持热加载）
try:
    from config_loader import config as _config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False

# 算子调度器
try:
    from operator_dispatcher import get_dispatcher
    _OPERATOR_DISPATCHER_AVAILABLE = True
except ImportError:
    _OPERATOR_DISPATCHER_AVAILABLE = False

def _cfg(key, default):
    if _CONFIG_AVAILABLE:
        return _config.get(key, default)
    return default

DID = _cfg("system.did", "DID-BR-000002")
TRACE = _cfg("system.trace", "Ω₀⊂⊙∞⊂Ω")
DASHBOARD_HOST = _cfg("dashboard.host", "0.0.0.0")
DASHBOARD_PORT = _cfg("dashboard.port", 8090)
DASHBOARD_DEBUG = _cfg("dashboard.debug", False)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>元极恒一｜全域自治仪表盘 v1.1</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',system-ui,sans-serif}
body{background:linear-gradient(135deg,#080c14 0%,#0d1424 50%,#0a1018 100%);color:#e6edf7;padding:16px;min-height:100vh}
.container{max-width:1600px;margin:0 auto}
.header{background:linear-gradient(90deg,rgba(20,40,80,0.6),rgba(15,30,60,0.4));border:1px solid #2a4068;border-radius:14px;padding:18px 24px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.header h1{font-size:24px;background:linear-gradient(90deg,#73c0ff,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .meta{color:#94a3b8;font-size:13px}
.header .status-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(74,222,128,0.15);color:#4ade80;padding:6px 14px;border-radius:20px;font-size:13px;border:1px solid rgba(74,222,128,0.3)}
.status-dot{width:8px;height:8px;border-radius:50%;background:#4ade80;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:16px}
.stat{background:linear-gradient(135deg,rgba(24,35,56,0.9),rgba(18,25,40,0.9));border:1px solid #2a3f5f;border-radius:12px;padding:16px;position:relative;overflow:hidden}
.stat::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:linear-gradient(180deg,#40a9ff,#73c0ff)}
.stat .label{font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px}
.stat .val{font-size:28px;font-weight:bold;margin-top:6px}
.stat .val.green{color:#4ade80}.stat .val.blue{color:#60a5fa}.stat .val.purple{color:#a78bfa}.stat .val.amber{color:#fbbf24}
.stat .sub{font-size:11px;color:#64748b;margin-top:4px}
.card{background:linear-gradient(135deg,rgba(20,30,50,0.85),rgba(15,22,38,0.85));border:1px solid #2a3f5f;border-radius:14px;padding:18px;margin-bottom:16px;backdrop-filter:blur(10px)}
.card h2{font-size:16px;margin-bottom:14px;color:#a5cdff;display:flex;align-items:center;gap:8px}
.card h2 .icon{font-size:18px}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.three-col{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:900px){.two-col,.three-col{grid-template-columns:1fr}}
.tri-state{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.tri-box{background:rgba(15,25,45,0.6);border-radius:10px;padding:14px;border:1px solid #2a3f5f}
.tri-box.logic{border-left:3px solid #60a5fa}
.tri-box.info{border-left:3px solid #4ade80}
.tri-box.energy{border-left:3px solid #fbbf24}
.tri-box h3{font-size:13px;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.tri-box .tri-val{font-size:20px;font-weight:bold;margin-bottom:4px}
.tri-box .tri-desc{font-size:11px;color:#94a3b8;line-height:1.5}
.chart{width:100%;height:300px}
.chart-sm{width:100%;height:240px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border:1px solid #24324b;padding:9px 10px;text-align:left}
th{background:linear-gradient(180deg,#1a273f,#162038);color:#b8d8ff;font-weight:600}
tr:hover{background:rgba(59,130,246,0.05)}
.online{color:#4ade80;font-weight:600}.offline{color:#f87171;font-weight:600}
.btn{background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff;border:none;padding:9px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:500;transition:all 0.2s}
.btn:hover{background:linear-gradient(135deg,#1d4ed8,#1e40af);transform:translateY(-1px);box-shadow:0 4px 12px rgba(37,99,235,0.4)}
.btn:disabled{opacity:0.5;cursor:not-allowed}
input,select{background:rgba(26,39,63,0.8);border:1px solid #344563;color:#e6edf7;padding:8px 12px;border-radius:6px;font-size:13px;outline:none;transition:border-color 0.2s}
input:focus,select:focus{border-color:#40a9ff}
.merkle-root{font-family:'Courier New',monospace;background:rgba(0,0,0,0.3);padding:10px 14px;border-radius:8px;color:#9ee0ff;font-size:12px;word-break:break-all;border:1px solid #2a4068}
.audit-log{font-size:12px;max-height:320px;overflow-y:auto;font-family:'Courier New',monospace}
.audit-entry{padding:6px 8px;border-bottom:1px solid #1a273f;display:flex;gap:10px}
.audit-entry .ts{color:#64748b;white-space:nowrap}
.audit-entry .evt{color:#73c0ff;white-space:nowrap}
.audit-entry .payload{color:#94a3b8;overflow:hidden;text-overflow:ellipsis}
.config-item{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1a273f;font-size:13px}
.config-item .key{color:#94a3b8}.config-item .val{color:#e6edf7;font-weight:500}
.fuse-normal{color:#4ade80}.fuse-warning{color:#fbbf24}.fuse-critical{color:#f87171}
.footer{text-align:center;color:#475569;font-size:12px;padding:20px 0}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#1a273f}
::-webkit-scrollbar-thumb{background:#344563;border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:#40a9ff}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <div>
    <h1>Ω₀⊂⊙∞⊂Ω 元极恒一全域自治仪表盘</h1>
    <div class="meta">DID-BR-000002 · 主中枢+次中枢集群 · 三态驱动引擎 v1.1 · 实时监控</div>
  </div>
  <div class="status-badge"><span class="status-dot"></span><span id="system-status">系统运行中</span></div>
</div>

<div class="grid" id="stats-grid"></div>

<div class="card">
  <h2><span class="icon">🔮</span>三态驱动引擎状态</h2>
  <div class="tri-state">
    <div class="tri-box logic">
      <h3>🧠 逻辑态 Logic State</h3>
      <div class="tri-val" id="logic-decision" style="color:#60a5fa">--</div>
      <div class="tri-desc" id="logic-desc">裁决与决策层：权限校验、规则匹配、冲突检测、熔断裁决</div>
    </div>
    <div class="tri-box info">
      <h3>📊 信息态 Info State</h3>
      <div class="tri-val" id="info-hash" style="color:#4ade80">--</div>
      <div class="tri-desc" id="info-desc">数据与真值载荷层：载荷验证、真值校验、Merkle锚定、内容哈希</div>
    </div>
    <div class="tri-box energy">
      <h3>⚡ 能量态 Energy State</h3>
      <div class="tri-val" id="energy-fuse" style="color:#fbbf24">--</div>
      <div class="tri-desc" id="energy-desc">资源配额与执行层：资源采集、阈值裁决、配额分配、熔断保护</div>
    </div>
  </div>
</div>

<div class="two-col">
  <div class="card">
    <h2><span class="icon">📈</span>能量态实时监控</h2>
    <div id="chart-energy" class="chart"></div>
  </div>
  <div class="card">
    <h2><span class="icon">🌐</span>节点集群拓扑</h2>
    <div id="chart-topology" class="chart"></div>
  </div>
</div>

<div class="card">
  <h2><span class="icon">🖥️</span>节点集群状态</h2>
  <table id="nodes-table">
  <thead><tr><th>节点ID</th><th>类型</th><th>状态</th><th>CPU%</th><th>内存%</th><th>最后心跳</th></tr></thead>
  <tbody><tr><td colspan="6">加载中...</td></tr></tbody>
  </table>
</div>

<div class="two-col">
  <div class="card">
    <h2><span class="icon">🔗</span>Merkle账本状态</h2>
    <div id="merkle-info"></div>
  </div>
  <div class="card">
    <h2><span class="icon">⚙️</span>配置加载器状态</h2>
    <div id="config-info"></div>
  </div>
</div>

<div class="card">
  <h2><span class="icon">📡</span>指令调度中心</h2>
  <div style="margin-bottom:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center">
    <select id="action-select">
      <option value="SCAN_ASSET">SCAN_ASSET 资产扫描</option>
      <option value="RUN_PIPELINE">RUN_PIPELINE 真值流水线</option>
      <option value="CROSS_VERIFY">CROSS_VERIFY 双向对账</option>
      <option value="SYNC_LEDGER">SYNC_LEDGER 账本同步</option>
      <option value="RELOAD_RULE">RELOAD_RULE 重载规则</option>
    </select>
    <select id="target-select">
      <option value="ALL">全域所有节点</option>
      <option value="node-01">node-01</option>
      <option value="node-02">node-02</option>
      <option value="node-03">node-03</option>
    </select>
    <select id="priority-select">
      <option value="normal">普通优先级</option>
      <option value="high">高优先级</option>
      <option value="critical">紧急优先级</option>
    </select>
    <button class="btn" onclick="dispatchCommand()">下发三态指令</button>
  </div>
  <table id="cmd-table">
  <thead><tr><th>指令ID</th><th>动作</th><th>目标</th><th>优先级</th><th>状态</th><th>创建时间</th></tr></thead>
  <tbody><tr><td colspan="6">加载中...</td></tr></tbody>
  </table>
</div>

<div class="card">
  <h2><span class="icon">📋</span>最近审计日志</h2>
  <div id="audit-log" class="audit-log"></div>
</div>

<div class="footer">
  元极恒一自治体系 v1.1 · Ω₀⊂⊙∞⊂Ω · DID-BR-000002 · 数据每5秒自动刷新
</div>

</div>

<script>
const energyChart = echarts.init(document.getElementById('chart-energy'));
const topologyChart = echarts.init(document.getElementById('chart-topology'));
let cpuData=[],memData=[],diskData=[],loadData=[],timeLabels=[];

function fetchData(){
  // 系统状态
  fetch('/api/status').then(r=>r.json()).then(d=>{
    document.getElementById('stats-grid').innerHTML = `
      <div class="stat"><div class="label">在线节点</div><div class="val green">${d.online_nodes}/${d.total_nodes}</div><div class="sub">主中枢+次中枢集群</div></div>
      <div class="stat"><div class="label">Merkle叶子</div><div class="val blue">${d.merkle_leaf_count||0}</div><div class="sub">SHA256增量Merkle树</div></div>
      <div class="stat"><div class="label">已执行指令</div><div class="val purple">${d.completed_cmds||0}</div><div class="sub">三态驱动指令</div></div>
      <div class="stat"><div class="label">网关真值</div><div class="val amber">${d.gateway_truth_count||'N/A'}</div><div class="sub">记忆网关云端存储</div></div>
    `;
    let nodesHtml = d.nodes.map(n=>`<tr>
      <td><strong>${n.node_id}</strong></td><td>${n.node_type}</td>
      <td class="${n.status}">${n.status}</td>
      <td>${n.cpu_usage||'-'}</td><td>${n.mem_usage||'-'}</td>
      <td>${n.last_heartbeat?new Date(n.last_heartbeat*1000).toLocaleTimeString():'-'}</td>
    </tr>`).join('');
    document.querySelector('#nodes-table tbody').innerHTML = nodesHtml || '<tr><td colspan="6">暂无节点</td></tr>';
    // 拓扑图
    updateTopology(d.nodes);
  });

  // 三态引擎
  fetch('/api/tri_state').then(r=>r.json()).then(d=>{
    if(d.error){document.getElementById('logic-decision').textContent='未初始化';return;}
    const s=d.stats||{};
    document.getElementById('logic-decision').textContent=`允许:${s.allowed||0} 拒绝:${s.denied_logic||0}`;
    document.getElementById('info-hash').textContent=`处理:${s.info_processed_count||0}`;
    document.getElementById('energy-fuse').textContent=`熔断:${s.fuse_events||0}`;
  });

  // 能量态
  fetch('/api/energy').then(r=>r.json()).then(d=>{
    const now=new Date().toLocaleTimeString();
    timeLabels.push(now);
    cpuData.push(d.cpu?.percent||0);memData.push(d.memory?.percent||0);
    diskData.push(d.disk?.percent||0);loadData.push(d.cpu?.load_avg_1m||0);
    if(timeLabels.length>30){timeLabels.shift();cpuData.shift();memData.shift();diskData.shift();loadData.shift();}
    const fuseClass=d.fuse_level==='critical'?'fuse-critical':d.fuse_level==='warning'?'fuse-warning':'fuse-normal';
    document.getElementById('energy-fuse').innerHTML=`<span class="${fuseClass}">${d.fuse_level?.toUpperCase()}</span>`;
    document.getElementById('energy-desc').textContent=`CPU:${d.cpu?.percent}% 内存:${d.memory?.percent}% 磁盘:${d.disk?.percent}% 负载:${d.cpu?.load_avg_1m}`;
    energyChart.setOption({
      backgroundColor:'transparent',tooltip:{trigger:'axis'},
      legend:{data:['CPU%','内存%','磁盘%','负载'],textStyle:{color:'#cbd5e1'},top:0},
      grid:{left:50,right:20,top:40,bottom:30},
      xAxis:{type:'category',data:timeLabels,axisLabel:{color:'#94a3b8',fontSize:10}},
      yAxis:{max:100,name:'%',nameTextStyle:{color:'#94a3b8'},axisLabel:{color:'#94a3b8'}},
      series:[
        {name:'CPU%',type:'line',data:cpuData,color:'#40a9ff',smooth:true,areaStyle:{opacity:0.15}},
        {name:'内存%',type:'line',data:memData,color:'#f59e0b',smooth:true,areaStyle:{opacity:0.1}},
        {name:'磁盘%',type:'line',data:diskData,color:'#a78bfa',smooth:true},
        {name:'负载',type:'line',data:loadData,color:'#4ade80',smooth:true}
      ]
    });
  });

  // Merkle
  fetch('/api/merkle').then(r=>r.json()).then(d=>{
    const mt=d.merkle_tree||{};
    document.getElementById('merkle-info').innerHTML = `
      <div style="margin-bottom:10px"><strong style="color:#a5cdff">根哈希:</strong></div>
      <div class="merkle-root">${mt.root||'未生成'}</div>
      <div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div class="stat" style="padding:10px"><div class="label">叶子数量</div><div class="val blue" style="font-size:22px">${mt.leaf_count||0}</div></div>
        <div class="stat" style="padding:10px"><div class="label">审计日志</div><div class="val green" style="font-size:22px">${d.audit_log?.entry_count||0}</div></div>
      </div>
      <div style="margin-top:10px;font-size:12px;color:#94a3b8">算法: ${mt.algorithm||'sha256'} · 更新: ${mt.updated_at?new Date(mt.updated_at*1000).toLocaleString():'-'}</div>
    `;
  });

  // 配置
  fetch('/api/config').then(r=>r.json()).then(d=>{
    const kc=d.key_configs||{};
    document.getElementById('config-info').innerHTML = `
      <div class="config-item"><span class="key">配置加载器</span><span class="val" style="color:${d.config_loader==='available'?'#4ade80':'#f87171'}">${d.config_loader}</span></div>
      <div class="config-item"><span class="key">元规则版本</span><span class="val">${d.meta_rules_version}</span></div>
      <div class="config-item"><span class="key">热加载</span><span class="val" style="color:${d.hot_reload?'#4ade80':'#f87171'}">${d.hot_reload?'已启用':'未启用'}</span></div>
      <div class="config-item"><span class="key">配置文件数</span><span class="val">${(d.config_files||[]).length}</span></div>
      <div class="config-item"><span class="key">主中枢循环</span><span class="val">${kc.master_loop_interval}s</span></div>
      <div class="config-item"><span class="key">Worker循环</span><span class="val">${kc.worker_loop_interval}s</span></div>
      <div class="config-item"><span class="key">仪表盘端口</span><span class="val">:${kc.dashboard_port}</span></div>
      <div class="config-item"><span class="key">备份保留</span><span class="val">${kc.backup_daily_retention}天</span></div>
    `;
  });

  // 指令
  fetch('/api/commands').then(r=>r.json()).then(d=>{
    let html=(d.commands||[]).slice(0,10).map(c=>`<tr>
      <td>${c.cmd_id}</td><td>${c.action}</td><td>${c.target_node}</td>
      <td>${c.priority||'normal'}</td><td>${c.status}</td>
      <td>${new Date(c.create_time*1000).toLocaleString()}</td>
    </tr>`).join('');
    document.querySelector('#cmd-table tbody').innerHTML=html||'<tr><td colspan="6">暂无指令</td></tr>';
  });

  // 审计
  fetch('/api/audit').then(r=>r.json()).then(d=>{
    document.getElementById('audit-log').innerHTML=(d.logs||[]).slice(0,40).map(l=>
      `<div class="audit-entry"><span class="ts">${new Date(l.ts*1000).toLocaleTimeString()}</span><span class="evt">${l.event}</span><span class="payload">${JSON.stringify(l.payload||{}).slice(0,100)}</span></div>`
    ).join('')||'暂无日志';
  });
}

function updateTopology(nodes){
  const nodeList=[{name:'MASTER',symbolSize:50,itemStyle:{color:'#40a9ff'},label:{show:true,color:'#fff',fontSize:12}}];
  const links=[];
  (nodes||[]).filter(n=>n.node_type!=='master').forEach((n,i)=>{
    const color=n.status==='online'?'#4ade80':'#f87171';
    nodeList.push({name:n.node_id,symbolSize:35,itemStyle:{color},label:{show:true,color:'#fff',fontSize:10}});
    links.push({source:'MASTER',target:n.node_id,lineStyle:{color:color,width:2,curveness:0.1}});
  });
  topologyChart.setOption({
    backgroundColor:'transparent',
    tooltip:{},
    series:[{type:'graph',layout:'force',roam:true,
      force:{repulsion:200,gravity:0.1,edgeLength:120},
      data:nodeList,links:links,
      lineStyle:{opacity:0.7},
      emphasis:{focus:'adjacency',lineStyle:{width:4}}
    }]
  });
}

function dispatchCommand(){
  const action=document.getElementById('action-select').value;
  const target=document.getElementById('target-select').value;
  const priority=document.getElementById('priority-select').value;
  const btn=event.target;btn.disabled=true;btn.textContent='下发中...';
  fetch('/api/dispatch',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({action,target_node:target,priority})})
    .then(r=>r.json()).then(d=>{
      alert('三态指令已下发: '+d.cmd_id+'\\n优先级: '+priority);
      fetchData();
    }).catch(()=>alert('指令下发失败')).finally(()=>{btn.disabled=false;btn.textContent='下发三态指令';});
}

fetchData();
setInterval(fetchData,5000);
window.addEventListener('resize',()=>{energyChart.resize();topologyChart.resize();});
</script>
</body>
</html>
"""


def get_db_connection():
    if MASTER_DB.exists():
        return get_connection(MASTER_DB)
    return None


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/status")
def api_status():
    nodes = []
    total_nodes = 0
    online_nodes = 0
    conn = get_db_connection()
    if conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM nodes ORDER BY node_type, node_id")
        for row in cur.fetchall():
            d = dict(row)
            nodes.append(d)
            total_nodes += 1
            if d["status"] == "online":
                online_nodes += 1
        cur.execute("SELECT COUNT(*) FROM commands WHERE status='completed'")
        completed = cur.fetchone()[0]
        cur.execute("SELECT root_hash, leaf_count FROM merkle_roots ORDER BY create_time DESC LIMIT 1")
        merkle_row = cur.fetchone()
        conn.close()
    else:
        completed = 0
        merkle_row = None

    merkle_root = merkle_row[0] if merkle_row else ""
    merkle_leaf = merkle_row[1] if merkle_row else 0

    return jsonify({
        "nodes": nodes,
        "total_nodes": total_nodes,
        "online_nodes": online_nodes,
        "completed_cmds": completed,
        "merkle_root": merkle_root,
        "merkle_leaf_count": merkle_leaf,
        "gateway_truth_count": None,
        "timestamp": time.time()
    })


@app.route("/api/commands")
def api_commands():
    commands = []
    conn = get_db_connection()
    if conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM commands ORDER BY create_time DESC LIMIT 50")
        commands = [dict(r) for r in cur.fetchall()]
        conn.close()
    return jsonify({"commands": commands})


@app.route("/api/audit")
def api_audit():
    logs = []
    audit_file = LEDGER_DIR / "audit_log.jsonl"
    if audit_file.exists():
        for line in audit_file.read_text(encoding="utf-8").strip().split("\n")[-50:]:
            if line.strip():
                try:
                    logs.append(json.loads(line))
                except Exception:
                    pass
    return jsonify({"logs": list(reversed(logs))})


@app.route("/api/dispatch", methods=["POST"])
def api_dispatch():
    data = request.get_json()
    action = data.get("action", "")
    target = data.get("target_node", "ALL")

    sys.path.insert(0, str(BASE_DIR / "comm" / "protocol"))
    from comm_protocol import ensure_queue_dirs, build_message, write_message, sha256_str
    ensure_queue_dirs()

    cmd_id = f"CMD-{int(time.time())}-{sha256_str(action+target)[:8]}"
    msg = build_message("COMMAND", "MASTER", target, {
        "cmd_id": cmd_id, "action": action, "payload": {}
    })
    write_message("master_out", msg)

    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute('''INSERT INTO commands (cmd_id, action, target_node, payload, status, create_time)
        VALUES (?,?,?,?, 'dispatched', ?)''',
        (cmd_id, action, target, "{}", time.time()))
        conn.commit()
        conn.close()

    return jsonify({"status": "dispatched", "cmd_id": cmd_id, "action": action, "target": target})


@app.route("/api/nodes/<node_id>")
def api_node_detail(node_id):
    conn = get_db_connection()
    if conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM nodes WHERE node_id=?", (node_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
    return jsonify({"error": "node not found"}), 404


@app.route("/api/tri_state")
def api_tri_state():
    """三态驱动引擎状态API"""
    try:
        import sys
        sys.path.insert(0, str(BASE_DIR / "worker"))
        from tri_state_engine import get_engine
        engine = get_engine()
        stats = engine.get_stats()
        return jsonify({
            "engine": "tri_state_engine",
            "version": "v1.0",
            "status": "running",
            "stats": stats,
            "three_states": {
                "logic_state": "裁决与决策层（权限校验/规则匹配/冲突检测/熔断裁决）",
                "info_state": "数据与真值载荷层（载荷验证/真值校验/Merkle锚定/内容哈希）",
                "energy_state": "资源配额与执行层（资源采集/阈值裁决/配额分配/熔断保护）",
            },
            "did": DID,
            "trace": TRACE,
        })
    except Exception as e:
        return jsonify({"error": str(e), "engine": "not_initialized"}), 500


@app.route("/api/energy")
def api_energy():
    """能量态实时统计API"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(BASE_DIR))
        load_avg = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0]

        # 阈值（从配置加载）
        cpu_warn = _cfg("worker.energy_cpu_warning", 80.0)
        cpu_crit = _cfg("worker.energy_cpu_critical", 95.0)
        mem_warn = _cfg("worker.energy_mem_warning", 80.0)
        mem_crit = _cfg("worker.energy_mem_critical", 95.0)

        # 熔断级别判定
        fuse_level = "normal"
        if cpu_percent >= cpu_crit or mem.percent >= mem_crit:
            fuse_level = "critical"
        elif cpu_percent >= cpu_warn or mem.percent >= mem_warn:
            fuse_level = "warning"

        return jsonify({
            "timestamp": time.time(),
            "fuse_level": fuse_level,
            "cpu": {
                "percent": round(cpu_percent, 1),
                "count": psutil.cpu_count(),
                "load_avg_1m": round(load_avg[0], 2),
                "load_avg_5m": round(load_avg[1], 2),
                "load_avg_15m": round(load_avg[2], 2),
            },
            "memory": {
                "percent": round(mem.percent, 1),
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
            },
            "disk": {
                "percent": round(disk.percent, 1),
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
            },
            "thresholds": {
                "cpu_warning": cpu_warn,
                "cpu_critical": cpu_crit,
                "mem_warning": mem_warn,
                "mem_critical": mem_crit,
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/merkle")
def api_merkle():
    """Merkle账本状态API"""
    try:
        merkle_file = LEDGER_DIR / "merkle_tree.json"
        audit_file = LEDGER_DIR / "audit_log.jsonl"

        result = {"timestamp": time.time()}

        if merkle_file.exists():
            with open(merkle_file, "r", encoding="utf-8") as f:
                merkle_data = json.load(f)
            result["merkle_tree"] = {
                "root": merkle_data.get("root", "N/A"),
                "leaf_count": merkle_data.get("leaf_count", len(merkle_data.get("leaves", []))),
                "algorithm": merkle_data.get("algorithm", "sha256"),
                "updated_at": merkle_data.get("updated_at", "N/A"),
            }
        else:
            result["merkle_tree"] = {"status": "not_found"}

        if audit_file.exists():
            audit_count = sum(1 for _ in open(audit_file, "r", encoding="utf-8"))
            result["audit_log"] = {
                "entry_count": audit_count,
                "file_size": audit_file.stat().st_size,
            }
        else:
            result["audit_log"] = {"status": "not_found"}

        # 主中枢数据库中的Merkle根
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT * FROM merkle_roots ORDER BY id DESC LIMIT 1")
                row = cur.fetchone()
                if row:
                    result["db_merkle_root"] = {
                        "root": row[1] if len(row) > 1 else "N/A",
                        "created_at": row[2] if len(row) > 2 else "N/A",
                    }
            except Exception:
                pass
            conn.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/config")
def api_config():
    """配置加载器状态API"""
    return jsonify({
        "config_loader": "available" if _CONFIG_AVAILABLE else "unavailable",
        "meta_rules_version": _cfg("meta_rules_version", "unknown"),
        "hot_reload": True,
        "config_files": [
            {"name": "meta_rules.json", "path": "config/meta_rules.json", "description": "元规则配置（15个配置段，支持热加载）"},
            {"name": "env.json", "path": "config/env.json", "description": "环境配置"},
            {"name": "supervisord.conf", "path": "config/supervisord.conf", "description": "Supervisor进程管理配置"},
            {"name": "requirements.txt", "path": "config/requirements.txt", "description": "Python依赖清单"},
            {"name": "system_deps.txt", "path": "config/system_deps.txt", "description": "系统依赖清单"},
        ],
        "key_configs": {
            "master_loop_interval": _cfg("master.loop_interval", 15),
            "slave_loop_interval": _cfg("slave.loop_interval", 15),
            "worker_loop_interval": _cfg("worker.loop_interval", 30),
            "dashboard_port": _cfg("dashboard.port", 8090),
            "gateway_url": _cfg("gateway.base_url", "N/A"),
            "backup_daily_retention": _cfg("backup.daily_retention_days", 7),
            "watchdog_interval": _cfg("watchdog.check_interval", 60),
        },
        "did": DID,
        "trace": TRACE,
    })


@app.route("/api/operators")
def api_operators():
    """27算子状态API"""
    if not _OPERATOR_DISPATCHER_AVAILABLE:
        return jsonify({
            "status": "unavailable",
            "message": "算子调度器未加载",
            "registered_operators": 0,
            "operators": [],
        })

    try:
        dispatcher = get_dispatcher()
        status = dispatcher.get_status()
        return jsonify({
            "status": "available",
            "dispatcher_status": status.get("dispatcher_status", "unknown"),
            "registered_operators": status.get("registered_operators", 0),
            "total_executions": status.get("total_executions", 0),
            "operators": status.get("operators", []),
            "persistence": status.get("persistence", {}),
            "modules_available": status.get("modules_available", False),
            "did": DID,
            "trace": TRACE,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/operators/run", methods=["POST"])
def api_operators_run():
    """执行算子API"""
    if not _OPERATOR_DISPATCHER_AVAILABLE:
        return jsonify({"status": "error", "message": "算子调度器未加载"}), 503

    try:
        data = request.get_json() or {}
        operator_id = data.get("operator_id")
        if not operator_id:
            return jsonify({"status": "error", "message": "缺少operator_id参数"}), 400

        dispatcher = get_dispatcher()
        result = dispatcher.run_operator(operator_id, **data.get("params", {}))
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/operators/inspection", methods=["POST"])
def api_operators_inspection():
    """执行算子每日巡检API"""
    if not _OPERATOR_DISPATCHER_AVAILABLE:
        return jsonify({"status": "error", "message": "算子调度器未加载"}), 503

    try:
        data = request.get_json() or {}
        mode = data.get("mode", "light")
        dispatcher = get_dispatcher()
        report = dispatcher.run_daily_inspection(mode=mode)
        return jsonify(report)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/health")
@app.route("/api/health/live")
def api_health_live():
    """健康检查 - liveness探针（K8s）
    检查进程是否存活，返回200表示存活，503表示不存活
    """
    healthy = True
    checks = {}

    # 1. 仪表盘进程自身（必然存活，因为能响应请求）
    checks["dashboard_process"] = {"status": "ok", "pid": os.getpid()}

    # 2. 配置加载器
    checks["config_loader"] = {"status": "ok" if _CONFIG_AVAILABLE else "degraded"}

    # 3. 主中枢数据库可访问
    try:
        conn = get_connection(str(MASTER_DB))
        conn.execute("SELECT 1")
        conn.close()
        checks["master_db"] = {"status": "ok"}
    except Exception as e:
        checks["master_db"] = {"status": "error", "error": str(e)}
        healthy = False

    return jsonify({
        "status": "ok" if healthy else "error",
        "liveness": healthy,
        "checks": checks,
        "timestamp": time.time(),
        "did": DID,
        "trace": TRACE,
    }), 200 if healthy else 503


@app.route("/api/health/ready")
def api_health_ready():
    """健康检查 - readiness探针（K8s）
    检查是否准备好接收流量，返回200表示就绪，503表示未就绪
    readiness比liveness更严格，需要所有核心组件正常
    """
    ready = True
    checks = {}

    # 1. 仪表盘进程
    checks["dashboard"] = {"status": "ok"}

    # 2. 主中枢数据库
    try:
        conn = get_connection(str(MASTER_DB))
        conn.execute("SELECT 1")
        conn.close()
        checks["master_db"] = {"status": "ok"}
    except Exception as e:
        checks["master_db"] = {"status": "error", "error": str(e)}
        ready = False

    # 3. 节点在线数（至少主中枢在线）
    try:
        conn = get_connection(str(MASTER_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE status='online'")
        online_nodes = cursor.fetchone()[0]
        conn.close()
        checks["nodes_online"] = {"status": "ok" if online_nodes >= 1 else "degraded", "count": online_nodes}
        if online_nodes < 1:
            ready = False
    except Exception as e:
        checks["nodes_online"] = {"status": "error", "error": str(e)}
        ready = False

    # 4. Merkle账本文件存在
    ledger_file = LEDGER_DIR / "merkle_tree.json"
    if ledger_file.exists():
        checks["merkle_ledger"] = {"status": "ok"}
    else:
        checks["merkle_ledger"] = {"status": "degraded", "error": "ledger file not found"}

    # 5. 算子调度器（如果可用）
    if _OPERATOR_DISPATCHER_AVAILABLE:
        try:
            dispatcher = get_dispatcher()
            op_count = dispatcher.get_status().get("registered_operators", 0)
            checks["operators"] = {"status": "ok", "registered": op_count}
        except Exception:
            checks["operators"] = {"status": "degraded"}
    else:
        checks["operators"] = {"status": "degraded", "error": "dispatcher not available"}

    return jsonify({
        "status": "ok" if ready else "error",
        "readiness": ready,
        "checks": checks,
        "timestamp": time.time(),
        "did": DID,
        "trace": TRACE,
    }), 200 if ready else 503


@app.route("/api/health/details")
def api_health_details():
    """健康检查 - 详细状态（所有组件）"""
    details = {
        "dashboard": {"status": "ok", "pid": os.getpid(), "port": DASHBOARD_PORT},
        "config_loader": {"status": "ok" if _CONFIG_AVAILABLE else "unavailable"},
        "timestamp": time.time(),
        "did": DID,
        "trace": TRACE,
    }

    # 数据库
    try:
        conn = get_connection(str(MASTER_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE status='online'")
        online_nodes = cursor.fetchone()[0]
        conn.close()
        details["master_db"] = {"status": "ok", "total_nodes": total_nodes, "online_nodes": online_nodes}
    except Exception as e:
        details["master_db"] = {"status": "error", "error": str(e)}

    # 算子
    if _OPERATOR_DISPATCHER_AVAILABLE:
        try:
            dispatcher = get_dispatcher()
            op_status = dispatcher.get_status()
            details["operators"] = {
                "status": "ok",
                "registered": op_status.get("registered_operators", 0),
                "persistence_results": op_status.get("persistence", {}).get("total_results", 0),
            }
        except Exception as e:
            details["operators"] = {"status": "error", "error": str(e)}

    # 三态引擎
    try:
        tri_state_file = BASE_DIR / "worker" / "tri_state_engine.py"
        details["tri_state_engine"] = {"status": "ok" if tri_state_file.exists() else "not_found"}
    except Exception:
        pass

    # Merkle账本
    try:
        ledger_file = LEDGER_DIR / "merkle_tree.json"
        if ledger_file.exists():
            with open(ledger_file, "r") as f:
                ledger = json.load(f)
            details["merkle_ledger"] = {
                "status": "ok",
                "root": ledger.get("root_hash", "N/A")[:32] + "...",
                "leaf_count": ledger.get("leaf_count", 0),
            }
        else:
            details["merkle_ledger"] = {"status": "not_found"}
    except Exception as e:
        details["merkle_ledger"] = {"status": "error", "error": str(e)}

    # 系统资源
    try:
        import psutil
        details["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
    except Exception:
        pass

    return jsonify(details)


@app.route("/metrics")
def api_metrics():
    """Prometheus指标导出端点
    暴露元极恒一体系的所有监控指标，供Prometheus抓取
    """
    metrics = []

    def add_metric(name, help_text, metric_type, value, labels=None):
        """添加一个Prometheus指标"""
        metrics.append(f"# HELP {name} {help_text}")
        metrics.append(f"# TYPE {name} {metric_type}")
        if labels:
            label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
            metrics.append(f"{name}{{{label_str}}} {value}")
        else:
            metrics.append(f"{name} {value}")

    # 1. 健康状态
    add_metric("yuanjihengyi_health_liveness", "Liveness健康状态(1=健康,0=不健康)", "gauge", 1)
    add_metric("yuanjihengyi_health_readiness", "Readiness就绪状态(1=就绪,0=未就绪)", "gauge", 1)

    # 2. 进程状态（从supervisor获取）
    try:
        import subprocess
        result = subprocess.run(
            ["supervisorctl", "-c", str(BASE_DIR / "config" / "supervisord.conf"), "status"],
            capture_output=True, text=True, timeout=5
        )
        process_count = 0
        running_count = 0
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    proc_name = parts[0].split(":")[-1] if ":" in parts[0] else parts[0]
                    proc_status = 1 if parts[1] == "RUNNING" else 0
                    add_metric("yuanjihengyi_process_status",
                               f"进程运行状态(1=RUNNING,0=其他)", "gauge", proc_status,
                               {"process": proc_name})
                    process_count += 1
                    running_count += proc_status
        add_metric("yuanjihengyi_process_total", "进程总数", "gauge", process_count)
        add_metric("yuanjihengyi_process_running", "运行中进程数", "gauge", running_count)
    except Exception:
        add_metric("yuanjihengyi_process_status", "进程状态获取失败", "gauge", 0, {"process": "unknown"})

    # 3. 节点状态
    try:
        conn = get_connection(str(MASTER_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT node_id, status FROM nodes")
        for node_id, status in cursor.fetchall():
            node_status = 1 if status == "online" else 0
            add_metric("yuanjihengyi_node_status",
                       "节点在线状态(1=online,0=offline)", "gauge", node_status,
                       {"node": node_id})
        cursor.execute("SELECT COUNT(*) FROM nodes")
        add_metric("yuanjihengyi_node_total", "节点总数", "gauge", cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE status='online'")
        add_metric("yuanjihengyi_node_online", "在线节点数", "gauge", cursor.fetchone()[0])
        conn.close()
    except Exception as e:
        add_metric("yuanjihengyi_node_status", "节点状态获取失败", "gauge", 0, {"node": "unknown", "error": str(e)})

    # 4. 算子状态
    if _OPERATOR_DISPATCHER_AVAILABLE:
        try:
            dispatcher = get_dispatcher()
            op_status = dispatcher.get_status()
            add_metric("yuanjihengyi_operator_registered", "已注册算子数", "gauge",
                       op_status.get("registered_operators", 0))
            add_metric("yuanjihengyi_operator_results_total", "算子持久化结果总数", "gauge",
                       op_status.get("persistence", {}).get("total_results", 0))
        except Exception:
            pass

    # 5. 系统资源
    try:
        import psutil
        add_metric("yuanjihengyi_system_cpu_percent", "CPU使用率(%)", "gauge",
                   round(psutil.cpu_percent(interval=0.1), 2))
        add_metric("yuanjihengyi_system_memory_percent", "内存使用率(%)", "gauge",
                   round(psutil.virtual_memory().percent, 2))
        add_metric("yuanjihengyi_system_memory_used_bytes", "内存使用量(bytes)", "gauge",
                   psutil.virtual_memory().used)
        add_metric("yuanjihengyi_system_disk_percent", "磁盘使用率(%)", "gauge",
                   round(psutil.disk_usage("/").percent, 2))
        add_metric("yuanjihengyi_system_disk_used_bytes", "磁盘使用量(bytes)", "gauge",
                   psutil.disk_usage("/").used)
    except Exception:
        pass

    # 6. Merkle账本状态
    try:
        ledger_file = LEDGER_DIR / "merkle_tree.json"
        if ledger_file.exists():
            with open(ledger_file, "r") as f:
                ledger = json.load(f)
            add_metric("yuanjihengyi_merkle_leaf_count", "Merkle账本叶子节点数", "gauge",
                       ledger.get("leaf_count", 0))
    except Exception:
        pass

    # 7. 审计日志条数
    try:
        audit_file = LEDGER_DIR / "audit_log.jsonl"
        if audit_file.exists():
            with open(audit_file, "r") as f:
                audit_count = sum(1 for _ in f)
            add_metric("yuanjihengyi_audit_log_count", "审计日志条数", "gauge", audit_count)
    except Exception:
        pass

    # 8. 联邦状态
    try:
        fed_config = BASE_DIR / "config" / "federation_config.json"
        if fed_config.exists():
            with open(fed_config, "r") as f:
                fed = json.load(f)
            add_metric("yuanjihengyi_federation_enabled", "联邦同步是否启用(1=启用,0=禁用)", "gauge",
                       1 if fed.get("sync_config", {}).get("enabled", False) else 0)
            add_metric("yuanjihengyi_federation_peer_count", "联邦对等节点数", "gauge",
                       len(fed.get("peer_instances", [])))
    except Exception:
        pass

    # 9. 配置加载器状态
    add_metric("yuanjihengyi_config_loader_enabled", "配置加载器是否启用(1=启用,0=禁用)", "gauge",
               1 if _CONFIG_AVAILABLE else 0)

    # 10. 元信息
    add_metric("yuanjihengyi_info", "元极恒一体系信息", "gauge", 1,
               {"version": "v1.5", "did": DID, "instance": socket.gethostname()})

    return "\n".join(metrics) + "\n", 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/api/system/metrics")
def api_system_metrics():
    """系统资源监控API
    返回CPU/内存/磁盘/网络/进程的详细实时数据，供监控面板使用
    """
    metrics = {
        "timestamp": time.time(),
        "did": DID,
        "trace": TRACE,
    }

    try:
        import psutil

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        metrics["cpu"] = {
            "percent": cpu_percent,
            "count": cpu_count,
            "freq_mhz": cpu_freq.current if cpu_freq else 0,
            "per_cpu": psutil.cpu_percent(percpu=True),
            "load_avg": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [],
        }

        # 内存
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        metrics["memory"] = {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        }

        # 磁盘
        disk_root = psutil.disk_usage("/")
        disk_home = psutil.disk_usage("/home/user")
        metrics["disk"] = {
            "root": {
                "total": disk_root.total,
                "used": disk_root.used,
                "free": disk_root.free,
                "percent": disk_root.percent,
            },
            "home": {
                "total": disk_home.total,
                "used": disk_home.used,
                "free": disk_home.free,
                "percent": disk_home.percent,
            },
        }

        # 网络
        net_io = psutil.net_io_counters()
        metrics["network"] = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
        }

        # 进程统计
        all_processes = list(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]))
        total_processes = len(all_processes)
        # Top 5 CPU进程
        top_cpu = sorted(all_processes, key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)[:5]
        # Top 5 内存进程
        top_mem = sorted(all_processes, key=lambda p: p.info.get("memory_percent", 0) or 0, reverse=True)[:5]
        metrics["processes"] = {
            "total": total_processes,
            "top_cpu": [{"pid": p.info["pid"], "name": p.info["name"], "cpu": p.info.get("cpu_percent", 0)} for p in top_cpu],
            "top_memory": [{"pid": p.info["pid"], "name": p.info["name"], "mem": p.info.get("memory_percent", 0)} for p in top_mem],
        }

        # 元极恒一进程
        yuanji_processes = []
        for p in all_processes:
            name = p.info.get("name", "")
            if any(k in name for k in ["python", "master_core", "slave_core", "worker_main", "dashboard", "watchdog"]):
                try:
                    cmdline = " ".join(p.cmdline()) if hasattr(p, "cmdline") else ""
                    if any(k in cmdline for k in ["yuanjihengyi", "master_core", "slave_core", "worker_main", "dashboard.py", "watchdog"]):
                        yuanji_processes.append({
                            "pid": p.info["pid"],
                            "name": name,
                            "cpu": p.info.get("cpu_percent", 0),
                            "memory": p.info.get("memory_percent", 0),
                            "cmdline": cmdline[:100],
                        })
                except Exception:
                    pass
        metrics["yuanji_processes"] = yuanji_processes

        # 启动时间
        metrics["boot_time"] = psutil.boot_time()
        metrics["uptime_seconds"] = time.time() - psutil.boot_time()

    except ImportError:
        metrics["error"] = "psutil not available"
    except Exception as e:
        metrics["error"] = str(e)

    return jsonify(metrics)


@app.route("/system-monitor")
def system_monitor():
    """系统资源监控面板页面"""
    monitor_file = Path(__file__).parent / "system_monitor.html"
    if monitor_file.exists():
        with open(monitor_file, "r", encoding="utf-8") as f:
            return f.read()
    return "System monitor page not found", 404


if __name__ == "__main__":
    print("=" * 50)
    print("元极恒一全域仪表盘启动")
    print(f"访问: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print(f"溯源: {TRACE} | {DID}")
    print(f"配置加载器: {'已启用(热加载)' if _CONFIG_AVAILABLE else '未启用(默认值)'}")
    print("=" * 50)
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=DASHBOARD_DEBUG)
