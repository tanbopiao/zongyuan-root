#!/bin/bash
# ZONGYUAN-ROOT AIOS 服务启动脚本
# 自动加载.env文件中的环境变量，然后启动Python服务
# 用法: ./start_service.sh <python脚本> <参数...>
# 示例: ./start_service.sh ai_proxy/ai_proxy.py --port 8021

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# 加载.env文件
if [ -f "$ENV_FILE" ]; then
    echo "[启动脚本] 加载环境变量: $ENV_FILE"
    # 导出.env中的所有变量（忽略注释和空行）
    while IFS= read -r line; do
        # 跳过注释和空行
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        # 导出变量
        export "$line"
    done < "$ENV_FILE"
    echo "[启动脚本] 环境变量加载完成"
else
    echo "[启动脚本] 警告: .env文件不存在: $ENV_FILE"
fi

# 启动Python服务
echo "[启动脚本] 启动: $@"
exec python3 "$@"
