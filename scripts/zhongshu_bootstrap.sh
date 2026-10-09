#!/usr/bin/env bash
# 云端全栈自举 | 关键资产漂移检测→自动恢复→告警留痕 | cron */30
set -uo pipefail
DOC="/www/wwwroot/huodouai.com"; DIR="$DOC/zhongshu/data/bootstrap"; mkdir -p "$DIR"
TS=$(date '+%Y-%m-%dT%H:%M:%S%z')
# 关键资产清单: 核心页面(logo/背景禁动, 仅检测存在与大小)
PAGES=("/index.html" "/monitor.html" "/zongyuan-whitepaper.html" "/cloud-hub-architecture.html" "/zhongshu/index.html" "/gallery/rose/index.html")
CORE_FILES=("/zhongshu/zhongshu-server/gateway_server.py" "/zhongshu/zhongshu-server/scheduler.py" "/zhongshu/zhongshu-server/truth_store.py")
SVCS=("zhongshu-gateway" "zhongshu-scheduler")
FAIL=""
for p in "${PAGES[@]}" "${CORE_FILES[@]}"; do
  f="$DOC$p"
  if [ ! -f "$f" ] || [ ! -s "$f" ]; then FAIL="$FAIL 缺:${p##*/}"; fi
done
for s in "${SVCS[@]}"; do
  systemctl is-active --quiet "$s" || FAIL="$FAIL 服务:${s}"
done
if [ -n "$FAIL" ]; then
  echo "[$TS] 漂移检测:$FAIL" >> "$DIR/bootstrap.log"
  # 自动恢复: 核心代码从 git 基线恢复
  (cd "$DOC/zhongshu/zhongshu-server" && git checkout -q -- . 2>/dev/null)
  for s in "${SVCS[@]}"; do systemctl restart "$s" 2>/dev/null; done
  # 页面缺失: 从同目录 .bak-* 备份恢复(不触 logo/背景, 只恢复缺失)
  for p in "${PAGES[@]}"; do
    f="$DOC$p"
    if [ ! -f "$f" ]; then
      bak=$(ls "${f%.html}".bak-* 2>/dev/null | head -1)
      [ -n "$bak" ] && cp "$bak" "$f"
    fi
  done
  curl -s -m 8 -X POST "https://zrntfy.huodouai.com/zongyuan-did-br-000002-7f3a9c2e-alert" -H "X-DID: DID-BR-000002" -d "{\"event\":\"bootstrap_recover\",\"detail\":\"$FAIL\",\"ts\":\"$TS\"}" >/dev/null 2>&1 || true
  echo "RECOVERED"
else
  echo "[$TS] 全栈自举健康: ${#PAGES[@]}页+${#CORE_FILES[@]}代码+${#SVCS[@]}服务 全绿" >> "$DIR/bootstrap.log"
  echo "OK"
fi
