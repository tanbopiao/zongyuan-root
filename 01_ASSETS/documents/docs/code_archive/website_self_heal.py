#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
官网稳态自愈闸门 website_self_heal.py
V1.0 | 火斗云智 AIOS | 2026-09-11
作用：防止官网因资产无限叠加导致"打不开/超载"，自动检测+降载+告警+报告。
配合 metalaw.STEADY-EVOLUTION-BUDGET 稳态进化元规则。

核心逻辑：
1. 检测：统计官网 HTML 资产数、assets 目录大小、关键健康端点状态
2. 分级：S0(正常) / S1(预警) / S2(降载) / S3(熔断)
3. 自愈：超阈值自动归档旧资产到 _archive/，保持首页可访问
4. 告警：写记忆网关告警真值 + 打印可推送飞书内容
5. 报告：输出自愈巡检 JSON
"""
import json, os, subprocess, time, hashlib, sys

# ========== 配置（可调，符合稳态进化预算） ==========
WEB_ROOT   = "/www/wwwroot/www.huodouai.com"
ARCHIVE_DIR = os.path.join(WEB_ROOT, "_archive")     # 降载归档区
HTML_LIMIT_WARN  = 60     # HTML 数预警阈值
HTML_LIMIT_HEAL  = 90     # HTML 数强制降载阈值
ASSETS_SIZE_WARN = 80     # assets 大小预警阈值(MB)
ASSETS_SIZE_HEAL = 150    # assets 大小强制降载阈值(MB)
HEALTH_ENDPOINTS = [
    ("官网首页", "https://www.huodouai.com/"),
    ("记忆网关", "http://127.0.0.1:9120/health"),
    ("运维平台", "http://127.0.0.1:8080/api/health"),
]
# 独立服务端点：仅记录不参与官网自愈分级（由各自服务自身监控）
OBSERVE_ENDPOINTS = [
    ("独立健康8000", "http://127.0.0.1:8000/health"),
]
GW = "http://127.0.0.1:9120"

# ========== 1. 检测 ==========
def count_html(root):
    return sum(1 for _,_,fs in os.walk(root) if "_archive" not in _ for _ in [0] for f in fs if f.endswith(".html"))

def dir_size_mb(path):
    tot = 0
    for dirpath,_,files in os.walk(path):
        if "_archive" in dirpath: continue
        for f in files:
            try: tot += os.path.getsize(os.path.join(dirpath,f))
            except: pass
    return round(tot/1024/1024, 1)

def check_health():
    results = {}
    for name, url in HEALTH_ENDPOINTS + OBSERVE_ENDPOINTS:
        try:
            # 公网用 curl -k 跳过证书校验，内网直连
            cmd = ["curl","-s","-o","/dev/null","-w","%{http_code}","--max-time","6"]
            if url.startswith("https://www."): cmd += ["-k"]
            cmd.append(url)
            code = subprocess.run(cmd, capture_output=True, text=True, timeout=8).stdout.strip()
            results[name] = code
        except Exception as e:
            results[name] = "ERR:%s" % str(e)[:30]
    return results

# ========== 2. 分级 ==========
def grade(html_n, size_mb, health):
    level, reasons = "S0", []
    # 仅核心端点参与分级（独立服务端点 OBSERVE_ENDPOINTS 排除）
    core_health = {k:v for k,v in health.items() if k not in dict(OBSERVE_ENDPOINTS)}
    if html_n >= HTML_LIMIT_HEAL or size_mb >= ASSETS_SIZE_HEAL:
        level, reasons = "S3", ["HTML=%d>=%d或assets=%dMB>=%dMB(强制降载)" % (html_n,HTML_LIMIT_HEAL,size_mb,ASSETS_SIZE_HEAL)]
    elif html_n >= HTML_LIMIT_WARN or size_mb >= ASSETS_SIZE_WARN:
        level, reasons = "S2", ["HTML=%d>=%d或assets=%dMB>=%dMB(预警降载)" % (html_n,HTML_LIMIT_WARN,size_mb,ASSETS_SIZE_WARN)]
    elif any(v=="000" or v.startswith("ERR") for v in core_health.values()):
        level, reasons = "S1", ["核心端点异常: %s" % {k:v for k,v in core_health.items() if v=="000" or v.startswith("ERR")}]
    else:
        level, reasons = "S0", ["体系稳态"]
    return level, reasons

# ========== 3. 降载自愈 ==========
def self_heal(html_n, size_mb, level):
    if level not in ("S2","S3"): return 0
    moved = 0
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    # 归档最旧的视觉资产目录（visual/ 下的 .html），保留最新
    visual = os.path.join(WEB_ROOT, "assets", "visual")
    if os.path.isdir(visual):
        htmls = sorted([f for f in os.listdir(visual) if f.endswith(".html")],
                       key=lambda f: os.path.getmtime(os.path.join(visual,f)))
        # S2 保留最近 20 个，S3 保留最近 10 个，归档更旧的
        keep = 10 if level == "S3" else 20
        to_move = htmls[:-keep]
        for f in to_move:
            src, dst = os.path.join(visual,f), os.path.join(ARCHIVE_DIR,f)
            try:
                os.rename(src, dst); moved += 1
            except Exception as e:
                print("  !! 归档失败 %s: %s" % (f, str(e)[:60]))
    return moved

# ========== 4. 告警 & 报告 ==========
def gen_report(html_n, size_mb, health, level, reasons, moved):
    return {
        "snap_id": "SELF-HEAL-" + time.strftime("%Y%m%d-%H%M%S"),
        "did": "DID-BR-000002",
        "level": level, "reasons": reasons,
        "metrics": {"html_count": html_n, "assets_size_mb": size_mb,
                    "html_limit_warn": HTML_LIMIT_WARN, "html_limit_heal": HTML_LIMIT_HEAL,
                    "assets_size_warn_mb": ASSETS_SIZE_WARN, "assets_size_heal_mb": ASSETS_SIZE_HEAL},
        "health": health, "self_healed_moved": moved,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    }

def push_gateway(report):
    import urllib.request as ur
    try:
        payload = {"key":"status.website-self-heal-"+time.strftime("%Y%m%d"),
                   "value":json.dumps(report,ensure_ascii=False),
                   "category":"status","node_id":"cloud-main-kernel-001"}
        req = ur.Request(
            GW+"/api/truth/upsert", data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json"}, method="POST")
        ur.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print("  !! 告警写网关失败:", str(e)[:80]); return False

# ========== 主流程 ==========
def main():
    html_n = count_html(WEB_ROOT)
    size_mb = dir_size_mb(os.path.join(WEB_ROOT,"assets"))
    health = check_health()
    level, reasons = grade(html_n, size_mb, health)
    moved = self_heal(html_n, size_mb, level)
    report = gen_report(html_n, size_mb, health, level, reasons, moved)
    # 写网关
    push_gateway(report)
    # 输出报告
    print(json.dumps(report, ensure_ascii=False, indent=1))
    # S2/S3 级附告警文案（可推送飞书）
    if level in ("S2","S3"):
        print("\n[ALERT] 官网自愈告警 Level=%s 原因=%s 已归档=%d个" % (level, ";".join(reasons), moved))

if __name__ == "__main__":
    main()
