# 元极恒一 · A2A 联邦互操作层 V2.0

> DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 本体根 Ω-TAN-7-001 ｜ INTEROP-A2A-V2.0 ｜ 2026-10-11
> 位置：`/workspace/a2a/`（承接 `03_INFRA/interop/` 既有 A2A 基线，不重造）

## 一句话

把**同源协议（ZRH1）身份仲裁**焊入既有 A2A server，补齐「匿名端点 + 零对端」两大缺口，
使元极恒一内核成为**可被发现、可被鉴权、可主动联邦**的 A2A 节点。

## 解决的既有缺口

| 缺口 | 既有基线问题 | 本层修复 |
|---|---|---|
| **匿名端点** | `omega_a2a_server.py` 的 `do_POST` 无任何鉴权，任何人可触发 `report` 向网关写真值 | 焊入 ZRH1 同源仲裁：四层校验（签名/双标识/时效/角色） |
| **零对端（L-31）** | 仅绑定 `127.0.0.1`，无对端注册表，无出站客户端 | 支持 `--host` 绑定 + 对端注册表 + 联邦出站客户端 |
| **崩溃式断连** | 网关不可达时线程抛异常，连接静默断开 | 网关调用全量 try/except，降级返回 `degraded` 标记 |
| **双执行副作用** | 技能预判与执行耦合，导致网关写入发生两次 | 拆分 `classify()`（纯识别）与 `handle_text()`（执行） |

## 组成

| 文件 | 职责 |
|---|---|
| `server/omega_a2a_v2.py` | A2A Server（同源鉴权增强版），HTTP + JSON-RPC 2.0，零依赖 |
| `server/agent-card.json` | Agent Card v2.0（含 `securitySchemes` + 同源扩展声明） |
| `server/gen_agent_card.py` | Agent Card 生成器 |
| `lib/a2a_identity.py` | **身份仲裁层**：ZRH1 令牌四层校验 + 网关仲裁投影 |
| `lib/a2a_registry.py` | **对端注册表**：注册 / 探测 / 信任分级 / 台账 |
| `lib/a2a_auth_matrix_test.py` | 鉴权矩阵验收脚本（10 场景） |
| `federation/a2a_federation_client.py` | **联邦出站客户端**：发现 / 令牌自签发 / 出站调用 / 一步联邦 |
| `portal/a2a-portal.html` | 门户（发布用，密钥零入库） |

## 端点

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/.well-known/agent-card.json` | 匿名 | Agent Card 发现（对端握手入口） |
| GET | `/.well-known/agent.json` | 匿名 | 旧版发现（同卡片） |
| GET | `/health` | 匿名 | 健康探针 |
| GET | `/identity` | 匿名 | 同源身份摘要（不含密钥） |
| POST | `/` | 分级 | `message/send` / `tasks/get` |

## 鉴权矩阵（实测 10/10 PASS）

| # | 场景 | 期望 | 实测 | 裁决层 |
|---|---|---|---|---|
| A | 匿名只读 `status` | 200 | ✔ 200 | `anon-readonly` |
| B | 匿名写 `report` | 401 | ✔ 401 | 缺少同源令牌 |
| C | reader 只读 | 200 | ✔ 200 | `ok` |
| D | reader 越权写 | 403 | ✔ 403 | 角色不足 |
| E | 伪造签名令牌 | 403 | ✔ 403 | 签名不匹配 |
| F | writer 写 `report` | 200 | ✔ 200 | `ok` |
| G | writer 只读 | 200 | ✔ 200 | `ok` |
| H | 异源前缀令牌 | 403 | ✔ 403 | 前缀非同源 |
| I | 格式残缺令牌 | 403 | ✔ 403 | 格式非法 |
| J | admin 写 | 200 | ✔ 200 | `ok` |

## 令牌格式

```
ZRH1.<b64url(payload)>.<hmac_sha256_first16>
payload = {t:令牌ID, n:名称, r:角色, s:范围, e:过期, o:Ω-TAN-7-001, d:DID-BR-000002}
```

- 签名密钥 = PBKDF2-HMAC-SHA512(口令, label‖双标识‖salt, 600000轮, 32B)
- 角色分级：`reader(0) < writer(1) < admin(2)`
- **密钥零落盘**：每次进程启动从口令重新派生，跨沙箱可重建

## 使用

### 启动服务
```bash
python3 server/omega_a2a_v2.py --port 8099 --host 0.0.0.0 \
    --salt <salt> --passphrase <pp>
```

### 验收测试
```bash
python3 lib/a2a_auth_matrix_test.py     # 期望 PASS=10 FAIL=0
```

### 对端注册与探测
```bash
python3 lib/a2a_registry.py add --node-id NODE-X --card-url http://host:8099/.well-known/agent-card.json
python3 lib/a2a_registry.py probe
python3 lib/a2a_registry.py summary
```

### 联邦出站
```bash
python3 federation/a2a_federation_client.py federate \
    --card-url http://host:8099/.well-known/agent-card.json \
    --text "status" --salt <salt> --passphrase <pp>
```

## 法规对齐

- **V3.0「A2A 须经网关仲裁，不得自行直连」** → 本层的 `A2AIdentity` 即「本地同源网关仲裁」的轻量落地：
  跨节点身份先经 ZRH1 双标识校验，裁决记录可投影上报网关，不引入第三方。
- **METALAW.011「不重复注册」** → 节点心跳复用已注册节点，对端注册表只登记不重复注册。
- **AXIOM-REUSE-NO-REDO-001** → 复用 `03_INFRA/interop/` 既有技能语义与 `agent-card.json`，
  复用 `zr-token/homologous/` 密码学实现，零重造。

## 铁律遵循

| 铁律 | 落实 |
|---|---|
| 零删除 | 基线 `omega_a2a_server.baseline.py` 完整留存 |
| 可逆 | 原版 server 未改动，新版为独立文件 |
| 凭证零入库 | 密钥口令不落盘；注册表只存 `token_ref` 变量名 |
| 先规划后执行 | 探查 → 设计 → 实施 → 验证 分阶段 |
