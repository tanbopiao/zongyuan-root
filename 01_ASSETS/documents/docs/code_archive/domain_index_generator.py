#!/usr/bin/env python3
"""
业务域索引页生成器 v1.0
- 为11大业务域生成独立索引页
- 每个索引页汇总该域所有页面、文档、媒体
- 打通域间交叉链接
- 生成全域业务域总索引
"""

import os
import json
import urllib.request

MAIN_SITE = "/www/wwwroot/www.huodouai.com"
ALT_SITE = "/www/wwwroot/huodouai.com"
DOMAINS_DIR = "domains"

# 业务域元数据（描述、关联域、核心页面）
DOMAIN_META = {
    "kunlun_drama": {
        "name": "昆仑洞天·短剧生产",
        "icon": "🎬",
        "desc": "AI短剧工业化流水线，从分集大纲到关键帧、视频生成、元秩序归档的全链路自动化生产体系。",
        "related": ["asset_ledger", "developer", "meta_kernel"],
        "core_pages": ["drama.huodouai.com", "/drama/pipeline.html", "/drama/assets/index.html"],
        "subdomains": ["drama.huodouai.com", "kunlun.huodouai.com"]
    },
    "gov_ai": {
        "name": "政务AI中台",
        "icon": "🏛️",
        "desc": "面向政务场景的AI中台，包含智能问答、公文处理、政策分析、政务知识库等能力。",
        "related": ["meta_kernel", "decision_intel", "governance_security"],
        "core_pages": ["gov.huodouai.com", "/gov/index.html", "/apps/gov-ai.html"],
        "subdomains": ["gov.huodouai.com"]
    },
    "meta_kernel": {
        "name": "元极恒一内核",
        "icon": "🧠",
        "desc": "超认知永恒自治内核，Lv8完全自治，自我认知、自我进化、自我防御的核心引擎。",
        "related": ["research_thought", "governance_security", "decision_intel"],
        "core_pages": ["/architecture.html", "/engines.html", "/kernel-memory.html", "/truth-transmutation.html", "/kernel/dashboard.html"],
        "subdomains": []
    },
    "governance_security": {
        "name": "治理与安全",
        "icon": "🛡️",
        "desc": "全域变更管控、端口安全固化、密钥确权、希尔伯特镜像态防御、AI资产锁档。",
        "related": ["meta_kernel", "status_monitor", "developer"],
        "core_pages": ["/governance.html", "/security/index.html", "/sovereignty/index.html", "/auto-ops.html", "/ai-asset-lock.html"],
        "subdomains": []
    },
    "decision_intel": {
        "name": "决策智能",
        "icon": "⚖️",
        "desc": "三维稳态决策公式（利益40%/风险35%/成本25%），五方仲裁，多智能体辩论决策。",
        "related": ["meta_kernel", "gov_ai", "product"],
        "core_pages": ["/decision-intelligence.html"],
        "subdomains": []
    },
    "research_thought": {
        "name": "研究与思想",
        "icon": "💡",
        "desc": "原创思想体系：涌现层级理论、学习进化方法论、高阶态维持、黎曼流形语义空间。",
        "related": ["meta_kernel", "education", "developer"],
        "core_pages": ["/philosophy.html", "/emergence.html", "/learning-evolution.html", "/research.html", "/high-order-state.html"],
        "subdomains": []
    },
    "developer": {
        "name": "开发者中心",
        "icon": "👨‍💻",
        "desc": "API文档、SOP手册、节点接入协议、同源节点对账、模型蒸馏引擎。",
        "related": ["meta_kernel", "asset_ledger", "status_monitor"],
        "core_pages": ["/developer-center.html", "/docs.html", "docs.huodouai.com", "api.huodouai.com", "console.huodouai.com"],
        "subdomains": ["docs.huodouai.com", "api.huodouai.com", "console.huodouai.com"]
    },
    "status_monitor": {
        "name": "状态与监控",
        "icon": "📊",
        "desc": "系统状态中心、内核健康监控、服务自愈、实时告警、可观测性面板。",
        "related": ["governance_security", "meta_kernel", "developer"],
        "core_pages": ["/status-center.html", "status.huodouai.com", "/digital-assets.html"],
        "subdomains": ["status.huodouai.com"]
    },
    "asset_ledger": {
        "name": "资产与台账",
        "icon": "📦",
        "desc": "全域数字资产可视化、Merkle-DAG账本、资产锁档、成果总览、真值库。",
        "related": ["meta_kernel", "kunlun_drama", "developer"],
        "core_pages": ["/digital-assets.html", "/ledger.html", "/achievements.html", "/assets/index.html"],
        "subdomains": []
    },
    "education": {
        "name": "普惠教育",
        "icon": "📚",
        "desc": "AI普惠教育，智能教师、知识图谱、个性化学习路径。",
        "related": ["research_thought", "product", "gov_ai"],
        "core_pages": ["/education.html"],
        "subdomains": []
    },
    "product": {
        "name": "产品与商业化",
        "icon": "🚀",
        "desc": "企业级AI操作系统、智能工作台、Agent Studio、差异化能力矩阵、Lite版试用。",
        "related": ["meta_kernel", "gov_ai", "education"],
        "core_pages": ["/product.html", "/products.html", "/workbench.html", "/agent-studio.html", "/diff.html", "/trial.html"],
        "subdomains": []
    }
}


def get_classification_data():
    """从digital_assets.json获取分类数据"""
    try:
        with open(os.path.join(MAIN_SITE, "digital_assets.json")) as f:
            return json.load(f).get("classification", [])
    except Exception:
        return []


def generate_domain_page(domain_id, meta, stats):
    """生成单个业务域索引页"""
    related_links = ""
    for rid in meta.get("related", []):
        rmeta = DOMAIN_META.get(rid, {})
        related_links += '<a href="/domains/%s.html" style="color:#8BC8EA;text-decoration:none;margin-right:15px">%s %s</a>' % (
            rid, rmeta.get("icon", "🔗"), rmeta.get("name", rid))

    core_pages_html = ""
    for page in meta.get("core_pages", []):
        if page.startswith("http") or "." in page and not page.startswith("/"):
            url = "https://" + page if not page.startswith("http") else page
            core_pages_html += '<li><a href="%s" target="_blank" style="color:#ccc">%s ↗</a></li>' % (url, page)
        else:
            core_pages_html += '<li><a href="%s" style="color:#ccc">%s</a></li>' % (page, page)

    subdomains_html = ""
    for sd in meta.get("subdomains", []):
        subdomains_html += '<a href="https://%s" target="_blank" class="sd-tag">%s ↗</a>' % (sd, sd)

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s · 火斗云智AIOS</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background:#0a0a0f; color:#e0e0e0; min-height:100vh; }
.container { max-width:900px; margin:0 auto; padding:80px 20px 40px; }
.domain-header { text-align:center; margin-bottom:40px; }
.domain-icon { font-size:4em; margin-bottom:15px; }
.domain-name { font-size:2em; background:linear-gradient(90deg,#d4af37,#f4e4bc,#d4af37); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:10px; }
.domain-desc { color:#888; max-width:600px; margin:0 auto; line-height:1.8; }
.stats-row { display:flex; justify-content:center; gap:30px; margin:30px 0; }
.stat-item { text-align:center; }
.stat-num { font-size:2em; color:#d4af37; font-weight:bold; }
.stat-label { color:#666; font-size:0.85em; }
.section { background:linear-gradient(145deg,#1a1a2e,#16213e); border:1px solid rgba(212,175,55,0.2); border-radius:12px; padding:25px; margin-bottom:20px; }
.section h2 { color:#d4af37; margin-bottom:15px; font-size:1.2em; border-left:4px solid #d4af37; padding-left:12px; }
.section ul { list-style:none; }
.section li { padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05); }
.section li a:hover { color:#d4af37; }
.sd-tag { display:inline-block; background:rgba(212,175,55,0.1); border:1px solid rgba(212,175,55,0.3); padding:6px 14px; border-radius:15px; font-size:0.85em; color:#8BC8EA; text-decoration:none; margin:3px; }
.related { margin-top:30px; padding-top:20px; border-top:1px solid rgba(212,175,55,0.1); }
.back-link { display:inline-block; margin-bottom:20px; color:#d4af37; text-decoration:none; font-size:0.9em; }
.back-link:hover { text-decoration:underline; }
</style>
</head>
<body>
<div class="container">
    <a href="/domains/" class="back-link">← 返回业务域总览</a>
    <div class="domain-header">
        <div class="domain-icon">%s</div>
        <h1 class="domain-name">%s</h1>
        <p class="domain-desc">%s</p>
        <div class="stats-row">
            <div class="stat-item"><div class="stat-num">%d</div><div class="stat-label">页面</div></div>
            <div class="stat-item"><div class="stat-num">%d</div><div class="stat-label">文档</div></div>
            <div class="stat-item"><div class="stat-num">%d</div><div class="stat-label">媒体资产</div></div>
        </div>
    </div>
    %s
    <div class="section">
        <h2>核心页面</h2>
        <ul>%s</ul>
    </div>
    <div class="related">
        <strong style="color:#d4af37">关联业务域：</strong> %s
    </div>
</div>
</body>
</html>''' % (
        meta["name"], meta["icon"], meta["name"], meta["desc"],
        stats.get("pages", 0), stats.get("docs", 0), stats.get("media", 0),
        ('<div class="section"><h2>子域名</h2>%s</div>' % subdomains_html) if subdomains_html else "",
        core_pages_html, related_links
    )
    return html


def generate_index_page(classification):
    """生成业务域总索引页"""
    cards = ""
    for dom in classification:
        meta = DOMAIN_META.get(dom["id"], {})
        cards += '''
        <a href="/domains/%s.html" style="text-decoration:none;color:inherit">
        <div style="background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.2);border-radius:12px;padding:25px;transition:transform 0.3s,box-shadow 0.3s" onmouseover="this.style.transform=\'translateY(-5px)\';this.style.boxShadow=\'0 10px 30px rgba(212,175,55,0.15)\'" onmouseout="this.style.transform=\'translateY(0)\';this.style.boxShadow=\'none\'">
            <div style="font-size:2.5em;margin-bottom:10px">%s</div>
            <div style="color:#d4af37;font-size:1.15em;font-weight:bold;margin-bottom:8px">%s</div>
            <div style="color:#888;font-size:0.85em;line-height:1.6;margin-bottom:15px">%s</div>
            <div style="display:flex;gap:15px;font-size:0.8em;color:#666">
                <span>📄 %d页面</span><span>📚 %d文档</span><span>🖼️ %d媒体</span>
            </div>
        </div></a>''' % (
            dom["id"], meta.get("icon", "📦"), meta.get("name", dom["id"]),
            meta.get("desc", ""), dom["pages"], dom["docs"], dom["media"])

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>业务域总览 · 火斗云智AIOS</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background:#0a0a0f; color:#e0e0e0; min-height:100vh; }
.container { max-width:1100px; margin:0 auto; padding:80px 20px 40px; }
h1 { text-align:center; font-size:2em; background:linear-gradient(90deg,#d4af37,#f4e4bc,#d4af37); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:10px; }
.subtitle { text-align:center; color:#888; margin-bottom:40px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:20px; }
.back-link { display:inline-block; margin-bottom:20px; color:#d4af37; text-decoration:none; font-size:0.9em; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-link">← 返回首页</a>
    <h1>业务域总览</h1>
    <p class="subtitle">%d大业务域 · 全域资产分类管理 · 域间链路互通</p>
    <div class="grid">%s</div>
</div>
</body>
</html>''' % (len(classification), cards)
    return html


def main():
    classification = get_classification_data()
    if not classification:
        print("❌ 无法获取分类数据")
        return

    # 生成每个业务域索引页
    for dom in classification:
        domain_id = dom["id"]
        meta = DOMAIN_META.get(domain_id)
        if not meta:
            continue
        html = generate_domain_page(domain_id, meta, dom)
        for site in [MAIN_SITE, ALT_SITE]:
            filepath = os.path.join(site, DOMAINS_DIR, domain_id + ".html")
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(html)
        print("  ✅ %s: %s" % (domain_id, meta["name"]))

    # 生成总索引页
    index_html = generate_index_page(classification)
    for site in [MAIN_SITE, ALT_SITE]:
        filepath = os.path.join(site, DOMAINS_DIR, "index.html")
        with open(filepath, "w") as f:
            f.write(index_html)
    print("  ✅ 业务域总索引页")

    print("\n✅ 共生成 %d 个业务域索引页 + 1个总索引页" % len(classification))


if __name__ == "__main__":
    main()
