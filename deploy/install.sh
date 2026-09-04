#!/bin/bash
# 火斗云智 AIOS 一键部署脚本 v9.11
set -e

LICENSE_KEY=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --license) LICENSE_KEY="$2"; shift 2 ;;
    --upgrade) UPGRADE=1; shift ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

echo "═══════════════════════════════════════"
echo " 火斗云智 AIOS 一键部署 v9.11"
echo "═══════════════════════════════════════"

# 1. 环境检测
echo "[1/6] 环境检测..."
python3 --version || { echo "需要Python3.10+"; exit 1; }
pip3 install fastapi uvicorn chromadb requests pyyaml 2>/dev/null | tail -1

# 2. 目录初始化
echo "[2/6] 目录初始化..."
mkdir -p /opt/ZONGYUAN-ROOT/{Ω-Brainμ,meta_order,multi_writer,customer_success,truth_architecture,memory_chain,backup,backups,logs,deploy,gov-ai,event_driven,federation,telemetry}

# 3. 真值基座初始化
echo "[3/6] 真值基座初始化..."
# （从安装包复制真值文件）

# 4. 服务配置
echo "[4/6] 12个systemd服务配置..."
for svc in vector omega-brain loip ance anchor gov license monitor event federation meta idle-engine; do
  cat > /etc/systemd/system/zongyuan-${svc}.service << SVCEOF
[Unit]
Description=ZONGYUAN-ROOT ${svc}
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/ZONGYUAN-ROOT/run_${svc}.py
Restart=always
RestartSec=5
[Install]
WantedBy=zongyuan.target
SVCEOF
done

# 5. 授权激活
echo "[5/6] 授权激活..."
if [ -n "$LICENSE_KEY" ]; then
  echo "{\"license_key\":\"$LICENSE_KEY\",\"activated_at\":\"$(date -Iseconds)\"}" > /opt/ZONGYUAN-ROOT/.license
  echo "  授权码: $LICENSE_KEY"
else
  echo "  ⚠️ 未指定授权码，使用免费版（10条真值）"
fi

# 6. 启动服务
echo "[6/6] 启动服务..."
systemctl daemon-reload
systemctl enable zongyuan.target
systemctl start zongyuan.target

echo ""
echo "✅ 部署完成！"
echo "  控制台: http://$(hostname -I | awk '{print $1}')/console/"
echo "  政务中台: http://$(hostname -I | awk '{print $1}')/gov/"
echo "  元秩序API: http://127.0.0.1:8009/api/v1/meta/health"
