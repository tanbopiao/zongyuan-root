#!/bin/bash
# ZONGYUAN-ROOT 身份节点API回滚脚本
# 用法: bash rollback.sh

set -e

SERVICE_NAME="zongyuan-identity-api"
BLUE_PORT=8300
GREEN_PORT=8301
BLUE_PATH="/opt/ZONGYUAN-ROOT/identity_api"
GREEN_PATH="/opt/ZONGYUAN-ROOT/identity_api_green"
BACKUP_PATH="/opt/ZONGYUAN-ROOT/backup/identity_api"

echo "=========================================="
echo "ZONGYUAN-ROOT 身份节点API回滚"
echo "=========================================="

# 步骤1：停止绿环境
echo "[1/4] 停止绿环境..."
pkill -f "uvicorn app.main:app --host 127.0.0.1 --port $GREEN_PORT" 2>/dev/null || true
echo "  绿环境已停止"

# 步骤2：恢复蓝环境
echo "[2/4] 确认蓝环境运行正常..."
systemctl restart "$SERVICE_NAME"
sleep 5
if curl -s "http://127.0.0.1:$BLUE_PORT/api/v1/identity/health" | grep -q "ok"; then
    echo "  蓝环境健康检查通过"
else
    echo "  警告: 蓝环境健康检查失败，尝试从备份恢复"
    LATEST_BACKUP=$(ls -td "$BACKUP_PATH"/*/ | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        echo "  从备份恢复: $LATEST_BACKUP"
        rm -rf "$BLUE_PATH"
        cp -r "$LATEST_BACKUP/identity_api" "$BLUE_PATH"
        systemctl restart "$SERVICE_NAME"
        sleep 5
    fi
fi

# 步骤3：Nginx流量切回蓝环境
echo "[3/4] Nginx流量切回蓝环境..."
echo "  提示: 请确认Nginx upstream已指向蓝环境端口$BLUE_PORT"

# 步骤4：验证
echo "[4/4] 回滚验证..."
curl -s "http://127.0.0.1:$BLUE_PORT/api/v1/identity/health"
echo ""
echo ""
echo "=========================================="
echo "回滚完成！"
echo "=========================================="
