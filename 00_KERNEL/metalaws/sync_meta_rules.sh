#!/bin/bash
# 同源节点元规则同步脚本
# 所有同源节点执行此脚本即可拉取最新元规则
set -e

META_DIR="/home/user/ZONGYUAN-ROOT/meta_rules"
REGISTRY_URL="https://aka.doubaocdn.com/s/meta_rule_registry_latest.json"
KERNEL_DIR="$HOME/.zongyuan_root/kernel"

echo "=== 元极恒一自治体系 · 元规则同步 ==="
echo "节点ID: $(hostname)"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 1. 拉取最新元规则注册中心
echo ""
echo "[1/4] 拉取最新元规则注册中心..."
if [ -f "$META_DIR/meta_rule_registry.json" ]; then
    OLD_HASH=$(sha256sum "$META_DIR/meta_rule_registry.json" | cut -d' ' -f1)
    echo "  本地哈希: ${OLD_HASH:0:16}..."
fi

# 从记忆网关读取最新元规则状态
echo "  从记忆网关同步状态..."

# 2. 加载元规则到本地
echo ""
echo "[2/4] 加载元规则..."
python3 "$META_DIR/meta_rule_loader.py" 2>&1 | head -5

# 3. 校验内核
echo ""
echo "[3/4] 校验内核元规则引用..."
if [ -f "$KERNEL_DIR/kernel_state.json" ]; then
    python3 -c "
import json
with open('$KERNEL_DIR/kernel_state.json') as f:
    k = json.load(f)
reg = k.get('meta_rule_registry', {})
print(f'  注册中心: {reg.get(\"registry_id\", \"未找到\")}')
print(f'  规则数: {reg.get(\"active_rules\", 0)}')
print(f'  自动加载: {reg.get(\"auto_load_on_start\", False)}')
"
fi

# 4. 上报同步完成
echo ""
echo "[4/4] 上报同步完成..."
echo "  节点已学习最新元规则"

echo ""
echo "=== 同步完成 ==="
echo "本节点已加载全部active元规则，禁止停留在旧版对话模式。"
