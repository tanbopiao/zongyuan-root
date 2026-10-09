#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 轻量化一键部署包生成器 v1.0
提取当前体系核心配置，生成新服务器快速部署脚本
包含：目录结构/核心服务/Nginx配置/元法则/基准/定时任务
"""
import json, os, time, subprocess

print("=" * 60)
print("轻量化一键部署包生成器")
print("=" * 60)

deploy_dir = "/opt/ZONGYUAN-ROOT/deploy_package"
os.makedirs(deploy_dir, exist_ok=True)

# 1. 生成部署清单
print("\n【1/5】生成部署清单...")
manifest = {
    "package_name": "ZONGYUAN-ROOT Lite Deploy",
    "version": "v1.0",
    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "estimated_time": "30分钟",
    "requirements": {
        "os": "OpenCloudOS 9.x / CentOS 9",
        "cpu": "2核+",
        "memory": "2GB+",
        "disk": "20GB+",
        "python": "Python 3.9+"
    },
    "core_services": [
        {"name": "记忆网关", "port": 9120, "script": "engine/scripts/unified_gateway_9120.py", "systemd": "zr-memory-gateway.service"},
        {"name": "飞书网关", "port": 8001, "script": "scripts/feishu_gateway.py", "systemd": "zongyuan-feishu-gateway.service"},
        {"name": "自愈守护", "port": None, "script": "scripts/unified_service_guard.sh", "cron": "*/2 * * * *"},
    ],
    "nginx_paths": [
        "/api/memory/", "/api/v1/gateway/status", "/aios-api/memory/",
        "/drama/", "/api/v1/*", "/ai-proxy/", "/vector/", "/docs/"
    ],
    "meta_rules_count": 101,
    "locked_files_count": 254,
}

with open(f"{deploy_dir}/manifest.json", "w") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print("✅ 部署清单已生成")

# 2. 生成一键部署脚本
print("\n【2/5】生成一键部署脚本...")
deploy_script = """#!/bin/bash
# ZONGYUAN-ROOT 轻量化一键部署脚本 v1.0
# 新服务器30分钟快速搭建
set -e

echo "=========================================="
echo "ZONGYUAN-ROOT 轻量化部署"
echo "=========================================="

# 步骤1: 目录结构
echo "[1/7] 创建目录结构..."
mkdir -p /opt/ZONGYUAN-ROOT/{engine/scripts,scripts,data,logs,baseline,backup}
mkdir -p /www/wwwroot/{www.huodouai.com,huodouai.com}

# 步骤2: 安装依赖
echo "[2/7] 安装系统依赖..."
yum install -y python3 python3-pip nginx sqlite curl crontabs 2>/dev/null || apt-get install -y python3 python3-pip nginx sqlite3 curl cron 2>/dev/null
pip3 install fastapi uvicorn requests 2>/dev/null || true

# 步骤3: 部署记忆网关
echo "[3/7] 部署记忆网关9120..."
# 此处上传unified_gateway_9120.py后启用
# cp unified_gateway_9120.py /opt/ZONGYUAN-ROOT/engine/scripts/

# 步骤4: 配置systemd服务
echo "[4/7] 配置systemd服务..."
cat > /etc/systemd/system/zr-memory-gateway.service << 'EOF'
[Unit]
Description=ZONGYUAN-ROOT Memory Gateway (9120)
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/opt/ZONGYUAN-ROOT
ExecStart=/usr/bin/python3 engine/scripts/unified_gateway_9120.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

# 步骤5: 配置Nginx反代
echo "[5/7] 配置Nginx反代..."
# 记忆网关反代配置（需API Key）
cat > /etc/nginx/conf.d/zongyuan.conf << 'EOF'
server {
    listen 443 ssl;
    server_name your-domain.com;
    # 记忆网关 - 读写需API Key
    location ^~ /api/memory/ {
        if ($http_x_api_key != "YOUR_API_KEY") { return 403; }
        proxy_pass http://127.0.0.1:9120/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    # 记忆网关 - 只读状态
    location = /api/v1/gateway/status {
        proxy_pass http://127.0.0.1:9120/api/status;
    }
}
EOF

# 步骤6: 配置定时任务
echo "[6/7] 配置定时任务..."
(crontab -l 2>/dev/null; echo "*/2 * * * * /opt/ZONGYUAN-ROOT/scripts/unified_service_guard.sh >> /opt/ZONGYUAN-ROOT/logs/guard.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 8 * * * /usr/bin/python3 /opt/ZONGYUAN-ROOT/scripts/health_check.py >> /opt/ZONGYUAN-ROOT/logs/health_check.log 2>&1") | crontab -

# 步骤7: 启动服务
echo "[7/7] 启动服务..."
systemctl daemon-reload
systemctl enable zr-memory-gateway
systemctl start zr-memory-gateway
systemctl enable nginx
systemctl start nginx

echo ""
echo "=========================================="
echo "部署完成！"
echo "记忆网关: http://127.0.0.1:9120/api/status"
echo "下一步: 配置SSL证书 + 上传业务脚本 + 导入元法则"
echo "=========================================="
"""

with open(f"{deploy_dir}/deploy.sh", "w") as f:
    f.write(deploy_script)
os.chmod(f"{deploy_dir}/deploy.sh", 0o755)
print("✅ 一键部署脚本已生成")

# 3. 导出元法则精简版
print("\n【3/5】导出元法则精简版...")
with open("/opt/ZONGYUAN-ROOT/meta_rule_set.json") as f:
    mr = json.load(f)
# 只导出L0/L1核心元法则
core_mr = [r for r in mr.get("meta_rules", []) if r.get("priority") in ["L0", "L1"]]
with open(f"{deploy_dir}/core_meta_rules.json", "w") as f:
    json.dump({"version": mr["version"], "core_rules": core_mr, "total_core": len(core_mr)}, f, ensure_ascii=False, indent=2)
print(f"✅ 已导出{len(core_mr)}条L0/L1核心元法则")

# 4. 生成部署SOP文档
print("\n【4/5】生成部署SOP...")
sop = """# ZONGYUAN-ROOT 轻量化部署SOP

## 前置准备
- 服务器：2核2G+，OpenCloudOS/CentOS 9
- 域名：已解析到服务器IP
- SSL证书：已申请

## 七步部署
1. 创建目录结构
2. 安装系统依赖(Python3/Nginx/SQLite)
3. 部署记忆网关9120
4. 配置systemd服务
5. 配置Nginx反代(记忆网关/短剧API)
6. 配置定时任务(自愈守护/健康检查)
7. 启动服务并验证

## 验证清单
- [ ] curl http://127.0.0.1:9120/api/status 返回JSON
- [ ] systemctl status zr-memory-gateway 显示running
- [ ] Nginx配置测试通过 nginx -t
- [ ] 定时任务已注册 crontab -l
- [ ] 元法则已导入 meta_rule_set.json

## 后续扩展
- 导入完整元法则(101条)
- 部署短剧API(8100)
- 部署向量数据库(8014)
- 部署知识图谱(8070)
- 配置飞书网关(8001)
- 部署官网页面
"""
with open(f"{deploy_dir}/DEPLOY_SOP.md", "w") as f:
    f.write(sop)
print("✅ 部署SOP已生成")

# 5. 打包
print("\n【5/5】打包部署包...")
result = subprocess.run(["tar", "-czf", f"{deploy_dir}/zongyuan-lite-deploy-v1.0.tar.gz",
                        "-C", deploy_dir, "manifest.json", "deploy.sh", "core_meta_rules.json", "DEPLOY_SOP.md"],
                       capture_output=True, text=True)
size = os.path.getsize(f"{deploy_dir}/zongyuan-lite-deploy-v1.0.tar.gz")
print(f"✅ 部署包已生成: {size//1024}KB")

print("\n" + "=" * 60)
print("轻量化部署包生成完成")
print("=" * 60)
print(f"位置: {deploy_dir}/")
print(f"包含: manifest.json / deploy.sh / core_meta_rules.json / DEPLOY_SOP.md")
print(f"打包: zongyuan-lite-deploy-v1.0.tar.gz ({size//1024}KB)")
