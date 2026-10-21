#!/bin/bash
# ZONGYUAN-ROOT COS 对账存储：对象存储层（bucket 结构）+ 账本↔实际对账引擎
# 对账口径：HASH-LEDGER.csv 登记资产（应收） vs 内核实际文件（实收）
# 产出：对账报告 + 差异清单（对象存储归档）+ 真值快照镜像
# 状态：consistent / has_gaps（差异明细）
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
COS="$ROOT/var/cos"
mkdir -p "$COS/reconcile" "$COS/snapshot" "$COS/assets"

python3 - "$COS" "$ROOT" <<'EOF'
import json, time, hashlib, csv, sys
from pathlib import Path
COS, ROOT = sys.argv[1:3]
TS = time.strftime('%Y-%m-%dT%H:%M:%S%z')
ledger = Path(ROOT) / 'HASH-LEDGER.csv'

def sha(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(65536),b''): h.update(c)
    return h.hexdigest()

# 1) 应收：账本登记（仅 FRAMEWORK/IDENTITY 类型行；同一 path 取最新登记）
expected = {}
rows = list(csv.reader(open(ledger, encoding='utf-8')))
for r in rows[1:]:
    if len(r) < 5: continue
    if r[0] not in ('FRAMEWORK','IDENTITY'): continue   # 资产账行（AUTO-IMG-*）不参与文件对账
    p = r[1].lstrip('/')
    expected[p] = r[3]

# 运行时豁免（自变数据与基准，不参与账实核对）
RUNTIME = ('var/workers/','var/heartbeat/','var/poll/','var/network/','var/truth/',
           'var/cos/','var/system/','var/tamper-test/')
def exempt(rel):
    if rel == 'HASH-LEDGER.csv': return True    # 对账基准自引用豁免
    if rel == 'var/kek.env': return True
    return any(rel.startswith(x) for x in RUNTIME)

# 2) 实收：内核实际文件（排除日志/KEK/运行时）
actual = {}
for p in sorted(Path(ROOT).rglob('*')):
    if not p.is_file(): continue
    rel = p.relative_to(ROOT).as_posix()
    if rel.startswith('logs/') or '/logs/' in rel: continue
    if exempt(rel): continue
    actual[rel] = sha(p)

# 应收侧也剔除豁免项（历史批次曾登记运行数据 → 不视为缺失）
for p in [p for p in expected if exempt(p)]:
    del expected[p]

# 3) 核对
missing = [p for p in expected if p not in actual]                      # 账有实无
hash_mismatch = {p: (expected[p][:12], actual[p][:12]) for p in expected if p in actual and expected[p] != actual[p]}
unregistered = [p for p in actual if p not in expected]                 # 实有账无（运行数据，非缺陷）
ok = [p for p in expected if p in actual and expected[p] == actual[p]]

report = {
  "reconcile_ts": TS, "node":"NODE-DEV-DOUBAO-WORK-001", "did":"DID-BR-000002",
  "status": "consistent" if not missing and not hash_mismatch else "has_gaps",
  "counts": {"ledger": len(expected), "actual": len(actual), "matched": len(ok),
             "missing": len(missing), "hash_mismatch": len(hash_mismatch), "unregistered_runtime": len(unregistered)},
  "missing": missing,
  "hash_mismatch": hash_mismatch,
  "unregistered_runtime_sample": unregistered[:20],
  "anchor": "Ω₀⊂⊙∞⊂Ω"
}
out = Path(COS) / 'reconcile' / f"reconcile-report-{time.strftime('%Y%m%d-%H%M%S')}.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"[reconcile] 账本 {len(expected)} / 实际 {len(actual)} / 相符 {len(ok)} / 缺失 {len(missing)} / 哈希不符 {len(hash_mismatch)}")
print(f"[reconcile] 状态: {report['status']} | 报告: {out}")
print(f"[reconcile] 运行数据未登记（正常）: {len(unregistered)} 个")

# 4) 快照镜像：最新锁档回执/身份/元内核清单 复制入 snapshot bucket（copy 不保留只读权限，避免覆盖失败）
import shutil, os
for name in ['meta-rules/worker-hardening.json']:
    src = Path(ROOT) / name
    if src.exists():
        dst = Path(COS) / 'snapshot' / src.name
        if dst.exists(): os.chmod(dst, 0o644)   # 解除历史只读，允许覆盖
        shutil.copy(src, dst)
locks = sorted(Path(ROOT,'卷宗').glob('GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-*.json'))
if locks:
    shutil.copy2(locks[-1], Path(COS) / 'snapshot' / locks[-1].name)
print(f"[cos] 快照镜像: snapshot bucket 最新锁档回执 + 元内核清单已归档")
EOF
