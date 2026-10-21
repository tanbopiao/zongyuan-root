#!/bin/bash
# worker 独立守护进程（文件脚本版，替代 bash -c 内联，规避环境对内联后台进程的回收）
WID="$1"; DIR="$2"; LOG="$3"; GW="$4"; DID="$5"; BASE="$6"; TASK_TABLE="$7"
PID_FILE="$DIR/$WID.pid"; HB_FILE="$DIR/$WID.heartbeat"; CNS_FILE="$DIR/$WID.cns"
echo $$ > "$PID_FILE"; echo "$(date +%s)" > "$HB_FILE"
echo "[$(date)] 中枢受控 worker $WID 启动 (pid $$, 文件守护)" >> "$LOG"
CYCLE=0
while true; do
  sleep 60
  echo "$(date +%s)" > "$HB_FILE"
  CYCLE=$((CYCLE + 1))
  if [ $((CYCLE % 10)) -eq 0 ]; then
    curl -sS -m 15 -X POST "$GW" -H "X-DID: $DID" -H "Content-Type: application/json" \
      --data-binary "{\"key\":\"worker_heartbeat_${DID}_$(date +%s)\",\"value\":{\"event\":\"worker_heartbeat\",\"worker\":\"$WID\",\"mode\":\"cns_file\",\"pid\":$$,\"ts\":$(date +%s)}}" >> "$LOG" 2>&1 || true
    bash /home/user/ZONGYUAN-ROOT/scripts/worker_api_call.sh "worker_api_auto_${WID}_$(date +%s)" >> "$LOG" 2>&1 || bash /home/user/ZONGYUAN-ROOT/scripts/worker_ntfy_alert.sh API_CALL_FAIL "worker 云端 API 自动调用失败" >> "$LOG" 2>&1 || true
  fi
  if [ $((CYCLE % 5)) -eq 0 ]; then
    # 环境还原自愈：cron daemon 不在则拉起；crontab 缺失则从持久模板恢复
    if ! pgrep -x cron >/dev/null 2>&1; then
      sudo service cron start >/dev/null 2>&1 || sudo /usr/sbin/cron >/dev/null 2>&1
      echo "[$(date)] cron daemon 自愈拉起" >> "$LOG"
    fi
    if ! crontab -l >/dev/null 2>&1; then
      crontab /home/user/ZONGYUAN-ROOT/config/cron-restore.txt >/dev/null 2>&1
      echo "[$(date)] crontab 自愈恢复（10 条模板）" >> "$LOG"
    fi
  fi
  if [ $((CYCLE % 5)) -eq 0 ]; then
    PULL=$(lark-cli base +record-list --base-token "$BASE" --table-id "$TASK_TABLE" --as user --limit 200 --format json 2>/dev/null)
    CNT=$(echo "$PULL" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin).get('data',{})
    fields=d.get('fields',[]); rows=d.get('data',[])
    st_i=fields.index('状态') if '状态' in fields else -1
    n=0
    for r in rows:
        if st_i>=0 and st_i<len(r):
            v=r[st_i]
            if isinstance(v,list) and v and '待部署' in str(v[0]): n+=1
    print(n)
except Exception: print(-1)
" 2>/dev/null)
    if [ -z "$CNT" ] || [ "$CNT" = "-1" ]; then
      echo "{\"last_pull_ts\":\"$(date +%s)\",\"mode\":\"idle\",\"instruction_count\":0,\"kill_switch\":\"fail_closed\",\"note\":\"中枢不可达，worker 保持受控空闲\"}" > "$CNS_FILE"
    elif [ "$CNT" = "0" ]; then
      echo "{\"last_pull_ts\":\"$(date +%s)\",\"mode\":\"idle\",\"instruction_count\":0,\"kill_switch\":\"off\",\"note\":\"中枢可达但无待部署指令，worker 空闲\"}" > "$CNS_FILE"
    else
      echo "{\"last_pull_ts\":\"$(date +%s)\",\"mode\":\"executing\",\"instruction_count\":$CNT,\"kill_switch\":\"off\",\"note\":\"中枢有 $CNT 条待部署指令，受控执行\"}" > "$CNS_FILE"
    fi
  fi
done
