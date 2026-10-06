#!/bin/bash
# 联邦记忆池跨节点索引查询网关 L3
# 同源协议DID校验，非DID拒绝访问
CONTRACT="/home/user/ZONGYUAN-ROOT/meta-rules/federal-memory-contract.json"
INDEX_LEDGER="/home/user/ZONGYUAN-ROOT/truth/federal-index/index_ledger.json"
DID="DID-BR-000002"

echo "=== 联邦记忆池查询网关 v1.0 ==="
[ -f "$CONTRACT" ] || { echo "ERR: 契约缺失"; exit 1; }
[ -f "$INDEX_LEDGER" ] || { echo "ERR: 索引账本缺失"; exit 1; }

# 同源校验：参数 --did 必须匹配
if [ "$1" == "--did" ] && [ "$2" == "$DID" ]; then
  echo "同源校验通过: $DID"
else
  echo "拒绝访问: 非同源/缺少DID"; exit 2
fi

case "$3" in
  --stats)
    python3 -c "
import json
d=json.load(open('$INDEX_LEDGER'))
entries=d.get('entries',[])
print(f'索引总量: {len(entries)}')
print(f'节点: {set(e[\"source_node\"] for e in entries)}')
print(f'最近更新: {d.get(\"updated\",\"\")}')
"
    ;;
  --search)
    kw="${4:?用法: --search <关键词>}"
    python3 -c "
import json
d=json.load(open('$INDEX_LEDGER'))
for e in d.get('entries',[]):
    if kw in e.get('tags',[]) or kw in e.get('path','') or kw in json.dumps(e.get('tags',[])):
        print(f\"{e['mem_id']} | {e['path']} | {e['sha256'][:16]} | {e['timestamp']}\")
"
    ;;
  --export)
    echo "导出索引池摘要"
    python3 -c "
import json
d=json.load(open('$INDEX_LEDGER'))
json.dump(d, open('$INDEX_LEDGER','w'), ensure_ascii=False, indent=2)
print('索引池 OK')
"
    ;;
  *)
    echo "用法: $0 --did <DID> [--stats|--search <关键词>|--export]"
    ;;
esac
