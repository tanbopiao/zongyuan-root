# 云端中枢元内核 + 官网 · 部署 SOP
DID-BR-000002 · Ω₀⊂⊙∞⊂Ω · 目标: lhins-laotwc5e (重装后)
版本: V1.0 · 2026-10-03

## 0. 前置
- 腾讯云重装系统 → 应用模板选 **宝塔 Linux 面板**
- 记录重装后的 SSH 登录方式（密钥/密码）+ 宝塔面板地址/账号
- 提供给我后，由我/你按本 SOP 执行

## 1. 传输部署包
- 代码包: 从数据湖 `cloud-hub-deploy/` 拉取（或本地直传）
  `git clone https://oauth2:<token>@modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git`
  取 `cloud-hub-deploy/` 目录
- 官网镜像 (611M): 从本地 scp 直传（不进数据湖，避免大文件）
  `scp homepage-mirror.tar.gz root@<ip>:/tmp/`

## 2. 一键部署
```bash
cd cloud-hub-deploy
bash install.sh            # 装依赖 + 建目录 + 部署中枢 + 恢复docroot + supervisor常驻
```
或分步：
```bash
bash official-site-recover/restore_site.sh /tmp/homepage-mirror.tar.gz   # 恢复官网
cd zhongshu-server && bash run.sh start                                  # 启动中枢三服务
```

## 3. 验证（verify.sh 六项）
```bash
bash verify.sh
# 1 官网根页 200 · 2 网关/api/status ok · 3 真值上报成功
# 4 未授权401 · 5 账本存在 · 6 调度worker运行
```

## 4. 网关/Nginx 对接
- 真值网关: 后端 127.0.0.1:9001 → Nginx 反代公网路径 `/api/report/truth`、`/api/status`
- 参考 Nginx location:
```
location /api/report/truth { proxy_pass http://127.0.0.1:9001; proxy_set_header X-DID $http_x_did; }
location /api/status { proxy_pass http://127.0.0.1:9001; }
```

## 5. 挂载体系页面（docroot 内新增）
- 恒一Agent 落地页 / 白皮书 / 云端缺口分析 的 doubao-html 链接
- 或直接放静态 html 到 docroot 并加导航（白名单新增，不动现有文件）

## 6. 打通双向
- 中枢调度 worker 已跑（每5分钟心跳+读任务表）
- 本地侧心跳握手脚本指向新网关域名，恢复 bidirectional_ok

## 7. 收尾
- 真值上报 deploy 完成事件 → 共享大脑任务表「云端中枢元内核构建」置已完成
- 全域锁档六环节留痕

## 回滚
- 服务异常: `bash zhongshu-server/run.sh stop`（不影响 docroot）
- docroot 异常: 重解压 homepage-mirror.tar.gz（镜像不可变，重放即还原）
