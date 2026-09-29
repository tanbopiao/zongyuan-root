#!/usr/bin/env python3
"""
官网骨架自动集成器 V1.0
自动检测新页面 → 分类 → 加入导航 → 双root同步 → HTTP验证
配合MR-091自动化部署与集成标准使用
"""
import os, json, subprocess, urllib.request, hashlib
from datetime import datetime

WWW_ROOTS = ["/www/wwwroot/www.huodouai.com/", "/www/wwwroot/huodouai.com/"]
INDEX_FILE = "index.html"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/auto_integrator.log"
STATE_FILE = "/opt/ZONGYUAN-ROOT/data/auto_integrator_state.json"

# 页面分类与导航名称映射（自动分类规则）
PAGE_CATEGORIES = {
    "中枢大脑": ["central-brain", "brain-strategy", "kernel", "self-model"],
    "进化战略": ["evolution-strategy", "evolution", "learning-evolution", "high-order-state"],
    "全网学习": ["global-learning", "research", "learning"],
    "智能体": ["agent-embodiment", "agent-studio", "agent"],
    "自动流水线": ["auto-pipeline", "auto-ops", "automation"],
    "经验库": ["experience-kb", "experience"],
    "架构": ["architecture", "engines", "vector"],
    "数字资产": ["digital-assets", "asset", "ledger"],
    "思想": ["philosophy", "truth-transmutation", "emergence"],
    "治理": ["governance", "decision-intelligence"],
    "教育": ["education", "edu-", "learning"],
    "状态": ["status", "status-center"],
    "工作台": ["workbench", "portal", "developer-center"],
    "产品": ["product", "products", "trial"],
    "文档": ["docs", "documentation"],
    "成果": ["achievements", "whitepaper"],
}

# 导航中已有的链接（避免重复）
EXISTING_NAV = ["/architecture.html", "/engines.html", "/digital-assets.html", "/philosophy.html", "/governance.html", "/domains/", "/experience-kb.html"]

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[%s] %s" % (ts, msg))
    with open(LOG_FILE, "a") as f:
        f.write("[%s] %s\n" % (ts, msg))

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"integrated_pages": [], "last_run": None}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def classify_page(filename):
    """根据文件名自动分类"""
    name = filename.lower().replace(".html", "")
    for category, keywords in PAGE_CATEGORIES.items():
        for kw in keywords:
            if kw in name:
                return category
    return "更多"

def scan_pages():
    """扫描所有HTML页面，返回未集成的新页面"""
    root = WWW_ROOTS[0]
    pages = []
    for f in os.listdir(root):
        if f.endswith(".html") and f != "404.html" and f != "index.html":
            pages.append(f)
    return sorted(pages)

def check_http_200(url_path):
    """验证页面HTTP 200"""
    try:
        req = urllib.request.Request("https://www.huodouai.com%s" % url_path, headers={"Host": "www.huodouai.com"})
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200
    except:
        return False

def integrate_to_nav(new_pages, state):
    """将新页面集成到导航"""
    index_path = os.path.join(WWW_ROOTS[0], INDEX_FILE)
    
    # 读取当前index.html
    with open(index_path, "r") as f:
        content = f.read()
    
    # 找到导航结束标签 </nav> 前插入新链接
    # 按分类组织新页面
    category_pages = {}
    for page in new_pages:
        cat = classify_page(page)
        if cat not in category_pages:
            category_pages[cat] = []
        category_pages[cat].append(page)
    
    # 构建新的导航链接（在短剧外部链接之前插入）
    new_links = []
    for cat, pages in category_pages.items():
        for page in pages:
            link = '<a href="/%s">%s</a>' % (page, cat if len(pages) == 1 else cat + "·" + page.replace(".html", "").split("-")[-1][:4])
            new_links.append(link)
    
    if not new_links:
        log("  无新页面需要集成")
        return 0
    
    # 在 </nav> 前插入（在外部链接之前）
    insert_point = content.find('<a href="https://drama.huodouai.com"')
    if insert_point == -1:
        insert_point = content.find("</nav>")
    
    links_str = "\n        ".join(new_links) + "\n        "
    new_content = content[:insert_point] + links_str + content[insert_point:]
    
    # 备份
    backup_path = index_path + ".bak." + datetime.now().strftime("%Y%m%d%H%M%S")
    subprocess.run(["cp", index_path, backup_path], capture_output=True)
    
    # 写入
    with open(index_path, "w") as f:
        f.write(new_content)
    
    # 双root同步
    for root in WWW_ROOTS[1:]:
        subprocess.run(["cp", index_path, os.path.join(root, INDEX_FILE)], capture_output=True)
    
    return len(new_pages)

def main():
    log("=" * 50)
    log("🚀 官网骨架自动集成器启动")
    
    state = load_state()
    all_pages = scan_pages()
    log("📊 扫描到 %d 个HTML页面" % len(all_pages))
    
    # 找出未集成的页面
    integrated = set(state.get("integrated_pages", []))
    # 也检查导航中已有的
    with open(os.path.join(WWW_ROOTS[0], INDEX_FILE)) as f:
        index_content = f.read()
    
    new_pages = []
    for page in all_pages:
        if page not in integrated and ("/%s" % page) not in index_content:
            new_pages.append(page)
    
    if not new_pages:
        log("✅ 所有页面已集成，无新页面")
        save_state(state)
        return
    
    log("📥 发现 %d 个未集成页面:" % len(new_pages))
    for p in new_pages:
        cat = classify_page(p)
        log("  - %s [%s]" % (p, cat))
    
    # 集成到导航
    count = integrate_to_nav(new_pages, state)
    log("✅ 已集成 %d 个页面到导航" % count)
    
    # 验证HTTP 200
    log("🔍 验证页面可访问性...")
    for page in new_pages:
        ok = check_http_200("/" + page)
        status = "✅" if ok else "⚠️"
        log("  %s %s" % (status, page))
    
    # 更新状态
    state["integrated_pages"] = list(integrated | set(new_pages))
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    
    # 上报记忆网关
    try:
        data = json.dumps({
            "key": "INTEGRATOR_REPORT_%s" % datetime.now().strftime("%Y%m%d%H%M%S"),
            "value": {"integrated": new_pages, "count": count, "total_pages": len(all_pages)},
            "category": "integration_report",
            "node_id": "auto-integrator"
        }).encode()
        req = urllib.request.Request("http://127.0.0.1:9120/api/truth/upsert", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        log("✅ 已上报记忆网关")
    except Exception as e:
        log("⚠️ 上报失败: %s" % e)
    
    log("=" * 50)

if __name__ == "__main__":
    main()
