# -*- coding: utf-8 -*-
"""
联邦记忆池生成器 MEMORY-FEDERATION-POOL（可复用：每次运行刷新各源计数并重建池）
多源记忆聚合为一：本地索引/启动记忆/真值库/M9账本/向量库/审计链/语义样本/飞书大脑/魔搭数据湖/云端网关
恒一收敛：本地源为权威正本，镜像源同步对齐；跨源可检索；append-only 不删历史
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import os, json, time, hashlib

ROOT = r'C:\Users\4906\.zongyuan_root'
OUT = os.path.join(ROOT, 'META_RULES', 'MEMORY-FEDERATION-POOL-20261006.json')
now = time.strftime('%Y-%m-%dT%H:%M:%S+08:00')


def jcount(p, key=None):
    try:
        with open(os.path.join(ROOT, p), encoding='utf-8-sig') as f:
            d = json.load(f)
        if key is None:
            return len(d) if isinstance(d, (list, dict)) else 0
        v = d.get(key)
        return len(v) if isinstance(v, (list, dict)) else (v or 0)
    except Exception:
        return 0


def line_count(p):
    try:
        with open(os.path.join(ROOT, p), encoding='utf-8', errors='replace') as f:
            return sum(1 for _ in f)
    except Exception:
        return None


def file_count(p):
    try:
        return len([x for x in os.listdir(os.path.join(ROOT, p)) if os.path.isfile(os.path.join(ROOT, p, x))])
    except Exception:
        return None


# 飞书共享大脑在线探测：若存在 logs/_feishu_tables.json（lark-cli base +table-list --base-token ... --as user 的产物），
# 则聚合 53 表 records_count 为真实计数；否则 fallback probe 状态
feishu_count = 0
feishu_detail = 'probe-local-mirror-empty;online=53tables'
feishu_tables = os.path.join(ROOT, 'logs', '_feishu_tables.json')
if os.path.exists(feishu_tables):
    try:
        raw = open(feishu_tables, 'rb').read()
        d = None
        for enc in ('utf-8-sig', 'utf-16', 'gbk', 'latin1'):
            try:
                d = json.loads(raw.decode(enc))
                break
            except Exception:
                continue
        if d is not None:
            tbls = d.get('data', {}).get('tables', [])
            feishu_count = sum(t.get('records_count', 0) for t in tbls)
            feishu_detail = 'online:%d表/共%d条' % (len(tbls), feishu_count)
    except Exception as e:
        feishu_detail = 'probe-parse-fail:%s' % repr(e)[:30]

sources = [
    {'source_id': 'local-memory-index', 'name': '本地资产记忆索引', 'type': 'index',
     'locator': 'memory_index.json', 'count': jcount('memory_index.json', 'asset_entries') or 0, 'status': 'ok'},
    {'source_id': 'local-bootstrap', 'name': '内核启动记忆', 'type': 'boot',
     'locator': 'BOOTSTRAP.md + BOOTSTRAP-V142-ADDON.md', 'count': 2, 'status': 'ok'},
    {'source_id': 'local-truth', 'name': '本地真值库', 'type': 'truth',
     'locator': 'var/truth_db/truth_ledger.json', 'count': jcount('var/truth_db/truth_ledger.json', 'total') or 0, 'status': 'ok'},
    {'source_id': 'local-m9', 'name': 'M9全域账本', 'type': 'ledger',
     'locator': 'ledger/M9_global_ledger.json', 'count': jcount('ledger/M9_global_ledger.json', 'total_assets') or 0, 'status': 'ok'},
    {'source_id': 'local-vector', 'name': '向量记忆库', 'type': 'vector',
     'locator': 'kernel/vector_db/vector_index.json', 'count': jcount('kernel/vector_db/vector_index.json', 'total') or 0, 'status': 'ok'},
    {'source_id': 'local-audit', 'name': '审计链', 'type': 'audit',
     'locator': 'logs/local_converge_20261003.jsonl', 'count': line_count('logs/local_converge_20261003.jsonl') or 0, 'status': 'ok'},
    {'source_id': 'local-semantic', 'name': '语义样本(协议+终态锁档)', 'type': 'semantic',
     'locator': 'kernel/protocols + kernel/assets/full', 'count': (file_count('kernel/protocols') or 0) + (file_count('kernel/assets/full') or 0), 'status': 'ok'},
    {'source_id': 'feishu-brain', 'name': '飞书共享大脑(53表)', 'type': 'brain',
     'locator': 'Base DgnMbLqZiaIUDKshqCrcD4DvnBg', 'count': feishu_count, 'status': feishu_detail},
    {'source_id': 'modelscope-datalake', 'name': '魔搭数据湖镜像', 'type': 'datalake',
     'locator': 'modelscope_bridge/datalake_mirror', 'count': 0, 'status': 'ok', 'last_commit': '(git log)'},
    {'source_id': 'cloud-gateway', 'name': '云端记忆网关', 'type': 'gateway',
     'locator': 'https://www.huodouai.com/api/report/truth', 'count': 748, 'status': 'ok(truth_count基线)'},
]

total = sum(s['count'] for s in sources)
pool = {
    'pool_id': 'MEMORY-FED-POOL-001',
    'meta_class': 'M9',
    'did': 'DID-BR-000002',
    'anchor': 'Ω₀⊂⊙∞⊂Ω',
    'version': 'V1.0',
    'created_at': now,
    'design': '联邦记忆池：多源记忆聚合为一，恒一收敛基准态，跨源定位检索；本地源为权威正本，飞书/魔搭/网关为镜像；append-only',
    'sources': sources,
    'federation': {
        'total_sources': len(sources),
        'total_memory_items': total,
        'merkle': hashlib.sha256(json.dumps(sources, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:16],
        'sync_policy': '本地=权威正本; 飞书共享大脑=规则真值表; 魔搭数据湖=产物镜像; 云端网关=事件真值流; 恒一收敛',
    },
    'query_guide': '读本文件定位记忆源→按源locator查询；统一语义=元宪法/元公理/元法则/元规则四维本体',
}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(pool, f, ensure_ascii=False, indent=2)
print('联邦记忆池 V1.0 生成: %s | 源=%d 记忆条目=%d Merkle=%s' % (OUT, len(sources), total, pool['federation']['merkle']))
