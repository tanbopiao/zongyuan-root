# 火斗云智AIOS 快速部署指南（QuickStart）

> 面向非技术人员 · 30分钟完成部署 · 每一步都有详细说明

---

## 📋 部署前准备

### 你需要什么？
1. 一台云服务器（Linux系统，1GB内存以上）
2. 一个域名（可选，用IP也可以）
3. 5分钟时间

### 服务器推荐配置
- CPU：1核以上
- 内存：1GB以上
- 磁盘：10GB以上
- 系统：Ubuntu / CentOS / OpenCloudOS均可

---

## 🚀 第一步：连接服务器

### Windows用户
1. 下载 [Putty](https://www.putty.org/) 或使用Windows自带的终端
2. 输入服务器IP地址，端口22
3. 输入用户名（通常是root）和密码

### Mac用户
打开终端，输入：
```bash
ssh root@你的服务器IP
```

---

## 🔍 第二步：检查环境

登录服务器后，运行环境检测脚本：

```bash
# 先拉取代码
git clone https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT.git
cd ZONGYUAN-ROOT

# 运行环境检测
python3 scripts/env_check.py
```

### 预期输出
```
==================================================
  火斗云智AIOS 环境检测
==================================================

  [✓ 通过] Python版本
         当前: 3.10.12
         要求: >= 3.8

  [✓ 通过] 磁盘空间
         当前: 剩余 40.0 GB
         要求: >= 10 GB

  ...

  检测完成: 7 通过, 0 失败
==================================================
  ✓ 环境检查全部通过，可以部署！
```

如果有失败项，按提示修复后再继续。

---

## 📦 第三步：部署展示页

### 一键部署命令
```bash
# 进入项目目录
cd /opt/ZONGYUAN-ROOT

# 拉取最新代码
git pull origin main

# 创建Web目录并复制文件
mkdir -p /www/wwwroot/www.example.com/diff
cp showcase-page/differential_capabilities_v2.html /www/wwwroot/www.example.com/diff/index.html

# 设置权限
chmod 644 /www/wwwroot/www.example.com/diff/index.html
```

> 注意：把 `/www/wwwroot/www.example.com` 换成你实际的Web根目录

---

## ✅ 第四步：验证部署

```bash
# 本地验证
curl -I http://localhost/diff/

# 预期输出
HTTP/1.1 200 OK
Content-Type: text/html
```

然后在浏览器访问：
```
http://你的服务器IP/diff/
```

如果能看到"火斗云智AIOS · 差异化能力矩阵"页面，说明部署成功！

---

## 🔧 常见问题排查

### 问题1：访问显示404

**原因：** Nginx配置了SPA路由，所有路径都重写到首页

**解决：** 
1. 检查Nginx配置：`cat /www/server/panel/vhost/nginx/你的域名.conf`
2. 找到 `try_files $uri /index.html;` 这行
3. 在前面加一行：`location = /diff.html { try_files $uri =404; }`
4. 重启Nginx：`nginx -s reload`

---

### 问题2：git pull失败

**原因：** 网络问题或权限问题

**解决：**
```bash
# 检查网络
ping gitee.com

# 检查Git凭证
cd /opt/ZONGYUAN-ROOT
git remote -v

# 手动拉取
git fetch origin
git reset --hard origin/main
```

---

### 问题3：文件权限错误

**原因：** Nginx用户没有权限读取文件

**解决：**
```bash
# 设置正确权限
chown www:www /www/wwwroot/www.example.com/diff/index.html
chmod 644 /www/wwwroot/www.example.com/diff/index.html
```

---

### 问题4：Python版本太低

**原因：** 系统自带Python版本低于3.8

**解决（Ubuntu）：**
```bash
apt update
apt install python3.10
```

**解决（CentOS）：**
```bash
yum install python3
```

---

## 🎯 下一步

部署成功后，你可以：

1. **访问在线Demo** → `/demo/` 体验握手流程
2. **使用校验工具** → `/checker/` 上传文件校验哈希
3. **查看API文档** → `/docs/api/` 了解接口用法
4. **集成到你的网站** → 在导航栏添加入口链接

---

## 📞 需要帮助？

如果遇到无法解决的问题：
1. 先看上方"常见问题排查"
2. 再看 `doc/faq_expanded.md` 完整FAQ
3. 联系技术支持，提供：
   - 服务器操作系统
   - 报错信息截图
   - 执行的命令和输出

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ QuickStart v1.0
