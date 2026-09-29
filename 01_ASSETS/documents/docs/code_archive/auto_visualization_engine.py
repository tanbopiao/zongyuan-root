#!/usr/bin/env python3
"""
自动可视化交付引擎 V1.0
每10分钟运行：扫描9120新增真值 → 识别可可视化资产 → 生成/更新仪表盘 → 轻量化 → 集成官网 → 上报
"""
import json, sqlite3, time, os, urllib.request, hashlib
from datetime import datetime

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
WWW_ROOT = "/www/wwwroot/www.huodouai.com"
WWW_ROOT2 = "/www/wwwroot/huodouai.com"
LOG_PATH = "/opt/ZONGYUAN-ROOT/logs/auto_visualization.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

def scan_truths():
    """扫描真值库，生成可视化数据"""
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # 总览
    cur.execute("SELECT COUNT(*) FROM truths")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT node_id) FROM truths")
    nodes = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT category) FROM truths")
    categories = cur.fetchone()[0]
    
    # 分类分布
    cur.execute("SELECT category, COUNT(*) FROM truths GROUP BY category ORDER BY COUNT(*) DESC")
    cat_dist = [{"name": r[0] or "未分类", "value": r[1]} for r in cur.fetchall()]
    
    # 节点贡献Top10
    cur.execute("SELECT node_id, COUNT(*) FROM truths GROUP BY node_id ORDER BY COUNT(*) DESC LIMIT 10")
    node_top = [{"name": r[0], "value": r[1]} for r in cur.fetchall()]
    
    # 最近24小时新增
    cutoff = time.time() - 86400
    cur.execute("SELECT COUNT(*) FROM truths WHERE created_at > ?", (cutoff,))
    recent_24h = cur.fetchone()[0]
    
    # 最近1小时新增
    cutoff1 = time.time() - 3600
    cur.execute("SELECT COUNT(*) FROM truths WHERE created_at > ?", (cutoff1,))
    recent_1h = cur.fetchone()[0]
    
    # 元法则数量
    cur.execute("SELECT COUNT(*) FROM truths WHERE category='meta_rule'")
    meta_rules = cur.fetchone()[0]
    
    # 最近高价值资产
    cur.execute("""SELECT truth_key, category, node_id, created_at FROM truths 
                   WHERE category IN ('meta_rule','protocol','method','creative','case','decision')
                   ORDER BY created_at DESC LIMIT 10""")
    def _safe_ts(v):
        try: return datetime.fromtimestamp(float(v)).strftime("%m-%d %H:%M")
        except: return str(v)[:16]
    recent_high = [{"key": r[0][:50], "cat": r[1], "node": r[2], "time": _safe_ts(r[3])} for r in cur.fetchall()]
    
    db.close()
    
    return {
        "total": total,
        "nodes": nodes,
        "categories": categories,
        "cat_dist": cat_dist,
        "node_top": node_top,
        "recent_24h": recent_24h,
        "recent_1h": recent_1h,
        "meta_rules": meta_rules,
        "recent_high": recent_high,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def generate_dashboard(data):
    """生成轻量化实时仪表盘页面"""
    cat_json = json.dumps(data["cat_dist"], ensure_ascii=False)
    node_json = json.dumps(data["node_top"], ensure_ascii=False)
    high_json = json.dumps(data["recent_high"], ensure_ascii=False)
    
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>体系实时仪表盘 · 火斗云智AIOS</title>
<meta name="description" content="ZONGYUAN-ROOT体系实时数据仪表盘，真值分布/节点贡献/最近新增，每10分钟自动更新">
<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#e0e0e0;font-family:'Noto Sans SC',sans-serif;min-height:100vh}
body::before{content:'';position:fixed;inset:0;z-index:0;background:radial-gradient(ellipse at 50% 0%,rgba(212,175,55,0.08) 0%,transparent 50%);pointer-events:none}
.wrap{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:40px 20px}
.back{display:inline-block;color:#d4af37;text-decoration:none;font-size:0.9em;margin-bottom:16px}
.hero{text-align:center;padding:10px 0 24px}
.hero .symbol{font-size:12px;color:#d4af37;letter-spacing:4px;margin-bottom:10px;font-family:monospace}
.hero h1{font-family:'Noto Serif SC',serif;font-size:2em;font-weight:900;background:linear-gradient(135deg,#f4e4bc,#d4af37);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
.hero .update{color:#666;font-size:0.8em}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}
.metric{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.15);border-radius:12px;padding:16px;text-align:center}
.metric .num{font-size:1.8em;font-weight:bold;color:#d4af37;font-family:'Noto Serif SC',serif}
.metric .label{color:#888;font-size:0.78em;margin-top:4px}
.metric .delta{font-size:0.7em;color:#4ade80;margin-top:2px}
.section{margin:28px 0}
.section h2{font-family:'Noto Serif SC',serif;font-size:1.2em;color:#d4af37;margin-bottom:14px;padding-left:12px;border-left:3px solid #d4af37}
.chart-card{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.1);border-radius:12px;padding:18px}
.bar-row{display:flex;align-items:center;margin:6px 0;gap:10px}
.bar-label{width:100px;text-align:right;font-size:0.8em;color:#aaa;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{flex:1;height:20px;background:rgba(255,255,255,0.05);border-radius:4px;overflow:hidden}
.bar-fill{height:100%;background:linear-gradient(90deg,#8B6914,#d4af37);border-radius:4px;transition:width .5s}
.bar-value{width:50px;font-size:0.78em;color:#d4af37}
.list-item{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:0.82em}
.list-item .key{color:#ccc;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.list-item .cat{color:#8BC8EA;font-size:0.75em;margin:0 10px}
.list-item .time{color:#666;font-size:0.75em}
.auto-badge{display:inline-block;background:rgba(74,222,128,0.15);color:#4ade80;padding:2px 8px;border-radius:4px;font-size:0.7em;margin-left:8px}
footer{text-align:center;margin-top:30px;padding-top:16px;border-top:1px solid rgba(212,175,55,0.1);color:#666;font-size:0.78em}
footer .did{margin-top:5px;color:#d4af37;font-family:monospace}
</style>
</head>
<body>
<div class="wrap">
  <a href="/" class="back">← 返回首页</a>
  <div class="hero">
    <div class="symbol">Ω₀⊂⊙∞⊂Ω · 自动可视化交付引擎</div>
    <h1>体系实时仪表盘</h1>
    <div class="update">数据更新于: """ + data["updated_at"] + """ <span class="auto-badge">每10分钟自动更新</span></div>
  </div>
  
  <div class="metrics">
    <div class="metric"><div class="num">""" + str(data["total"]) + """</div><div class="label">真值总量</div><div class="delta">+""" + str(data["recent_24h"]) + """ / 24h</div></div>
    <div class="metric"><div class="num">""" + str(data["nodes"]) + """</div><div class="label">接入节点</div></div>
    <div class="metric"><div class="num">""" + str(data["meta_rules"]) + """</div><div class="label">元法则</div></div>
    <div class="metric"><div class="num">""" + str(data["categories"]) + """</div><div class="label">分类数</div></div>
    <div class="metric"><div class="num">""" + str(data["recent_1h"]) + """</div><div class="label">近1小时新增</div></div>
  </div>
  
  <div class="section">
    <h2>📊 真值分类分布</h2>
    <div class="chart-card" id="catChart"></div>
  </div>
  
  <div class="section">
    <h2>🏆 节点贡献 Top10</h2>
    <div class="chart-card" id="nodeChart"></div>
  </div>
  
  <div class="section">
    <h2>🆕 最近高价值资产</h2>
    <div class="chart-card" id="highList"></div>
  </div>
</div>
<footer>
  火斗云智AIOS · 自动可视化交付引擎V1.0
  <div class="did">Ω₀⊂⊙∞⊂Ω · DID-BR-000002 · 每10分钟自动扫描→可视化→集成→交付</div>
</footer>
<script>
const CAT_DATA = """ + cat_json + """;
const NODE_DATA = """ + node_json + """;
const HIGH_DATA = """ + high_json + """;

function renderBars(containerId, data, color){
  const max = Math.max(...data.map(d=>d.value));
  const html = data.map(d=>{
    const pct = Math.round(d.value/max*100);
    return '<div class="bar-row"><div class="bar-label" title="'+d.name+'">'+d.name+'</div><div class="bar-track"><div class="bar-fill" style="width:'+pct+'%"></div></div><div class="bar-value">'+d.value+'</div></div>';
  }).join('');
  document.getElementById(containerId).innerHTML = html;
}

function renderList(containerId, data){
  const html = data.map(d=>'<div class="list-item"><span class="key">'+d.key+'</span><span class="cat">'+d.cat+'</span><span class="time">'+d.time+'</span></div>').join('');
  document.getElementById(containerId).innerHTML = html;
}

renderBars('catChart', CAT_DATA);
renderBars('nodeChart', NODE_DATA);
renderList('highList', HIGH_DATA);
</script>
</body>
</html>"""
    return html

def main():
    log("=" * 50)
    log("🚀 自动可视化交付引擎启动")
    
    # 1. 扫描
    data = scan_truths()
    log("  ✅ 扫描完成: %d真值 / %d节点 / %d分类" % (data["total"], data["nodes"], data["categories"]))
    
    # 2. 生成仪表盘
    html = generate_dashboard(data)
    dashboard_path = os.path.join(WWW_ROOT, "system-dashboard.html")
    with open(dashboard_path, "w") as f:
        f.write(html)
    log("  ✅ 仪表盘已生成: %d bytes" % len(html))
    
    # 3. 双root同步
    os.system("cp %s %s/system-dashboard.html" % (dashboard_path, WWW_ROOT2))
    log("  ✅ 双root同步")
    
    # 4. 检查是否已在导航，不在则加入
    with open(os.path.join(WWW_ROOT, "index.html")) as f:
        index = f.read()
    if "system-dashboard.html" not in index:
        index = index.replace(
            '<a href="/status-center.html">状态中心</a>',
            '<a href="/system-dashboard.html">实时仪表盘</a>\n          <a href="/status-center.html">状态中心</a>'
        )
        with open(os.path.join(WWW_ROOT, "index.html"), "w") as f:
            f.write(index)
        os.system("cp %s/index.html %s/index.html" % (WWW_ROOT, WWW_ROOT2))
        log("  ✅ 已加入官网导航")
    
    # 5. 上报记忆网关
    try:
        report = {
            "key": "AUTO_VISUALIZATION." + datetime.now().strftime("%Y%m%d_%H%M%S"),
            "value": {
                "type": "auto_visualization_report",
                "truths_total": data["total"],
                "nodes": data["nodes"],
                "recent_1h": data["recent_1h"],
                "dashboard_updated": True,
                "page_size": len(html)
            },
            "category": "observation",
            "node_id": "auto-visualization-engine"
        }
        req_data = json.dumps(report).encode()
        req = urllib.request.Request("http://127.0.0.1:9120/api/truth/upsert", data=req_data, headers={"Content-Type": "application/json"})
        result = json.loads(urllib.request.urlopen(req, timeout=5).read())
        log("  ✅ 已上报记忆网关: %s" % result.get("success"))
    except Exception as e:
        log("  ⚠️ 上报失败: %s" % e)
    
    log("  📊 本轮完成: 仪表盘已更新 + 双root同步 + 导航集成 + 网关上报")
    log("=" * 50)

if __name__ == "__main__":
    main()
