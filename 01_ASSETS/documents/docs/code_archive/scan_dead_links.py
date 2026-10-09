#!/usr/bin/env python3
"""扫描官网死链"""
import re, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open("/www/wwwroot/www.huodouai.com/index.html") as f:
    html = f.read()

# 提取所有内部链接
links = re.findall(r'href=["\'](/[^"\']+)["\']', html)
links = list(set(links))
links.sort()

print("共发现 %d 个内部链接" % len(links))
dead = []
alive = []
for link in links:
    if link.startswith("//") or link.startswith("http"):
        continue
    url = "https://www.huodouai.com" + link
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=8, context=ctx)
        code = resp.getcode()
        if code == 200:
            alive.append(link)
        else:
            dead.append((link, code))
    except Exception as e:
        dead.append((link, str(e)[:40]))

print("\n✅ 正常: %d 个" % len(alive))
print("❌ 死链: %d 个" % len(dead))
for link, err in dead:
    print("  %s -> %s" % (link, err))
