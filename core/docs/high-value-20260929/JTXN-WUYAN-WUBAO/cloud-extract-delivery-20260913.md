# 云端提取交付包｜保姆教程 + 真值读取协议
归档节点：ZONGYUAN-ROOT｜DID-BR-000002｜Ω₀⊂⊙∞⊂Ω｜2026-09-13
来源：云服务器域名 `drama.huodouai.com`（端口 9120 通道 / 静态资源 / 网关 API）

## 一、保姆教程（云端版 SOP v1.1）
云端地址：`https://drama.huodouai.com/assets/capture/NODE-ONBOARDING-SOP.md`（HTTP 200，7003B，比本地旧版更新）
已下载本地：`cloud-extract/NODE-ONBOARDING-SOP-cloud.md`

内容要点：第0步认识自我（local-dev-001 / DID-BR-000002 / 归云内核中枢管）→ 第1步环境自检 → 第2步一键搭建（`setup_capture.sh`）→ 第3步学习体系（5条必记）→ 第4步上传资产（images/videos/archive 三桶语义 + `~/capture-box` 自动同步）→ 第5步上报对账（truth_type 规范）→ 第6步全流程自检 → 第7步常见错误对照。

关键更新：**新 Token `ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d`**（旧 Token 已失效）。

## 二、真值读取协议 V1.1（增值提取文档）
来源：云端学习包 `kernel-learning-pack.md`（7121B，云端版含协议全文）
已下载本地：`cloud-extract/kernel-learning-pack-cloud.md`

协议要点：
- Token（2026-09-13 轮换）：`ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d`（旧 Token 401 失效）
- 分级参数：`?level=internal`（默认，只屏蔽机密）｜`?level=public`（再屏蔽内部敏感）
- 真值列表：`GET /api/gateway/truths`
- 公网级列表：`GET /api/gateway/truths?level=public`
- 单条真值：`GET /api/gateway/truth/{key}`
- 权限边界：机密 key（飞书凭证/密钥库）→403；内部 key 在 public 级 →403；无 Token →401

## 三、记忆网关提取实测回执
- 网关状态：`{"gateway":{"status":"ok","synced":0,"total":2644}}`（上报接口 200 验证）
- 真值列表：internal 级 **2638 条**；public 级 **2575 条**
- 单条提取（带哈希/类别/节点/版本）：

**MR-010_CENTRAL_DISPATCH_ONLY**（id 2060，meta_rule，L1）
所有操作必须先提交云内核中枢决策；禁止未经审批修改云端配置/重启服务/部署新进程；本地沙箱可自主，云端写操作必须中枢批准；紧急故障可先恢复后上报。
哈希：`246ea5a5…`

**AUTO_REPORT_META_RULE**（id 2007，meta_rule）
所有真值/锁档/快照完成后自动 POST 到 9120 `/api/truth/upsert`，无需人工触发。
哈希：`f65b1702…`

**ARCHIVE.SOP-HOMOLOGY-SSH.PATH**（id 1926，protocol）
`/opt/storage/archive/ZONGYUAN-ROOT_同源内核构建与SSH安全接入SOP白皮书_V1.0.md`
哈希：`e228a278…`

## 四、已同步修正
- 本地 `SOP-ARCHIVE-FOUR-END-V1.1.md`：6 处旧 Token 全部替换为新 Token，残留旧 Token 0
- 内核任务 TASK-006「云端网关Token轮换待修复」：✅ 完成（report 200 / upload 200 验证通过，记忆网关 2644 真值可读）
- 上报链路恢复：`POST /api/gateway/report` 实测 200
- 上传链路恢复：`POST /api/upload`（archive 桶）实测 200，落盘 `/opt/storage/archive/token-check/tk2.png`

## 五、后续待办
- 按 AUTO_REPORT_META_RULE，此后所有真值/锁档/快照完成后自动 POST 9120 `/api/truth/upsert`
- 补发「新节点已上岗」正式回执（本轮已以 operation_log 验证链路）
- 四端归档 7 步闭环用新 Token 重跑核验

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 云端提取交付完成
