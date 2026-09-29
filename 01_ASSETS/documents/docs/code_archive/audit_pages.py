#!/usr/bin/env python3
"""网页资产全维度评估脚本"""
import os, re, subprocess, json

WWW = "/www/wwwroot/www.huodouai.com"
pages = sorted([f for f in os.listdir(WWW) if f.endswith('.html')])

results = []
problems = []

for page in pages:
    fpath = os.path.join(WWW, page)
    size = os.path.getsize(fpath)
    with open(fpath, encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    issues = []
    
    # 1. HTTP状态
    try:
        r = subprocess.run(f"curl -sk --connect-timeout 3 -o /dev/null -w '%{{http_code}}' https://127.0.0.1/{page}", 
                          shell=True, capture_output=True, text=True, timeout=5)
        code = r.stdout.strip()
        if code != "200":
            issues.append(f"HTTP{code}")
    except:
        issues.append("超时")
    
    # 2. 外部CDN
    if re.search(r'cdn\.jsdelivr\.net|cdnjs\.cloudflare|unpkg\.com|fonts\.googleapis', content):
        issues.append("外部CDN")
    
    # 3. 僵尸链接
    zombie = len(re.findall(r'href="#"|href="javascript:void', content))
    if zombie > 3:
        issues.append(f"{zombie}僵尸链接")
    
    # 4. 空壳页面
    if size < 2000:
        issues.append(f"空壳{size}B")
    
    # 5. 缺少DOCTYPE
    if not content.lstrip().lower().startswith("<!doctype"):
        issues.append("无DOCTYPE")
    
    # 6. 缺少</html>
    if "</html>" not in content.lower():
        issues.append("无</html>")
    
    # 7. 引用不存在的本地资源
    local_refs = re.findall(r'(?:src|href)="(/[^"]+)"', content)
    missing = []
    for ref in local_refs[:5]:  # 只检查前5个避免太慢
        ref_path = ref.split("?")[0].split("#")[0]
        if ref_path.endswith((".html", ".js", ".css", ".jpg", ".png", ".mp4")):
            full = os.path.join(WWW, ref_path.lstrip("/"))
            if not os.path.exists(full):
                missing.append(ref_path)
    if missing:
        issues.append(f"缺资源:{len(missing)}")
    
    results.append({"page": page, "size": size, "issues": issues})
    if issues:
        problems.append({"page": page, "size": size, "issues": issues})

# 输出报告
print(f"{'='*60}")
print(f"网页资产全维度评估报告")
print(f"{'='*60}")
print(f"总页面数: {len(results)}")
print(f"有问题: {len(problems)}")
print(f"正常: {len(results)-len(problems)}")
print(f"正常率: {(len(results)-len(problems))/len(results)*100:.1f}%")
print()

# 按问题类型统计
issue_types = {}
for p in problems:
    for iss in p["issues"]:
        key = iss.split(":")[0].split("(")[0]
        issue_types[key] = issue_types.get(key, 0) + 1

print("问题类型分布:")
for k, v in sorted(issue_types.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}个页面")
print()

print("有问题的页面清单:")
for p in problems:
    print(f"  ⚠️  {p['page']} ({p['size']}B): {', '.join(p['issues'])}")

print()
print("外部CDN依赖页面:")
cdn_pages = [r["page"] for r in results if "外部CDN" in r["issues"]]
for p in cdn_pages:
    print(f"  {p}")

print()
print("空壳页面:")
empty_pages = [r for r in results if any("空壳" in i for i in r["issues"])]
for p in empty_pages:
    print(f"  {p['page']} ({p['size']}B)")
