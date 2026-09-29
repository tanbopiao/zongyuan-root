#!/bin/bash
# ============================================================
# ZONGYUAN-ROOT 云服务器一键部署脚本
# 用法: bash deploy.sh [安装路径]
# 默认安装到当前目录
# ============================================================

set -e

INSTALL_DIR="${1:-$(pwd)}"
OLD_PATH="/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT"
NEW_PATH="$INSTALL_DIR"

echo "============================================"
echo " ZONGYUAN-ROOT 云服务器部署"
echo " 安装路径: $NEW_PATH"
echo "============================================"

# 1. 检查Python
echo ""
echo "[1/5] 检查Python环境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "错误: 未找到python3，请先安装Python 3.10+"
    exit 1
fi

# 2. 安装依赖
echo ""
echo "[2/5] 安装Python依赖..."
pip3 install -r "$NEW_PATH/requirements.txt" -q 2>&1 | tail -3 || {
    echo "警告: 部分依赖安装失败，尝试继续..."
}

# 3. 路径替换（解决硬编码问题）
echo ""
echo "[3/5] 替换硬编码路径..."
COUNT=0
for f in $(find "$NEW_PATH" -name "*.py" -not -path "*/.git/*" -not -path "*/__pycache__/*"); do
    if grep -q "$OLD_PATH" "$f" 2>/dev/null; then
        sed -i "s|$OLD_PATH|$NEW_PATH|g" "$f"
        COUNT=$((COUNT + 1))
    fi
done
echo "  已替换 $COUNT 个文件中的路径"

# 4. 创建必要目录
echo ""
echo "[4/5] 创建运行时目录..."
mkdir -p "$NEW_PATH/logs"
mkdir -p "$NEW_PATH/executor"
mkdir -p "$NEW_PATH/lock_archive"
mkdir -p "$NEW_PATH/cache/vector_cache"
echo "  目录创建完成"

# 5. 启动服务
echo ""
echo "[5/5] 启动Ω-Brainμ服务..."
cd "$NEW_PATH/omega_brain"

# 方式A: 直接启动（前台）
echo ""
echo "============================================"
echo " 部署完成！启动方式："
echo "============================================"
echo ""
echo "方式1 - 前台启动（调试用）:"
echo "  cd $NEW_PATH/omega_brain"
echo "  python3 omega_brain_service.py"
echo ""
echo "方式2 - 守护进程启动（推荐）:"
echo "  cd $NEW_PATH/omega_brain"
echo "  python3 daemon_manager.py start"
echo "  python3 daemon_manager.py status"
echo "  python3 daemon_manager.py stop"
echo ""
echo "方式3 - uvicorn启动（生产推荐）:"
echo "  cd $NEW_PATH/omega_brain"
echo "  uvicorn omega_brain_service:app --host 0.0.0.0 --port 8765 --workers 1"
echo ""
echo "健康检查: curl http://127.0.0.1:8765/health"
echo "API文档:  http://127.0.0.1:8765/docs"
echo "============================================"
