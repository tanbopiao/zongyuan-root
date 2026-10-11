# 元极恒一 · A2A 接入规范 V1.0

> **规范编号**：SPEC-A2A-ONBOARD-V1.0 ｜ **锚定**：Ω₀⊂⊙∞⊂Ω ｜ 本体根 Ω-TAN-7-001 ｜ 资产根 DID-BR-000002
> **发布节点**：NODE-DEV-WORKBUDDY-001 ｜ **生效日期**：2026-10-11 ｜ **适用**：体系内全部节点
> **依据**：INTEROP-A2A-V2.0（协议实现）｜ V3.0「A2A 须经网关仲裁」｜ METALAW.011「不重复注册」

---

## 0. 本规范解决什么

体系内节点要互联，需回答三个问题：**找得到吗？信得过吗？调得动吗？**

本规范给出一份**统一契约**，任何节点按此接入即可与本节点联邦通信，**无需改动自身技能语义**。

> **接入前提**：仅限 DID-BR-000002 体系内节点。跨体系对接须另行报批。

---

## 1. 一句话接入

```
① 发现 → GET  {对端}/.well-known/agent-card.json
② 鉴权 → 携带 X-ZR-Token: ZRH1.<payload>.<sig16>
③ 调用 → POST {对端}/ message/send（JSON-RPC 2.0）
```

三件事：**发现、鉴权、调用**。

---

## 2. 端点契约（必须遵守）

| 端点 | 方法 | 鉴权 | 用途 |
|---|---|---|---|
| `/.well-known/agent-card.json` | GET | **匿名** | 对端发现（握手入口） |
| `/.well-known/agent.json` | GET | 匿名 | 旧版发现（同一份卡片） |
| `/health` | GET | 匿名 | 健康探针 |
| `/identity` | GET | 匿名 | 同源身份摘要（不含密钥） |
| `/` | POST | **分级** | JSON-RPC 2.0：`message/send` / `tasks/get` |

### 2.1 响应约定

- 内容类型：`application/json; charset=utf-8`
- RPC 成功：`{"jsonrpc":"2.0","id":<同请求>,"result":{...}}`
- RPC 失败：`{"jsonrpc":"2.0","id":<同请求>,"error":{"code":<负整数>,"message":"..."}}`
- **鉴权失败用 HTTP 状态码**：401（缺令牌）/ 403（令牌无效或角色不足）
- **任何情况下不得静默断连**（网关不可达须降级返回）

### 2.2 错误码表

| code | 含义 |
|---|---|
| -32700 | JSON 解析失败 |
| -32601 | 方法不存在 |
| -32001 | 任务不存在 |
| -32002 | 未授权（缺令牌） |
| -32003 | 身份层未初始化 |
| -32004 | 禁止（签名/双标识/时效/角色不通过） |
| -32000 | 内部错误（兜底） |

---

## 3. 身份契约（核心）

### 3.1 令牌格式

```
ZRH1.<b64url(payload)>.<hmac_sha256_first16>
```

`payload` 字段：

| 字段 | 含义 | 约束 |
|---|---|---|
| `t` | 令牌 ID | `HTK` + 8位十六进制 |
| `n` | 持有者名称 | 建议=节点 ID |
| `r` | 角色 | `reader` / `writer` / `admin` |
| `s` | 范围 | 自由文本，如 `a2a-federation` |
| `e` | 过期时间 | Unix 秒 |
| `o` | **本体根** | 必须 = `Ω-TAN-7-001` |
| `d` | **资产根** | 必须 = `DID-BR-000002` |

### 3.2 密钥派生（跨节点共源）

```
key = PBKDF2-HMAC-SHA512(口令, salt, 600000轮, 32B)
salt = "ZR-HOMOLOGOUS-v1" || "Ω-TAN-7-001" || "DID-BR-000002" || <公开salt>
```

- 派生库：`/workspace/zr-token/homologous/homologous_keyderive.py`
- **密钥零落盘**：每次进程启动从口令重新派生
- **同源判定**：口令 + salt 相同 → 派生同一密钥 → 互认令牌

> ⚠️ **拼接格式必须字节级一致**：使用**双竖线 `||`** 作为分隔符。
> 常见错误：写成单竖线 `|` → 派生出完全不同的密钥 → 令牌全部失配（表现为「有效令牌被 403 拒绝」）。
> **请直接 import 体系的 `homologous_keyderive.derive_key()`，勿自造实现**（本规范配套的
> `a2a_onboard.py` 内置实现已与该库字节级对齐，可作对照）。

> ⚠️ **口令是信任根**。弱口令 = 全体系令牌可被伪造。口令须由各节点安全持有，**严禁写入任何仓库或资料库**。

### 3.3 四层校验（对端必须实现）

| 层 | 校验内容 | 失败响应 |
|---|---|---|
| ① 格式 | 前缀 `ZRH1`、三段式 | 403 `format` |
| ② 签名 | HMAC-SHA256 前16位，**时序安全比较** | 403 `signature` |
| ③ 双标识 | `o`=Ω-TAN-7-001 且 `d`=DID-BR-000002 | 403 `identity` |
| ④ 时效 | `e` > 当前时间 | 403 `expiry` |
| ⑤ 角色 | 持者角色 ≥ 所需角色 | 403 `role` |

### 3.4 角色权限矩阵

| 技能 | 所需角色 | 匿名 |
|---|---|---|
| `omega_status` | reader | ✅ 可（只读通道） |
| `truth_recall` | reader | ✅ 可 |
| `memory_anchor` | reader | ✅ 可 |
| `truth_report` | **writer** | ❌ 401 |
| `node_heartbeat` | **writer** | ❌ 401 |

**角色分级**：`reader(0) < writer(1) < admin(2)`——高角色可执行低角色技能。

---

## 4. Agent Card 契约

发现端点返回的 JSON 必须包含：

```json
{
  "name": "<节点显示名>",
  "version": "2.0.0",
  "url": "<节点可达地址>",
  "capabilities": {
    "streaming": false,
    "stateTransitionHistory": true,
    "extensions": [{
      "uri": "https://huodouai.com/a2a/homologous-identity/v1",
      "params": {"header": "X-ZR-Token", "scheme": "ZRH1",
                 "roles": ["reader","writer","admin"]}
    }]
  },
  "securitySchemes": {
    "homologousZRH1": {"type":"apiKey","in":"header","name":"X-ZR-Token"}
  },
  "metadata": {
    "did": "DID-BR-000002",
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "ontology_root": "Ω-TAN-7-001",
    "node_id": "<节点 ID>"
  },
  "skills": [{"id":"...","name":"...","description":"...","tags":[...]}]
}
```

**必填**：`name` / `version` / `url` / `metadata.node_id` / `metadata.did` / `skills`

---

## 5. 技能清单（标准五技能）

接入节点**必须**宣称以下技能 ID，保证跨节点调用语义一致：

| 技能 ID | 触发词 | 说明 | 角色 |
|---|---|---|---|
| `omega_status` | `status` / `状态` | 返回内核版本、节点身份、运行时长 | reader |
| `truth_recall` | `recall <key>` | 从网关下行召回真值 | reader |
| `memory_anchor` | `anchor <kw>` | 本地记忆索引锚定检索 | reader |
| `truth_report` | `report <key>=<value>` | 向网关确权上报真值 | writer |
| `node_heartbeat` | `heartbeat` | 同源节点心跳 | writer |

> 节点可**追加**自有技能，但**不得修改**上表五技能的 ID 与语义。

---

## 6. 网关端点契约（重要勘误）

体系内节点调用中枢网关时，**必须使用以下正确姿势**：

| 操作 | 正确写法 | 常见误用 |
|---|---|---|
| 读取真值 | `GET /api/truth?key=<key>` | ❌ `GET /api/truth/<key>` → 404 |
| 列表真值 | `GET /api/truth?limit=<n>` | — |
| 写入真值 | `POST /api/report/truth` + 合法 JSON body | ❌ 空 body → 404 |
| 台账 | `GET /api/ledger?limit=<n>` | — |
| 状态 | `GET /api/status` | — |

> ⚠️ **本勘误已实地验证**：`GET /api/truth/<key>`（路径参数）**恒返回 404**，
> 已导致体系内多处误报「通道主=404备=404」。**根因是用错端点，非通道故障。**
> 详见网关记录 `ERRATA.GATEWAY.ENDPOINT-USAGE.20261011`（seq 9400）。

### 6.1 写请求头

```
Content-Type: application/json
X-DID: DID-BR-000002
X-Capture-Token: <按需>
```

`value` 字段**必须是 JSON 对象**（不是字符串），否则被拒。

---

## 7. 接入检查清单

节点接入后，**必须逐项自检通过**：

- [ ] 1. `GET /.well-known/agent-card.json` 返回合法卡片（含五技能）
- [ ] 2. `GET /health` 返回 `status: healthy`
- [ ] 3. 匿名 `status` 调用 → **200**（只读通道）
- [ ] 4. 匿名 `report` 调用 → **401**（写拦截）
- [ ] 5. reader 令牌 `status` → **200**
- [ ] 6. reader 令牌 `report` → **403**（角色不足）
- [ ] 7. 伪造签名令牌 → **403**（签名不匹配）
- [ ] 8. writer 令牌 `report` → **200**
- [ ] 9. 异源前缀令牌 → **403**
- [ ] 10. 残缺令牌 → **403**

**10/10 全过 = 接入合格**。自检脚本见 §9。

---

## 8. 对端登记

接入双方须**互登对端注册表**：

```bash
python3 a2a_registry.py add \
  --node-id <对端节点ID> \
  --card-url http://<对端>/.\well-known/agent-card.json \
  --trust unverified
```

信任等级：`unverified` → `verified`（自检通过）→ `trusted`（长期稳定）；`blocked` 为拉黑。

> **METALAW.011**：节点心跳复用已注册节点，不重复注册。

---

## 9. 接入工具包

本节点提供**可直接复制**的参考实现，位于 `03_INFRA/a2a/`：

| 文件 | 用途 |
|---|---|
| `server/omega_a2a_v2.py` | 服务端参考实现（零依赖） |
| `server/agent-card.json` | Agent Card 模板 |
| `lib/a2a_identity.py` | 身份仲裁层（可直接复用） |
| `lib/a2a_registry.py` | 对端注册表 |
| `lib/a2a_auth_matrix_test.py` | **10 项自检脚本** |
| `federation/a2a_federation_client.py` | 出站联邦客户端 |

### 快速自检
```bash
python3 lib/a2a_auth_matrix_test.py    # 期望 PASS=10 FAIL=0
```

---

## 10. 安全红线

| 红线 | 说明 |
|---|---|
| **口令零入库** | 口令/密钥严禁写入仓库、资料库、网关 |
| **令牌不落盘** | 令牌按需签发，即时使用 |
| **仅体系内** | 不向公网无差别开放 |
| **不得自行直连** | 跨节点身份须经同源校验（V3.0） |
| **不得静默失败** | 任何异常须显式返回错误码 |
| **不得重复注册** | 心跳复用已注册节点（METALAW.011） |

---

## 11. 变更管理

- 本规范版本：`SPEC-A2A-ONBOARD-V1.0`
- 变更须更新**规范编号**并在网关登记（key 前缀 `SPEC.A2A.ONBOARD`）
- 技能 ID 与语义**向后兼容**，不得破坏性变更

---

**发布方**：NODE-DEV-WORKBUDDY-001 ｜ **锚定**：Ω₀⊂⊙∞⊂Ω
**依据实现**：INTEROP-A2A-V2.0（鉴权矩阵 10/10 PASS，已被体系节点 seq 9386 独立复核）
