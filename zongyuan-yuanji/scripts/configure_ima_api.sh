#!/bin/bash
# IMA OpenAPI 凭证配置脚本

echo "========================================"
echo "  🚀 IMA OpenAPI 凭证配置工具"
echo "========================================"
echo ""

# 检查是否已有凭证
if [ -f ~/.config/ima/client_id ] && [ -f ~/.config/ima/api_key ]; then
    echo "⚠️  已发现配置文件："
    echo "   client_id: $(head -c 20 ~/.config/ima/client_id)...[隐藏]"
    echo "   api_key:   $(head -c 20 ~/.config/ima/api_key)...[隐藏]"
    echo ""
    read -p "是否覆盖？(y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "❌ 取消操作"
        exit 0
    fi
fi

echo ""
echo "请前往 https://ima.qq.com/agent-interface 获取凭证"
echo ""

read -p "请输入 Client ID: " CLIENT_ID
read -sp "请输入 API Key: " API_KEY
echo ""

# 验证输入
if [ -z "$CLIENT_ID" ] || [ -z "$API_KEY" ]; then
    echo "❌ Client ID 或 API Key 为空，退出"
    exit 1
fi

# 创建目录
mkdir -p ~/.config/ima

# 写入凭证
echo "$CLIENT_ID" > ~/.config/ima/client_id
echo "$API_KEY" > ~/.config/ima/api_key

# 设置权限
chmod 600 ~/.config/ima/client_id
chmod 600 ~/.config/ima/api_key

echo ""
echo "✅ 配置成功！"
echo ""
echo "凭证路径:"
echo "  ~/.config/ima/client_id"
echo "  ~/.config/ima/api_key"
echo ""
echo "测试连接..."

# 测试（可选）
if command -v node &> /dev/null; then
    cd /.octop/workspaces/main/skills/ima/ima-skill
    
    # 导出环境变量
    export IMA_OPENAPI_CLIENTID="$CLIENT_ID"
    export IMA_OPENAPI_APIKEY="$API_KEY"
    
    echo "✅ 环境变量已设置"
else
    echo "⚠️  Node.js 未安装，无法测试 API"
fi

echo ""
echo "🎉 IMA OpenAPI 配置完成！"
