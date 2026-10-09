#!/usr/bin/env python3
# 从9120提取同源节点最高价值成果（修正版）
import json
import urllib.request

def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

def get_truth(key):
    data = get_json(f"http://127.0.0.1:9120/api/truth/{key}")
    return data.get('truth', data)

print("=" * 60)
print("【从9120提取同源节点最高价值成果】")
print("=" * 60)

# 1. 获取所有key
data = get_json("http://127.0.0.1:9120/api/truths")
all_keys = data.get('truths', [])
print(f"\n总真值数: {len(all_keys)}")

# 2. 按顶层分类统计
categories = {}
for key in all_keys:
    if not key:
        continue
    top = key.split('.')[0] if '.' in key else key
    categories[top] = categories.get(top, 0) + 1

print("\n【真值分类统计 Top 30】")
for k, v in sorted(categories.items(), key=lambda x: -x[1])[:30]:
    print(f"  {k}: {v}条")

# 3. 筛选高价值key
high_value_prefixes = ['MR-', 'META', 'SERVICE', 'PARADIGM', 'RULE', 'SELF', 'ORIGIN',
                       'KD-', 'PROD', 'SOP', 'PROTOCOL', 'DECISION', 'ARCHITECTURE',
                       'ENGINE', 'SYSTEM', 'CORE', 'BASELINE', 'STRATEGY', 'AIOS',
                       'ACHIEVEMENT', 'DRAMA', 'WEBSITE', 'GATEWAY', 'KERNEL',
                       'TRUTH', 'EVOLUTION', 'CLUSTER', 'WORKER', 'API', 'MODEL']

hv_keys = []
for key in all_keys:
    if not key:
        continue
    key_upper = key.upper()
    for prefix in high_value_prefixes:
        if key_upper.startswith(prefix) or prefix in key_upper:
            hv_keys.append(key)
            break

print(f"\n【高价值成果key数】: {len(hv_keys)}")

# 4. 按前缀分组统计
hv_groups = {}
for key in hv_keys:
    top = key.split('.')[0] if '.' in key else key
    hv_groups[top] = hv_groups.get(top, 0) + 1

print("\n【高价值成果分组】")
for k, v in sorted(hv_groups.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}条")

# 5. 提取元法则MR-系列
print("\n" + "=" * 60)
print("【元法则清单 MR-系列】")
print("=" * 60)
mr_keys = sorted([k for k in all_keys if k and k.startswith('MR-')])
print(f"\n元法则总数: {len(mr_keys)}")
for key in mr_keys:
    print(f"  {key}")

# 6. 提取今日成果（20260915）
print("\n" + "=" * 60)
print("【今日最新成果 20260915】")
print("=" * 60)
today_keys = sorted([k for k in all_keys if k and '20260915' in k])
print(f"\n今日成果数: {len(today_keys)}")
for key in today_keys:
    print(f"  {key}")

# 7. 获取Top高价值成果详情
print("\n" + "=" * 60)
print("【Top 20 高价值成果详情】")
print("=" * 60)

# 优先获取元法则和今日成果
priority_keys = mr_keys[-10:] + today_keys[-10:]
seen = set()
count = 0
for key in priority_keys:
    if key in seen:
        continue
    seen.add(key)
    truth = get_truth(key)
    if isinstance(truth, dict):
        value = str(truth.get('truth_value', truth.get('value', '')))[:120]
        node = truth.get('node_id', truth.get('source_node', 'unknown'))
        ver = truth.get('version', 1)
        print(f"\n  [{count+1}] {key}")
        print(f"      节点: {node} | 版本: v{ver}")
        print(f"      内容: {value}")
        count += 1
        if count >= 20:
            break

print("\n" + "=" * 60)
print(f"提取完成: 总{len(all_keys)}条 → 高价值{len(hv_keys)}条 → 元法则{len(mr_keys)}条 → 今日{len(today_keys)}条")
print("=" * 60)
