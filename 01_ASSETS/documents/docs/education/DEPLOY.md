# 火斗云智·教育数字化中台 官网部署指南

## 部署包信息

- **包名**: edu-midplatform-v1.0.0-deploy.tar.gz
- **大小**: 28KB
- **版本**: v1.0.0
- **确权**: ZONGYUAN-ROOT-EDU-MIDPLATFORM / DID-EDU-MIDPLATFORM-v1.0

## 快速部署（3步）

### 第1步：上传部署包到服务器

```bash
# 本地执行，上传到服务器
scp edu-midplatform-v1.0.0-deploy.tar.gz root@你的服务器IP:/opt/
```

### 第2步：解压并执行部署脚本

```bash
# 服务器上执行
cd /opt
tar -xzf edu-midplatform-v1.0.0-deploy.tar.gz
cd edu-midplatform
chmod +x deploy.sh
sudo ./deploy.sh
```

部署脚本会自动完成：
- 安装 Python3 和依赖
- 部署到 /opt/edu-midplatform
- 配置 systemd 服务（开机自启）
- 启动服务并验证

### 第3步：访问验证

浏览器打开：`http://你的服务器IP:8000`

演示账号：**demo / demo123**

---

## 配置域名（可选）

如果需要通过域名80端口访问，配置Nginx反向代理：

```bash
# 1. 安装nginx
apt install nginx -y  # 或 yum install nginx

# 2. 复制配置并修改域名
cp nginx.conf /etc/nginx/conf.d/edu-midplatform.conf
vim /etc/nginx/conf.d/edu-midplatform.conf  # 修改server_name为你的域名

# 3. 重载nginx
nginx -t && systemctl reload nginx
```

---

## 对接真实大模型（可选）

默认使用Mock模拟模式，无需API Key。对接真实大模型：

```bash
# 编辑服务配置
systemctl edit edu-midplatform

# 添加以下内容（替换为你的真实配置）：
[Service]
Environment="AI_PROVIDER=openai"
Environment="AI_API_KEY=你的API_KEY"
Environment="AI_API_BASE=https://api.openai.com/v1"
Environment="AI_MODEL=gpt-3.5-turbo"

# 重启服务
systemctl restart edu-midplatform
```

支持任何OpenAI兼容格式的API接口。

---

## 服务管理命令

```bash
# 查看状态
systemctl status edu-midplatform

# 重启
systemctl restart edu-midplatform

# 停止
systemctl stop edu-midplatform

# 查看实时日志
journalctl -u edu-midplatform -f

# 查看最近100行日志
journalctl -u edu-midplatform -n 100
```

---

## 数据备份

数据库文件位置：`/opt/edu-midplatform/edu_midplatform.db`

```bash
# 备份
cp /opt/edu-midplatform/edu_midplatform.db /backup/edu_$(date +%Y%m%d).db

# 恢复
cp /backup/edu_xxx.db /opt/edu-midplatform/edu_midplatform.db
systemctl restart edu-midplatform
```

---

## 端口说明

| 端口 | 用途 | 说明 |
|------|------|------|
| 8000 | 应用服务 | FastAPI默认端口 |
| 80 | Nginx反向代理 | 可选，配置域名后使用 |

---

## 防火墙配置

```bash
# Ubuntu/Debian
ufw allow 8000/tcp
ufw allow 80/tcp

# CentOS
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload
```

---

## 部署检查清单

- [ ] 服务器Python3已安装
- [ ] 部署包已上传并解压
- [ ] deploy.sh已执行，服务状态为running
- [ ] 浏览器可访问 http://IP:8000
- [ ] 登录demo账号正常
- [ ] PPT生成功能测试通过
- [ ] （可选）Nginx域名配置完成
- [ ] （可选）真实大模型API对接完成
- [ ] （可选）数据库备份策略配置

---

## 技术支持

- 体系名称：火斗云智·教育数字化中台
- 内部代号：ZONGYUAN-ROOT EDU-MIDPLATFORM
- 最高主权：DID-BR-000002
- 公益属性：全校师生永久免费
