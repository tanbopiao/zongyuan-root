#!/bin/bash
# 前置冲突检测 - 修改共享资源前必须执行
# 用法: ./pre_change_check.sh <window_id> <resource_type>

WINDOW="$1"
RESOURCE="$2"
AI_PROXY="/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py"
NGINX_CONF="/www/server/panel/vhost/nginx/huodouai.com.conf"

echo "=== 前置冲突检测 [窗口:$WINDOW] [资源:$RESOURCE] ==="

PASS=0
FAIL=0

check() {
    local NAME="$1"
    local RESULT="$2"
    if [ "$RESULT" = "0" ]; then
        echo "  ✅ $NAME"
        PASS=$((PASS+1))
    else
        echo "  ❌ $NAME"
        FAIL=$((FAIL+1))
    fi
}

case "$RESOURCE" in
    ai-proxy)
        # 检查AI Proxy语法
        python3 -c "import py_compile; py_compile.compile('$AI_PROXY', doraise=True)" 2>/dev/null
        check "AI Proxy语法" "$?"
        
        # 检查重复端点
        DUPES=$(grep -oP 'self\.path == "[^"]+"' "$AI_PROXY" | sort | uniq -d | wc -l)
        check "无重复端点" "$DUPES"
        ;;
        
    nginx)
        # 检查Nginx配置
        nginx -t 2>&1 | grep -q "syntax is ok"
        check "Nginx语法" "$?"
        
        # 检查重复location（同一server块内）
        DUP_LOC=$(grep -c 'location /api/drama/' "$NGINX_CONF")
        if [ "$DUP_LOC" -le 2 ]; then
            check "Nginx location无异常重复(HTTP+HTTPS各1)" "0"
        else
            check "Nginx location无异常重复(发现$DUP_LOC个)" "1"
        fi
        ;;
        
    endpoint)
        # 端点冲突检测需要传入端点路径
        ENDPOINT="$3"
        EXISTS=$(grep -c "self.path == \"$ENDPOINT\"" "$AI_PROXY")
        if [ "$EXISTS" = "0" ]; then
            check "端点$ENDPOINT未被占用" "0"
        else
            check "端点$ENDPOINT已被占用!" "1"
        fi
        ;;
        
    port)
        PORT="$3"
        IN_USE=$(ss -tlnp | grep -c ":$PORT ")
        check "端口$PORT未被占用" "$IN_USE"
        ;;
        
    all)
        echo "--- AI Proxy ---"
        python3 -c "import py_compile; py_compile.compile('$AI_PROXY', doraise=True)" 2>/dev/null
        check "AI Proxy语法" "$?"
        DUPES=$(grep -oP 'self\.path == "[^"]+"' "$AI_PROXY" | sort | uniq -d | wc -l)
        check "无重复端点" "$DUPES"
        
        echo "--- Nginx ---"
        nginx -t 2>&1 | grep -q "syntax is ok"
        check "Nginx语法" "$?"
        
        echo "--- 关键服务端口（应处于监听状态） ---"
        for p in 8021:zongyuan-aiproxy 8022:zongyuan-drift; do
            PORT=${p%%:*}
            SVC=${p##*:}
            IN_USE=$(ss -tlnp | grep -c ":$PORT ")
            if [ "$IN_USE" -gt 0 ]; then
                check "端口$PORT($SVC)正常监听" "0"
            else
                check "端口$PORT($SVC)未监听!" "1"
            fi
        done
        ;;
esac

echo ""
echo "=== 检测结果: 通过=$PASS 失败=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then
    echo "⚠️  存在冲突风险，请修复后再修改"
    exit 1
else
    echo "✅ 无冲突，可以安全修改"
    exit 0
fi
