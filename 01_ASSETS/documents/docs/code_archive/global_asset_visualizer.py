#!/usr/bin/env python3
"""
全域数字资产可视化引擎 v1.0
整合: 真值库 + 媒体资产 + 文档 + 服务状态 + 元法则
输出: JSON数据供官网动态展示
每15分钟自动运行
"""

import os
import json
import sqlite3
import urllib.request
from datetime import datetime, timedelta

OUTPUT_JSON = "/www/wwwroot/www.huodouai.com/digital_assets.json"
STORAGE_DIR = "/opt/storage"
DOCS_DIR = "/opt/ZONGYUAN-ROOT/docs"
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
META_RULE_PATH = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"


def get_truth_stats():
    """真值库统计"""
    try:
        req = urllib.request.Request("http://127.0.0.1:9120/api/status")
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        stats = data.get("stats", {})

        # 按类别统计
        category_stats = {}
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT category, COUNT(*) FROM truths GROUP BY category")
            for row in c.fetchall():
                category_stats[row[0] or "uncategorized"] = row[1]
            conn.close()
        except Exception:
            pass

        # 最近7天增长
        daily_growth = []
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for i in range(6, -1, -1):
                day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                c.execute("SELECT COUNT(*) FROM truths WHERE DATE(created_at)=?", (day,))
                count = c.fetchone()[0]
                daily_growth.append({"day": day, "count": count})
            conn.close()
        except Exception:
            pass

        return {
            "total": stats.get("truths", 0),
            "nodes": stats.get("nodes", 0),
            "audit_logs": stats.get("audit_logs", 0),
            "by_category": category_stats,
            "daily_growth": daily_growth
        }
    except Exception as e:
        return {"total": 0, "error": str(e)}


def get_media_stats():
    """媒体资产统计"""
    images = 0
    videos = 0
    total_size = 0
    image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp")
    video_extensions = (".mp4", ".mov", ".avi", ".mkv")

    for root, dirs, files in os.walk(STORAGE_DIR):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            filepath = os.path.join(root, f)
            try:
                size = os.path.getsize(filepath)
                total_size += size
                if ext in image_extensions:
                    images += 1
                elif ext in video_extensions:
                    videos += 1
            except Exception:
                pass

    return {
        "images": images,
        "videos": videos,
        "total_size_mb": round(total_size / 1024 / 1024, 1),
        "storage_path": STORAGE_DIR
    }


def get_docs_stats():
    """文档统计"""
    docs = []
    if os.path.exists(DOCS_DIR):
        for f in os.listdir(DOCS_DIR):
            if f.endswith(".md"):
                filepath = os.path.join(DOCS_DIR, f)
                try:
                    size = os.path.getsize(filepath)
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
                    docs.append({"name": f, "size_kb": round(size / 1024, 1), "updated": mtime})
                except Exception:
                    pass
    docs.sort(key=lambda x: x["updated"], reverse=True)
    return {"total": len(docs), "recent": docs[:10]}


def get_meta_rules():
    """元法则统计"""
    try:
        with open(META_RULE_PATH) as f:
            rules = json.load(f)
        if isinstance(rules, list):
            rule_list = rules
        else:
            rule_list = rules.get("rules", rules.get("meta_rules", []))
        return {"total": len(rule_list), "latest": rule_list[-3:] if rule_list else []}
    except Exception:
        return {"total": 0}


def get_service_status():
    """核心服务状态"""
    services = [
        ("记忆网关", 9120, "/api/status"),
        ("通信网关", 9122, "/"),
        ("希尔伯特镜像态", 9125, "/api/status"),
        ("GEO晶格", 9151, "/"),
        ("量子纠缠层", 9160, "/entangle/status"),
        ("飞书网关", 8001, "/"),
        ("本地LLM", 8081, "/health"),
        ("自愈引擎", 8161, "/health"),
        ("向量数据库", 8014, "/health"),
        ("RAG服务", 8085, "/health"),
    ]
    result = []
    for name, port, path in services:
        try:
            code = urllib.request.urlopen(
                f"http://127.0.0.1:{port}{path}", timeout=2
            ).getcode()
            status = "online" if code == 200 else "warning"
        except Exception:
            status = "offline"
        result.append({"name": name, "port": port, "status": status})
    return result


def get_web_assets_stats():
    """网页资产统计 - 所有页面、子域名、子目录"""
    WEB_ROOT = "/www/wwwroot"
    MAIN_SITE = "/www/wwwroot/www.huodouai.com"

    # 主官网页面
    main_pages = []
    if os.path.exists(MAIN_SITE):
        for f in os.listdir(MAIN_SITE):
            if f.endswith(".html"):
                main_pages.append(f)

    # 子目录页面
    subdirs = {}
    if os.path.exists(MAIN_SITE):
        for d in os.listdir(MAIN_SITE):
            dpath = os.path.join(MAIN_SITE, d)
            if os.path.isdir(dpath) and not d.startswith("_"):
                count = sum(1 for _, _, files in os.walk(dpath) for f in files if f.endswith(".html"))
                if count > 0:
                    subdirs[d] = count

    # 子域名
    subdomains = []
    domain_names = ["drama.huodouai.com", "gov.huodouai.com", "docs.huodouai.com",
                    "status.huodouai.com", "api.huodouai.com", "console.huodouai.com",
                    "kunlun.huodouai.com", "ops.huodouai.com", "mirror.huodouai.com"]
    for domain in domain_names:
        dpath = os.path.join(WEB_ROOT, domain)
        if os.path.exists(dpath):
            page_count = 0
            total_size = 0
            for r, _, files in os.walk(dpath):
                for f in files:
                    if f.endswith(".html"):
                        page_count += 1
                    try:
                        total_size += os.path.getsize(os.path.join(r, f))
                    except Exception:
                        pass
            size_mb = round(total_size / 1024 / 1024, 1)
            # HTTP状态
            try:
                code = urllib.request.urlopen(
                    f"https://{domain}/", timeout=3,
                    context=__import__("ssl")._create_unverified_context()
                ).getcode()
                http_status = "online" if code == 200 else "warning"
            except Exception:
                http_status = "offline"
            subdomains.append({
                "domain": domain,
                "pages": page_count,
                "size_mb": size_mb,
                "status": http_status
            })

    total_pages = len(main_pages) + sum(subdirs.values()) + sum(s["pages"] for s in subdomains)

    return {
        "total_html": total_pages,
        "main_site_pages": len(main_pages),
        "main_site_list": sorted(main_pages),
        "subdirectories": subdirs,
        "subdomains": subdomains,
        "total_subdomains": len(subdomains)
    }


def get_auto_classification():
    """自动分类 - 按业务域归类所有资源"""
    MAIN_SITE = "/www/wwwroot/www.huodouai.com"
    DOCS_DIR = "/opt/ZONGYUAN-ROOT/docs"
    STORAGE_DIR = "/opt/storage"

    # 定义11大业务域及关键词匹配规则
    domains = {
        "kunlun_drama": {
            "name": "昆仑洞天·短剧生产",
            "icon": "🎬",
            "keywords": ["drama", "kunlun", "短剧", "赤华", "九天玄女", "keyframe", "character", "EP0", "瑶池", "白帝"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": ["drama.huodouai.com", "kunlun.huodouai.com"]
        },
        "gov_ai": {
            "name": "政务AI中台",
            "icon": "🏛️",
            "keywords": ["gov", "政务", "gov-ai"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": ["gov.huodouai.com"]
        },
        "meta_kernel": {
            "name": "元极恒一内核",
            "icon": "🧠",
            "keywords": ["kernel", "architecture", "engines", "truth", "meta", "内核", "元极", "真值", "META_RULES", "GLOBAL_TRUTH"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": []
        },
        "governance_security": {
            "name": "治理与安全",
            "icon": "🛡️",
            "keywords": ["governance", "security", "sovereignty", "auto-ops", "asset-lock", "安全", "治理", "SECURITY", "defense"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": []
        },
        "decision_intel": {
            "name": "决策智能",
            "icon": "⚖️",
            "keywords": ["decision", "决策", "三维稳态"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": []
        },
        "research_thought": {
            "name": "研究与思想",
            "icon": "💡",
            "keywords": ["philosophy", "emergence", "learning", "research", "high-order", "whitepaper", "思想", "研究", "涌现", "进化", "EVOLUTION", "SHANHAIJING"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": []
        },
        "developer": {
            "name": "开发者中心",
            "icon": "👨‍💻",
            "keywords": ["developer", "docs", "api", "SOP", "sop", "NODE", "协议", "GITHUB", "GIT", "VOLCENGINE"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": ["docs.huodouai.com", "api.huodouai.com", "console.huodouai.com"]
        },
        "status_monitor": {
            "name": "状态与监控",
            "icon": "📊",
            "keywords": ["status", "monitor", "状态", "监控"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": ["status.huodouai.com"]
        },
        "asset_ledger": {
            "name": "资产与台账",
            "icon": "📦",
            "keywords": ["digital-assets", "ledger", "achievements", "assets", "资产", "台账", "成果"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": []
        },
        "education": {
            "name": "普惠教育",
            "icon": "📚",
            "keywords": ["education", "教育"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": []
        },
        "product": {
            "name": "产品与商业化",
            "icon": "🚀",
            "keywords": ["product", "products", "diff", "trial", "workbench", "agent-studio", "portal", "产品", "试用"],
            "pages": [],
            "docs": [],
            "media_count": 0,
            "subdomains": []
        }
    }

    # 分类主站页面
    if os.path.exists(MAIN_SITE):
        for f in os.listdir(MAIN_SITE):
            if f.endswith(".html"):
                name_lower = f.lower()
                matched = False
                for domain_id, domain in domains.items():
                    if any(kw.lower() in name_lower for kw in domain["keywords"]):
                        domain["pages"].append(f)
                        matched = True
                        break
                if not matched:
                    domains["meta_kernel"]["pages"].append(f)  # 默认归内核

    # 分类子目录
    if os.path.exists(MAIN_SITE):
        for d in os.listdir(MAIN_SITE):
            dpath = os.path.join(MAIN_SITE, d)
            if os.path.isdir(dpath) and not d.startswith("_"):
                d_lower = d.lower()
                for domain_id, domain in domains.items():
                    if any(kw.lower() in d_lower for kw in domain["keywords"]):
                        count = sum(1 for _, _, files in os.walk(dpath) for f in files if f.endswith(".html"))
                        for _ in range(count):
                            domain["pages"].append(f"/{d}/")
                        break

    # 分类文档
    if os.path.exists(DOCS_DIR):
        for f in os.listdir(DOCS_DIR):
            if f.endswith(".md"):
                name_lower = f.lower()
                matched = False
                for domain_id, domain in domains.items():
                    if any(kw.lower() in name_lower for kw in domain["keywords"]):
                        domain["docs"].append(f)
                        matched = True
                        break
                if not matched:
                    domains["developer"]["docs"].append(f)  # 默认归开发者

    # 分类媒体资产
    if os.path.exists(STORAGE_DIR):
        for root, dirs, files in os.walk(STORAGE_DIR):
            for f in files:
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".mp4", ".mov")):
                    path_lower = os.path.join(root, f).lower()
                    for domain_id, domain in domains.items():
                        if any(kw.lower() in path_lower for kw in domain["keywords"]):
                            domain["media_count"] += 1
                            break

    # 统计
    result = []
    for domain_id, domain in domains.items():
        result.append({
            "id": domain_id,
            "name": domain["name"],
            "icon": domain["icon"],
            "pages": len(domain["pages"]),
            "docs": len(domain["docs"]),
            "media": domain["media_count"],
            "subdomains": domain["subdomains"],
            "page_list": domain["pages"][:10],
            "doc_list": domain["docs"][:10]
        })

    # 按总资产排序
    result.sort(key=lambda x: x["pages"] + x["docs"] + x["media"], reverse=True)
    return result


def get_system_stats():
    """系统资源统计"""
    # 内存
    mem_info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if "MemTotal" in line:
                    mem_info["total_mb"] = int(line.split()[1]) // 1024
                elif "MemAvailable" in line:
                    mem_info["available_mb"] = int(line.split()[1]) // 1024
        mem_info["used_mb"] = mem_info.get("total_mb", 0) - mem_info.get("available_mb", 0)
        mem_info["usage_percent"] = round(mem_info["used_mb"] / mem_info.get("total_mb", 1) * 100, 1)
    except Exception:
        pass

    # 磁盘
    disk_info = {}
    try:
        stat = os.statvfs("/")
        disk_info["total_gb"] = round(stat.f_frsize * stat.f_blocks / 1024**3, 1)
        disk_info["used_gb"] = round(stat.f_frsize * (stat.f_blocks - stat.f_bfree) / 1024**3, 1)
        disk_info["usage_percent"] = round((stat.f_blocks - stat.f_bfree) / stat.f_blocks * 100, 1)
    except Exception:
        pass

    return {"memory": mem_info, "disk": disk_info}


def main():
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

    data = {
        "generated_at": datetime.now().isoformat(),
        "version": "v1.1",
        "truths": get_truth_stats(),
        "media": get_media_stats(),
        "documents": get_docs_stats(),
        "meta_rules": get_meta_rules(),
        "services": get_service_status(),
        "web_assets": get_web_assets_stats(),
        "classification": get_auto_classification(),
        "system": get_system_stats()
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 全域资产可视化数据已生成: {OUTPUT_JSON}")
    print(f"   真值: {data['truths'].get('total', 0)}条")
    print(f"   媒体: {data['media'].get('images', 0)}图 + {data['media'].get('videos', 0)}视频")
    print(f"   文档: {data['documents'].get('total', 0)}篇")
    print(f"   元法则: {data['meta_rules'].get('total', 0)}条")
    print(f"   服务: {sum(1 for s in data['services'] if s['status']=='online')}/{len(data['services'])}在线")


if __name__ == "__main__":
    main()
