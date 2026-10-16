#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drift_patrol.py · SM-BS 漂移巡检 (Lv8 元认知治理)
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
对核心资产扫描 SHA256 指纹, 与 HASH-LEDGER 已确权账本比对,
检测"文件已变更但未入账本"的漂移项, 输出漂移率(<5% PASS)。
"""
import os, json, time, hashlib, csv

R = '/opt/ZONGYUAN-ROOT'
LEDGER = os.path.join(R, 'HASH-LEDGER.csv')
DID = 'DID-BR-000002'

# 读取已确权账本: relpath -> sha256 (跳过注释/表头)
known = {}
if os.path.exists(LEDGER):
    with open(LEDGER, encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) >= 5 and row[0].strip() and not row[0].startswith('#') and row[0] != 'date':
                known[row[2].strip()] = row[3].strip()

def sha256(p):
    h = hashlib.sha256()
    try:
        with open(p, 'rb') as fh:
            for b in iter(lambda: fh.read(65536), b''):
                h.update(b)
        return h.hexdigest()
    except Exception:
        return None

scopes = ['meta-rules', '00_KERNEL', 'core/kernel', 'config', 'truth']
total = 0
drifted = 0
drift_list = []
scanned_scopes = {}
for s in scopes:
    base = os.path.join(R, s)
    if not os.path.isdir(base):
        continue
    n = 0
    for root, dirs, files in os.walk(base):
        for f in files:
            if not f.endswith(('.md', '.json', '.sh', '.py', '.txt')):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, R)
            sha = sha256(p)
            if sha is None:
                continue
            total += 1
            n += 1
            if rel in known and known[rel] != sha:
                drifted += 1
                drift_list.append(rel)
    scanned_scopes[s] = n

drift_rate = round(drifted / max(total, 1) * 100, 2)
report = {
    'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'did': DID,
    'scanned_total': total,
    'drifted': drifted,
    'drift_rate_pct': drift_rate,
    'threshold_pct': 5.0,
    'scoped_count': scanned_scopes,
    'drift_list': drift_list[:30],
    'status': 'PASS' if drift_rate < 5 else 'WARN',
}
outdir = os.path.join(R, '00_KERNEL', 'evolution', 'drift')
os.makedirs(outdir, exist_ok=True)
out = os.path.join(outdir, 'DRIFT-PATROL-' + time.strftime('%Y%m%d') + '.json')
json.dump(report, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False))
