#!/bin/bash
# ZONGYUAN-ROOT 内核启动授权检查
# 所有内核服务启动前必须通过此脚本验证授权

LICENSE_GUARD="/opt/ZONGYUAN-ROOT/license_guard.py"
LICENSE_FILE="/opt/ZONGYUAN-ROOT/.license"
LOG_FILE="/opt/ZONGYUAN-ROOT/logs/license_guard.log"

mkdir -p /opt/ZONGYUAN-ROOT/logs

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 检查授权状态
RESULT=$(python3 "$LICENSE_GUARD" status 2>/dev/null)
VALID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['license']['valid'])" 2>/dev/null || echo "False")
PLAN=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['license']['plan'])" 2>/dev/null || echo "free")

if [ "$VALID" = "True" ]; then
    log "授权验证通过: plan=$PLAN"
    echo "✅ 授权验证通过 | 版本: $PLAN"
else
    REASON=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['license']['reason'])" 2>/dev/null || echo "未知")
    log "授权验证失败: $REASON, 降级为免费版"
    echo "⚠️  授权验证失败: $REASON"
    echo "ℹ️  降级为免费版运行（10条真值/1实例/基础功能）"
    echo "ℹ️  激活授权: python3 $LICENSE_GUARD activate <授权码>"
fi

# 检查到期警告
WARNING=$(echo "$RESULT" | python3 -c "import sys,json; w=json.load(sys.stdin).get('expiry_warning',{}); print(w.get('message','')) if w.get('warning') else print('')" 2>/dev/null)
if [ -n "$WARNING" ]; then
    log "到期警告: $WARNING"
    echo "⚠️  $WARNING"
fi

# 导出授权环境变量
export ZY_LICENSE_PLAN="$PLAN"
export ZY_LICENSE_VALID="$VALID"

# 根据版本设置功能开关
case "$PLAN" in
    free|trial)
        export ZY_FEATURE_MULTI_TENANT="false"
        export ZY_FEATURE_SLA="false"
        ;;
    professional)
        export ZY_FEATURE_MULTI_TENANT="false"
        export ZY_FEATURE_SLA="false"
        ;;
    enterprise)
        export ZY_FEATURE_MULTI_TENANT="true"
        export ZY_FEATURE_SLA="true"
        ;;
esac

log "内核启动授权检查完成: plan=$PLAN valid=$VALID"
exit 0
