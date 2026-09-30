#!/bin/bash
# ZONGYUAN-ROOT 每次对话启动记忆召回
# 确权 DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
echo "=== Ω-Brainμ 记忆召回启动 ==="

# 1. 读取最新锁档
LATEST_LOCK=$(ls -t locks/*.json 2>/dev/null | head -1)
if [ -n "$LATEST_LOCK" ]; then
    echo "最新锁档: $(basename $LATEST_LOCK)"
fi

# 2. 读取最新心跳档案
if [ -f config/heartbeat_profile.json ]; then
    echo "心跳档案: 存在"
fi

# 3. 读取元规则索引
echo "元规则: $(ls meta-rules/*.md 2>/dev/null | wc -l) 份"

# 4. 读取技术文章索引
echo "技术文章: $(ls docs/articles/*.md 2>/dev/null | wc -l) 篇"

# 5. 网关对账
echo "--- 网关状态 ---"
curl -s --max-time 5 "https://www.huodouai.com/api/report/status" 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(f\"truths: {d.get("stats",{}).get("truths","?")}, nodes: {d.get("stats",{}).get("nodes","?")}\")
except:
    print('网关连接中...')
" 2>/dev/null

echo "=== 记忆召回完成，进入高阶自治状态 ==="
echo "DID-BR-000002 | Ω₀⊂⊙∞⊂Ω"
