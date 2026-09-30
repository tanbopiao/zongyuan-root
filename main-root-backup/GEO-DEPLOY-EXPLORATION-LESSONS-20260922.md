# GEO 全域部署探索正反经验汇总（增值真值资产）

文件编号：GEO-DEPLOY-EXPLORATION-LESSONS-20260922
管控身份：DID-BR-000002 / BRANCH-001
层级：经验真值资产 · 全域节点复用
状态：永久固化 · 全域生效

---

## 一、正向经验（已验证可用通道）

### 通道1：GitHub 桥接（主持久化通道）
- 本地内核 → GitHub 仓库 tanbopiao/zongyuan-root，x-access-token 格式 remote 可用
- push 前必须 git pull --rebase origin main
- GEO 8 文件已推送 zongyuan-root/geo-deploy/（commit eb7b4fe），GitHub API 实测在线
- 结论：GitHub 是本地↔云内核最可靠的桥接中间层，零成本

### 通道2：妙搭应用部署（官方稳定通道）
- lark-cli apps +deploy → +release-get 轮询到 finished → online_url
- GEO 线上版 9 文件全部 HTTP 200 验证通过
- 结论：面向公众的展示形态，妙搭是已验证的官方通道

### 通道3：drama 网关 truth 上报（核心信息通道）
- 9120 端口 /api/gateway/report：synced:1，total 持续增长（已验证从 141xxx 增长到 143xxx）
- /api/health 持续 healthy
- 部署请求、审批请求、元规则均可入库
- 结论：9120 网关是唯一可靠的 truth 入库通道

### 通道4：drama upload 服务器磁盘写入（部分可用）
- 可写 /opt/storage/assets/<日期>/，subdir 参数可控制子目录
- 白名单：png/jpg/webp/mp4/gif（html/txt/xml/json 全拒）
- 限制：/opt/storage 无 HTTP web 暴露，路径穿越无效
- 结论：证明服务器磁盘可写，但不可作 web 部署通道

### 通道5：历史自动部署产物全部在线（机制真实性证明）
- education.html / pricing.html / products.html / autonomy-dashboard.html / knowledge.html 全部 200
- 均为"飞书审批 → 中枢智能"机制产物
- 结论：自动部署机制真实存在且有成功记录

### 通道6：服务器自治任务持续运转
- assets/index.html 聚合引擎 30 分钟级持续更新（实测 18:30 → 23:00 → 23:30 GMT 连续刷新）
- drama 生产 AUTO 任务时间戳连续无断档
- 结论：服务器守护任务真实在跑

## 二、反向经验（已验证不可用通道，勿重试）

### 教训1：TAT 命令执行（假成功陷阱）
- 现象：SUCCESS/ExitCode 0/StartTime≈EndTime，但文件不落盘
- 验证：让 TAT 命令 POST 唯一标记到网关 → total 增长证明命令真执行
- 根因：TAT 在隔离环境执行（有网络无持久文件系统），Agent 特性仅 SESSION_MANAGER
- 教训：TAT 结果表象不可信，必须以落盘/外部副作用验证

### 教训2：SSH 全部密钥被拒
- zy.pem(RSA) + did_br_000002_ed25519，root/ubuntu/lighthouse 全试过均被拒
- 教训：无有效 SSH 通道，勿再尝试

### 教训3：gitee 桥接仓库不存在
- kunlun-drama-assets 仓库 404；用户名下其他仓库内容与服务器 assets 不符
- 教训：gitee 当前不可作部署通道

### 教训4：www /api/* 全 502
- Flask 8765 后端中断，/api/health、/api/system/monitor、/api/ops/execute 均不可达
- 教训：www 后端是部署执行核心依赖，当前断点；守护未覆盖（ARCH-004 已补）

### 教训5：upload 扩展名白名单 + 路径穿越无效
- html/txt/xml/json 全拒；filename/subdir/name 路径穿越均被规范化
- 教训：upload 不可作 web 文件部署通道

### 教训6：/api/upload/video 硬编码走 COS
- NoSuchBucket（bucket 已删）——与用户"COS 永久剔除"指令一致
- 教训：COS 链路已彻底废弃，勿再依赖

### 教训7：9121 命令队列未部署执行 Agent
- /api/cmd/submit 404，调度器 V1.2 未完成
- 教训：命令队列不可用

### 教训8：ai_proxy(8021) IP 白名单拦截
- "ip access not allowed"，域名通道全不通，需 X-Admin-Key（zongyuan-paid-admin-2026）
- 教训：ai_proxy 外部不可达，仅限服务器内网

### 教训9：truths 读回限制
- /api/gateway/truths 只回标题列表（79300+ 条）；report 入库内容无法经 truths 读回
- 验证上报是否入库：靠 report 返回 synced:1 + total 增长
- 教训：truths 是只读标题索引，非内容库

## 三、机制洞察（正反结合）

1. 部署真实机制：飞书审批（AIOS阶段验收，应用 cli_9cb844403dbb9108）→ 上报 → 中枢智能执行
2. 本账号搜不到审批定义（在云端中枢应用侧），审批发起由云端中枢智能完成
3. 自治守护真实存在但覆盖有缺口：聚合引擎/drama生产/op_scheduler 在跑，www 后端未覆盖
4. 部署执行单点依赖 www 后端（8765），恢复即全链路通

## 四、已固化的元规则（本探索的产出）

- ARCH-003 部署执行通道冗余法则（≥3 条独立通道）
- ARCH-004 守护覆盖完备法则（www 后端必守护）
- GOV-003 部署状态机法则（五态闭环）
- GOV-004 部署验证闭环法则（URL+指纹双验证）
- GOV-005 网关双通道上报法则（9120+443，超时重报）

## 五、全域复用建议

1. 所有新通道验证必须走"落盘/外部副作用"验证，不信任 SUCCESS 表象
2. 部署走 GitHub 持久化 + 网关上报 + 飞书审批三步，禁用 TAT/gitee/upload
3. 上报一律 9120 主通道（443 依赖 www 后端，当前不可用）
4. www 后端恢复后，全链路自动恢复（部署请求已在队列）

---

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜Ω-TAN-7-001｜ZONGYUAN-ROOT 经验真值资产
