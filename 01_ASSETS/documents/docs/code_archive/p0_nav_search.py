#!/usr/bin/env python3
"""P0优化：扩充搜索索引+修复导航+创建站点地图"""
import os

WWW = "/www/wwwroot/www.huodouai.com"

# 页面分类映射
CATEGORIES = {
    "index": ("首页", "核心", "火斗云智AIOS全域智能操作系统首页"),
    "products": ("产品总览", "产品", "火斗云智AIOS全产品矩阵展示"),
    "product-matrix": ("产品矩阵图", "产品", "产品矩阵可视化"),
    "product-map": ("产品地图", "产品", "产品生态地图"),
    "product": ("产品详情", "产品", "产品详细介绍"),
    "commercial": ("商业方案", "产品", "商业化解决方案"),
    "pricing": ("定价", "产品", "产品定价方案"),
    "solutions": ("解决方案", "产品", "全行业解决方案"),
    "cases": ("客户案例", "产品", "成功案例展示"),
    "agent-network": ("智能体网络", "智能体", "多智能体协同网络"),
    "agent-embodiment": ("智能体实体化", "智能体", "网页即智能体身体"),
    "agent-studio": ("智能体工作室", "智能体", "智能体开发工作台"),
    "high-capabilities": ("高阶能力中心", "智能体", "高阶智能能力展示"),
    "character-ai": ("角色AI", "智能体", "角色智能体"),
    "central-brain": ("中枢大脑", "内核", "体系中枢战略大脑"),
    "brain-strategy": ("战略全景", "内核", "全域战略规划"),
    "kernel-memory": ("内核记忆", "内核", "元内核记忆系统"),
    "kernel-status": ("内核状态", "内核", "内核运行状态"),
    "kernel-lock-visual": ("内核锁档可视化", "内核", "锁档状态可视化"),
    "architecture": ("架构总览", "技术", "七层纵向架构总览"),
    "architecture-deep": ("深度架构", "技术", "深度架构解析"),
    "microkernel-architecture": ("微内核架构", "技术", "微内核架构设计"),
    "engines": ("核心引擎", "技术", "算力调度与三维蒸馏"),
    "governance": ("治理安全", "技术", "全域治理与安全防护"),
    "whitepaper": ("技术白皮书", "技术", "完整技术白皮书"),
    "developers": ("开发者中心", "技术", "开发者资源中心"),
    "developer-center": ("开发者中心", "技术", "API文档与SDK"),
    "docs": ("文档中心", "技术", "产品文档与指南"),
    "prometheus-api-docs": ("API文档", "技术", "API接口文档"),
    "vector": ("向量知识库", "技术", "企业级向量检索"),
    "semantic-dashboard": ("语义仪表盘", "技术", "语义分析仪表盘"),
    "truth-transmutation": ("真值转化", "技术", "真值提炼与转化"),
    "memory-gateway": ("记忆网关", "技术", "9120记忆网关"),
    "ai-gateway": ("AI网关", "技术", "AI智能路由网关"),
    "token-gateway": ("令牌网关", "技术", "API令牌管理"),
    "dlp-gateway": ("DLP网关", "技术", "数据防泄漏网关"),
    "notary-api": ("存证API", "技术", "哈希存证接口"),
    "sec-tower-v1": ("秒塔架构", "技术", "四层分层推理架构"),
    "sec-tower-roadmap": ("秒塔推广规划", "技术", "秒塔全域推广路线图"),
    "lightweight-v3": ("轻量化战略V3", "战略", "轻量化优先战略V3(AI对话版)"),
    "lightweight-v2": ("轻量化战略V2", "战略", "轻量化战略V2(活体感版)"),
    "lightweight-strategy": ("轻量化战略", "战略", "轻量化优先战略"),
    "evolution-strategy": ("进化战略", "战略", "体系进化战略规划"),
    "global-learning": ("全网学习", "战略", "全域交叉学习"),
    "philosophy": ("原创思想", "战略", "元极恒一哲学体系"),
    "high-order-state": ("高阶状态", "战略", "高阶认知状态"),
    "emergence": ("涌现", "战略", "智能涌现理论"),
    "drift": ("认知漂移", "战略", "认知漂移监控与防控"),
    "safe-evolution": ("安全进化", "战略", "安全进化机制"),
    "research": ("AI研究", "战略", "人工智能前沿研究"),
    "knowledge": ("知识图谱", "战略", "全域知识图谱"),
    "kunlun-drama": ("昆仑洞天短剧", "短剧", "东方神话短剧品牌"),
    "drama-factory": ("短剧工厂", "短剧", "短剧生产流水线"),
    "works-gallery-v2": ("作品库V2", "短剧", "短剧作品展示库"),
    "keyframe-gallery": ("关键帧资产库", "短剧", "关键帧素材库"),
    "education": ("普惠教育", "教育", "源域通识教育平台"),
    "edu-ai-teacher": ("AI教师", "教育", "AI智能教师"),
    "edu-chat": ("教育对话", "教育", "教育AI对话"),
    "edu-knowledge-graph": ("教育知识图谱", "教育", "教育领域知识图谱"),
    "education-line": ("教育产品线", "教育", "教育产品线路线图"),
    "gov-line": ("政务产品线", "政务", "政务AI产品线路线图"),
    "ops-center": ("运维中心", "运维", "全域运维中心"),
    "ops-monitor": ("运维监控", "运维", "运维监控面板"),
    "ops-line": ("运维产品线", "运维", "运维产品线路线图"),
    "auto-ops": ("自动运维", "运维", "自动化运维系统"),
    "monitor": ("监控大屏", "运维", "服务监控大屏"),
    "server-monitor": ("服务器监控", "运维", "服务器资源监控"),
    "status-center": ("状态中心", "运维", "统一状态监控入口"),
    "system-dashboard": ("系统仪表盘", "运维", "实时系统仪表盘"),
    "auto-pipeline": ("自动化流水线", "运维", "全自动生产流水线"),
    "workbench": ("工作台", "运维", "智能工作台"),
    "digital-assets": ("数字资产", "资产", "数字资产总览"),
    "asset-center": ("资产中心", "资产", "资产管理中心"),
    "change-ledger": ("变更台账", "资产", "系统变更记录台账"),
    "ledger": ("真值账本", "资产", "Merkle-DAG真值账本"),
    "experience-kb": ("经验库", "资产", "经验沉淀知识库"),
    "achievements": ("成果展示", "资产", "体系成果展示"),
    "ai-asset-lock": ("AI资产锁", "资产", "AI资产确权锁档"),
    "standardization-center": ("标准化中心", "资产", "标准化管理中心"),
    "standard-sop": ("标准SOP", "资产", "标准作业流程"),
    "delivery-standard": ("交付标准", "资产", "交付标准规范V1.0"),
    "meta-rules-v2": ("元规则V2", "资产", "系统开发元规则V2.0"),
    "global-audit-report": ("全球审计报告", "资产", "全域审计报告"),
    "security-compliance": ("安全合规", "安全", "安全合规体系"),
    "security-line": ("安全产品线", "安全", "安全产品线路线图"),
    "startup-loop-defense-whitepaper": ("启动环防御白皮书", "安全", "希尔伯特镜像态防御"),
    "opensource": ("开源", "安全", "开源计划"),
    "decision-intelligence": ("决策智能", "决策", "三维稳态决策系统"),
    "roi-calculator": ("ROI计算器", "决策", "投资回报率计算"),
    "model-compare-lab": ("模型对比实验室", "决策", "多模型对比测试"),
    "enterprise-system": ("企业系统体验版", "体验", "17模块企业系统演示"),
    "kb-saas": ("知识库SaaS", "体验", "知识库SaaS平台"),
    "aios-image": ("AIOS形象", "体验", "AIOS品牌形象"),
    "logo-design": ("Logo设计", "体验", "品牌Logo设计"),
    "blog": ("博客", "内容", "技术博客"),
    "roadmap": ("路线图", "内容", "发展路线图"),
    "about-line": ("关于", "内容", "关于我们"),
    "content-line": ("内容产品线", "内容", "内容产品线路线图"),
    "ecosystem-line": ("生态产品线", "内容", "生态产品线路线图"),
    "learning-evolution": ("学习进化", "内容", "持续学习进化"),
    "book-demo": ("书籍演示", "内容", "书籍内容演示"),
    "search": ("全站搜索", "工具", "全站页面搜索"),
    "404": ("404页面", "工具", "页面未找到"),
}

# 生成搜索索引JS
index_items = []
for fname, (title, cat, desc) in CATEGORIES.items():
    keywords = f"{title} {cat} {desc}"
    index_items.append(f"{{title:'{title}',url:'/{fname}.html',desc:'{desc}',keywords:'{keywords}',category:'{cat}'}}")

index_js = "const PAGE_INDEX = [" + ",".join(index_items) + "];"

# 更新search.html
search_path = os.path.join(WWW, "search.html")
with open(search_path, encoding="utf-8") as f:
    content = f.read()

# 替换旧的PAGE_INDEX
import re
content = re.sub(r"const PAGE_INDEX = \[.*?\];", index_js, content, flags=re.DOTALL)

with open(search_path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"✅ search.html索引扩充至 {len(index_items)} 个页面")

# 修复首页导航中的失效链接
index_path = os.path.join(WWW, "index.html")
with open(index_path, encoding="utf-8") as f:
    idx = f.read()
idx = idx.replace('/digital-gallery-v3.html">数字画廊V3', '/works-gallery-v2.html">作品库V2')
with open(index_path, "w", encoding="utf-8") as f:
    f.write(idx)
print("✅ 首页导航失效链接已修复")

# 创建sitemap.html
sitemap_items = ""
current_cat = ""
for fname, (title, cat, desc) in sorted(CATEGORIES.items(), key=lambda x: (x[1][1], x[0])):
    if cat != current_cat:
        current_cat = cat
        sitemap_items += f'<h3 class="sm-cat">{cat}</h3><div class="sm-grid">'
    sitemap_items += f'<a href="/{fname}.html" class="sm-link"><span class="sm-title">{title}</span><span class="sm-desc">{desc}</span></a>'
    # 每4个关闭一个grid
sitemap_items += "</div>"

sitemap_html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>站点地图 - 火斗云智AIOS</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0f;color:#e0e0e8;min-height:100vh}}
.sm-header{{background:linear-gradient(135deg,#1a1a2e,#0a0a0f);padding:40px 20px;text-align:center;border-bottom:1px solid rgba(212,175,55,.2)}}
.sm-header h1{{color:#d4af37;font-size:2em;margin-bottom:8px}}
.sm-header p{{color:#888;font-size:.95em}}
.sm-container{{max-width:1200px;margin:0 auto;padding:30px 20px}}
.sm-cat{{color:#d4af37;font-size:1.2em;margin:24px 0 12px;padding-bottom:8px;border-bottom:1px solid rgba(212,175,55,.15)}}
.sm-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}}
.sm-link{{display:block;padding:12px 16px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:8px;text-decoration:none;transition:all .2s}}
.sm-link:hover{{border-color:rgba(212,175,55,.4);background:rgba(212,175,55,.05);transform:translateY(-2px)}}
.sm-title{{color:#ddd;font-weight:600;font-size:.95em;display:block;margin-bottom:4px}}
.sm-desc{{color:#888;font-size:.8em;line-height:1.4}}
.sm-footer{{text-align:center;padding:30px;color:#555;font-size:.85em}}
</style></head><body>
<div class="sm-header"><h1>站点地图</h1><p>火斗云智AIOS · {len(index_items)}个页面 · Ω₀⊂⊙∞⊂Ω</p></div>
<div class="sm-container">{sitemap_items}</div>
<div class="sm-footer">DID-BR-000002 ｜ 元极恒一超认知永恒自治体系</div>
</body></html>"""

sitemap_path = os.path.join(WWW, "sitemap.html")
with open(sitemap_path, "w", encoding="utf-8") as f:
    f.write(sitemap_html)
print(f"✅ sitemap.html创建完成（{len(index_items)}个页面）")

print("\n✅ P0优化完成")
