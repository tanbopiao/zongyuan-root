#!/bin/bash
# zrrsh — 云端SSH通道 (持久层自愈版)
# 2026-10-22: .ssh曾被整体清空(根因未定位), 现内置自愈: key缺失时自动从持久层备份恢复
KEY=/root/.ssh/zongyuan-sh-20261021
BAK="$(cd "$(dirname "$0")/../.." && pwd)/persist_snapshot/ssh/zongyuan_new.enc"
if [ ! -s "$KEY" ]; then
  if [ -s "$BAK" ]; then
    mkdir -p /root/.ssh
    umask 077
    cp "$BAK" "$KEY" && chmod 600 "$KEY"
    echo "[zrrsh] SELF-HEAL: key restored from persistent layer ($BAK)" >&2
  else
    echo "[zrrsh] FATAL: key missing and persistent backup not found: $BAK" >&2
    exit 255
  fi
fi
# ---- Agent SSH 网关清洗模式 (--clean host command...) ----
# 受控执行通道: 拒绝交互式会话, 阻断编码/管道逃逸, 只转发单条非交互指令
if [ "$1" = "--clean" ]; then
  shift
  HOST="$1"; shift
  [ -n "$HOST" ] || { echo "[zrrsh --clean] FATAL: missing host" >&2; exit 64; }
  [ $# -ge 1 ] || { echo "[zrrsh --clean] FATAL: missing command" >&2; exit 64; }
  CMD="$*"
  # 黑名单: eval / sh -c / 交互标记 / 编码绕过 / 历史擦除 (网关预审后二次兜底)
  if printf '%s' "$CMD" | grep -qE '(\beval\b|(^|[;&|])[[:space:]]*(ba|z|d)?sh[[:space:]]+-c\b|history[[:space:]]+-c|HISTFILE|base64[[:space:]]+(-d|--decode)|xxd[[:space:]]+-r|bash[[:space:]]+/dev/(stdin|fd))'; then
    echo "[zrrsh --clean] BLOCKED: escape pattern rejected" >&2
    exit 65
  fi
  exec ssh -T -i "$KEY" -o ProxyCommand="nc -X connect -x 127.0.0.1:18080 %h %p" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=25 -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -o RequestTTY=no -o RemoteCommand=none -o ClearAllForwardings=yes -o PermitLocalCommand=no -- "$HOST" "$CMD"
fi

exec ssh -i "$KEY" -o ProxyCommand="nc -X connect -x 127.0.0.1:18080 %h %p" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=25 -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=6 "$@"
