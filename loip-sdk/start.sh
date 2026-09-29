#!/bin/bash
# LOIP 服务启动脚本
# 用法: ./start.sh [--port 8000] [--baseline ./baseline.json] [--backend auto]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认配置
PORT=${LOIP_PORT:-8000}
HOST=${LOIP_HOST:-0.0.0.0}
BASELINE=${LOIP_BASELINE:-./data/baseline.json}
AUDIT_DIR=${LOIP_AUDIT_DIR:-./data/audit}
BACKEND=${LOIP_BACKEND:-auto}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --port) PORT="$2"; shift 2 ;;
        --host) HOST="$2"; shift 2 ;;
        --baseline) BASELINE="$2"; shift 2 ;;
        --audit-dir) AUDIT_DIR="$2"; shift 2 ;;
        --backend) BACKEND="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# 创建数据目录
mkdir -p "$(dirname "$BASELINE")" "$AUDIT_DIR"

echo "============================================"
echo "  LOIP 逻辑本体智能协议服务"
echo "============================================"
echo "  版本: $(python3 -c 'from loip import __version__; print(__version__)' 2>/dev/null || echo '0.2.0')"
echo "  地址: http://$HOST:$PORT"
echo "  文档: http://$HOST:$PORT/docs"
echo "  基线: $BASELINE"
echo "  审计: $AUDIT_DIR"
echo "  后端: $BACKEND"
echo "============================================"

# 检查依赖
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "[LOIP] 安装API服务依赖..."
    pip install -q fastapi uvicorn pydantic
fi

# 启动服务
exec python3 -m loip.api_server \
    --host "$HOST" \
    --port "$PORT" \
    --baseline "$BASELINE" \
    --audit-dir "$AUDIT_DIR" \
    --backend "$BACKEND"
