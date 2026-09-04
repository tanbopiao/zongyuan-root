#!/bin/bash
# 元秩序启动前置检查 - 所有服务ExecStartPre调用
cd /opt/ZONGYUAN-ROOT/meta_order

# 检查元宪法完整性
RESULT=$(python3 meta_constitution_validator.py integrity 2>/dev/null)
STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)

if [ "$STATUS" = "TAMPERED" ]; then
    echo "[元秩序告警] 元宪法哈希不匹配，可能被篡改！"
    echo "$RESULT"
    exit 1  # 阻止启动
fi

# 检查四元锚定链
AUDIT=$(python3 quad_anchor_engine.py audit 2>/dev/null)
VIOLATIONS=$(echo "$AUDIT" | python3 -c "import sys,json; print(json.load(sys.stdin)['violation_count'])" 2>/dev/null)

if [ "$VIOLATIONS" != "0" ] && [ -n "$VIOLATIONS" ]; then
    echo "[元秩序告警] 四元锚定链存在 $VIOLATIONS 处违规"
    echo "$AUDIT" | python3 -c "import sys,json; [print(f'  - {v}') for v in json.load(sys.stdin)['violations']]" 2>/dev/null
fi

echo "[元秩序] 自检通过: 元宪法完整, 四元锚定链正常"
exit 0
