#!/bin/bash
# steady_evolve_bootstrap — 启动自检口令 (四环节方法论第1+3环节落地)
# 用法: bash 00_KERNEL/scripts/steady_evolve_bootstrap.sh
# 语义: 沙箱/实例重置后一句口令复原周期调度:
#       自检环境 → 校验周期任务定义 → 确保执行器daemon存活(不存活则拉起) → 输出状态
# 幂等: 可重复执行; 无网络写入(告警由执行器任务按时间窗去重)
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SDIR="$ROOT/var/steady_evolve"
SCRIPT="$ROOT/00_KERNEL/scripts/steady_evolve.py"
mkdir -p "$SDIR"

echo "== steady_evolve bootstrap =="
echo "root: $ROOT"
echo "time: $(date '+%F %T %z')"

# 1. 环境自检
echo "-- env --"
python3 --version 2>&1 | sed 's/^/  /'
for b in crontab atomcode curl git; do
  if command -v "$b" >/dev/null 2>&1; then echo "  $b: OK ($(command -v $b))"; else echo "  $b: MISSING"; fi
done

# 2. 周期任务定义校验
echo "-- tasks def --"
python3 - "$ROOT/var/periodic-tasks.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    ts = d.get("tasks", [])
    print(f"  loaded: {len(ts)} tasks ->", ", ".join(
        f"{t['name']}({t['interval_sec']}s{',off' if not t.get('enabled',True) else ''})" for t in ts))
except Exception as e:
    print(f"  ERROR: {e}"); sys.exit(3)
PY
[ $? -ne 0 ] && echo "  FATAL: periodic-tasks.json 无效" && exit 3

# 3. daemon 存活检查与拉起
PIDF="$SDIR/daemon.pid"
ALIVE=0
if [ -f "$PIDF" ]; then
  PID=$(cat "$PIDF" 2>/dev/null || echo 0)
  if kill -0 "$PID" 2>/dev/null; then ALIVE=1; fi
fi
echo "-- daemon --"
if [ "$ALIVE" = "1" ]; then
  echo "  alive pid=$PID (noop)"
else
  nohup python3 "$SCRIPT" daemon >> "$SDIR/daemon.out" 2>&1 &
  disown 2>/dev/null || true
  sleep 1
  NEWPID=$(cat "$PIDF" 2>/dev/null || echo "")
  if [ -n "$NEWPID" ] && kill -0 "$NEWPID" 2>/dev/null; then
    echo "  started pid=$NEWPID"
  else
    echo "  FAILED to start (see $SDIR/daemon.out)"; exit 4
  fi
fi

# 4. 立即跑一次心跳探针(首轮自检)
echo "-- first probe --"
python3 "$SCRIPT" run gateway_steady_probe 2>&1 | sed 's/^/  /'

# 5. 状态摘要
echo "-- status --"
python3 "$SCRIPT" status 2>&1 | head -40
echo "== bootstrap done =="
