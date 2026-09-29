# 石猴余脉基准作品库 · 线上部署状态报告

确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-20 01:25

## 部署目标
将本地基准作品库（23 图 + 23 webp + works_data.json + gallery 页面）部署至线上作品库 drama.huodouai.com

## 部署通道（最终采用）
**Gitee 官网 git 通道**（唯一合法通道，SSH 铁律禁止 + /api/upload 502 待修复）

```
本地 → Gitee web-deploy 分支 → 云端 5min cron pull → /www/wwwroot/huodouai.com 与 www.huodouai.com
```

## 已成功 ✅
| 项目 | 结果 |
|---|---|
| Gitee 推送 | `d9470cf`（web-deploy 分支） |
| works_data.json | 23 条作品元数据，已推送并核验（远程 total=23） |
| 缩略图 | 23 张 webp（kd02/kd03/kd04），已推送并核验 |
| gallery 页面 | gallery-baseline-v1.html，已推送 |
| README-DEPLOY.md | 部署说明已推送 |
| 云端指令上报 | `ZONGYUAN.DEPLOY.DRAMA.GALLERY.READY.20260920`（请求执行层拉取） |
| 状态记录上报 | `ZONGYUAN.DEPLOY.DRAMA.GALLERY.STATUS.20260920` |

## 阻塞项 ⚠️（云端侧，非本地可解）
- 云端 web root **未执行** `cloud_remote_setup.sh`（LOCK-WEBSITE-CLOUD-DEPLOY 状态为 `DEPLOY-READY-AWAITING-CLOUD`）
- 即：/www/wwwroot/* 尚未配置 git remote + cron pull，推送的文件不会自动上线
- `/api/upload` 502 待中枢修复（备用通道）

## 云端执行层需完成的一次性动作
```bash
# 在云端服务器执行一次（管理员窗口或执行层）：
curl -sL https://gitee.com/huodou-cloud-intelligence-aios/huodouai-website/raw/web-deploy/scripts/cloud_remote_setup.sh | bash
```
执行后：git remote 指向 web-deploy + cron 每 5 分钟 pull → 作品库自动上线。

## 上线后核验清单
- [ ] https://www.huodouai.com/drama/gallery-baseline-v1.html → 200 且含"石猴余脉基准作品库"标题
- [ ] https://www.huodouai.com/drama/works_data.json → total=23（当前为 219 旧数据）
- [ ] https://www.huodouai.com/drama/keyframes/kd04/thumbs/KD-04-IMG-01.webp → 200 image/webp

## 断点续传点（云端修复后自动续传）
Gitee web-deploy 分支已就绪 → 云端 pull 后即生效 → 回读核验 → 上报部署完成真值
