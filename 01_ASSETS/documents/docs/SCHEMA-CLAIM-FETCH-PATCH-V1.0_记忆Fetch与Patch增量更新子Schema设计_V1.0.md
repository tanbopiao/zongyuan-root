# SCHEMA-CLAIM-FETCH-PATCH-V1.0 · 记忆 Fetch 单条读取 + Patch 增量更新子Schema 设计

> 项目：火斗云智AIOS｜联邦记忆内核标准套件 ｜ 基线：BASELINE-V40
> DID：DID-BR-000002 ｜ 节点：ZR-NODE-DC2E51C0 ｜ 溯源：Ω₀⊂⊙∞⊂Ω
> 状态：**locked（用户批准执行，2026-10-21 正式锁定并注册至 MEM-SCHEMA-BUNDLE-V1.0）**
> 配套资产：SCHEMA-CLAIM-ATOM-V1.0 / CONFLICT-MELD-V1.0 / RETRIEVE-V1.0 / MEM-SCHEMA-BUNDLE-V1.0
> 约束：本子Schema为**新增资产**，不修改任何 locked 基准Schema（套件元规则：BASELINE-V40 迭代只走补丁卷宗追加）
> 机器可读版：`01_ASSETS/documents/docs/SCHEMA-CLAIM-FETCH-PATCH-V1.0.json`

---

## 1. 定位与链路插入点

补齐全套件第 6/6.5 步的正式规范（原流水线仅有 retrieve 检索、未定义单条读取与增量更新）：

```
标准流水线（扩展后）：
1 写入Claim → 2 Z3校验<S,P>冲突 → 3 MELD裁决 → 4 retrieve_req → 5 retrieve_resp
→ 6 Fetch单条完整读取【本Schema-A】 → 6.5 Patch增量更新【本Schema-B】 → 7 卷宗打包上报
```

```
fetch路径：Organizer/A2A ──fetch_req──► 记忆网关 ──claim_id直读──► Claim存储 ──fetch_resp──► 上层
patch路径：Agent ──patch_req──► 白名单+Z3预检 ─┬─ meta_only ─► 版本+1·审计入链·invariant不变 ─► resp
                                              └─ supersede ─► 新增Claim+旧条目archived/revoked ─► MELD(若同S+P冲突) ─► resp
```

## 2. 设计原则（继承五条核心元公理）

| 元公理 | 在本子Schema的落法 |
|---|---|
| 语义不变量（Z3只算S+P+O） | meta_only patch 前后 `invariant_hash` **必须相等**，否则拒绝（INV-FP-2） |
| 锁档规则（locked禁改S/P/O） | `ops` 路径白名单**不含** /subject /predicate /object；语义变更唯一合法路径是 `supersede`（新增+归档/作废），与 MELD 衔接（INV-FP-3/4） |
| 载体分离 | fetch 应答的 `claim` 是语义断言本体，JSON 只是传输包；patch 结果连同工单/审计打包进卷宗 |
| 降级规则（8014） | Fetch 按 claim_id **直读存储，不经向量库**，8014 不可达不降级、不阻塞；仅 retrieve 受降级规则约束（INV-FP-1） |
| 审计溯源 | 每次 fetch/patch 生成独立审计真值（audit_id+seq），入链并随卷宗上报（INV-FP-6） |

## 3. Schema-A：Fetch 单条读取

### 3.1 fetch_req

```json
{
  "msg_type": "claim_fetch_req",
  "req_id": "UUID",
  "ts": "2026-10-21T16:40:00+08:00",
  "node": "ZR-NODE-DC2E51C0",
  "agent_id": "organizer|a2a:<agent>",
  "claim_id": "CLM-...",
  "version_selector": { "mode": "latest | at_version | at_ts", "at_version": 3, "at_ts": "..." },
  "content_view": "full | semantic | meta_only",
  "include_history": true,
  "include_conflict_tickets": false,
  "audit": { "purpose": "string", "trace": "Ω₀⊂⊙∞⊂Ω" }
}
```

### 3.2 fetch_resp

```json
{
  "msg_type": "claim_fetch_resp",
  "req_id": "UUID",
  "status": "ok | not_found | forbidden | degraded",
  "claim": {
    "claim_id": "CLM-...", "version": 3, "rev": "7f3a...",
    "subject": "S", "predicate": "P", "object": "O",
    "invariant_hash": "sha256(S|P|O 口径同Z3校验)",
    "confidence": 0.97,
    "lock_status": "locked | unlocked | archived | revoked",
    "meta": { "labels": [], "source": "", "node": "", "tags": [] },
    "created_ts": "", "updated_ts": "",
    "prev_claim_ids": [],
    "provenance": { "origin_batch": "", "bundle_ref": "" }
  },
  "history": [ { "version": 2, "change": "supersede", "audit_id": "AUD-..." } ],
  "conflict_tickets": [ { "ticket_id": "TCK-...", "state": "closed" } ],
  "degrade_note": "claim_id 直读不依赖 8014 向量库；仅存储整体不可达时 status=degraded 并给出重试指引",
  "audit": { "audit_id": "AUD-...", "seq": 123 },
  "trace": "Ω₀⊂⊙∞⊂Ω"
}
```

- `content_view=semantic` 仅返回 S/P/O+invariant_hash+confidence；`meta_only` 仅元数据（省带宽给 A2A 摘要回传用）。
- archived/revoked 条目可读（审计需要），但响应带 `lock_status` 供上层**禁用为新推理依据**。

## 4. Schema-B：Patch 增量更新

### 4.1 两种补丁模式（关键设计）

| 模式 | 允许对象 | 前置条件 | 后置条件 |
|---|---|---|---|
| `meta_only` | **白名单路径**：`/meta/**`、`/confidence`、`/tags/**`、`/meta/node`、`/meta/labels/**` | `expected_version` 匹配（乐观并发）；lock_status 变更须 `approval_ref` | `invariant_hash` 不变；version+1；审计入链 |
| `supersede` | **S/P/O 语义变更的唯一通道** | 携带完整 `new_claim`；同 S+P 已存在他条时必须有 `meld_ticket_ref`，否则网关自动开 MELD 工单转裁决 | 新增 Claim（新 claim_id）+ 旧条目 `archived` 或 `revoked`；工单+前后哈希入审计 |

### 4.2 patch_req

```json
{
  "msg_type": "claim_patch_req",
  "req_id": "UUID",
  "ts": "...", "node": "ZR-NODE-DC2E51C0", "agent_id": "...",
  "claim_id": "CLM-...",
  "expected_version": 3,
  "expected_invariant_hash": "sha256(S|P|O)",
  "patch_mode": "meta_only | supersede",
  "ops": [ { "op": "add | replace | remove", "path": "/meta/labels/-", "value": "fed" } ],
  "supersede": {
    "reason": "object 证据更新",
    "new_claim": { "subject": "S", "predicate": "P", "object": "O2", "confidence": 0.99, "meta": {} },
    "disposition": "archive | revoke",
    "meld_ticket_ref": "TCK-... | null"
  },
  "approval_ref": "APR-... | null",
  "audit": { "purpose": "", "trace": "Ω₀⊂⊙∞⊂Ω" }
}
```

### 4.3 patch_resp

```json
{
  "msg_type": "claim_patch_resp",
  "req_id": "UUID",
  "status": "applied | conflict | rejected | routed_to_meld | needs_approval",
  "new_version": 4,
  "new_claim_id": "CLM-...(supersede时)",
  "invariant_hash_unchanged": true,
  "old_disposition": "archived | revoked | null",
  "meld_ticket_id": "TCK-... | null",
  "error": { "code": "E-FP-...", "detail": "" },
  "audit": { "audit_id": "AUD-...", "seq": 124 },
  "trace": "Ω₀⊂⊙∞⊂Ω"
}
```

## 5. 不变量与错误码（Z3 可校验谓词）

| 编号 | 谓词（Z3表达意图） | 违反响应 |
|---|---|---|
| INV-FP-1 | fetch 通路 ∩ 向量库(8014) = ∅ | 存储可达即必答，向量库无关 |
| INV-FP-2 | meta_only: hash_before(S,P,O) = hash_after(S,P,O) | E-FP-422 |
| INV-FP-3 | ops.path ∉ {/subject,/predicate,/object} | E-FP-423 |
| INV-FP-4 | supersede ⇒ 新增记录 ∧ 旧条目∈{archived,revoked}；同S+P他条存在 ⇒ meld_ticket_ref ≠ null（否则自动开单） | routed_to_meld |
| INV-FP-5 | expected_version = 当前 version，否则零写入 | E-FP-409 |
| INV-FP-6 | 每次 fetch/patch ⇒ 存在 audit 真值且随卷宗上报 | 拒绝出网关 |

错误码：`E-FP-404` 条目不存在｜`E-FP-409` 版本冲突（无写入，返回当前 version 供重取）｜`E-FP-422` 白名单/不变量违反｜`E-FP-423` locked 目标被改语义｜`E-FP-451` 需 approval_ref（如 unlock）｜`E-FP-503` 存储不可达（上层按降级规则不阻塞 A2A：返回 retry 指引 + 可选走 retrieve 的最新版本缓存）

## 6. 与配套资产的衔接

- **ATOM**：patch 产物仍是标准 Claim（同一 invariant_hash 口径与锁档标记）。
- **CONFLICT-MELD**：supersede 检出同 S+P 冲突 → 五分支裁决（insert/merge/relate/conflict/reject）；被裁决为 merge/conflict 的旧条目 disposition 强制 archived。
- **RETRIEVE**：检索命中的是 claim_id，Fetch 是其第 6 步标准取全通道；retrieve 降级 exact_sp 与本Schema无关（直读）。
- **A2A/Organizer**：`content_view=meta_only` 供摘要回传控 token；Patch 的 needs_approval 状态回 Organizer 走人工审批，不自动放行。
- **卷宗**：fetch/patch 审计 + 工单按第 7 步打包 `MEM-SCHEMA-BUNDLE` 补丁卷宗，append_patch 上报中枢与仓库。

## 7. 状态与后续

- 设计状态：**proposed**——正式 `lock_status: locked`、写入合集卷宗、推送魔搭/AtomGit/中枢为**部署类动作，待人工批准**；
- 通过后：以补丁卷宗形式追加（不改 BASELINE-V40 基准三Schema），并注册至 `MEM-SCHEMA-BUNDLE` 的 `associated_assets`。
