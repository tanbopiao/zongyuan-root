#!/usr/bin/env python3
# 提取所有元法则详细内容
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

# 获取所有key
data = get_json("http://127.0.0.1:9120/api/truths")
all_keys = data.get('truths', [])

# 筛选所有元法则相关key
metalaw_keys = []
for key in all_keys:
    if not key:
        continue
    key_lower = key.lower()
    if (key.startswith('MR-') or 
        'metalaw' in key_lower or 
        'meta_law' in key_lower or 
        'meta-rule' in key_lower or
        'metarule' in key_lower or
        '元法则' in key):
        metalaw_keys.append(key)

print(f"找到 {len(metalaw_keys)} 条元法则相关key")
print("=" * 70)

# 逐个获取详细内容
metalaws = []
for i, key in enumerate(sorted(metalaw_keys)):
    truth = get_truth(key)
    if isinstance(truth, dict):
        value = truth.get('truth_value', truth.get('value', ''))
        node = truth.get('node_id', truth.get('source_node', 'unknown'))
        version = truth.get('version', 1)
        category = truth.get('category', '')
        metalaws.append({
            'key': key,
            'value': value,
            'node': node,
            'version': version,
            'category': category
        })
        # 解析value中的标题
        title = key
        try:
            if isinstance(value, str) and value.startswith('{'):
                vj = json.loads(value)
                title = vj.get('title', vj.get('law_id', key))
        except:
            pass
        print(f"[{i+1}] {key}")
        print(f"    标题: {title}")
        print(f"    节点: {node} | 版本: v{version} | 分类: {category}")
        print(f"    内容预览: {str(value)[:100]}")
        print()

# 保存完整元法则集合
output = {
    'total': len(metalaws),
    'extracted_at': '2026-09-15T20:45:00+08:00',
    'metalaws': metalaws
}

with open('/tmp/all_metalaws.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("=" * 70)
print(f"✅ 共提取 {len(metalaws)} 条元法则，已保存到 /tmp/all_metalaws.json")

# 统计分类
categories = {}
for m in metalaws:
    cat = m['category'] or 'uncategorized'
    categories[cat] = categories.get(cat, 0) + 1
print("\n【元法则分类统计】")
for k, v in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}条")
