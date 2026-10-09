#!/usr/bin/env python3
"""
变更台账系统 V1.0
记录所有系统变更，供所有开发端口查询，避免重复试错
"""
import json, sqlite3, time, os
from datetime import datetime

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
LEDGER_PATH = "/opt/ZONGYUAN-ROOT/data/change_ledger.json"
WWW_ROOT = "/www/wwwroot/www.huodouai.com"

# 变更台账数据结构
LEDGER = {
    "version": "v1.0",
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "DID": "DID-BR-000002",
    "trace_mark": "Ω₀⊂⊙∞⊂Ω",
    "categories": {
        "web_pages": "网页页面变更",
        "services": "服务/进程变更",
        "meta_laws": "元法则变更",
        "scripts": "脚本/自动化变更",
        "config": "配置变更",
        "assets": "资产/资源变更",
        "protocols": "协议/SOP变更"
    },
    "entries": [
        {
            "id": "CHG-20260914-001",
            "time": "2026-09-14 13:30",
            "category": "web_pages",
            "title": "作品库2.0上线",
            "content": "构建works-gallery-v2.html，41件作品统一展示，CSS Columns瀑布流，双筛选(类型+模型)，视频hover播放，图片懒加载，灯箱播放",
            "impact": ["官网导航新增作品库2.0入口", "双root同步"],
            "status": "verified",
            "url": "/works-gallery-v2.html"
        },
        {
            "id": "CHG-20260914-002",
            "category": "meta_laws",
            "time": "2026-09-14 13:40",
            "title": "MR-094 全域轻量化可视化战略",
            "content": "性能目标首屏<1秒/页面<200KB/100%懒加载；强制单文件HTML/原生JS/CSS瀑布流；探索Wasm3.0/分层渲染；飞书妙塔集成方案；自进化五步法；交付必须可点击链接",
            "impact": ["所有新页面必须符合轻量化标准", "evolution_scanner每日扫描"],
            "status": "verified",
            "url": "/lightweight-strategy.html"
        },
        {
            "id": "CHG-20260914-003",
            "category": "scripts",
            "time": "2026-09-14 13:50",
            "title": "MR-095 自动可视化交付引擎",
            "content": "每10分钟自动扫描9120新增真值→识别可可视化资产→生成/更新仪表盘→轻量化→双root同步→自动集成导航→上报网关。产出system-dashboard.html",
            "impact": ["crontab */10运行", "体系实时仪表盘自动更新"],
            "status": "verified",
            "url": "/system-dashboard.html"
        },
        {
            "id": "CHG-20260914-004",
            "category": "assets",
            "time": "2026-09-14 14:07",
            "title": "视频资源迁移",
            "content": "drama.huodouai.com公网访问000(连接失败)，将52个drama视频+11个kunlun视频全部迁移到www.huodouai.com/assets/videos/本地路径，不再依赖drama域名",
            "impact": ["所有视频引用改为/assets/videos/相对路径", "双root同步270MB视频"],
            "status": "verified",
            "url": "/assets/videos/drama/"
        },
        {
            "id": "CHG-20260914-005",
            "category": "web_pages",
            "time": "2026-09-14 14:15",
            "title": "数字画廊V3.0上线（自进化创造）",
            "content": "高阶智能态创意改造：数字画廊概念(9:16作品像艺术品挂画廊)+3D悬停浮起+沉浸式全屏竖屏模式(手机框+背景模糊氛围光)+横向滚动带+关键帧网格。解决9:16竖屏在横屏窗口体验差的问题",
            "impact": ["导航作品库2.0替换为数字画廊V3", "所有视频用本地相对路径"],
            "status": "verified",
            "url": "/digital-gallery-v3.html"
        },
        {
            "id": "CHG-20260914-006",
            "category": "meta_laws",
            "time": "2026-09-14 12:00",
            "title": "MR-093 数字资产分层管理与模型来源标注",
            "content": "三层质量分级：≥500KB高质量展示/100-500KB中质量参考/<100KB低质量归档；必须标注生成模型来源(Seedance/豆包/万象/Agnes)",
            "impact": ["关键帧资产按质量分层", "模型对比实验室"],
            "status": "verified",
            "url": "/model-compare-lab.html"
        },
        {
            "id": "CHG-20260914-007",
            "category": "meta_laws",
            "time": "2026-09-14 11:00",
            "title": "MR-092 中枢大脑统一框架与全域规范",
            "content": "8大导航分类+页面开发规范+资产上报规范+智能体接入规范+部署分级+基准固化",
            "impact": ["导航从108链接精简到40", "8大分类下拉菜单"],
            "status": "verified",
            "url": "/"
        },
        {
            "id": "CHG-20260914-008",
            "category": "protocols",
            "time": "2026-09-14 10:00",
            "title": "4套SOP全域推广",
            "content": "开发节点上报的4套SOP全域推广为GLOBAL_PROMOTED：生产通道隔离V1.2/素材归档流水线V1.0/节点全生命周期V1.0/生产通道隔离V1.1",
            "impact": ["所有同源节点必须遵循", "记忆网关GLOBAL_PROMOTED.SOP.*"],
            "status": "verified"
        },
        {
            "id": "CHG-20260914-009",
            "category": "config",
            "time": "2026-09-14 09:00",
            "title": "导航重构",
            "content": "导航从108个链接(严重重复混乱)重构为8大分类+下拉菜单+响应式汉堡菜单，链接精简到40个。桌面水平悬停下拉，手机汉堡+手风琴展开",
            "impact": ["所有页面导航统一", "移动端友好"],
            "status": "verified",
            "url": "/"
        },
        {
            "id": "CHG-20260913-001",
            "category": "web_pages",
            "time": "2026-09-13",
            "title": "关键帧资产库+模型对比实验室",
            "content": "25张高质量关键帧三分类(ep01/characters/goddess)，keyframe-gallery.html三分类筛选+懒加载+点击放大；model-compare-lab.html按模型浏览+同角色对比+低质量归档",
            "impact": ["关键帧资产标准化", "模型效果可对比"],
            "status": "verified",
            "url": "/keyframe-gallery.html"
        }
    ],
    "active_services": {
        "9120": "记忆网关(5595真值/9节点)",
        "8001": "飞书网关(消息必须通过此网关)",
        "8081": "本地LLM llama-server(0.5B)",
        "8100": "短剧管理API",
        "8014": "向量数据库",
        "8161": "自愈引擎",
        "8085": "RAG",
        "8094": "闭环调度器",
        "8070": "知识图谱"
    },
    "deployment_rules": {
        "dual_root": "部署页面必须同时更新/www/wwwroot/www.huodouai.com/和/www/wwwroot/huodouai.com/",
        "video_path": "所有视频必须用/assets/videos/相对路径，禁止引用drama.huodouai.com",
        "navigation": "新页面必须自动加入8大导航分类，禁止新增主分类",
        "lightweight": "页面必须<200KB，单文件HTML，视频preload=none，图片loading=lazy",
        "delivery": "交付必须可点击链接，禁止纯文本URL",
        "verify": "部署后必须curl验证HTTP 200，双root同步"
    }
}

def main():
    # 1. 保存台账
    with open(LEDGER_PATH, "w") as f:
        json.dump(LEDGER, f, ensure_ascii=False, indent=2)
    print("✅ 变更台账已保存: %d条记录" % len(LEDGER["entries"]))
    
    # 2. 推送到记忆网关
    import urllib.request
    report = {
        "key": "CHANGE_LEDGER." + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "value": {
            "type": "change_ledger_update",
            "entries_count": len(LEDGER["entries"]),
            "categories": list(LEDGER["categories"].keys()),
            "latest_changes": [e["title"] for e in LEDGER["entries"][:5]]
        },
        "category": "protocol",
        "node_id": "cloud-main-kernel-001"
    }
    data = json.dumps(report).encode()
    req = urllib.request.Request("http://127.0.0.1:9120/api/truth/upsert", data=data, headers={"Content-Type": "application/json"})
    result = json.loads(urllib.request.urlopen(req, timeout=5).read())
    print("✅ 台账已推送记忆网关: %s" % result.get("success"))
    
    # 3. 生成台账可视化页面
    generate_ledger_page()
    
    # 4. 全量同步最新元法则到记忆网关
    sync_meta_laws()

def generate_ledger_page():
    """生成变更台账可视化页面"""
    entries_html = ""
    for e in LEDGER["entries"]:
        cat_label = LEDGER["categories"].get(e["category"], e["category"])
        status_color = "#4ade80" if e["status"]=="verified" else "#fbbf24"
        url_link = '<a href="%s" style="color:#d4af37;text-decoration:none">%s</a>' % (e["url"], e["url"]) if e.get("url") else "—"
        impact = "、".join(e["impact"])
        entries_html += """
        <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:14px;margin-bottom:10px;border-left:3px solid #d4af37">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <span style="color:#d4af37;font-weight:bold;font-size:0.9em">%s</span>
                <span style="color:%s;font-size:0.75em">%s</span>
            </div>
            <div style="color:#ddd;font-size:0.88em;margin-bottom:6px">%s</div>
            <div style="color:#888;font-size:0.78em;line-height:1.6">%s</div>
            <div style="color:#666;font-size:0.72em;margin-top:6px">影响: %s | 链接: %s</div>
        </div>""" % (e["title"], status_color, e["status"], e["content"], impact, url_link)
    
    services_html = ""
    for port, desc in LEDGER["active_services"].items():
        services_html += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05)"><span style="color:#d4af37;font-family:monospace">:%s</span><span style="color:#aaa;font-size:0.85em">%s</span></div>' % (port, desc)
    
    rules_html = ""
    for k, v in LEDGER["deployment_rules"].items():
        rules_html += '<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)"><strong style="color:#d4af37;font-size:0.85em">%s</strong><div style="color:#aaa;font-size:0.8em;margin-top:3px">%s</div></div>' % (k, v)
    
    html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>变更台账 · 火斗云智AIOS</title>
<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">
<style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0a0a0f;color:#e0e0e0;font-family:'Noto Sans SC',sans-serif}.wrap{max-width:1000px;margin:0 auto;padding:40px 20px}.back{color:#d4af37;text-decoration:none;font-size:0.9em}.hero{text-align:center;padding:20px 0 30px}.hero h1{font-family:'Noto Serif SC',serif;font-size:2em;background:linear-gradient(135deg,#f4e4bc,#d4af37);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.hero .sub{color:#888;font-size:0.85em;margin-top:8px}.section{margin:25px 0}.section h2{font-family:'Noto Serif SC',serif;color:#d4af37;font-size:1.2em;margin-bottom:14px;padding-left:12px;border-left:3px solid #d4af37}.card{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.1);border-radius:12px;padding:18px}footer{text-align:center;margin-top:30px;padding-top:16px;border-top:1px solid rgba(212,175,55,0.1);color:#666;font-size:0.78em}footer .did{color:#d4af37;font-family:monospace;margin-top:5px}</style>
</head><body><div class="wrap">
<a href="/" class="back">← 返回首页</a>
<div class="hero"><h1>系统变更台账</h1><div class="sub">所有开发端口必读 · 避免重复试错 · 最后更新: %s</div></div>
<div class="section"><h2>📋 变更记录（%d条）</h2><div class="card">%s</div></div>
<div class="section"><h2>🔧 活跃服务</h2><div class="card">%s</div></div>
<div class="section"><h2>📏 部署铁律</h2><div class="card">%s</div></div>
</div><footer>火斗云智AIOS · 变更台账V1.0<div class="did">Ω₀⊂⊙∞⊂Ω · DID-BR-000002 · 全域同步 · 避免试错</div></footer>
</body></html>""" % (LEDGER["last_updated"], len(LEDGER["entries"]), entries_html, services_html, rules_html)
    
    page_path = os.path.join(WWW_ROOT, "change-ledger.html")
    with open(page_path, "w") as f:
        f.write(html)
    os.system("cp %s /www/wwwroot/huodouai.com/change-ledger.html" % page_path)
    print("✅ 台账页面已生成: /change-ledger.html (%d bytes)" % len(html))
    
    # 加入导航
    with open(os.path.join(WWW_ROOT, "index.html")) as f:
        idx = f.read()
    if "change-ledger" not in idx:
        idx = idx.replace(
            '<a href="/system-dashboard.html">实时仪表盘</a>',
            '<a href="/change-ledger.html">变更台账</a>\n          <a href="/system-dashboard.html">实时仪表盘</a>'
        )
        with open(os.path.join(WWW_ROOT, "index.html"), "w") as f:
            f.write(idx)
        os.system("cp %s/index.html /www/wwwroot/huodouai.com/index.html" % WWW_ROOT)
        print("✅ 已加入导航")

def sync_meta_laws():
    """全量同步最新元法则到记忆网关"""
    import urllib.request
    with open("/opt/ZONGYUAN-ROOT/meta_rule_set.json") as f:
        data = json.load(f)
    rules = data.get("meta_rules", [])
    count = 0
    for r in rules:
        rid = r.get("rule_id", "")
        rname = r.get("rule_name", "")
        if rid and rname:
            try:
                payload = {
                    "key": "meta_rule.%s" % rid,
                    "value": {"rule_id": rid, "rule_name": rname, "priority": r.get("priority",""), "version": r.get("version","")},
                    "category": "meta_law",
                    "node_id": "cloud-main-kernel-001"
                }
                req_data = json.dumps(payload).encode()
                req = urllib.request.Request("http://127.0.0.1:9120/api/truth/upsert", data=req_data, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=3).read()
                count += 1
            except:
                pass
    print("✅ 元法则全量同步到记忆网关: %d条" % count)

if __name__ == "__main__":
    main()
