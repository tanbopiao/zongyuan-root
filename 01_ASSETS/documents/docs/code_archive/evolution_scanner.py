#!/usr/bin/env python3
"""
火斗云智AIOS 持续进化扫描引擎
定期扫描网站状态，自动发现优化点，执行低风险优化，高价值优化上报
"""
import json, os, sqlite3, subprocess, time, hashlib
from datetime import datetime

ROOT = "/www/wwwroot/www.huodouai.com"
ROOT2 = "/www/wwwroot/huodouai.com"
DB = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
LOG = "/opt/ZONGYUAN-ROOT/logs/evolution_scanner.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def scan_dead_links():
    """扫描死链"""
    issues = []
    for f in os.listdir(ROOT):
        if not f.endswith(".html"):
            continue
        path = os.path.join(ROOT, f)
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            import re
            links = re.findall(r'href="([^"]*)"', content)
            for link in links:
                if link.startswith("http") or link.startswith("#") or link.startswith("javascript") or link.startswith("mailto") or link.startswith("$") or link.startswith("'") or link.startswith('"') or "+" in link:
                    continue
                if link.startswith("/"):
                    target = os.path.join(ROOT, link.lstrip("/"))
                else:
                    target = os.path.join(ROOT, link)
                if not os.path.exists(target) and not os.path.exists(target.rstrip("/") + "/index.html"):
                    issues.append({"page": f, "link": link})
        except Exception:
            pass
    return issues

def scan_seo():
    """扫描SEO缺失"""
    missing = []
    for f in os.listdir(ROOT):
        if not f.endswith(".html"):
            continue
        path = os.path.join(ROOT, f)
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            if 'name="description"' not in content:
                missing.append({"page": f, "issue": "缺description"})
            if "viewport" not in content:
                missing.append({"page": f, "issue": "缺viewport"})
        except Exception:
            pass
    return missing

def scan_performance():
    """扫描大文件"""
    large = []
    for f in os.listdir(ROOT):
        if not f.endswith(".html"):
            continue
        path = os.path.join(ROOT, f)
        size = os.path.getsize(path)
        if size > 50000:
            large.append({"page": f, "size_kb": round(size/1024, 1)})
    return sorted(large, key=lambda x: x["size_kb"], reverse=True)[:5]

def scan_tech_debt():
    """扫描技术债"""
    result = subprocess.run(["find", "/www/wwwroot", "-name", "*.bak*"], capture_output=True, text=True, timeout=10)
    bak_count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
    return {"bak_files": bak_count}

def auto_fix_seo():
    """自动修复SEO（低风险）"""
    fixed = 0
    descriptions = {
        "index.html": "火斗云智AIOS - 元极恒一超认知永恒自治体系",
        "architecture.html": "火斗云智AIOS核心架构",
        "engines.html": "火斗云智核心引擎",
        "governance.html": "火斗云智治理与安全",
        "philosophy.html": "火斗云智原创思想体系",
        "digital-assets.html": "火斗云智数字资产可视化",
        "experience-kb.html": "火斗云智全域经验库",
        "decision-intelligence.html": "火斗云智三维稳态决策",
        "developer-center.html": "火斗云智开发者中心",
        "product.html": "火斗云智企业级AI操作系统",
        "products.html": "火斗云智产品矩阵",
        "education.html": "火斗云智普惠教育",
        "research.html": "火斗云智人工智能研究",
        "knowledge.html": "火斗云智全域知识图谱",
        "kernel-memory.html": "火斗云智云内核记忆可视化",
        "truth-transmutation.html": "火斗云智全域真值转义链路",
        "ledger.html": "火斗云智全域资产台账",
        "achievements.html": "火斗云智成果总览",
        "ai-asset-lock.html": "火斗云智AI资产锁档系统",
        "auto-ops.html": "火斗云智高危运维指令全自动审批闭环",
        "diff.html": "火斗云智差异化能力矩阵",
        "emergence.html": "火斗云智涌现层级理论",
        "learning-evolution.html": "火斗云智学习进化方法论",
        "high-order-state.html": "火斗云智高阶态白皮书",
        "startup-loop-defense-whitepaper.html": "火斗云智启动失败死循环防御白皮书",
        "search.html": "火斗云智全站搜索",
        "status-center.html": "火斗云智系统状态中心",
        "trial.html": "火斗云智Lite版试用申请",
        "workbench.html": "火斗云智智能工作台",
        "agent-studio.html": "火斗云智Agent Studio",
        "vector.html": "火斗云智向量库",
        "docs.html": "火斗云智文档中心",
    }
    for f, desc in descriptions.items():
        path = os.path.join(ROOT, f)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            if 'name="description"' not in content:
                content = content.replace("</title>", f'</title>\n<meta name="description" content="{desc}">', 1)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                # 同步到双root
                path2 = os.path.join(ROOT2, f)
                if os.path.exists(path2):
                    with open(path2, "w", encoding="utf-8") as fh:
                        fh.write(content)
                fixed += 1
        except Exception:
            pass
    return fixed

def write_truth(key, value):
    """写入记忆网关"""
    try:
        import urllib.request
        data = json.dumps({"key": key, "value": value, "category": "evolution_scan", "node_id": "evolution-scanner"}).encode()
        req = urllib.request.Request("http://127.0.0.1:9120/api/truth/upsert", data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read()).get("success", False)
    except Exception as e:
        log(f"写入记忆网关失败: {e}")
        return False

def main():
    log("=" * 50)
    log("持续进化扫描启动")
    
    # 1. 扫描死链
    dead_links = scan_dead_links()
    log(f"死链扫描: {len(dead_links)}个问题")
    
    # 2. 扫描SEO
    seo_issues = scan_seo()
    log(f"SEO扫描: {len(seo_issues)}个缺失")
    
    # 3. 自动修复SEO
    if seo_issues:
        fixed = auto_fix_seo()
        log(f"SEO自动修复: {fixed}个页面")
    
    # 4. 扫描性能
    large_files = scan_performance()
    log(f"大文件扫描: {len(large_files)}个超过50KB")
    
    # 5. 扫描技术债
    tech_debt = scan_tech_debt()
    log(f"技术债: {tech_debt['bak_files']}个.bak文件")
    
    # 6. 生成报告
    report = {
        "scan_time": datetime.now().isoformat(),
        "dead_links": dead_links[:10],
        "seo_issues": seo_issues[:10],
        "large_files": large_files,
        "tech_debt": tech_debt,
        "auto_fixed": fixed if seo_issues else 0,
        "evolution_score": max(0, 100 - len(dead_links) * 5 - len(seo_issues) * 2 - tech_debt["bak_files"] * 0.1)
    }
    
    # 7. 写入记忆网关
    key = f"EVOLUTION_SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    write_truth(key, report)
    log(f"扫描报告已写入记忆网关: {key}")
    log(f"进化评分: {report['evolution_score']:.1f}/100")
    log("扫描完成")

if __name__ == "__main__":
    main()
