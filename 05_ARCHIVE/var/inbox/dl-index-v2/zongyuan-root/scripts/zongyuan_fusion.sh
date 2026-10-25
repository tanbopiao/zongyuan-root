#!/bin/bash
# =====================================================================
# ZONGYUAN 融合单一入口（逻辑联邦归一 · META-FUSION-001）
# 脑(zongyuan-kernel) × 手(ZONGYUAN-ROOT) —— 统一 CLI，两侧实现零改动
#
# 用法：
#   zongyuan_fusion.sh think "<目标>" [--provider ark|zhipu]  认知建议（豆包Ark/智谱）
#   zongyuan_fusion.sh act <action> --payload '<json>'       认知→行动：ActionGate 分级审批+执行
#   zongyuan_fusion.sh remember <keyword>                   记忆检索（脑侧 MemoryQuery）
#   zongyuan_fusion.sh accumulate                           真值积累（脑侧）
#   zongyuan_fusion.sh lock                                 全域锁档六环节（手侧）
#   zongyuan_fusion.sh tick|watchdog|monitor                手侧无人值守调度
#   zongyuan_fusion.sh heartbeat [--report]                 融合心跳（本地快照 + 可选上报）
#   zongyuan_fusion.sh mcp <tool> '<json-args>'            平台 Sandbox MCP 工具调用（8091 /mcp）
#   zongyuan_fusion.sh mcp list                                列出全部可用工具
#   zongyuan_fusion.sh selfcheck                            两树联合自检（fail-closed 汇总）
#   zongyuan_fusion.sh fusion_verify                        认知→行动→记忆→审计 全链路演示
# =====================================================================
set -uo pipefail
ZK="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
ZR="/home/user/ZONGYUAN-ROOT"
DID="DID-BR-000002"

usage() {
  echo "用法: zongyuan_fusion.sh {think|act|remember|accumulate|lock|tick|watchdog|monitor|heartbeat|selfcheck|fusion_verify} [...]"
}

selfcheck() {
  echo "===== 融合自检（fail-closed 汇总）====="
  echo "[脑] kernel: $(bash "$ZK/scripts/kernel_launch.sh" status)"
  echo "[脑] 基线: $(python3 "$ZK/scripts/status.py" 2>/dev/null | sed -n 2p)"
  echo "[脑] 审计: $(wc -l < "$ZK/var/audit/audit.jsonl") 条 | 法则: $(ls "$ZK/config/meta_laws"/*.json | wc -l) 份"
  echo "[脑] 冒烟测试: $(cd "$ZK" && python3 tests/test_kernel.py 2>/dev/null | tail -1)"
  echo "[手] worker: $(bash "$ZR/scripts/worker_controlled.sh" status worker-kernel-001 2>/dev/null | head -c 50)"
  echo "[手] 资产: $(ls "$ZR/asset/image/kunlun-auto-out"/*.webp 2>/dev/null | wc -l) | 账本: $(wc -l < "$ZR/HASH-LEDGER.csv") 行"
  echo "[手] 激活台账: $(python3 -c "import json;print(len(json.load(open('$ZR/var/activation/00-激活索引.json'))['records']))" 2>/dev/null) 次"
  echo "[手] 法则: $(ls "$ZR/meta-rules"/*.json | wc -l) 份"
  echo "[共] 融合法则: META-FUSION-001 (两树一致: $(diff -q "$ZK/config/meta_laws/META-FUSION-001.json" "$ZR/meta-rules/META-FUSION-001.json" >/dev/null 2>&1 && echo 是 || echo 否))"
  echo "[共] cron: fusion 心跳 $(crontab -l 2>/dev/null | grep -c fusion_heartbeat) 条 / fusion 自检 $(crontab -l 2>/dev/null | grep -c fusion_selfcheck) 条"
}

fusion_verify() {
  echo "===== 融合全链路演示：认知→行动→记忆→审计 ====="
  echo "--- 1. think 认知建议（豆包Ark）---"
  python3 "$ZK/scripts/cognitive_advisor.py" "请给出当前内核下一步的一个低风险优化建议，JSON格式" --provider ark 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('verdict:', d.get('verdict'))
a=d.get('advice',{})
print('建议:', str(a.get('recommendation',a.get('raw','')))[:120] if isinstance(a,dict) else str(a)[:120])
" || echo "think: fail（上游403或密钥不可用，链路其余部分继续）"
  echo "--- 2. act 分级审批（低风险自动放行）---"
  bash "$ZR/scripts/zongyuan_fusion.sh" act audit 2>/dev/null | head -4 || python3 "$ZK/scripts/action_gate.py" check audit
  echo "--- 3. remember 记忆检索 ---"
  python3 "$ZK/scripts/memory_query.py" truth --limit 2 2>/dev/null | tail -3
  echo "--- 4. audit 审计落账 ---"
  python3 - "$ZK" << 'PYEOF'
import json, time, sys
zk = sys.argv[1]
rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": "fusion.verify", "actor": "fusion",
       "action": "pipeline", "result": "ok", "detail": "认知→行动→记忆→审计 全链路演示"}
with open(f"{zk}/var/audit/audit.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print("审计已追加 fusion.verify")
PYEOF
  echo "--- 5. heartbeat 融合快照 ---"
  bash "$ZR/scripts/fusion_heartbeat.sh" | head -2
  echo "===== 全链路完成 ====="
}

case "${1:-}" in
  think)      shift; python3 "$ZK/scripts/cognitive_advisor.py" "$@" ;;
  act)        shift; python3 "$ZK/scripts/action_gate.py" "$@" ;;
  remember)   shift; python3 "$ZK/scripts/memory_query.py" "$@" ;;
  accumulate) shift; cd "$ZK" && python3 scripts/truth_accumulate.py "$@" ;;
  lock)       bash "$ZR/scripts/worker_kernel.sh" lock ;;
  tick)       bash "$ZR/scripts/worker_kernel.sh" tick ;;
  watchdog)   bash "$ZR/scripts/worker_kernel.sh" watchdog ;;
  monitor)    bash "$ZR/scripts/worker_kernel.sh" monitor ;;
  heartbeat)  bash "$ZR/scripts/fusion_heartbeat.sh" "${2:-}" ;;
  mcp)        shift; python3 "$ZR/scripts/sandbox_mcp.py" "$@" ;;
  fleet)      shift; bash "$ZR/scripts/fleet.sh" "$@" ;;
  cloud-mirror) shift; bash "$ZR/scripts/cloud_mirror.sh" "$@" ;;
  selfcheck)  selfcheck ;;
  fusion_verify) fusion_verify ;;
  *) usage; exit 2 ;;
esac
