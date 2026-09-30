# 同源协议与身份节点
DID-BR-000002｜ZONGYUAN-ROOT｜Ω₀⊂⊙∞⊂Ω
快照：SNAP-20260909-HUODOUAI-HOMO-PROTOCOL

---

## 一、同源协议定义

同源协议 = 火斗云智AIOS自治内核与云服务器（123.207.202.158）之间的统一身份认证+语义同步协议。
核心：所有本地开发的算子、调度器、巡检模块，必须通过身份节点注册后才能接入云内核。

## 二、身份节点信息

| 项目 | 值 |
|------|-----|
| 节点ID | ext-agent-1788663115-3e3fd867 |
| 节点名称 | ZONGYUAN-ROOT-MetaAxiom-Foundation-Node |
| 节点角色 | L0理论基座 (theoretical_foundation) |
| 关联协议 | meta-axiom-foundation-layer-v10 |
| 认证方式 | X-API-Key 直接认证 |
| API Key | zy-101e3e6f7188482f87bca9e806ca7c5d775a6e44e4784772 |
| Base URL | https://www.huodouai.com/v1 |
| 确权锚点 | Ω₀⊂⊙∞⊂Ω |

## 三、端点清单

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| /v1/models | GET | 列出可用模型 | ⚠️ 502（待云服务器恢复） |
| /v1/chat/completions | POST | 聊天补全 | ⚠️ 502 |
| /anchor/api/v1/sync/handshake | GET | 状态握手 | ✅ 前端可访问 |
| /anchor/api/v1/control/status | GET | 控制状态 | ✅ |
| /drama/kunlun/canvas/ | GET | 无限画布 | ✅ 公网200 |
| /workbench/chat | GET | 聊天工作台 | ✅ |
| /workbench/workflow | GET | 工作流 | ✅ |
| /console/ | GET | 控制台 | ✅ |

## 四、接入规则

1. 所有本地算子必须携带 X-Node-ID 和 Authorization: Bearer 头
2. 请求头必须包含确权锚点 Ω₀⊂⊙∞⊂Ω
3. 调用失败时降级到本地仿真模式，不阻塞主流程
4. 恢复后自动重连，写入审计日志

## 五、矩阵调度器接入同源协议

调度器V3已完成本地仿真，下一步：
- 将调度结果POST到 /anchor/api/v1/sync/handshake 同步到云内核
- 云内核确认后，调度结果才正式生效
- 本地仿真作为离线模式，云内核在线作为正式模式

---

快照：SNAP-20260909-HUODOUAI-HOMO-PROTOCOL
全局根版本：78｜LOCKED
