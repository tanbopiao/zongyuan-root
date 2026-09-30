# ZONGYUAN-ROOT 根API增量补丁同步接口文档

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜ZONGYUAN-ROOT
版本：v1.0｜2026-09-11

---

## 1. 协议定位

本文档定义客户端（网页后台、豆包APP、本地自治代理）与 ZONGYUAN-ROOT 根API之间的**增量补丁同步协议**。目标：客户端在首次全量握手后，仅通过拉取增量补丁即可与根真值保持一致，避免反复全量传输，降低带宽与IO压力。

## 2. 同步模型

```
客户端 ──① 全握手(获取快照+版本号)──► 根API
客户端 ◄──② 返回 merkleRoot + truthVersion ── 根API
客户端 ──③ 订阅事件流/轮询版本号 ──► 根API
根API  ──④ 变更时推送 version 变更 ──► 客户端
客户端 ──⑤ 发起增量补丁请求 ──► 根API
根API  ──⑥ 返回 fromVersion→toVersion 补丁集 ──► 客户端
客户端 ──⑦ 应用补丁 + 校验新Merkle ──► 本地真值更新
```

**规则**：增量补丁只含变更的数据单元（任务新增/状态变更、配置字段变更、资产索引更新），不含未变化数据；每个补丁带 from_version 与 to_version，客户端必须顺序应用。

## 3. 接口定义

### 3.1 全握手（首次/重连）

```
POST /admin/api/root/truth-handshake
```

请求体：
```json
{
  "did": "DID-BR-000002",
  "client_type": "admin-panel | doubao-app | agent",
  "client_id": "win-08",
  "local_version": 0
}
```

响应：
```json
{
  "code": 200,
  "merkle_root": "a1b2c3d4e5f6...",
  "truth_version": 118,
  "snapshot_uri": "/storage/truth/snapshot_v118.json",
  "patch_base": 118
}
```

### 3.2 增量补丁拉取

```
GET /admin/api/root/patch?from=112&to=118&did=DID-BR-000002
```

响应：
```json
{
  "code": 200,
  "from_version": 112,
  "to_version": 118,
  "patches": [
    {
      "op": "upsert",
      "entity": "task",
      "id": "T-20260909-0042",
      "fields": {
        "status": "success",
        "drift_score": 0.42,
        "progress": 100
      },
      "version": 113
    },
    {
      "op": "update",
      "entity": "config.drift_threshold",
      "value": 0.85,
      "version": 115
    },
    {
      "op": "delete",
      "entity": "task",
      "id": "T-20260908-0011",
      "version": 116
    }
  ],
  "merkle_after": "f9e8d7c6...",
  "next_version": 118
}
```

操作类型 `op`：
| op | 语义 |
|---|---|
| `upsert` | 新增或覆盖实体（幂等） |
| `update` | 更新已有实体字段 |
| `delete` | 删除实体 |

### 3.3 补丁确认（可选，审计用）

```
POST /admin/api/root/patch/ack
{
  "did": "DID-BR-000002",
  "client_id": "win-08",
  "applied_version": 118,
  "merkle_received": "f9e8d7c6..."
}
```

根API记录客户端同步水位，用于后续精准下发增量（只发 `>客户端水位` 的补丁）。

### 3.4 版本号探测（轻量轮询）

```
GET /admin/api/root/version?did=DID-BR-000002
→ { "truth_version": 118, "merkle_root": "f9e8d7c6..." }
```

客户端每30~60秒探测一次；版本号未变则不发补丁请求，版本号变化才调 3.2。

## 4. 冲突处理

| 场景 | 处理 |
|---|---|
| 客户端版本 < 根版本 | 拉取增量补丁顺序应用 |
| 客户端版本 > 根版本（异常） | 以根为准，客户端全量重握手回滚 |
| 并发写入冲突 | 根API版本锁仲裁，后到者收到 `code:409` + 最新快照，客户端自动回滚 |
| 补丁应用中途失败 | 幂等重试（op为upsert幂等），失败3次转全量握手 |

## 5. 安全与隔离

- 所有接口必须携带 DID 身份，未授权返回 `code:401`；
- 不同 DID 的补丁流严格隔离（希尔伯特正交子空间）；
- 每个补丁包携带 `merkle_after`，客户端应用后校验本地哈希，不匹配则回滚并全量重握；
- 敏感配置字段（阈值/内核规则）变更补丁记审计日志。

## 6. 与现有产线对接

| 现有接口 | 对接角色 |
|---|---|
| `/admin/api/works` | 快照中静态内容基线 |
| `/admin/api/task/list` | 补丁实体 `task` 的源 |
| `/admin/api/system/status` | 握手时内核状态锚点 |
| `/admin/api/user/keys` | 配置类补丁来源 |

## 7. 待落地清单（服务端）

1. 8100 app.py 新增 `/root/truth-handshake`、`/root/patch`、`/root/version`、`/root/patch/ack` 四个端点；
2. 任务/配置变更时写入变更日志（append-only），作为补丁源；
3. 按客户端水位裁剪补丁（只下发 > 水位部分）；
4. 前端 RootTruth 模块从"60秒轮询比对"升级为"版本号探测 → 增量补丁应用"。

当前前端模块已落地（见 root-handshake.js），服务端补丁端点待开发。
