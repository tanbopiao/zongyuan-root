#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sitemap.xml 自动生成 v1.0 | 枚举全站活跃页 | Ω₀⊂⊙∞⊂Ω"""
import os, glob, time, re

WEB = "/www/wwwroot/huodouai.com"
BASE = "https://www.huodouai.com"
SKIP = ("archive", "legacy", "_archive", "_zongyuan-assets", "zhongshu", "whitepaper", "data:", "_bak")
CORE = ["/", "/products.html", "/pipeline.html", "/portal.html", "/kunlun.html", "/status.html",
        "/architecture.html", "/autonomy.html", "/central-brain.html", "/docs/", "/articles/",
        "/api.html", "/gov/", "/pricing.html", "/research.html"]

def is_archive(rel): return any(k in rel for k in SKIP)

urls = {}
# 核心页
for c in CORE:
    p = WEB + c if not c.endswith("/") else WEB + c.rstrip("/") + "/index.html"
    if os.path.exists(WEB + (c if c != "/" else "index.html")) or os.path.exists(p):
        urls[(BASE + "/" if c == "/" else BASE + c)] = 0.9
# 全站
for f in glob.glob(f"{WEB}/**/*.html", recursive=True):
    rel = os.path.relpath(f, WEB)
    if is_archive(rel) or "_bak" in rel: continue
    u = BASE + "/" + rel.replace("\\", "/").replace("index.html", "").replace("//", "/")
    if u.endswith("/"): u = u[:-1]
    if u == BASE: u = BASE + "/"
    urls.setdefault(u, 0.6)
# docs md
for f in glob.glob(f"{WEB}/docs/*.md"):
    urls[BASE + "/docs/" + os.path.basename(f)] = 0.5

today = time.strftime("%Y-%m-%d")
out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u, pri in sorted(urls.items()):
    out.append(f'  <url><loc>{u}</loc><lastmod>{today}</lastmod><priority>{pri}</priority></url>')
out.append('</urlset>')
open(f"{WEB}/sitemap.xml", "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"sitemap生成: {len(urls)} 条")

def base_url(c):
    if c == "/": return BASE + "/"
    return BASE + c
