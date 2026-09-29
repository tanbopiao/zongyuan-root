# Gitee 最大化利用规划 V1.0
确权：DID-BR-000002｜Ω₀⊂⊙∞⊂Ω
日期：2026-09-20｜子域：SD-RND-001

---

## 一、当前现状
| 项 | 现状 |
|---|---|
| 仓库 | huodouai-website |
| 分支 | web-deploy（已推送 dd25d71） |
| 内容 | 作品库部署文件（works_data、gallery、缩略图、视频） |
| 作用 | 云端部署通道（cron pull 到 web root） |

## 二、最大化利用规划（6 大方向）

### 方向 1：多仓库矩阵（按子域拆分）
| 仓库 | 用途 | 对应子域 |
|---|---|---|
| huodouai-website | 官网+作品库部署 | SD-IP-001 |
| zongyuan-root-truths | 真值库+元法则+锁档凭证 | SD-RND-001 |
| kunlun-assets | 数字资产归档（图片/视频/凭证） | SD-AST-001 |
| kunlun-docs | SOP+技术文档+方案库 | SD-RND-001 |

### 方向 2：分支策略
| 分支 | 用途 |
|---|---|
| main | 生产稳定版 |
| web-deploy | 部署分支（cron pull 到云端） |
| dev | 开发测试 |
| feature/* | 功能分支 |

### 方向 3：静态资源托管（零成本 CDN）
- 图片/视频/文档全部 push 到 Gitee raw 链接
- 直接用 `raw.githubusercontent` 类似的 `raw.gitee.com` 链接引用
- 作品库、文档站直接加载 Gitee 静态资源

### 方向 4：Gitee Pages 文档站
- 免费静态站点托管
- 部署 SOP 文档、技术方案、资产目录
- 域名：`huodouai-website.gitee.io`

### 方向 5：四层备份的第二层
- Gitee = 云服务器备份层
- 所有本地资产 push 到 Gitee 即完成云端备份
- 异地灾备：魔搭 CPU 冷备（第四层）

### 方向 6：版本管理 + 变更追溯
- 所有资产版本历史可追溯
- commit 记录 = 变更日志
- tag 标记版本里程碑（V1.0/V1.1/V2.0）

## 三、零成本合规确认
| 项 | 状态 |
|---|---|
| 仓库容量 | ✅ 公开仓库免费不限 |
| Pages | ✅ 免费 |
| raw 链接 | ✅ 免费 |
| 无付费功能 | ✅ 纯免费 |
| 无 SSH 直连 | ✅ 走 HTTPS git |

## 四、实施步骤
1. 现有 huodouai-website 继续用于作品库部署
2. 新建 zongyuan-root-truths 仓库用于真值+元法则+锁档
3. 新建 kunlun-assets 仓库用于数字资产归档
4. 配置 Gitee Pages 文档站
5. 所有本地资产定期 push 到对应仓库
6. 云端 cron pull 拉取部署

---
Gitee 最大化利用 V1.0｜SD-RND-001
