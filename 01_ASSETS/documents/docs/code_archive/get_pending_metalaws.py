#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""获取33条待审批元法则的详细内容，整理成审批材料"""

import json
import urllib.request

def get_truth(key):
    try:
        resp = urllib.request.urlopen(f'http://127.0.0.1:9120/api/truth/{key}', timeout=5)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

# 获取所有待审批key
resp = urllib.request.urlopen("http://127.0.0.1:9120/api/truths?limit=2000", timeout=10)
data = json.loads(resp.read().decode())
keys = data.get("truths", [])
pending_keys = sorted([k for k in keys if isinstance(k, str) and "APPROVAL_PENDING" in k])

print(f"共 {len(pending_keys)} 条待审批元法则")
print("=" * 70)

# 分类
categories = {
    "核心战略元法则": [],
    "短剧生产元法则": [],
    "性能优化元法则": [],
    "其他元法则": []
}

results = []
for key in pending_keys:
    detail = get_truth(key)
    value = detail.get("value", "")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except:
            pass
    
    # 提取名称和描述
    name = key
    desc = ""
    if isinstance(value, dict):
        name = value.get("law_name", value.get("name", key))
        desc = value.get("core_insight", value.get("description", value.get("content", "")))
        if not desc:
            desc = str(value)[:200]
    elif isinstance(value, str):
        desc = value[:200]
    
    # 分类
    if any(kw in key for kw in ["MR-020", "MR-025", "MR-026", "DUAL_MODEL", "COMMERCIAL", "META_HENGYI"]):
        categories["核心战略元法则"].append((key, name, desc))
    elif any(kw in key for kw in ["MR-027", "MR-028", "MR-029", "QUALITY", "CINEMATIC", "DRAM"]):
        categories["短剧生产元法则"].append((key, name, desc))
    elif any(kw in key for kw in ["PERF", "META-PERF"]):
        categories["性能优化元法则"].append((key, name, desc))
    else:
        categories["其他元法则"].append((key, name, desc))
    
    results.append({"key": key, "name": name, "desc": desc[:300]})

# 输出分类结果
for cat, items in categories.items():
    if items:
        print(f"\n【{cat}】({len(items)}条)")
        print("-" * 50)
        for key, name, desc in items:
            print(f"  • {name}")
            print(f"    Key: {key}")
            if desc:
                print(f"    摘要: {desc[:100]}...")
            print()

# 保存完整结果到文件
with open("/tmp/pending_metalaws.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n完整结果已保存到 /tmp/pending_metalaws.json")
print(f"总计: {len(results)}条待审批元法则")
