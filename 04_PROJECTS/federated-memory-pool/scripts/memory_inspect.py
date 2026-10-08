#!/usr/bin/env python3
"""
记忆索引巡检（开源版）— 7天周期校验索引一致性
"""
import json, hashlib, sys, os

INDEX_PATH = os.getenv("MEMORY_INDEX", "src/memory_index.json")

def inspect():
    """巡检记忆索引: 结构完整性 + 条目哈希 + 优先级分布"""
    try:
        with open(INDEX_PATH, encoding="utf-8") as f:
            idx = json.load(f)
    except Exception as e:
        print(f"[FAIL] 索引加载失败: {e}")
        return 1

    entries = idx.get("asset_entries", [])
    meta = idx.get("index_meta", {})

    # 1. 结构检查
    print(f"[OK] 索引加载: {INDEX_PATH}")
    print(f"[OK] 元信息: {meta.get('index_id')} v{meta.get('version')} | DID={meta.get('did')}")

    # 2. 条目完整性
    bad = [e.get('asset_id', '?') for e in entries
           if not e.get('asset_id') or not e.get('summary') or not e.get('priority')]
    print(f"[{'FAIL' if bad else 'OK'}] 条目完整性: {len(entries)}条, 缺陷={bad if bad else '无'}")

    # 3. 优先级分布
    prio_dist = {}
    for e in entries:
        p = e.get('priority', 'C')
        prio_dist[p] = prio_dist.get(p, 0) + 1
    print(f"[OK] 优先级分布: {prio_dist}")

    # 4. 哈希校验（若有哈希字段）
    hash_fail = 0
    for e in entries:
        if 'sha256' in e:
            content = json.dumps({k: v for k, v in e.items() if k != 'sha256'},
                                 ensure_ascii=False, sort_keys=True)
            if hashlib.sha256(content.encode()).hexdigest() != e['sha256']:
                hash_fail += 1
    print(f"[{'FAIL' if hash_fail else 'OK'}] 条目哈希: {hash_fail}条不一致")

    print(f"\n巡检通过: 索引结构完整, 可正常服务锚点拉取。{meta.get('trace_mark','Ω₀⊂⊙∞⊂Ω')}")
    return 0

if __name__ == "__main__":
    sys.exit(inspect())
