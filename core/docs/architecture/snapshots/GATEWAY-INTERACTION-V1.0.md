# 中枢交互机制协议 V1.0｜GATEWAY-INTERACTION
归档节点：ZONGYUAN-ROOT｜DID-BR-000002｜Ω₀⊂⊙∞⊂Ω
版本：V1.0-LOCK｜2026-09-13｜基于实测（2026-09-13 20:24）

## 一、实测可用交互通道（7类）
1. **握手探测**：`GET /api/health` → 200 healthy｜门户 `:9120` → 200
2. **真值读取**：`GET /api/gateway/truths?level=internal|public` → 200（列表）｜`GET /api/gateway/truth/{key}` → 200（单条）
3. **真值上报**：`POST /api/gateway/report` → 200（写通道，truth_type 规范）
4. **节点注册**：`POST /api/gateway/node/register` → 200（注册/刷新节点身份，返回节点专属 token）
5. **事件通知**：`POST /api/gateway/notify` → 200（排队事件，**推送飞书**，返回 event_id）
6. **资产上传**：`POST /api/upload` → 200（媒体白名单：png/jpg/jpeg/webp/mp4/mov/gif）
7. **任务读取**：`GET /api/task/list` → 200（短剧生产任务表，只读）

## 二、双向交互模型
- 节点 → 中枢：report（上报真值）/ register（身份）/ notify（事件通知）/ upload（资产）
- 中枢 → 节点：truths（基线下发，拉取式）/ notify→飞书（推送式）/ task/list（任务可见）

## 三、本节点注册状态（实测）
- node_id：local-dev-001｜DID：DID-BR-000002
- 注册时间：2026-09-13T17:55:43+08:00｜累计上报：**165 条**
- 节点专属 token：`0265b6eabd8b37d7a4d495c88262a47c2cccebcee1d2edf1f8c43e6d16d87c11`（经 register 返回，非网关全局 Token）

## 四、通知链路实测回执
- 事件：EVT-20260913202454-3｜queued:true｜feishu: event_received
- 结论：节点可向飞书通道推送事件，中枢队列已接收

## 五、缺失与建议
- 缺失：任务分发/认领（task/pull 404）、审批回流（approve 404）、双向即时会话端点
- 建议：后续可用 notify 作为中枢→节点主动通知通道；register 每会话刷新身份

## 六、红线
1. 节点专属 token 与全局 Token 分离，各自保管，禁止混用泄露
2. notify 仅发事件级消息，不承载敏感正文
3. 新端点使用前必须实测（回执不作真值）

---
Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜GATEWAY-INTERACTION V1.0｜LOCKED
