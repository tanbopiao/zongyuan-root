#!/bin/bash
# ZONGYUAN-ROOT 身份节点API蓝绿部署自动化脚本
# 用法: bash blue_green_deploy.sh <green_version_path>

set -e

SERVICE_NAME="zongyuan-identity-api"
BLUE_PORT=8300
GREEN_PORT=8301
BLUE_PATH="/opt/ZONGYUAN-ROOT/identity_api"
GREEN_PATH="/opt/ZONGYUAN-ROOT/identity_api_green"
NGINX_CONF="/www/server/panel/vhost/nginx/identity-api.conf"
BACKUP_PATH="/opt/ZONGYUAN-ROOT/backup/identity_api"
HEALTH_ENDPOINT="/api/v1/identity/health"

echo "=========================================="
echo "ZONGYUAN-ROOT 身份节点API蓝绿部署"
echo "=========================================="

# 步骤1：备份当前蓝环境
echo "[1/6] 备份当前蓝环境..."
BACKUP_DIR="$BACKUP_PATH/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r "$BLUE_PATH" "$BACKUP_DIR/"
echo "  备份完成: $BACKUP_DIR"

# 步骤2：部署到绿环境
echo "[2/6] 部署到绿环境..."
if [ -z "$1" ]; then
    echo "  错误: 请提供绿环境版本路径"
    exit 1
fi
GREEN_SOURCE="$1"
rm -rf "$GREEN_PATH"
cp -r "$GREEN_SOURCE" "$GREEN_PATH"
echo "  绿环境部署完成: $GREEN_PATH"

# 步骤3：启动绿环境服务
echo "[3/6] 启动绿环境服务（端口$GREEN_PORT）..."
cd "$GREEN_PATH"
# 修改配置使用绿端口
sed -i "s/"port": $BLUE_PORT/"port": $GREEN_PORT/" config/settings.json 2>/dev/null || true
# 启动绿环境（临时进程）
nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port $GREEN_PORT --workers 1 > /tmp/identity_api_green.log 2>&1 &
GREEN_PID=$!
echo "  绿环境PID: $GREEN_PID"
sleep 5

# 步骤4：绿环境健康检查
echo "[4/6] 绿环境健康检查..."
for i in {1..10}; do
    if curl -s "http://127.0.0.1:$GREEN_PORT$HEALTH_ENDPOINT" | grep -q "ok"; then
        echo "  绿环境健康检查通过"
        break
    fi
    echo "  等待绿环境启动... ($i/10)"
    sleep 3
done

if ! curl -s "http://127.0.0.1:$GREEN_PORT$HEALTH_ENDPOINT" | grep -q "ok"; then
    echo "  错误: 绿环境健康检查失败，自动回滚"
    kill $GREEN_PID 2>/dev/null || true
    exit 1
fi

# 步骤5：Nginx流量切换（金丝雀发布）
echo "[5/6] Nginx流量切换..."
# 这里可以实现金丝雀发布，先切换5%流量
# 简化版：直接切换全部流量
# 实际生产环境应使用upstream权重控制
echo "  提示: 当前为简化版，需手动修改Nginx upstream切换流量"
echo "  生产环境建议使用: upstream identity_api { server 127.0.0.1:$GREEN_PORT weight=5; server 127.0.0.1:$BLUE_PORT weight=95; }"

# 步骤6：验证并完成
echo "[6/6] 部署验证..."
echo "  蓝环境: http://127.0.0.1:$BLUE_PORT$HEALTH_ENDPOINT"
echo "  绿环境: http://127.0.0.1:$GREEN_PORT$HEALTH_ENDPOINT"
echo ""
echo "=========================================="
echo "蓝绿部署完成！"
echo "=========================================="
echo "下一步操作:"
echo "  1. 验证绿环境功能正常"
echo "  2. 逐步切换Nginx流量到绿环境"
echo "  3. 确认稳定后，将绿环境升级为蓝环境"
echo "  4. 旧蓝环境保留作为回滚备份"
echo ""
echo "回滚命令: bash rollback.sh"
