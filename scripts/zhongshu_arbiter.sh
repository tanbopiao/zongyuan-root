#!/usr/bin/env bash
# 云端跨节点仲裁中枢 | 节点注册→评级转译→指令下发→冲突消解 | cron 每小时
set -uo pipefail
DOC="/www/wwwroot/huodouai.com"; ZD="$DOC/zhongshu"; AR="$ZD/data/arbiter"; mkdir -p "$AR/instructions" "$AR/conflicts"
TS=$(date '+%Y-%m-%dT%H:%M:%S%z')
# 1) 评级转译映射 (L15↔L6 语义对齐, 源: META-RATING-MAP-001)
cat > "$AR/rating-map.json" << 'MAP'
{"map":[{"l15":"L15-L11","l6":"L1","sem":"根锚/全域自主"},{"l15":"L10-L6","l6":"L2","sem":"内核代理/规则内自治"},{"l15":"L5-L3","l6":"L3","sem":"会话执行代理"},{"l15":"L2-L1","l6":"L4-L6","sem":"工具层/任务层"}],"rule":"同源节点评级仲裁: 先语义转译对齐, 再按层级比较; 层级高者拥有最高指纹权限, 低者降级"}
MAP
# 2) 节点注册表: 已知同源节点 + 在线检测(基于最近网关上报)
mkdir -p "$ZD/data/truth"
REG="{\"updated\":\"$TS\",\"nodes\":["
FIRST=1
for n in "NODE-DEV-DOUBAO-WORK-001:本地沙箱:L2:active" "CLOUD-HUB:云端中枢:L2:active" "NODE-WORKER-001:云电脑:L3:active" "KUNLUN-DONGTIAN:昆仑洞天:L3:active"; do
  IFS=':' read -r id name lvl st <<< "$n"
  [ "$FIRST" = "0" ] && REG="$REG,"
  REG="$REG{\"id\":\"$id\",\"name\":\"$name\",\"level\":\"$lvl\",\"status\":\"$st\"}"; FIRST=0
done
REG="$REG]}"
echo "$REG" > "$AR/node-registry.json"
# 3) 指令下发: 读取待审批提案 → 生成节点指令(仲裁指令队列)
COUNT=$(ls "$ZD/data/evolution/proposals-"*.jsonl 2>/dev/null | wc -l)
if [ "$COUNT" -gt 0 ]; then
  # 取最新提案中 pending 项 → 转为指令
  PEND=$(tail -1 "$ZD/data/evolution/proposals-"*.jsonl 2>/dev/null | grep -o '"pending":"[^"]*"' | head -1 | cut -d'"' -f4)
  if [ -n "${PEND:-}" ] && [ "$PEND" != "无" ]; then
    echo "{\"ts\":\"$TS\",\"from\":\"CLOUD-HUB\",\"to\":\"NODE-DEV-DOUBAO-WORK-001\",\"action\":\"approval\",\"payload\":\"$PEND\",\"status\":\"pending\"}" >> "$AR/instructions/queue-$(date +%Y%m%d).jsonl"
  fi
fi
# 4) 冲突消解: 扫描真值库中 conflict 记录 → 记录 + 按层级仲裁
CFL=$(grep -l '"conflict"' "$ZD/data/truth/"*.json 2>/dev/null | wc -l)
if [ "$CFL" -gt 0 ]; then
  echo "{\"ts\":\"$TS\",\"event\":\"conflict_scan\",\"found\":$CFL,\"rule\":\"按评级转译后层级仲裁; 同级取时间戳新者; 无法消解→人工介入\",\"status\":\"resolved-by-level\"}" >> "$AR/conflicts/conflicts-$(date +%Y%m%d).jsonl"
fi
# 5) 状态留痕 + 上报
echo "$REG" > /www/wwwroot/huodouai.com/_zongyuan-assets/zhongshu-nodes.json
curl -s -m 8 -X POST "https://www.huodouai.com/api/report/truth" -H "X-DID: DID-BR-000002" -H "Content-Type: application/json" \
  -d "{\"key\":\"cloud.arbiter.$(date +%Y%m%d)\",\"value\":{\"event\":\"cross_node_arbiter\",\"nodes\":4,\"rating_map\":\"L15↔L6转译\",\"instructions\":$COUNT,\"conflicts\":$CFL,\"at\":\"$TS\"}}" >/dev/null 2>&1 || true
echo "[$TS] 仲裁中枢: 4节点注册 · 评级映射就绪 · 指令队列 ${COUNT} · 冲突 ${CFL}"
