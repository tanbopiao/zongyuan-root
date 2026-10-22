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
exec ssh -i "$KEY" -o ProxyCommand="nc -X connect -x 127.0.0.1:18080 %h %p" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=25 -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=6 "$@"
