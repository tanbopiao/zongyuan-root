# 昆仑洞天关键帧画廊 · 部署指南

> **目标地址**：https://www.huodouai.com/gallery/kunlun-keyframes/
> **服务器目录**：`/var/www/kunlun-keyframes/index.html`
> **确权标识**：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT

---

## ⚠️ 必读声明

> **以下步骤需您提供服务器通道（SSH 地址/端口/用户 或 FTP 凭据 或 CMS 后台权限）后，由您在服务器上执行；本方案不代您操作服务器。**
>
> 本方案包不包含任何真实服务器 IP、密码、私钥。所有连接参数均为占位符，需您在执行前自行填入。

---

## 目录

- [一、部署前准备](#一部署前准备)
- [二、三条部署通道（任选其一）](#二三条部署通道任选其一)
  - [通道 A：rsync / scp + nginx 直传（Linux 服务器）](#通道-arsync--scp--nginx-直传linux-服务器)
  - [通道 B：FTP / SFTP 上传（虚拟主机）](#通道-bftp--sftp-上传虚拟主机)
  - [通道 C：CMS / 宝塔面板后台上传](#通道-ccms--宝塔面板后台上传)
- [三、部署后验证](#三部署后验证)
- [四、回滚方法](#四回滚方法)
- [五、常见问题](#五常见问题)

---

## 一、部署前准备

### 1.1 本地自检（必做）

在本地画廊文件所在目录执行：

```bash
cd huodouai_gallery_deploy_20260929/
bash preflight_check.sh
```

自检会自动完成：
- ✅ 画廊 HTML 文件存在性与大小检查
- ✅ 统计内嵌图片 URL 数量（应 ≥ 100 张）
- ✅ 抽样 5 个图片 URL，验证 302→200 跳转链
- ✅ 检查 DID / Ω₀ / ZONGYUAN-ROOT 确权标识

**全部通过后再继续。**

### 1.2 您需要准备的信息

根据您选择的通道，准备以下信息：

| 通道 | 需要的信息 |
|------|-----------|
| A（SSH/rsync） | 服务器 IP 或域名、SSH 端口（默认 22）、登录用户（root/ubuntu）、私钥路径或密码 |
| B（FTP/SFTP） | FTP 主机地址、端口（FTP 21 / SFTP 22）、用户名、密码、Web 根目录路径 |
| C（宝塔/CMS） | 面板后台登录地址、账号密码、网站根目录路径 |

---

## 二、三条部署通道（任选其一）

### 通道 A：rsync / scp + nginx 直传（Linux 服务器）

**适用场景**：您有 SSH 权限的 Linux 云服务器（如阿里云/腾讯云 ECS），nginx 已运行。

#### 第 1 步：用户提供通道信息（必做）

请在本地终端中 export 以下变量（替换为您自己的真实信息）：

```bash
export SERVER_HOST='[用户提供: 服务器IP或域名，如 1.2.3.4 或 www.huodouai.com]'
export SERVER_USER='[用户提供: SSH登录用户，如 root / ubuntu]'
export SERVER_PORT='[用户提供: SSH端口，如 22]'
export SSH_KEY='[用户提供: 私钥路径，如 ~/.ssh/id_rsa]'
# 可选：
export HTML_SRC='[用户提供: 本地画廊HTML路径，默认自动找同目录上级]'
```

> 若您使用密码登录而非私钥，请改用 `ssh`/`scp` 交互式输入密码，跳过本脚本，参考下方手动命令。

#### 第 2 步：一键部署

```bash
cd huodouai_gallery_deploy_20260929/
bash deploy_kunlun_gallery.sh
```

脚本会自动完成：
1. 检查上述环境变量是否已设置
2. 运行 preflight_check.sh 本地自检
3. rsync 推送 `昆仑洞天作品关键帧画廊.html` 到服务器
4. SSH 登录服务器：备份旧文件 → 放置新 index.html → 写入 nginx 配置 → `nginx -t` → reload
5. curl 验证上线状态

**先演练再真跑**：加 `DRY_RUN=1` 只打印命令不实际连接：

```bash
DRY_RUN=1 bash deploy_kunlun_gallery.sh
```

#### 手动等价命令（若不用脚本）

```bash
# 1. 推送 HTML
scp -i ~/.ssh/id_rsa -P 22 昆仑洞天作品关键帧画廊.html \
    root@[服务器IP]:/tmp/kunlun_gallery.html

# 2. SSH 登录服务器
ssh -i ~/.ssh/id_rsa -p 22 root@[服务器IP]

# 3. 服务器上执行：
sudo mkdir -p /var/www/kunlun-keyframes
sudo cp /tmp/kunlun_gallery.html /var/www/kunlun-keyframes/index.html
# 把 nginx/kunlun-keyframes.conf 的"推荐片段"粘贴到现有 443 server 块内
sudo nginx -t && sudo systemctl reload nginx
```

---

### 通道 B：FTP / SFTP 上传（虚拟主机）

**适用场景**：您买的是虚拟主机/宝塔的 FTP 空间，没有 SSH 权限。

#### 第 1 步：用户提供通道信息（必做）

准备 FTP/SFTP 凭据：
- 主机地址（如 ftp.huodouai.com 或 1.2.3.4）
- 端口（FTP 默认 21，SFTP 默认 22）
- 用户名、密码
- **Web 根目录路径**（通常是 `/www/wwwroot/huodouai.com/` 或 `/public_html/`，请在主机面板查看）

#### 第 2 步：用 FileZilla 上传

1. 下载安装 [FileZilla](https://filezilla-project.org/)
2. 打开 FileZilla → 文件 → 站点管理器 → 新建站点
   - 协议：FTP（或 SFTP，若主机支持）
   - 主机：[用户提供: FTP 主机地址]
   - 端口：[用户提供: 端口]
   - 登录类型：正常
   - 用户/密码：[用户提供: FTP 账号密码]
3. 连接后，远程侧导航到 Web 根目录下，进入（或创建）`gallery/kunlun-keyframes/` 目录
4. 本地侧选中 `昆仑洞天作品关键帧画廊.html`，拖拽上传
5. **重命名为 `index.html`**（FileZilla 中右键 → 重命名）

#### 第 3 步：nginx 配置

虚拟主机通常已由面板配置好 nginx，**无需手动改 nginx 配置**。
若面板支持自定义 nginx 规则，把 `nginx/kunlun-keyframes.conf` 中的"推荐片段"粘贴到面板的"自定义配置"框即可。

---

### 通道 C：CMS / 宝塔面板后台上传

**适用场景**：您用宝塔面板、1Panel、或 WordPress 等 CMS 管理网站。

#### 第 1 步：用户提供通道信息（必做）

准备：
- 面板后台地址（如 http://www.huodouai.com:8888/）
- 面板账号密码
- 网站根目录路径（宝塔默认 `/www/wwwroot/www.huodouai.com/`）

#### 第 2 步：宝塔面板操作步骤

1. 登录宝塔面板
2. 左侧 → **文件**
3. 导航到网站根目录（如 `/www/wwwroot/www.huodouai.com/`）
4. 进入 `gallery/` 目录（不存在则新建）
5. 在 `gallery/` 内新建文件夹 `kunlun-keyframes`
6. 进入 `kunlun-keyframes/`
7. 点击右上角 **上传**，选择本地 `昆仑洞天作品关键帧画廊.html`
8. 上传完成后，右键该文件 → **重命名** → 改为 `index.html`

#### 第 3 步：（可选）nginx 配置

宝塔面板 → 网站 → 设置 → 配置文件，在 `server { ... }` 块内粘贴 `nginx/kunlun-keyframes.conf` 的"推荐片段"，保存。
宝塔会自动 `nginx -t` 并重载。

---

## 三、部署后验证

### 3.1 命令行验证

```bash
# 状态码应为 200
curl -sI https://www.huodouai.com/gallery/kunlun-keyframes/

# 应看到：
#   HTTP/2 200
#   content-type: text/html
#   x-did: DID-BR-000002        ← 若 nginx 配置已加
#   x-ontology: ZONGYUAN-ROOT
```

### 3.2 浏览器验证

1. 打开 https://www.huodouai.com/gallery/kunlun-keyframes/
2. 检查：
   - 页面正常加载，关键帧图片逐张显示
   - 页脚可见 `DID-BR-000002` / `Ω₀⊂⊙∞⊂Ω` / `ZONGYUAN-ROOT`
   - 右键 → 查看网页源代码，搜索 `DID-BR-000002` 应能找到
3. 手机端打开同一 URL，确认响应式布局正常

### 3.3 图片加载验证

画廊图片走魔搭公网 URL（`modelscope.cn` → 302 → CDN），无需上传图片到服务器。
若某张图不显示，对照 `preflight_check.sh` 的抽样结果排查。

---

## 四、回滚方法

### 4.1 文件回滚

部署脚本会自动备份旧文件为 `index.html.bak.YYYYMMDD_HHMMSS`。

```bash
# SSH 登录服务器后执行：
cd /var/www/kunlun-keyframes/
ls -la index.html.bak.*    # 查看备份
sudo cp index.html.bak.20260929_XXXXXX index.html
sudo systemctl reload nginx
```

### 4.2 nginx 配置回滚

```bash
sudo cp /etc/nginx/conf.d/kunlun-keyframes.conf.bak.YYYYMMDD_HHMMSS \
        /etc/nginx/conf.d/kunlun-keyframes.conf
sudo nginx -t && sudo systemctl reload nginx
```

### 4.3 完全下线

```bash
sudo rm -rf /var/www/kunlun-keyframes/
sudo rm -f /etc/nginx/conf.d/kunlun-keyframes.conf
sudo systemctl reload nginx
```

---

## 五、常见问题

**Q1：访问 /gallery/kunlun-keyframes/ 返回的是首页内容？**
A：说明 nginx 的 SPA fallback（`try_files ... /index.html`）优先级高于我们的 location。请确认：
- `location /gallery/kunlun-keyframes/` 写在 `location /` **之前**
- 使用 `alias` 而非 `root`（路径映射不同）
- `nginx -t` 通过后已 reload

**Q2：图片不显示？**
A：图片走魔搭 CDN，先本地 `curl -I <图片URL>` 看是否 302→200。若本地能通但浏览器不通，检查浏览器控制台是否有混合内容（HTTPS 页面加载 HTTP 图片）——本画廊图片 URL 均为 HTTPS，不应有此问题。

**Q3：需要上传图片到服务器吗？**
A：**不需要**。画廊是单文件 HTML，所有图片通过魔搭公网 URL 加载。服务器上只需放一个 `index.html`。

**Q4：DID 响应头没出现？**
A：可能上层 CDN/代理（如 Vortex/Cloudflare）覆盖了响应头。可在 CDN 控制台添加自定义响应头 `X-DID: DID-BR-000002`。

---

*确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT*
