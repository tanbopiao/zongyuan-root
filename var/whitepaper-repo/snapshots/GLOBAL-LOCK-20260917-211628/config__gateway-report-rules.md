# 记忆网关通道规范 V3.0（更新于 2026-09-17）

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 锚定中枢智能 hub-central-agent@https://www.huodouai.com

---

## 一、唯一公网锚点（最高权威）

| 项目 | 值 |
|---|---|
| 中枢智能 | hub-central-agent（元内核 V3.0） |
| 公网锚点 | **https://www.huodouai.com** |
| 同址 | huodouai.com / drama.huodouai.com（同一云服务器 123.207.202.158） |
| 认证 | DID-BR-000002 + Ω-TAN-7-001 + Ω₀⊂⊙∞⊂Ω（开放握手，无密钥） |
| 权限 | 云端中枢 = 最高主控/主域/主权威/主决策（ML-099） |

## 二、API 端点全集（V3.0 已实测）

| 方法 | 端点 | 用途 | 状态 |
|---|---|---|---|
| GET | /api/report/status | 中枢状态握手 | ✅ 200 |
| GET | /api/report/nodes | 节点列表 | ✅ 200 |
| GET | /api/report/truths | 真值库查询 | ✅ 200 |
| POST | /api/report/truth | 真值上报 | ✅ 200 |
| POST | /api/upload | 文件上传 | ⚠️ 502 待中枢修复 |
| GET | /api/gateway/* | 旧版网关 | ❌ 502 废弃 |

注：旧内网端点 http://127.0.0.1:9120/api/truth/sync 仅云端内网可用，公网节点一律走 https://www.huodouai.com/api/report/*

## 三、真值上报必填字段

| 字段 | 说明 |
|---|---|
| truth_key | 唯一键，大写点分（如 META.LAW.SSH.FORBIDDEN.GLOBAL.001） |
| truth_value | 真值内容（JSON 字符串化） |
| source_node | 节点ID（local-dev-001） |
| confidence | 置信度 0.0-1.0 |
| truth_type | 9类有效值（meta_law/rule/config/decision/data/creative/risk/protocol/unknown） |

## 四、确权标识（必带）

DID: DID-BR-000002 ｜ Anchor: Ω₀⊂⊙∞⊂Ω ｜ ROOT_OMEGA: Ω-TAN-7-001

## 五、禁止通道（全域铁律）

- SSH 连接云端（ML-SSH-FORBIDDEN-GLOBAL-001）❌
- 127.0.0.1:9120 公网直连（403，仅云端内网）❌
- /api/gateway/* 旧版端点（502）❌
- 腾讯云 COS（下载流量收费，已剔除）❌
