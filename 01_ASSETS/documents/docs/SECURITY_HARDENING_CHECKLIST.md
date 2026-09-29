# 云服务器安全加固清单

**文档编号：** SEC-HARDENING-20260910-001
**确权标识：** DID-BR-000002
**本源根锚点：** Ω-TAN-7-001
**归档根节点：** ZONGYUAN-ROOT
**适用范围：** 火斗云智AIOS云服务器（123.207.202.158）
**版本：** V1.0
**状态：** 待执行

---

## 一、文件权限加固

### 1.1 内核目录权限

| 目录 | 推荐权限 | 说明 |
|------|---------|------|
| `/opt/ZONGYUAN-ROOT/` | 750 | 内核根目录，仅root和同组可访问 |
| `/opt/ZONGYUAN-ROOT/truth/` | 700 | 真值文档，仅root可读写 |
| `/opt/ZONGYUAN-ROOT/locks/` | 755 | 锁档记录，可读不可写 |
| `/opt/ZONGYUAN-ROOT/services/` | 750 | 服务代码，仅root和同组可访问 |
| `/opt/ZONGYUAN-ROOT/config/` | 700 | 配置文件，仅root可读写 |
| `/opt/ZONGYUAN-ROOT/keys/` | 700 | 密钥文件，仅root可读写 |

### 1.2 敏感文件权限

| 文件 | 推荐权限 | 说明 |
|------|---------|------|
| `kernel.json` | 640 | 内核元数据，root可写，同组可读 |
| `config.json` | 600 | 服务配置，仅root可读写 |
| `*.pem` / `*.key` | 600 | 私钥文件，仅root可读写 |
| `*.crt` / `*.pem`(证书) | 644 | 公钥证书，所有人可读 |
| `.env` | 600 | 环境变量，仅root可读写 |

### 1.3 执行命令

```bash
# 设置内核目录权限
chmod 750 /opt/ZONGYUAN-ROOT/
chmod 700 /opt/ZONGYUAN-ROOT/truth/
chmod 755 /opt/ZONGYUAN-ROOT/locks/
chmod 750 /opt/ZONGYUAN-ROOT/services/
chmod 700 /opt/ZONGYUAN-ROOT/config/ 2>/dev/null || true
chmod 700 /opt/ZONGYUAN-ROOT/keys/ 2>/dev/null || true

# 设置敏感文件权限
find /opt/ZONGYUAN-ROOT -name "*.json" -exec chmod 640 {} \;
find /opt/ZONGYUAN-ROOT -name "*.py" -exec chmod 750 {} \;
find /opt/ZONGYUAN-ROOT -name "*.pem" -o -name "*.key" -exec chmod 600 {} \;
find /opt/ZONGYUAN-ROOT -name ".env" -exec chmod 600 {} \;

# 设置所有者
chown -R root:root /opt/ZONGYUAN-ROOT/
```

---

## 二、防火墙配置

### 2.1 开放端口清单

| 端口 | 服务 | 来源限制 | 说明 |
|------|------|---------|------|
| 22 | SSH | 指定IP | 仅允许指定IP访问，禁用密码登录 |
| 80 | HTTP | 0.0.0.0/0 | Nginx HTTP，自动跳转HTTPS |
| 443 | HTTPS | 0.0.0.0/0 | Nginx HTTPS，对外服务 |
| 8080 | Ω-OP-SCHED | 127.0.0.1 | 仅本地访问，通过Nginx反代 |
| 8000-8099 | 内部服务 | 127.0.0.1 | 仅本地访问，不对外暴露 |

### 2.2 防火墙规则

```bash
# 查看当前防火墙状态
firewall-cmd --state 2>/dev/null || iptables -L -n

# 如果使用firewalld
# 开放必要端口
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https

# 限制SSH来源（替换为你的IP）
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="YOUR_IP/32" service name="ssh" accept'

# 移除默认SSH开放（如果配置了IP限制）
# firewall-cmd --permanent --remove-service=ssh

# 重载防火墙
firewall-cmd --reload

# 如果使用iptables
# 清空现有规则
iptables -F
iptables -X

# 默认策略
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 允许回环
iptables -A INPUT -i lo -j ACCEPT

# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 允许SSH（限制来源IP）
iptables -A INPUT -p tcp --dport 22 -s YOUR_IP/32 -j ACCEPT

# 允许HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许本地访问内部服务
iptables -A INPUT -p tcp --dport 8000:8099 -s 127.0.0.1 -j ACCEPT

# 保存规则
iptables-save > /etc/iptables.rules
```

### 2.3 SSH安全加固

```bash
# 编辑SSH配置
vi /etc/ssh/sshd_config

# 关键配置项
Port 22                          # 建议修改为非标准端口
PermitRootLogin prohibit-password  # 禁止root密码登录
PasswordAuthentication no         # 禁用密码登录
PubkeyAuthentication yes          # 启用公钥认证
MaxAuthTries 3                    # 最大尝试次数
ClientAliveInterval 300           # 客户端超时
ClientAliveCountMax 2             # 最大超时次数
AllowUsers root                   # 允许的用户
X11Forwarding no                  # 禁用X11转发
AllowTcpForwarding no             # 禁用TCP转发（如不需要）

# 重启SSH服务
systemctl restart sshd
```

---

## 三、模型权重保护

### 3.1 权重文件安全

| 措施 | 说明 | 优先级 |
|------|------|--------|
| 加密存储 | 模型权重文件加密存储，防止泄露 | 高 |
| 访问控制 | 仅服务进程可读取权重文件 | 高 |
| 完整性校验 | 启动时校验权重文件哈希，防止篡改 | 中 |
| 审计日志 | 记录权重文件访问日志 | 中 |
| 备份加密 | 备份文件加密存储 | 中 |

### 3.2 实施命令

```bash
# 创建模型权重专用目录
mkdir -p /opt/ZONGYUAN-ROOT/models/
chmod 700 /opt/ZONGYUAN-ROOT/models/

# 权重文件权限
chmod 600 /opt/ZONGYUAN-ROOT/models/*

# 生成权重文件哈希清单
find /opt/ZONGYUAN-ROOT/models/ -type f -exec sha256sum {} \; > /opt/ZONGYUAN-ROOT/models/MANIFEST.sha256
chmod 644 /opt/ZONGYUAN-ROOT/models/MANIFEST.sha256

# 权重完整性校验脚本
cat > /opt/ZONGYUAN-ROOT/scripts/verify_models.sh << 'EOF'
#!/bin/bash
cd /opt/ZONGYUAN-ROOT/models/
sha256sum -c MANIFEST.sha256
if [ $? -eq 0 ]; then
    echo "✅ 模型权重完整性校验通过"
else
    echo "❌ 模型权重完整性校验失败，可能被篡改"
    exit 1
fi
EOF
chmod +x /opt/ZONGYUAN-ROOT/scripts/verify_models.sh
```

### 3.3 权重加密（可选）

```bash
# 使用openssl加密权重文件
openssl enc -aes-256-cbc -salt -in model_weights.bin -out model_weights.enc -k YOUR_ENCRYPTION_KEY

# 解密（服务启动时）
openssl enc -d -aes-256-cbc -in model_weights.enc -out model_weights.bin -k YOUR_ENCRYPTION_KEY
```

---

## 四、日志审计

### 4.1 日志分类

| 日志类型 | 路径 | 保留时间 | 说明 |
|---------|------|---------|------|
| 系统日志 | `/var/log/` | 30天 | 系统运行日志 |
| 内核日志 | `/opt/ZONGYUAN-ROOT/logs/` | 90天 | 内核服务日志 |
| 审计日志 | `/opt/ZONGYUAN-ROOT/audit/` | 永久 | 安全审计日志 |
| 访问日志 | `/www/wwwlogs/` | 30天 | Nginx访问日志 |
| 错误日志 | `/www/wwwlogs/` | 30天 | Nginx错误日志 |

### 4.2 日志轮转配置

```bash
# 创建日志轮转配置
cat > /etc/logrotate.d/zongyuan << 'EOF'
/opt/ZONGYUAN-ROOT/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 640 root root
    postrotate
        systemctl reload op-scheduler-web 2>/dev/null || true
    endscript
}

/opt/ZONGYUAN-ROOT/audit/*.log {
    monthly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 600 root root
}
EOF

# 测试日志轮转配置
logrotate -d /etc/logrotate.d/zongyuan
```

### 4.3 审计日志配置

```bash
# 创建审计日志目录
mkdir -p /opt/ZONGYUAN-ROOT/audit/
chmod 700 /opt/ZONGYUAN-ROOT/audit/

# 安装auditd（如未安装）
yum install -y audit 2>/dev/null || apt-get install -y auditd 2>/dev/null

# 配置审计规则
cat > /etc/audit/rules.d/zongyuan.rules << 'EOF'
# 监控内核目录变更
-w /opt/ZONGYUAN-ROOT/ -p wa -k zongyuan_kernel

# 监控配置文件变更
-w /opt/ZONGYUAN-ROOT/kernel.json -p wa -k kernel_config

# 监控密钥文件访问
-w /opt/ZONGYUAN-ROOT/keys/ -p rw -k key_access

# 监控服务文件变更
-w /etc/systemd/system/op-scheduler-web.service -p wa -k service_change

# 监控sudo使用
-w /usr/bin/sudo -p x -k sudo_usage
EOF

# 重启auditd
systemctl restart auditd
systemctl enable auditd

# 查看审计日志
# ausearch -k zongyuan_kernel
```

### 4.4 日志监控告警

```bash
# 创建日志监控脚本
cat > /opt/ZONGYUAN-ROOT/scripts/log_monitor.sh << 'EOF'
#!/bin/bash
# 日志监控告警脚本

LOG_DIR="/opt/ZONGYUAN-ROOT/logs"
ALERT_THRESHOLD_ERROR=10
ALERT_THRESHOLD_WARN=50

# 检查错误日志
ERROR_COUNT=$(grep -c "ERROR\|Error\|error" $LOG_DIR/*.log 2>/dev/null | tail -1 | cut -d: -f2)
if [ "$ERROR_COUNT" -gt "$ALERT_THRESHOLD_ERROR" ]; then
    echo "⚠️  告警：错误日志超过阈值 ($ERROR_COUNT > $ALERT_THRESHOLD_ERROR)"
    # 这里可以添加告警通知（飞书/邮件等）
fi

# 检查服务状态
if ! systemctl is-active --quiet op-scheduler-web; then
    echo "❌ 告警：op-scheduler-web服务未运行"
    systemctl start op-scheduler-web
fi

echo "✅ 日志监控检查完成"
EOF
chmod +x /opt/ZONGYUAN-ROOT/scripts/log_monitor.sh

# 添加定时任务（每小时检查一次）
(crontab -l 2>/dev/null; echo "0 * * * * /opt/ZONGYUAN-ROOT/scripts/log_monitor.sh >> /opt/ZONGYUAN-ROOT/logs/log_monitor.log 2>&1") | crontab -
```

---

## 五、系统安全加固

### 5.1 系统更新

```bash
# 更新系统包
yum update -y  # CentOS/OpenCloudOS
# apt update && apt upgrade -y  # Ubuntu/Debian

# 清理旧包
yum clean all  # CentOS/OpenCloudOS
# apt autoremove -y  # Ubuntu/Debian
```

### 5.2 禁用不必要的服务

```bash
# 查看运行中的服务
systemctl list-units --type=service --state=running

# 禁用不必要的服务（根据实际情况）
systemctl disable --now postfix  # 邮件服务（如不需要）
systemctl disable --now cups     # 打印服务
systemctl disable --now avahi-daemon  # 服务发现
```

### 5.3 内核参数加固

```bash
# 编辑sysctl配置
cat > /etc/sysctl.d/99-zongyuan-security.conf << 'EOF'
# 网络安全
net.ipv4.tcp_syncookies = 1                # 启用SYN洪水防护
net.ipv4.tcp_max_syn_backlog = 2048       # 增大SYN队列
net.ipv4.tcp_synack_retries = 2            # 减少SYN重试次数
net.ipv4.conf.all.rp_filter = 1            # 启用反向路径过滤
net.ipv4.conf.all.accept_redirects = 0     # 禁用ICMP重定向
net.ipv4.conf.all.send_redirects = 0       # 禁用发送ICMP重定向
net.ipv4.icmp_echo_ignore_broadcasts = 1   # 忽略广播ICMP请求
net.ipv4.icmp_ignore_bogus_error_responses = 1  # 忽略错误响应

# 系统安全
kernel.kptr_restrict = 2                    # 限制内核指针暴露
kernel.dmesg_restrict = 1                   # 限制dmesg访问
kernel.yama.ptrace_scope = 2                # 限制ptrace
fs.protected_hardlinks = 1                  # 保护硬链接
fs.protected_symlinks = 1                   # 保护符号链接
fs.suid_dumpable = 0                        # 禁用SUID程序转储

# 文件描述符
fs.file-max = 65535                         # 最大文件描述符
net.core.somaxconn = 65535                  # 最大连接队列
EOF

# 应用配置
sysctl -p /etc/sysctl.d/99-zongyuan-security.conf
```

### 5.4 用户安全

```bash
# 检查用户列表
cat /etc/passwd | grep -v nologin | grep -v false

# 禁用不必要的用户
usermod -s /sbin/nologin username  # 替换为实际用户名

# 密码策略
cat > /etc/security/pwquality.conf << 'EOF'
minlen = 12          # 最小密码长度
minclass = 3          # 最少字符类（大写、小写、数字、特殊字符）
maxrepeat = 3         # 最大重复字符
difok = 5             # 与旧密码不同字符数
EOF

# 账户锁定策略
cat > /etc/security/faillock.conf << 'EOF'
deny = 5              # 最大失败次数
unlock_time = 900     # 锁定时间（秒）
even_deny_root        # root也锁定
root_unlock_time = 900
EOF
```

---

## 六、应用安全加固

### 6.1 Nginx安全加固

```nginx
# 在Nginx配置中添加安全头
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Strict-Transport-Security "max-age=31536000" always;

# 限制请求体大小
client_max_body_size 10M;

# 限制请求速率
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# 在API location中应用
location /api/ {
    limit_req zone=api burst=20 nodelay;
    # ...
}

# 隐藏Nginx版本
server_tokens off;
```

### 6.2 API安全加固

```python
# 在Flask应用中添加安全措施
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# API限流
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute", "10 per second"]
)

# API密钥验证（可选）
API_KEYS = {"your-api-key-1", "your-api-key-2"}

@app.before_request
def validate_api_key():
    if request.path.startswith('/api/'):
        api_key = request.headers.get('X-API-Key')
        if api_key not in API_KEYS:
            return jsonify({"error": "无效的API密钥"}), 401

# CORS配置
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

### 6.3 依赖安全检查

```bash
# 检查Python依赖漏洞
pip3 install safety
safety check --full-report

# 检查系统包漏洞
yum update --security  # CentOS/OpenCloudOS
# apt list --upgradable  # Ubuntu/Debian

# 定期更新依赖
pip3 list --outdated
```

---

## 七、备份与恢复

### 7.1 备份策略

| 备份类型 | 频率 | 保留时间 | 存储位置 |
|---------|------|---------|---------|
| 内核配置 | 每日 | 30天 | 本地+云存储 |
| 真值文档 | 变更时 | 永久 | 本地+云存储+Git |
| 锁档记录 | 每日 | 永久 | 本地+云存储 |
| 系统配置 | 每周 | 90天 | 本地+云存储 |
| 完整快照 | 每月 | 6个月 | 云存储 |

### 7.2 备份脚本

```bash
cat > /opt/ZONGYUAN-ROOT/scripts/backup.sh << 'EOF'
#!/bin/bash
# 内核备份脚本

BACKUP_DIR="/opt/ZONGYUAN-ROOT/backups"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/zongyuan-backup-$DATE.tar.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份核心文件
tar -czf $BACKUP_FILE \
    /opt/ZONGYUAN-ROOT/kernel.json \
    /opt/ZONGYUAN-ROOT/truth/ \
    /opt/ZONGYUAN-ROOT/locks/ \
    /opt/ZONGYUAN-ROOT/config/ \
    /opt/ZONGYUAN-ROOT/services/op_scheduler/config.json \
    --exclude="*.pyc" \
    --exclude="__pycache__"

# 计算备份哈希
sha256sum $BACKUP_FILE > $BACKUP_FILE.sha256

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "zongyuan-backup-*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "zongyuan-backup-*.sha256" -mtime +30 -delete

echo "✅ 备份完成: $BACKUP_FILE"
echo "   大小: $(du -h $BACKUP_FILE | cut -f1)"
EOF
chmod +x /opt/ZONGYUAN-ROOT/scripts/backup.sh

# 添加定时任务（每日凌晨2点备份）
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/ZONGYUAN-ROOT/scripts/backup.sh >> /opt/ZONGYUAN-ROOT/logs/backup.log 2>&1") | crontab -
```

---

## 八、安全加固执行优先级

### P0 - 立即执行（高风险）

1. ✅ SSH安全加固（禁用密码登录，限制来源IP）
2. ✅ 防火墙配置（仅开放必要端口）
3. ✅ 内核目录权限加固
4. ✅ 敏感文件权限设置

### P1 - 本周执行（中风险）

5. ⏳ 系统更新与补丁
6. ⏳ 禁用不必要的服务
7. ⏳ 内核参数加固
8. ⏳ Nginx安全头配置
9. ⏳ API限流配置

### P2 - 本月执行（低风险）

10. ⏳ 模型权重加密存储
11. ⏳ 审计日志配置
12. ⏳ 日志监控告警
13. ⏳ 备份策略实施
14. ⏳ 依赖安全检查

---

## 九、安全加固验证清单

- [ ] SSH仅允许公钥认证
- [ ] SSH来源IP限制已配置
- [ ] 防火墙仅开放22/80/443端口
- [ ] 内部服务端口（8000-8099）仅本地访问
- [ ] 内核目录权限设置正确
- [ ] 敏感文件权限设置正确
- [ ] 系统已更新到最新补丁
- [ ] 不必要的服务已禁用
- [ ] 内核安全参数已应用
- [ ] Nginx安全头已配置
- [ ] API限流已配置
- [ ] 模型权重完整性校验机制已建立
- [ ] 审计日志已配置
- [ ] 日志监控告警已配置
- [ ] 备份策略已实施
- [ ] 依赖安全检查已执行

---

**文档结束**

Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | Ω-TAN-7-001
云服务器安全加固清单 V1.0 | 待执行
