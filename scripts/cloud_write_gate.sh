#!/usr/bin/env bash
# 云内核写闸门 v1.0 | 多节点SSH写操作统一通道: staging→审批→原子应用→审计
# 用法: cloud_write_gate.sh submit <node> <target> <file> [approval:auto|pending]
#       cloud_write_gate.sh apply <staging-file>        # 审批后应用(flock串行+原子替换+备份+审计)
#       cloud_write_gate.sh list                        # 查看待审批队列
set -uo pipefail
DOC="/www/wwwroot/huodouai.com"; GATE="$DOC/zhongshu/data/write-gate"
STAGE="$GATE/staging"; APPLIED="$GATE/applied"; LOG="$GATE/gate.log"
LOCK="$GATE/.gate.lock"
TS=$(date '+%Y-%m-%dT%H:%M:%S%z')
mkdir -p "$STAGE" "$APPLIED"
# 合法目标白名单: 只允许写这些区域, 防越权
ALLOWED_PREFIXES=("$DOC/zhongshu/data/seed-truth" "$DOC/zhongshu/data/evolution" "$DOC/zhongshu/data/decisions" "$DOC/_zongyuan-assets/seed-truth")

log(){ echo "[$TS] $*" >> "$LOG"; }

case "${1:-}" in
  submit)
    NODE="${2:?node}"; TARGET="${3:?target}"; FILE="${4:?file}"; APPROVAL="${5:-auto}"
    # 目标路径白名单校验
    OK=0
    for p in "${ALLOWED_PREFIXES[@]}"; do case "$TARGET" in "$p"*) OK=1;; esac; done
    [ "$OK" = "1" ] || { echo "REJECT: 目标不在白名单 $TARGET"; log "REJECT submit $NODE -> $TARGET (非白名单)"; exit 1; }
    [ -f "$FILE" ] || { echo "REJECT: 文件不存在"; exit 1; }
    HASH=$(sha256sum "$FILE" | awk '{print $1}')
    META="{\"node\":\"$NODE\",\"target\":\"$TARGET\",\"hash\":\"$HASH\",\"approval\":\"$APPROVAL\",\"ts\":\"$TS\",\"submitter\":\"${SUDO_USER:-$USER}\"}"
    SP="$STAGE/$(date +%Y%m%d%H%M%S)-$NODE-$(basename "$TARGET").json"
    echo "$META" > "$SP"
    cp "$FILE" "${SP%.json}.payload"
    if [ "$APPROVAL" = "auto" ]; then
      "$0" apply "$SP" ; else
      echo "SUBMITTED: $SP (待审批)"; log "SUBMIT $NODE -> $TARGET approval=$APPROVAL stage=$SP"
    fi
    ;;
  apply)
    SP="${2:?staging-file}"
    [ -f "$SP" ] || { echo "REJECT: 无此staging"; exit 1; }
    exec 9>"$LOCK"; flock 9   # 并发串行锁: 同刻只有一个节点能应用
    META=$(cat "$SP"); PAYLOAD="${SP%.json}.payload"
    NODE=$(echo "$META"|grep -o '"node":"[^"]*"'|cut -d'"' -f4)
    TARGET=$(echo "$META"|grep -o '"target":"[^"]*"'|cut -d'"' -f4)
    HASH=$(echo "$META"|grep -o '"hash":"[^"]*"'|cut -d'"' -f4)
    [ "$(sha256sum "$PAYLOAD"|awk '{print $1}')" = "$HASH" ] || { echo "REJECT: 载荷哈希不符"; log "REJECT apply $NODE (hash mismatch)"; exit 1; }
    mkdir -p "$(dirname "$TARGET")"
    [ -f "$TARGET" ] && cp "$TARGET" "$TARGET.bak-$(date +%Y%m%d%H%M%S)"  # 先备份
    python3 - "$PAYLOAD" "$TARGET" << 'PY'
import sys, os, shutil
src, dst = sys.argv[1], sys.argv[2]
tmp = dst + ".tmp-" + os.urandom(4).hex()
shutil.copy2(src, tmp)          # 原子替换
os.replace(tmp, dst)
print("APPLIED atomic:", dst)
PY
    mv "$SP" "$APPLIED/"; mv "$PAYLOAD" "$APPLIED/"
    log "APPLY $NODE -> $TARGET hash=$HASH (flock串行+原子+备份)"
    echo "APPLIED: $TARGET"
    ;;
  list)
    echo "=== 待审批队列 ==="; ls -t "$STAGE/"*.json 2>/dev/null | while read f; do echo "$f: $(cat "$f"|head -c 200)"; done
    echo "=== 最近应用 ==="; tail -5 "$LOG" 2>/dev/null
    ;;
  *) echo "用法: cloud_write_gate.sh submit|apply|list"; exit 1;;
esac
