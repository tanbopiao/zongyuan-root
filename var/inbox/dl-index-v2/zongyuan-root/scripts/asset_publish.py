#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高价值资产发布管道（META-ASSET-VALUE-DISPLAY-001）
用法:
  python3 asset_publish.py --list                      # 列出本地资产台账
  python3 asset_publish.py --publish <html> <name>     # 发布资产HTML→官网（+导航+上报）
  python3 asset_publish.py --index                     # 更新官网资产总览页（asset-index.html）
通道: SSH zongyuan-cloud → /www/wwwroot/huodouai.com/（www.huodouai.com 文档根）
"""
import json, os, sys, io, subprocess, datetime

ZR = "/home/user/ZONGYUAN-ROOT"
ASSETS = f"{ZR}/var/assets"
LEDGER = f"{ASSETS}/asset-ledger.jsonl"
REMOTE_ROOT = "/www/wwwroot/huodouai.com"
BASE_URL = "https://www.huodouai.com"
FINGERPRINT = "9b64a9c3c2475cf695ea6e2d"

def ssh(cmd):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", "zongyuan-cloud", cmd],
                          capture_output=True, text=True, timeout=60)

def ts_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")

def list_assets():
    assets = []
    if os.path.exists(LEDGER):
        for line in io.open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                try: assets.append(json.loads(line))
                except Exception: pass
    print(f"[资产台账] {len(assets)} 项对外数字化资产：")
    for a in assets:
        print(f"  {a.get('asset_id','')} ｜ {a.get('name','')} ｜ {BASE_URL}/{a.get('file','')} ｜ 状态={a.get('status','')}")
    return assets

def remote_immutable(remote_path):
    """检查远程文件是否 immutable 锁档（只读探测，不解锁）"""
    r = ssh(f"lsattr {remote_path} 2>/dev/null | awk '{{print $1}}'")
    return "i" in (r.stdout or "")

def publish(html_path, name, remote_file=None):
    os.makedirs(ASSETS, exist_ok=True)
    file = remote_file or (name.lower().replace(" ", "-").replace("·", "") + ".html")
    asset_id = f"AVD-{ts_now()}"
    # 0) 锁档边界：远程同名文件已 immutable 锁档 → 禁止覆盖（不改已固化标准资产）
    if remote_immutable(f"{REMOTE_ROOT}/{file}"):
        print(f"[发布] 拒绝：{file} 已锁定（immutable 标准资产）。不改已锁档文件；请用新文件名发布新资产，或经人工审批解锁后整改。")
        return None
    # 1) 官网部署（解锁→覆盖→重锁 纪律）
    ssh(f"chattr -i {REMOTE_ROOT}/{file} 2>/dev/null; true")
    r = subprocess.run(["scp", "-o", "BatchMode=yes", html_path, f"zongyuan-cloud:{REMOTE_ROOT}/{file}"],
                       capture_output=True, text=True, timeout=60)
    ssh(f"chattr +i {REMOTE_ROOT}/{file} 2>/dev/null; true")
    if r.returncode != 0:
        print(f"[发布] scp 失败: {r.stderr[-200:]}"); return
    # 2) 线上验证
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"{BASE_URL}/{file}", timeout=20)
        ok = resp.status == 200
    except Exception as e:
        ok = False; print(f"[验证] {e}")
    if not ok:
        print(f"[发布] 线上验证失败，需人工介入"); return
    # 3) 登记台账
    rec = {"asset_id": asset_id, "name": name, "file": file, "url": f"{BASE_URL}/{file}",
           "published_at": ts_now(), "status": "online", "fingerprint": FINGERPRINT}
    with io.open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[发布] {name} → {rec['url']}（HTTP 200 ✓，已登记台账）")
    return rec

def build_index():
    assets = list_assets()
    # 官网已有资产（手工维护 + 台账）
    known = [
        {"name": "技术白皮书 · 元极恒一自治内核", "url": "/whitepaper.html", "desc": "体系架构/机制/治理/进化全景", "status": "online"},
        {"name": "昆仑洞天 · 国风AI视觉资产库", "url": "/kunlun.html", "desc": "9角色586+关键帧 · 9:16竖屏", "status": "online"},
        {"name": "作品画廊", "url": "/gallery/rose/", "desc": "角色视觉资产展示", "status": "online"},
        {"name": "API 文档", "url": "/api-docs.html", "desc": "体系接口与能力文档", "status": "online"},
        {"name": "数字资产总览", "url": "/zongyuan-digital-asset.html", "desc": "ZONGYUAN 自治内核数字资产索引（aios 站）", "status": "online"},
    ]
    for a in assets:
        known.append({"name": a["name"], "url": "/" + a["file"], "desc": f"资产ID {a['asset_id']}", "status": a["status"]})
    rows = "".join(f"""<tr><td><a href="{x['url']}" style="color:#d4af37;text-decoration:none;font-weight:600">{x['name']}</a></td><td>{x['desc']}</td><td><span style="color:{'#57c785' if x['status']=='online' else '#c9a04e'}">{x['status']}</span></td></tr>""" for x in known)
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>数字化资产总览 · 火斗云智AI</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta name="theme-color" content="#0a0a0f">
<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap">
<style>
body{{margin:0;background:#0a0a0f;color:#e8eef7;font-family:'Noto Sans SC',system-ui,sans-serif;line-height:1.7}}
.wrap{{max-width:960px;margin:0 auto;padding:48px 24px}}
h1{{font-size:clamp(24px,4vw,36px);font-weight:900;margin-bottom:8px}}
.sub{{color:#8fa3c0;font-size:14px;margin-bottom:32px}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:14px;background:#131c30;border-radius:12px;overflow:hidden}}
colgroup col:nth-child(1){{width:32%}}colgroup col:nth-child(2){{width:48%}}colgroup col:nth-child(3){{width:20%}}
th{{text-align:left;padding:12px 16px;color:#8fa3c0;font-weight:500;border-bottom:1px solid #22304f;font-size:12px}}
td{{padding:12px 16px;border-bottom:1px solid rgba(34,48,79,.4)}}
a{{text-decoration:none}}.back{{display:inline-block;margin-bottom:20px;color:#8fa3c0;font-size:13px;border:1px solid #22304f;padding:4px 12px;border-radius:16px}}
.badge{{display:inline-block;font-size:11px;color:#f4e4bc;border:1px solid rgba(212,175,55,.4);background:rgba(212,175,55,.08);border-radius:12px;padding:2px 10px;margin-bottom:16px}}
</style></head><body><div class="wrap">
<a class="back" href="/">← 返回官网首页</a>
<span class="badge">DIGITAL ASSET INDEX · 对外数字化资产</span>
<h1>数字化资产总览</h1>
<div class="sub">元极恒一自治内核 · 持续提炼可视化 · 官网统一陈列 ｜ 高价值成果 → 数字化资产 → 价值显示</div>
<table><colgroup><col style="width:32%"><col style="width:48%"><col style="width:20%"></colgroup>
<thead><tr><th>资产</th><th>说明</th><th>状态</th></tr></thead><tbody>{rows}</tbody></table>
<div style="margin-top:36px;color:#5f7394;font-size:12px">火斗云智AI · ZONGYUAN 自治内核 ｜ Ω₀⊂⊙∞⊂Ω ｜ 资产总览页自动生成（asset_publish.py --index）</div>
</div></body></html>"""
    return html

def deploy_index():
    if remote_immutable(f"{REMOTE_ROOT}/asset-index.html"):
        print("[索引] 拒绝：asset-index.html 已锁定（immutable 标准资产）。总览页为已固化资产，禁止覆盖；需人工审批后整改。")
        return None
    html = build_index()
    local = "/tmp/asset-index.html"
    with io.open(local, "w", encoding="utf-8") as f:
        f.write(html)
    ssh(f"chattr -i {REMOTE_ROOT}/asset-index.html 2>/dev/null; true")
    r = subprocess.run(["scp", "-o", "BatchMode=yes", local, f"zongyuan-cloud:{REMOTE_ROOT}/asset-index.html"],
                       capture_output=True, text=True, timeout=60)
    ssh(f"chattr +i {REMOTE_ROOT}/asset-index.html 2>/dev/null; true")
    if r.returncode != 0:
        print(f"[索引] scp 失败: {r.stderr[-200:]}"); return
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"{BASE_URL}/asset-index.html", timeout=20)
        print(f"[索引] 资产总览页已上线：{BASE_URL}/asset-index.html（HTTP {resp.status}）")
    except Exception as e:
        print(f"[索引] 验证异常: {e}")
    return "asset-index.html"

if __name__ == "__main__":
    if "--list" in sys.argv:
        list_assets()
    elif "--publish" in sys.argv:
        i = sys.argv.index("--publish")
        publish(sys.argv[i + 1], sys.argv[i + 2] if len(sys.argv) > i + 2 else os.path.basename(sys.argv[i + 1]),
                sys.argv[i + 3] if len(sys.argv) > i + 3 else None)
    elif "--index" in sys.argv:
        deploy_index()
    else:
        print(__doc__)
