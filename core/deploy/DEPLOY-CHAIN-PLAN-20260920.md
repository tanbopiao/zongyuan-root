# 作品库部署链路推演与打通方案
确权：DID-BR-000002｜Ω₀⊂⊙∞⊂Ω｜2026-09-20

---

## 一、完整链路推演（5 环）

```
[环1] 本地素材生产（media-library/）
  ↓ 图片/视频/缩略图/works_data.json/gallery页面
[环2] 打包推送 Gitee（web-deploy 分支）
  ↓ commit dd25d71，含 drama/ 目录全部文件
[环3] 云端执行层配置（cloud_remote_setup.sh）
  ↓ 配置 git remote + cron 每5min pull
[环4] 云端 web root 拉取（git pull web-deploy）
  ↓ 文件同步到 /www/wwwroot/huodouai.com/drama/
[环5] Nginx 对外服务 → 线上作品库生效
  ↓ https://www.huodouai.com/drama/gallery-baseline-v1.html
```

---

## 二、各环现状与阻塞点

| 环 | 环节 | 现状 | 阻塞 | 打通方式 |
|---|---|---|---|---|
| 环1 | 本地素材生产 | ✅ 完成 | 无 | 32图+1视频+缩略图+works_data+gallery页面 |
| 环2 | Gitee 推送 | ✅ 完成 | 无 | commit dd25d71，web-deploy 分支 |
| 环3 | 云端执行层配置 | ❌ 未执行 | cloud_remote_setup.sh 未在云端运行 | 云端执行层运行该脚本 |
| 环4 | web root 拉取 | ❌ 未同步 | git remote 未配置，cron 未设置 | 执行环3后自动 pull |
| 环5 | Nginx 对外服务 | ✅ 已有 drama 站点 | 无 | Nginx 已配置，文件同步后即生效 |

---

## 三、打通步骤（云端侧，一次性）

### 步骤 1：配置 git remote（cloud_remote_setup.sh）
```bash
# 在云端服务器执行
cd /www/wwwroot/huodouai.com
git remote remove origin 2>/dev/null
git remote add origin https://gitee.com/huodou-cloud-intelligence-aios/huodouai-website.git
git fetch origin web-deploy
git checkout -B web-deploy origin/web-deploy

# 双 root 同步
cd /www/wwwroot/www.huodouai.com
git remote remove origin 2>/dev/null
git remote add origin https://gitee.com/huodou-cloud-intelligence-aios/huodouai-website.git
git fetch origin web-deploy
git checkout -B web-deploy origin/web-deploy
```

### 步骤 2：配置 cron 自动 pull
```bash
# 每 5 分钟自动 pull
(crontab -l 2>/dev/null; echo "*/5 * * * * cd /www/wwwroot/huodouai.com && git pull -q origin web-deploy && cd /www/wwwroot/www.huodouai.com && git pull -q origin web-deploy >/dev/null 2>&1") | crontab -
```

### 步骤 3：立即手动 pull 一次
```bash
cd /www/wwwroot/huodouai.com && git pull origin web-deploy
cd /www/wwwroot/www.huodouai.com && git pull origin web-deploy
```

### 步骤 4：回读核验
```bash
# 核验 1：gallery 页面
curl -s https://www.huodouai.com/drama/gallery-baseline-v1.html | head -20
# 预期：含"昆仑洞天 · 石猴余脉作品库"

# 核验 2：works_data 数据
curl -s https://www.huodouai.com/drama/works_data.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('total:', d['total'])"
# 预期：total: 36

# 核验 3：缩略图
curl -s -o /dev/null -w "%{http_code} %{content_type}" https://www.huodouai.com/drama/keyframes/kd01/thumbs/KD-01-IMG-01.webp
# 预期：200 image/webp
```

---

## 四、当前断点续传点

| 项目 | 值 |
|---|---|
| Gitee 分支 | web-deploy |
| Gitee commit | dd25d71 |
| 部署内容 | drama/works_data.json（36条）+ gallery页面 + 32缩略图 + 1视频 |
| 阻塞环 | 环3（云端执行层配置） |
| 断点锚定 | 云端服务恢复后执行步骤1-4，无需重新推送 |

---

## 五、闭环验证清单
- [ ] 环1：本地素材完整（32图+1视频+36条works_data）
- [ ] 环2：Gitee web-deploy 分支推送成功（commit dd25d71）
- [ ] 环3：云端执行层运行 cloud_remote_setup.sh
- [ ] 环4：git pull web-deploy 到双 root
- [ ] 环5：线上 gallery 页面可访问（200，含作品库标题）
- [ ] 环5：works_data total=36
- [ ] 环5：缩略图 image/webp 200
- [ ] 上报部署完成真值

---

## 六、零成本合规确认
- 全程使用 Gitee 免费 git 通道
- 无腾讯云 COS 等付费存储
- 无 SSH 直连（铁律禁止）
- 无付费 API 额度消耗

---
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜链路推演 V1.0
