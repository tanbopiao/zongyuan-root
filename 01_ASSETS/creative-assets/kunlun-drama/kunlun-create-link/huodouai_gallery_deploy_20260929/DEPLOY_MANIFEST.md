# DEPLOY_MANIFEST · 部署包自述

> **包名**：huodouai_gallery_deploy_20260929
> **生成时间**：2026-09-29
> **目标**：https://www.huodouai.com/gallery/kunlun-keyframes/
> **确权**：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT

---

## 一、文件清单

```
huodouai_gallery_deploy_20260929/
├── deploy_kunlun_gallery.sh    # 一键部署脚本（本地→服务器，rsync+ssh）
├── preflight_check.sh          # 部署前本地自检（只读，不需要服务器通道）
├── nginx/
│   └── kunlun-keyframes.conf    # nginx location 片段 + 完整 server 块示例
├── README_部署指南.md           # 三通道部署指南（SSH/FTP/宝塔）+ 验证 + 回滚
├── DEPLOY_MANIFEST.md           # 本文件
└── probe_report.md             # 官网只读探测报告
```

| 文件 | 用途 | 执行位置 | 是否需要服务器凭据 |
|------|------|----------|-------------------|
| `preflight_check.sh` | 本地自检：HTML存在性/图片URL抽样302→200/确权标识 | 本地 | 否 |
| `deploy_kunlun_gallery.sh` | 一键部署：rsync推送+ssh配置nginx+验证 | 本地（连远程） | **是（用户export）** |
| `nginx/kunlun-keyframes.conf` | nginx 配置片段，需粘贴到现有 443 server 块 | 服务器 | 否（文本文件） |
| `README_部署指南.md` | 三通道操作手册 | 阅读 | - |
| `probe_report.md` | 2026-09-29 官网探测结果 | 阅读 | - |

---

## 二、占位符变量说明

`deploy_kunlun_gallery.sh` 启动时强制检查以下环境变量，**未设置则立即退出**。本包不包含任何真实值：

| 变量名 | 含义 | 示例（用户自行填写） |
|--------|------|---------------------|
| `SERVER_HOST` | 服务器 IP 或域名 | `1.2.3.4` 或 `www.huodouai.com` |
| `SERVER_USER` | SSH 登录用户 | `root` / `ubuntu` |
| `SERVER_PORT` | SSH 端口 | `22` |
| `SSH_KEY` | 私钥文件路径 | `~/.ssh/id_rsa` |
| `HTML_SRC` | 本地画廊 HTML 路径（可选） | `../昆仑洞天作品关键帧画廊.html` |
| `SITE_DIR` | 服务器端站点目录（可选） | `/var/www/kunlun-keyframes` |
| `DRY_RUN` | 演练模式（可选） | `1` = 只打印命令不执行 |

**示例执行流程**：
```bash
export SERVER_HOST='您的服务器IP'
export SERVER_USER='root'
export SERVER_PORT='22'
export SSH_KEY='~/.ssh/id_rsa'
bash deploy_kunlun_gallery.sh
```

---

## 三、设计原则

1. **绝不硬编码凭据**：所有服务器连接参数均为环境变量，脚本开头逐一检查。
2. **幂等**：重复执行不会重复添加 nginx 配置（会先备份旧文件再覆盖）。
3. **自动备份**：每次部署自动备份旧 `index.html` 和 nginx 配置（带时间戳后缀）。
4. **DRY_RUN 模式**：`DRY_RUN=1` 可先演练，不实际连接服务器。
5. **安全头继承**：官网已有 HSTS / X-Frame-Options / X-Content-Type-Options 等安全头，本画廊继承之；额外追加 DID/本体锚定头。
6. **单文件静态托管**：画廊为单 HTML，图片走魔搭公网 CDN，服务器无需存图。

---

## 四、硬约束合规声明

- [x] 本包**不包含**任何真实服务器 IP、密码、私钥
- [x] 本包生成过程中**未发起**任何到用户服务器的 ssh/scp/ftp/rsync 连接
- [x] 所有需服务器通道的步骤均用 `[用户提供: ...]` 占位符标注
- [x] 脚本均含 `set -euo pipefail`、备份逻辑、中文注释
- [x] README 首页明确标注"由您在服务器上执行；本方案不代您操作服务器"

---

*Ω₀⊂⊙∞⊂Ω · DID-BR-000002*
