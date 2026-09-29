#!/usr/bin/env python3
# 从9120提取同源节点最高价值成果
import json
import urllib.request

def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

# 1. 获取所有真值
print("=" * 60)
print("【从9120提取同源节点最高价值成果】")
print("=" * 60)

data = get_json("http://127.0.0.1:9120/api/truths")
truths = data.get('truths', data) if isinstance(data, dict) else data

if not isinstance(truths, list):
    print(f"数据结构异常: {type(data)}")
    print(str(data)[:300])
    exit()

print(f"\n总真值数: {len(truths)}")

# 2. 按顶层分类统计
categories = {}
for t in truths:
    key = t.get('truth_key', t.get('key', ''))
    top = key.split('.')[0] if '.' in key else key
    categories[top] = categories.get(top, 0) + 1

print("\n【真值分类统计 Top 25】")
for k, v in sorted(categories.items(), key=lambda x: -x[1])[:25]:
    print(f"  {k}: {v}条")

# 3. 提取高价值类别
high_value_prefixes = ['MR-', 'META', 'SERVICE', 'PARADIGM', 'RULE', 'SELF', 'ORIGIN', 
                       'KD-', 'PROD', 'SOP', 'PROTOCOL', 'DECISION', 'ARCHITECTURE',
                       'ENGINE', 'SYSTEM', 'CORE', 'BASELINE', 'STRATEGY', 'AIOS']

print("\n" + "=" * 60)
print("【高价值成果提取】")
print("=" * 60)

high_value = []
for t in truths:
    key = t.get('truth_key', t.get('key', ''))
    value = t.get('truth_value', t.get('value', ''))
    node = t.get('node_id', t.get('source_node', 'unknown'))
    category = t.get('category', '')
    
    for prefix in high_value_prefixes:
        if key.upper().startswith(prefix) or prefix in key.upper():
            high_value.append({
                'key': key,
                'value_preview': str(value)[:100],
                'node': node,
                'category': category,
                'version': t.get('version', 1)
            })
            break

print(f"\n高价值成果总数: {len(high_value)}")

# 按类别分组
hv_by_category = {}
for item in high_value:
    cat = item['category'] or 'uncategorized'
    hv_by_category.setdefault(cat, []).append(item)

print("\n【按类别分组】")
for cat, items in sorted(hv_by_category.items(), key=lambda x: -len(x[1])):
    print(f"\n  [{cat}] ({len(items)}条)")
    for item in items[:5]:  # 每类显示前5条
        print(f"    - {item['key']} (节点: {item['node']})")
    if len(items) > 5:
        print(f"    ... 还有{len(items)-5}条")

# 4. 提取元法则（MR-开头）
print("\n" + "=" * 60)
print("【元法则清单 MR-系列】")
print("=" * 60)

meta_laws = [t for t in truths if t.get('truth_key', '').startswith('MR-')]
print(f"\n元法则总数: {len(meta_laws)}")
for t in sorted(meta_laws, key=lambda x: x.get('truth_key', '')):
    key = t.get('truth_key', '')
    value = str(t.get('truth_value', ''))[:80]
    print(f"  {key}: {value}")

# 5. 提取最近的成果（按版本或key判断）
print("\n" + "=" * 60)
print("【最新成果（含20260915日期的）】")
print("=" * 60)

recent = [t for t in truths if '20260915' in t.get('truth_key', '')]
print(f"\n今日成果数: {len(recent)}")
for t in sorted(recent, key=lambda x: x.get('truth_key', '')):
    key = t.get('truth_key', '')
    value = str(t.get('truth_value', ''))[:80]
    print(f"  {key}")
    print(f"    → {value}")
