#!/bin/bash
# 企业知识中枢 · 跨部门检索网关 v1.0
# 路径全部参数化；DID 同源校验通过后方可 stats/search/export。
# 用法:
#   knowledge_gateway.sh --ledger <账本.json> --did <YOUR_DID> [--stats|--search <关键词>|--export]
set -u

LEDGER=""; CALLER_DID=""; CMD=""; KW=""
while [ $# -gt 0 ]; do
  case "$1" in
    --ledger) LEDGER="$2"; shift 2 ;;
    --did)    CALLER_DID="$2"; shift 2 ;;
    --stats)  CMD="stats"; shift ;;
    --search) CMD="search"; KW="${2:?用法: --search <关键词>}"; shift 2 ;;
    --export) CMD="export"; shift ;;
    *) echo "用法: $0 --ledger <账本.json> --did <DID> [--stats|--search <关键词>|--export]"; exit 1 ;;
  esac
done

[ -n "$LEDGER" ] || { echo "ERR: 缺少 --ledger"; exit 1; }
[ -f "$LEDGER" ] || { echo "ERR: 索引账本缺失: $LEDGER"; exit 1; }
[ -n "$CALLER_DID" ] || { echo "ERR: 缺少 --did"; exit 1; }

# OP-04 同源校验：账本归属 DID
LEDGER_DID=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('did',''))" "$LEDGER")
if [ "$CALLER_DID" != "$LEDGER_DID" ]; then
  echo "拒绝访问: 调用方 DID=$CALLER_DID 与账本归属 DID=$LEDGER_DID 不一致"
  exit 2
fi
echo "=== 企业知识中枢检索网关 v1.0 ==="
echo "同源校验通过: $CALLER_DID"

case "$CMD" in
  stats)
    python3 - "$LEDGER" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
es = d.get('entries', [])
depts = sorted({e.get('department','') for e in es})
conf = sum(1 for e in es if e.get('conflict'))
print(f"索引总量: {len(es)}")
print(f"部门: {depts}")
print(f"冲突条目: {conf}")
print(f"最近更新: {d.get('updated','')}")
PY
    ;;
  search)
    python3 - "$LEDGER" "$KW" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); kw = sys.argv[2].lower()
hits = 0
for e in d.get('entries', []):
    blob = ' '.join(e.get('tags', [])) + ' ' + e.get('path','') + ' ' + e.get('title','')
    if kw in blob.lower():
        hits += 1
        print(f"{e['entry_id']} | {e.get('department','')} | {e['path']} | {e['sha256'][:16]} | {e['timestamp']}")
print(f"命中: {hits} 条（仅返回元信息，原文按需受控拉取）")
PY
    ;;
  export)
    python3 - "$LEDGER" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
summary = {
    'ledger_id': d.get('ledger_id'),
    'updated': d.get('updated'),
    'entry_count': len(d.get('entries', [])),
    'departments': sorted({e.get('department','') for e in d.get('entries',[])}),
    'conflict_count': sum(1 for e in d.get('entries',[]) if e.get('conflict')),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
print('[Export] 索引池摘要导出完成（原文本体不集中迁移）')
PY
    ;;
  *)
    echo "用法: $0 --ledger <账本.json> --did <DID> [--stats|--search <关键词>|--export]" ;;
esac
