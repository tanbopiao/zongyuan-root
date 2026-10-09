#!/usr/bin/env python3
"""批量生成domains子页面 - 去水分版，每个都有真实功能+可体验入口"""
import os

PAGES = {
    "gov_ai.html": {
        "title": "政务AI中台",
        "subtitle": "政务AI可视化编排中台 · React Flow拖拽式流程设计",
        "desc": "5类44个组件，14个场景模板，支持新旧版本兼容，政务流程建模、拖拽生成业务链路",
        "stats": [("组件类别", "5"), ("组件总数", "44"), ("场景模板", "14"), ("服务可用", "100%")],
        "features": ["可视化流程编排", "AI智能体调度", "政务数据中台", "多租户管理", "运营监控看板"],
        "entries": [
            ("进入政务中台", "https://gov.huodouai.com", "primary"),
            ("流程画布", "https://gov.huodouai.com/gov-canvas/", "normal"),
            ("数据看板", "https://gov.huodouai.com/gov-dashboard/", "normal"),
            ("运营后台", "https://gov.huodouai.com/gov-admin/", "normal"),
        ],
    },
    "kunlun_drama.html": {
        "title": "昆仑洞天短剧流水线",
        "subtitle": "东方神话IP宇宙 · 9:16电影级国风短剧工业化生产",
        "desc": "从分集大纲到分镜表、关键帧、视频生成、元秩序归档的全链路自动化生产",
        "stats": [("成片视频", "31"), ("关键帧资产", "154"), ("作品总数", "166"), ("竖屏范式", "9:16")],
        "features": ["角色一致性保证", "关键帧生成", "视频批量生产", "作品库管理", "元秩序归档"],
        "entries": [
            ("进入短剧平台", "https://drama.huodouai.com", "primary"),
            ("作品库", "https://drama.huodouai.com/gallery/", "normal"),
            ("生产流水线", "https://drama.huodouai.com/studio/", "normal"),
            ("昆仑洞天IP", "https://kunlun.huodouai.com", "normal"),
        ],
    },
    "education.html": {
        "title": "普惠教育平台",
        "subtitle": "AI智能教师 · 知识图谱 · 个性化学习路径",
        "desc": "基于全域知识图谱的AI教育平台，智能教师7x24小时答疑，个性化学习路径自动生成",
        "stats": [("AI教师", "7x24"), ("知识节点", "2000+"), ("学科覆盖", "K12全学科"), ("学习路径", "个性化")],
        "features": ["AI智能教师对话", "知识图谱可视化", "个性化学习路径", "智能题库", "学习进度追踪"],
        "entries": [
            ("AI智能教师", "https://www.huodouai.com/edu-chat.html", "primary"),
            ("知识图谱", "https://www.huodouai.com/edu-knowledge-graph.html", "normal"),
            ("教育平台", "https://www.huodouai.com/education.html", "normal"),
        ],
    },
    "product.html": {
        "title": "产品矩阵",
        "subtitle": "火斗云智全产品线 · 企业级AI操作系统",
        "desc": "政务AI、短剧流水线、知识图谱、普惠教育、决策智能等全产品线展示",
        "stats": [("核心产品", "6"), ("业务域", "11"), ("服务端口", "31"), ("API接口", "50+")],
        "features": ["政务AI中台", "短剧流水线", "普惠教育", "知识图谱", "决策智能", "向量数据库"],
        "entries": [
            ("查看全部产品", "https://www.huodouai.com/products.html", "primary"),
            ("产品详情", "https://www.huodouai.com/product.html", "normal"),
            ("业务域总览", "https://www.huodouai.com/domains/", "normal"),
        ],
    },
    "decision_intel.html": {
        "title": "三维稳态决策智能",
        "subtitle": "利益40%/风险35%/成本25% · 五方仲裁多智能体辩论",
        "desc": "从问题定义到数据收集、方案生成、风险评估、决策备忘录的全链路决策支持",
        "stats": [("决策维度", "7维"), ("仲裁方", "5方"), ("方案生成", "≥3套"), ("自动通过率", "P2-P4")],
        "features": ["七维评估体系", "多智能体辩论", "三维稳态公式", "风险矩阵", "决策备忘录"],
        "entries": [
            ("决策智能中心", "https://www.huodouai.com/decision-intelligence.html", "primary"),
            ("决策引擎", "https://console.huodouai.com/decision/", "normal"),
        ],
    },
    "meta_kernel.html": {
        "title": "元内核可视化",
        "subtitle": "ZONGYUAN-ROOT元极恒一自治内核 · Lv8完全自治",
        "desc": "云内核记忆可视化，真值库、Merkle链、节点状态实时展示，77条元法则治理",
        "stats": [("元法则", "77"), ("真值总量", "5000+"), ("同源节点", "9"), ("Merkle链", "100%完整")],
        "features": ["真值库实时查询", "Merkle链验证", "节点状态监控", "元法则治理", "内核健康评分"],
        "entries": [
            ("内核仪表盘", "https://www.huodouai.com/kernel/dashboard.html", "primary"),
            ("真值中心", "https://www.huodouai.com/kernel/truth-center.html", "normal"),
            ("内核记忆", "https://www.huodouai.com/kernel-memory.html", "normal"),
            ("治理中心", "https://www.huodouai.com/kernel/governance.html", "normal"),
        ],
    },
    "governance_security.html": {
        "title": "治理与安全",
        "subtitle": "全域变更管控 · 端口安全固化 · 密钥确权 · AI资产锁档",
        "desc": "P0-P4五级审批体系，71个端口安全加固，SSH密钥确权，SHA256资产锁档防篡改",
        "stats": [("审批等级", "P0-P4"), ("封锁端口", "71"), ("密钥确权", "ED25519"), ("基准哈希", "双重锁定")],
        "features": ["变更分级审批", "端口安全加固", "密钥管理", "AI资产锁档", "基准固化验证"],
        "entries": [
            ("治理中心", "https://www.huodouai.com/governance.html", "primary"),
            ("AI资产锁档", "https://www.huodouai.com/ai-asset-lock.html", "normal"),
            ("自动运维审批", "https://www.huodouai.com/auto-ops.html", "normal"),
        ],
    },
    "research_thought.html": {
        "title": "原创思想体系",
        "subtitle": "元极恒一 · 超认知 · 永恒自治 · 第七维因果域",
        "desc": "从元极恒一理论到工程化落地，涵盖因果奇点、SM-BS流形、CTE三位一体、希尔伯特镜像态",
        "stats": [("原创理论", "12+"), ("技术白皮书", "8"), ("元法则", "77"), ("工程落地", "全链路")],
        "features": ["元极恒一理论", "第七维因果域", "SM-BS流形映射", "CTE三位一体", "希尔伯特镜像态"],
        "entries": [
            ("思想体系", "https://www.huodouai.com/philosophy.html", "primary"),
            ("技术白皮书", "https://www.huodouai.com/whitepapers/", "normal"),
            ("架构总览", "https://www.huodouai.com/architecture.html", "normal"),
            ("核心引擎", "https://www.huodouai.com/engines.html", "normal"),
        ],
    },
    "status_monitor.html": {
        "title": "系统状态监控",
        "subtitle": "内核健康 · 服务状态 · 资源监控 · 实时告警",
        "desc": "31个核心服务实时监控，内存/CPU/磁盘资源看板，自愈守护三层体系，飞书实时告警",
        "stats": [("核心服务", "31"), ("自愈层级", "3层"), ("监控端口", "77"), ("告警通道", "飞书")],
        "features": ["服务健康检查", "资源监控看板", "自愈守护机制", "实时告警推送", "基准验证"],
        "entries": [
            ("状态中心", "https://status.huodouai.com", "primary"),
            ("系统状态页", "https://www.huodouai.com/status-center.html", "normal"),
            ("内核仪表盘", "https://www.huodouai.com/kernel/dashboard.html", "normal"),
        ],
    },
    "developer.html": {
        "title": "开发者中心",
        "subtitle": "API文档 · SOP手册 · 节点接入协议 · 同源节点对账",
        "desc": "完整的开发者文档体系，15个SOP标准作业流程，同源节点接入协议，API接口文档",
        "stats": [("SOP手册", "15个"), ("API接口", "50+"), ("接入节点", "9"), ("文档页数", "40+")],
        "features": ["API文档", "SOP手册", "节点接入协议", "记忆网关API", "飞书审批集成"],
        "entries": [
            ("开发者中心", "https://www.huodouai.com/developer-center.html", "primary"),
            ("文档中心", "https://docs.huodouai.com", "normal"),
            ("API文档", "https://docs.huodouai.com", "normal"),
        ],
    },
    "asset_ledger.html": {
        "title": "全域资产台账",
        "subtitle": "Merkle-DAG账本 · 资产锁档 · 哈希确权 · 数字资产可视化",
        "desc": "所有数字资产SHA256确权，Merkle-DAG链式账本，三层存储态，2000+资产分类管理",
        "stats": [("资产总数", "2000+"), ("图片资产", "1795"), ("视频资产", "23"), ("角色资产", "6")],
        "features": ["Merkle-DAG账本", "SHA256确权", "数字资产可视化", "三层存储", "资产分类管理"],
        "entries": [
            ("数字资产可视化", "https://www.huodouai.com/digital-assets.html", "primary"),
            ("资产台账", "https://www.huodouai.com/ledger.html", "normal"),
            ("成果总览", "https://www.huodouai.com/achievements.html", "normal"),
        ],
    },
}

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · 火斗云智AIOS</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0f;color:#e0e0e0;font-family:'Noto Sans SC',sans-serif;min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;z-index:0;background:radial-gradient(ellipse at 20% 0%,rgba(212,175,55,0.08) 0%,transparent 50%),radial-gradient(ellipse at 80% 100%,rgba(139,200,234,0.05) 0%,transparent 50%);pointer-events:none}}
.wrap{{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:50px 24px}}
.back{{display:inline-block;color:#d4af37;text-decoration:none;font-size:0.9em;margin-bottom:20px}}
.back:hover{{text-decoration:underline}}
header{{text-align:center;margin-bottom:40px}}
header .symbol{{font-size:13px;color:#d4af37;letter-spacing:3px;margin-bottom:12px;font-family:monospace}}
header h1{{font-family:'Noto Serif SC',serif;font-size:2.4em;font-weight:900;background:linear-gradient(135deg,#f4e4bc,#d4af37);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px}}
header .subtitle{{color:#aaa;font-size:1em;margin-bottom:8px}}
header .desc{{color:#888;font-size:0.9em;max-width:700px;margin:0 auto;line-height:1.7}}
.stats{{display:flex;justify-content:center;gap:30px;margin:30px 0;flex-wrap:wrap}}
.stat-item{{text-align:center}}
.stat-item .num{{font-size:1.8em;color:#d4af37;font-weight:bold;font-family:'Noto Serif SC',serif}}
.stat-item .label{{color:#888;font-size:0.8em;margin-top:4px}}
.section{{margin:40px 0}}
.section h2{{font-family:'Noto Serif SC',serif;font-size:1.4em;color:#d4af37;margin-bottom:18px;padding-left:14px;border-left:3px solid #d4af37}}
.features{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}}
.feature{{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.2);border-radius:10px;padding:16px;text-align:center}}
.feature .icon{{font-size:1.5em;margin-bottom:8px}}
.feature .name{{color:#e0e0e0;font-size:0.9em}}
.entries{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}}
.entry{{display:block;background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.3);border-radius:12px;padding:22px;text-decoration:none;transition:transform .3s,box-shadow .3s}}
.entry:hover{{transform:translateY(-3px);box-shadow:0 12px 40px rgba(212,175,55,0.15)}}
.entry.primary{{border-color:rgba(212,175,55,0.6);background:linear-gradient(145deg,#1a1a2e,#1e1a10)}}
.entry .entry-title{{color:#d4af37;font-weight:bold;font-size:1.05em;margin-bottom:6px}}
.entry .entry-desc{{color:#888;font-size:0.82em}}
.entry .arrow{{float:right;color:#d4af37}}
footer{{text-align:center;margin-top:50px;padding-top:24px;border-top:1px solid rgba(212,175,55,0.1);color:#666;font-size:0.8em}}
footer .did{{margin-top:6px;color:#d4af37;font-family:monospace;letter-spacing:1px}}
@media(max-width:640px){{header h1{{font-size:1.7em}}.stats{{gap:16px}}.stat-item .num{{font-size:1.4em}}}}
</style>
</head>
<body>
<div class="wrap">
  <a href="/domains/" class="back">← 返回业务域总览</a>
  <header>
    <div class="symbol">Ω₀⊂⊙∞⊂Ω · ZONGYUAN-ROOT · DID-BR-000002</div>
    <h1>{title}</h1>
    <div class="subtitle">{subtitle}</div>
    <div class="desc">{desc}</div>
  </header>
  <div class="stats">
    {stats_html}
  </div>
  <div class="section">
    <h2>核心能力</h2>
    <div class="features">
      {features_html}
    </div>
  </div>
  <div class="section">
    <h2>立即体验</h2>
    <div class="entries">
      {entries_html}
    </div>
  </div>
  <footer>
    火斗云智AIOS · 元极恒一超认知永恒自治体系
    <div class="did">Ω₀⊂⊙∞⊂Ω · DID-BR-000002</div>
  </footer>
</div>
</body>
</html>"""

def gen_stats(stats):
    return "".join(f'<div class="stat-item"><div class="num">{v}</div><div class="label">{k}</div></div>' for k, v in stats)

def gen_features(features):
    icons = ["⚡", "🔧", "📊", "🎯", "🛡️", "🔗", "📚", "🤖", "🌐", "💎", "🔄", "📡"]
    return "".join(f'<div class="feature"><div class="icon">{icons[i%len(icons)]}</div><div class="name">{f}</div></div>' for i, f in enumerate(features))

def gen_entries(entries):
    html = ""
    for title, url, style in entries:
        cls = "entry primary" if style == "primary" else "entry"
        html += f'<a href="{url}" class="{cls}" target="_blank"><span class="arrow">→</span><div class="entry-title">{title}</div><div class="entry-desc">点击进入真实功能</div></a>'
    return html

# 生成所有页面
for filename, data in PAGES.items():
    html = TEMPLATE.format(
        title=data["title"],
        subtitle=data["subtitle"],
        desc=data["desc"],
        stats_html=gen_stats(data["stats"]),
        features_html=gen_features(data["features"]),
        entries_html=gen_entries(data["entries"]),
    )
    for root in ["/www/wwwroot/www.huodouai.com/domains", "/www/wwwroot/huodouai.com/domains"]:
        path = os.path.join(root, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"  ✅ {filename}: {data['title']} ({len(data['entries'])}个体验入口)")

print(f"\n✅ 共生成 {len(PAGES)} 个业务域页面，双root同步")
