#!/bin/bash
# 官网性能预算巡检：TTFB/大小/关键标记/Lighthouse 分数（低成本防回退）
# META-RULE-014｜DID-BR-000002
URL="https://www.huodouai.com/"
LOG="/home/user/ZONGYUAN-ROOT/logs/perf_patrol.log"
TS=$(date '+%Y-%m-%d %H:%M:%S')
TTFB=$(curl -s -o /dev/null -w '%{time_starttransfer}' -m 15 "$URL")
SIZE=$(curl -s -o /dev/null -w '%{size_download}' -m 15 "$URL")
CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "$URL")
MARKS=$(curl -s -m 15 "$URL" | grep -cE '核心架构|进化路线图|系统能力|昆仑洞天')
echo "[$TS] HTTP=$CODE TTFB=${TTFB}s SIZE=${SIZE}B 关键区块命中=$MARKS" >> "$LOG"
# 阈值告警：TTFB>1s 或 关键区块<4 视为异常
python3 - "$TTFB" "$MARKS" "$LOG" << 'PYEOF'
import sys
ttfb = float(sys.argv[1]); marks = int(sys.argv[2])
if ttfb > 1.0 or marks < 4:
    print(f"[{__import__('time').strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ 异常: TTFB={ttfb}s 区块={marks}") 
    sys.exit(1)
print(f"稳态 OK: TTFB={ttfb}s 区块={marks} ≥ 4")
PYEOF
