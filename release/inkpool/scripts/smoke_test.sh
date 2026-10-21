#!/usr/bin/env bash
# 阶段二·初验冒烟测试 — inkstone.yaml: anchor.smoke_script 指向本脚本
# 用法: smoke_test.sh <node> <health_probe>
# 覆盖核心链路接口：健康探针 + 首页 + 核心 API（按部署环境实际地址改写 BASE）
set -euo pipefail

NODE="${1:?node required}"
PROBE="${2:-/health}"
BASE="${BASE_URL:-http://${NODE}:8080}"

fail=0
check() {
  local name="$1" url="$2"
  if curl -fsS --max-time 10 -o /dev/null "$url"; then
    echo "[PASS] $name -> $url"
  else
    echo "[FAIL] $name -> $url"
    fail=1
  fi
}

check "health"  "${BASE}${PROBE}"
check "index"   "${BASE}/"
check "core-api" "${BASE}/api/v1/ping"

exit $fail
