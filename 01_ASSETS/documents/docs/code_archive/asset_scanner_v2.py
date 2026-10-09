#!/usr/bin/env python3
"""
资产自动发现扫描器 V2.1
每小时扫描/www/wwwroot下所有HTML，生成资产清单JSON
供门户动态加载
"""
import os
import json
import re
from datetime import datetime

ROOT = "/www/wwwroot/huodouai.com"
OUTPUT = "/www/wwwroot/huodouai.com/aios/_assets.json"
EXCLUDE_DIRS = ["_backup_nav_inject", "assets", ".well-known", "_shots", "_archive_quality", "_archive", "backup", "backups"]
EXCLUDE_FILES = [".bak", ".backup", "404.html", "500.html"]

def classify(path, title=""):
    """智能分类：基于路径和标题，产品矩阵优先于AIOS内核"""
    p = path.lower()
    t = title.lower()
    
    # 根目录产品页面优先归到产品矩阵/文档白皮书
    is_root = path.count("/") == 1
    root_product_keywords = [
        "pricing", "cases", "compare", "roi", "book-demo", "roadmap",
        "showcase", "changelog", "contact", "partners", "template-market",
        "workbench", "capability", "agent-", "education", "edu-",
        "knowledge", "/ai/", "platform", "api-usage", "opensource",
        "blog", "logo", "high-order", "decision", "semantic",
        "startup-loop", "memory-gateway", "solutions", "whitepaper",
        "architecture-deep", "product-map", "about-line", "gov-line",
        "ops-line", "ecosystem-line", "content-line", "security-line",
        "index-new", "prometheus", "kernel-memory", "server-monitor",
        "kunlun-drama", "token-gateway", "index.html", "drama-line",
        "gov-ai", "gov-mobile", "gov-admin", "gov-api-docs",
        "gov-agents", "gov-canvas", "gov-compete", "gov-pricing",
        "gov-sales", "gov-cases", "gov-dashboard", "gov-monitor",
        "gov-operator-admin", "gov-tenant", "gov-analytics"
    ]
    if is_root and any(k in p for k in root_product_keywords):
        if "whitepaper" in p or "白皮书" in t or "报告" in t or "研究" in t:
            return "文档白皮书"
        return "产品矩阵"
    
    # 文档白皮书（优先于AIOS内核）
    if any(k in p for k in ["/docs/", "/whitepaper", "/whitepapers", "whitepaper", "白皮书", "文档", "报告", "report", "/aios/archive/"]):
        return "文档白皮书"
    if any(k in t for k in ["白皮书", "文档", "报告", "whitepaper", "report"]):
        return "文档白皮书"
    
    # 产品矩阵
    if any(k in p for k in ["/products/", "/apps/", "/solutions/", "/pricing", "/cases", "/compare", "/roi", "/book-demo", "/roadmap", "/showcase", "/changelog", "/contact", "/partners", "/template-market", "/workbench", "/capability", "/agent-", "/education", "/edu-", "/knowledge", "/ai/", "/platform", "/api-usage", "/opensource", "/blog", "/logo"]):
        return "产品矩阵"
    if any(k in t for k in ["产品", "解决方案", "定价", "案例", "对比", "演示", "路线图", "展示", "更新日志", "联系", "合作", "模板", "工作台", "能力", "教育", "老师", "知识图谱", "开源", "博客", "logo", "投资回报"]):
        return "产品矩阵"
    
    # AIOS内核（只匹配明确的内核相关）
    if any(k in p for k in ["/aios/", "meta-law", "meta_law", "geo-lattice", "ge-lattice", "truth-value", "truth_value", "元法则", "真值", "晶格"]):
        return "AIOS内核"
    if any(k in t for k in ["元法则", "真值", "晶格", "记忆网关", "内核运维", "自治体系", "元极恒一"]):
        return "AIOS内核"
    
    # 短剧工厂
    if any(k in p for k in ["/drama/", "/kunlun/", "drama", "短剧", "角色", "分镜", "关键帧"]):
        return "短剧工厂"
    if any(k in t for k in ["短剧", "昆仑", "角色", "分镜", "关键帧", "玄女", "西王母", "太阴"]):
        return "短剧工厂"
    
    # 政务中台
    if any(k in p for k in ["/gov", "gov-", "政务", "中台", "tenant", "operator-admin"]):
        return "政务中台"
    if any(k in t for k in ["政务", "中台", "政府", "tenant", "operator"]):
        return "政务中台"
    
    # 架构中心
    if any(k in p for k in ["/architecture/", "/pages/", "architecture", "架构", "拓扑", "蓝图", "design"]):
        return "架构中心"
    if any(k in t for k in ["架构", "拓扑", "蓝图", "设计", "architecture"]):
        return "架构中心"
    
    # 监控中心
    if any(k in p for k in ["monitor", "dashboard", "grafana", "监控", "仪表盘", "告警", "alert", "status", "score-trend", "drift"]):
        return "监控中心"
    if any(k in t for k in ["监控", "仪表盘", "告警", "状态", "dashboard", "grafana"]):
        return "监控中心"
    
    # 运维管理
    if any(k in p for k in ["/ops/", "/internal/", "/console/", "ops", "运维", "部署", "backup", "security", "rbac", "identity", "api-platform", "notification-config"]):
        return "运维管理"
    if any(k in t for k in ["运维", "部署", "安全", "权限", "identity", "rbac", "console"]):
        return "运维管理"
    
    # 研究哲学
    if any(k in p for k in ["/research/", "/philosophy/", "/theory/", "/sovereignty/", "/evolution/", "研究", "哲学", "理论", "主权", "进化"]):
        return "研究哲学"
    if any(k in t for k in ["研究", "哲学", "理论", "主权", "进化", "元极恒一", "超认知"]):
        return "研究哲学"
    
    # 关于体系
    if any(k in p for k in ["/about/", "about", "关于", "隐私", "terms", "privacy", "security-compliance"]):
        return "关于体系"
    if any(k in t for k in ["关于", "隐私", "条款", "合规", "about"]):
        return "关于体系"
    
    return "其他"

def scan_assets():
    assets = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        
        for f in filenames:
            if not f.endswith(".html"):
                continue
            if any(ex in f for ex in EXCLUDE_FILES):
                continue
            
            fp = os.path.join(dirpath, f)
            rel_path = "/" + os.path.relpath(fp, ROOT)
            
            try:
                stat = os.stat(fp)
                size = stat.st_size
                mtime = stat.st_mtime
                
                title = f.replace(".html", "").replace("-", " ").replace("_", " ").title()
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read(2000)
                        m = re.search(r"<title>(.*?)</title>", content, re.DOTALL)
                        if m:
                            title = m.group(1).strip()[:60]
                except:
                    pass
                
                category = classify(rel_path, title)
                
                assets.append({
                    "title": title,
                    "path": rel_path,
                    "size": size,
                    "mtime": mtime,
                    "mtime_str": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                    "category": category,
                })
            except Exception as e:
                continue
    
    assets.sort(key=lambda x: x["mtime"], reverse=True)
    
    categories = {}
    recent_7d = 0
    for a in assets:
        cat = a["category"]
        categories[cat] = categories.get(cat, 0) + 1
        if (datetime.now().timestamp() - a["mtime"]) < 7 * 86400:
            recent_7d += 1
    
    stats = {
        "total": len(assets),
        "categories": categories,
        "recent_7d": recent_7d,
        "scan_time": datetime.now().isoformat(),
    }
    
    result = {
        "stats": stats,
        "assets": assets,
        "recent": assets[:20],
    }
    
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ 扫描完成: " + str(len(assets)) + "个资产, " + str(recent_7d) + "个近7天更新")
    print("   分类统计: " + str(categories))
    return result

if __name__ == "__main__":
    scan_assets()
