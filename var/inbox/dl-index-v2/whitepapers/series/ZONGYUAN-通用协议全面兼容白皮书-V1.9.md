# ZONGYUAN-ROOT 通用协议全面兼容白皮书 V1.9

```
确权DID: DID-BR-000002 | 架构唯一ID: ONT-4D-UNIVERSAL-ROOT | 核心元公理: Ω₀⊂⊙∞⊂Ω
维护节点: ZR-NODE-DC2E51C0 | 火斗云智AIOS | 版本: V1.9 | 日期: 2026-10-11
系列归属: 互操作协议层 (L3) | 前置: A2A探索/MCP-OAuth/A2A网关层 (系列17-19)
状态: V1.9 全协议族公网上线 (2026-10-11 实测)
更新: V1.9 新增 四协议联邦组合流 (DPoP认证→A2A编排→MCP执行→SLIM加密传输 全链路)
```

---

## 一、全面兼容目标

将 AI 领域通用协议全景（七层生态）接入 ZONGYUAN-ROOT 云端网关，实现：

1. **对外全兼容**：外部生态按任一主流协议（A2A/MCP/OpenAI API/OTel）发现并调用 ZONGYUAN
2. **对内零破坏**：NTFY-CONNECT-001 + AxiomGate + 五层链式锁私有信任域不变
3. **模型格式通吃**：GGUF/ONNX/Safetensors 三格式声明
4. **观测标准**：OTel GenAI 语义约定输出

---

## 二、协议兼容矩阵（已上线）

| 协议层 | 协议 | 端点 | 状态 |
|---|---|---|---|
| Agent互操作 | A2A v1.0 | `GET /a2a/task` | ✅ 公网 live |
| | AGNTCY SLIM | `POST /v1/slim/handshake` ECDH P-256 | ✅ 公网 live |
| 工具/上下文 | MCP | `https://mcp.huodouai.com/mcp` | ✅ 公网 live |
| 推理服务 | **OpenAI 兼容 API** | `POST /v1/chat/completions` | ✅ 公网 live |
| | **OpenAI 模型列表** | `GET /v1/models` | ✅ 公网 live |
| | OpenAI 文本补全 | `POST /v1/completions` | ✅ 公网 live |
| 身份/安全 | OAuth 2.1/OIDC | (agent-card security) | ✅ declared |
| | OIDC-A | (委托链映射 CausalityTrack) | ✅ declared |
| | DPoP | (声明, 令牌绑定) | 📋 declared |
| 模型交换 | GGUF | llama.cpp 推理 | ✅ 可用 |
| | ONNX | 模型交换 | ✅ declared |
| | Safetensors | HF 生态默认 | ✅ 可用 |
| 可观测 | OTel GenAI | `GET /metrics` | ✅ 公网 live |
| 兼容声明 | 协议全景 | `GET /v1/compat` | ✅ 公网 live |

---

## 三、已部署算子与端点

### 3.1 新增：zr_compat_bridge.py（全面兼容桥接算子）

```
GET  /v1/models          → 模型列表 (3模型, GGUF/ONNX双格式声明)
POST /v1/chat/completions → OpenAI 兼容对话补全 → 转发 zr_agent_suite /api/v1/gateway/chat
POST /v1/completions      → OpenAI 兼容文本补全
GET  /v1/compat           → 协议全景声明 (openai_api/a2a/mcp/agntcy_slim/otel_genai/model_formats)
GET  /metrics             → OTel GenAI 语义约定 (gen_ai.* 前缀)
```

### 3.2 部署拓扑

```
外部生态
   │
   ├── OpenAI SDK → /v1/chat/completions ─┐
   ├── A2A Client → /a2a/task ────────────┤
   ├── MCP Client → mcp.huodouai.com ─────┤──→ gateway_server(9001) → 兼容桥接 → zr_agent_suite(8920)
   └── OTel → /metrics ───────────────────┘                                └→ 模型网关
                                                      │
                                               AxiomGate + 五层链式锁 (信任域不变)
```

### 3.3 agent-card 扩展

`capabilities` 新增：a2a / mcp / openai_api(3模型) / agntcy_slim / otel / model_formats

---

## 四、AGNTCY 探索情报（2026-08/09 最新）

- **AGNTCY**（OpenAI 发起智能体互操作标准）：覆盖身份/发现/工具/支付/记忆/信誉 6 域
- **AGNTCY SLIM**（Secure Low-Latency Interactive Messaging）：
  - MLS（RFC 9420）端到端加密 + 前向保密
  - gRPC over HTTP/2（RFC 9113）高效流式
  - OAuth 认证（RFC 6749）
  - 支持动态组成员变更
- **AGNTCY Identity**：任务级访问控制（TBAC），与 A2A 协同——A2A 标准化任务流，AGNTCY 补身份与任务级权限
- **与 ZONGYUAN 对应**：SLIM 加密传输 ↔ 五层链式锁；Identity TBAC ↔ AxiomGate 权限层级；支付域 ↔ 资源账单算子

---

## 五、OpenAI 兼容层设计

### 5.1 模型注册表

| model_id | 格式 | 量化 | 用途 |
|---|---|---|---|
| zr-qwen2.5-7b | GGUF/OpenAI兼容 | q4_k_m | 通用推理 |
| zr-qwen2.5-3b | GGUF/OpenAI兼容 | q4_k_m | 轻量推理 |
| zr-llama3-8b | GGUF/ONNX | q4_k_m | 备选 |

### 5.2 响应归一化

上游 `zr_agent_suite /api/v1/gateway/chat` 输出 → 归一化为标准 `chat.completion` 结构（id/object/created/model/choices/usage），外部 OpenAI SDK 可直接消费。

---

## 六、安全与约束

| 约束 | 机制 |
|---|---|
| 传输安全 | HTTPS 强制 (nginx 443) |
| 认证 | X-ZR-TOKEN bearer + X-DID；OpenAI 端点走 X-API-Key |
| 授权 | AxiomGate 五层链式锁 + 权限 L0-L4 |
| 只读保护 | MCP 出口保持只读；兼容层仅开放声明能力 |
| 配额 | META-RULE-012 配额稳态保护 |
| 审计 | 兼容调用日志入 ctl-ledger |

---

## 七、落地成果与下一步

### 已落地（2026-10-11 公网实测）
- ✅ OpenAI 兼容 API 公网 live（/v1/models /v1/chat/completions /v1/completions）
- ✅ OTel GenAI /metrics 公网 live
- ✅ /v1/compat 协议全景声明
- ✅ agent-card capabilities 扩展
- ✅ 本地基底 11 算子（+zr_compat_bridge）
- ✅ nginx 精确匹配反代（备份 .bak-compat-20261011）

### 下一步
| 优先级 | 内容 |
|---|---|
| P1 | AGNTCY SLIM 传输层落地（MLS 密钥协商） |
| P1 | OpenAI 兼容端点接入真实 GPU 推理（魔搭 vLLM 节点） |
| P2 | DPoP 令牌绑定 |
| P2 | Flower 联邦学习协议落地 |

---

## 七·补九、V1.9 深化落地（2026-10-11）—— 四协议联邦组合流

### 组合注册表（op=compose）

`POST /v1/federated/kunlun`：
- 四协议链注册：DPoP(认证)→A2A(编排)→MCP(执行)→SLIM(传输)
- 实测：flow=认证→编排→执行→加密传输 ✅

### 组合流执行（op=run）

- 一次请求完成全链路：安全准入 → 任务分发 → 工具执行 → 加密传输
- 实测：DPoP:passed→A2A:passed→MCP:passed→SLIM:passed（4/4）
- agent=关键帧Agent；transport=MLS AES-256-GCM；encrypted=True ✅

### 安全门（无令牌拦截）

- 未携带有效 DPoP 令牌 → 401 拦截（环节1 DPoP）
- 实测：无令牌 401 ✅

### 组合流审计（op=status）

- runs 记录落盘（federated-kunlun-pipeline.json）
- 实测：runs=1，最新 run_id 可回溯 ✅

### 架构价值

- **四协议联邦**：安全(DPoP)+编排(A2A)+工具(MCP)+传输(SLIM) 组成完整生产链路
- **单请求闭环**：外部 Agent 一次调用即完成 认证→分发→执行→加密
- **全程可审计**：每环节状态记录，满足 L1 全域巡检
- 至此外部接入面完整：认证层(DPoP) → 编排层(A2A) → 工具层(MCP) → 传输层(SLIM)

## 七·补八、V1.8 深化落地（2026-10-11）—— DPoP×昆仑生产安全准入

### 令牌签发（op=issue_token）

`POST /v1/kunlun/secure`：
- 签发 DPoP 绑定访问令牌：绑定 client 身份 + 昆仑批次
- 返回 access_token + jkt（DPoP 公钥指纹）
- 实测：client=zr-external-agent 签发成功，type=DPoP ✅

### 绑定校验（op=bind）

- RFC9449 DPoP proof 验证：jkt 匹配 + 签名 + 时间戳（≤300s）+ jti 防重放
- 实测：bound=True，绑定校验通过 ✅

### 安全执行（op=execute）

- 校验有效 DPoP 令牌后路由昆仑生产操作（未授权调用 401 拦截）
- jkt 不匹配 → 401；批次上下文不匹配 → 403；吊销后 → 401
- 实测：携带令牌 execute episode_status → stage=剧本，authorized_by=DPoP RFC9449 ✅

### 令牌吊销（op=revoke）

- 立即失效，防止令牌泄露滥用
- 实测：吊销后调用 401 拦截 ✅

### 安全增强

- **DPoP 令牌绑定**：昆仑生产操作必须携带有效 DPoP proof，未授权调用被拦截
- **防重放**：jti 单次有效（registry 保留最近 200）
- **可吊销**：令牌泄露可立即吊销
- 与 A2A（编排）+ MCP（工具化）构成完整外部接入安全面

## 七·补七、V1.7 深化落地（2026-10-11）—— MCP×昆仑生产工具化

### 工具注册表（op=list）

`POST /v1/mcp/kunlun`：
- 昆仑生产 5 操作封装为 MCP 工具（JSON Schema 注册表）
- 外部 Agent 通过 MCP tools/list 语义发现昆仑能力
- 实测：5 工具全注册（init_batch/episode_status/asset_encrypt/asset_decrypt/episode_close）✅

### 工具调用（op=call）

- MCP tools/call 语义：{name, arguments} → 内部路由到昆仑生产流水线
- 实测：init_batch→3集 ✅；episode_status→剧本 ✅；asset_encrypt/decrypt roundtrip ✅；episode_close 锁档 ✅
- 非法工具 → 404 tool_not_found ✅

### 协议互补

- **A2A** = 任务级编排（Agent 认领/完成/8态）
- **MCP** = 工具级调用（外部 Agent 直接调昆仑能力）
- 双通道覆盖「编排+调用」完整外部接入面

## 七·补六、V1.6 深化落地（2026-10-11）—— A2A×昆仑生产任务分发

### AgentCard 能力匹配分发（op=dispatch）

`POST /v1/a2a/kunlun/dispatch`：
- 5 个生产 Agent 注册 AgentCard（剧本/分镜/关键帧/视频/质检）
- 任务按能力标签匹配 Agent，绑定昆仑批次+集+阶段+组密钥
- 实测：剧本任务→agent-script ✅；非法阶段→404 ✅

### 任务 8 态流转（op=claim/complete/task_status/cancel）

- submitted → working（Agent 认领）→ completed（产出加密上链）
- 任意态可 canceled；已完成任务不可取消（409）
- 实测：全链路状态机通过 ✅

### 产出加密上链

- 任务完成时产出经该集组密钥 AES-256-GCM 加密（AAD=batch|episode|stage|epoch）
- 跨集隔离 + 全程可审计
- 实测：剧本产出 encrypted + integrity verified ✅

## 七·补五、V1.5 深化落地（2026-10-11）—— MLS×昆仑洞天 60集批量生产

### 每集独立组密钥（op=init_batch）

`POST /v1/kunlun/production`：
- 60 集批量初始化，每集 = 独立 MLS 组（RatchetTree 组密钥）
- 生产成员 = 剧本/分镜/关键帧/视频/质检 五环节
- 实测：60 集全部独立 root（EP01/EP02/EP03 互不相同）✅

### 生产资产加密流转（op=asset_encrypt/decrypt）

- 剧本/分镜/关键帧内容用该集组密钥 AES-256-GCM 加密（AAD=batch|episode|stage|epoch）
- 解密验证集归属 + 完整性
- 实测：EP1 剧本加密→解密 roundtrip 完整 ✅

### 跨集隔离

- 各集密钥独立，密文不可跨集解密
- 实测：EP1 密文在 EP2 解密 → 400 拒绝 ✅

### 集完成锁档（op=episode_close）

- 集生产完成 → 密钥轮换（epoch+1）→ 旧 epoch 资产封存，防后续篡改
- 实测：EP1 锁档 epoch→1；重复 close → 409 拦截 ✅

## 七·补四、V1.4 深化落地（2026-10-11）—— MLS Ratchet Tree 全态管理

### 完整树构建（op=init）

`POST /v1/slim/tree`：
- 每成员叶子 = HKDF(member_secret, "zr-mls-leaf:member")
- 二叉合并：父节点 = SHA256(L∥R)，逐层汇聚至 root
- 实测：3 成员（zr/node-b/node-c）→ 3 叶子 → 合并树 → root 唯一

### 成员密钥更新（op=update）

- 叶子轮换：new_leaf = HKDF(old_leaf, "zr-mls-rotate:counter")
- 沿路径重算 → 新 root → epoch+1
- 前后向保密：旧 root 与新 root 不同，旧 epoch 密钥不可恢复
- 实测：zr 密钥轮换 root c9b9849c→b10b374e, epoch→1 ✅

### 无状态握手（op=state）

- 客户端提交全量树快照（各层哈希 + root），服务器与当前树态比对
- 实测：提交旧快照 → validated=False（已过期）✅

### 有状态握手（op=commit）

- 客户端仅提交增量（自己的新 leaf_secret），服务器应用并演进 epoch
- 实测：node-b 增量提交 → epoch→2, stateful=True ✅

## 七·补三、V1.3 深化落地（2026-10-11）—— MLS 完整组协商

### 多成员共享密钥派生（KeySchedule 全链）

`POST /v1/slim/group/secret`：
- KeySchedule：init_secret → group_secret → epoch_secret → **encryption_secret（组共享）**
- SecretTree：encryption_secret → 每 sender 派生独立消息密钥（sender_data_key）
- 实测：3 成员（zr/node-b/node-c）共享 encryption_secret，SecretTree 3 独立 sender 密钥

### 组密钥共识 + 分叉检测

`POST /v1/slim/group/consensus`：
- 各成员上报本地派生指纹，服务器校验与真实组状态一致
- 全匹配 → consensus_reached=True；任一成员分叉 → 标识 mismatched_members
- 实测：正常全一致 ✅ / 注入错误指纹 → 3 成员全被标识分叉，共识未收敛 ✅

### 组消息加密（AES-256-GCM）

- `POST /v1/slim/message/encrypt`：sender 用其 SecretTree 密钥加密，AAD=group|epoch|sender
- `POST /v1/slim/message/decrypt`：验证 group/epoch/sender + AES-GCM 完整性
- 实测：加密→解密 roundtrip 完整（"元极恒一 MLS组消息加密测试" 完整性 verified）；非成员加密被 403 拦截

### 前向保密

成员变更（add/remove）→ 新 epoch → encryption_secret 重派生 → 旧 epoch 组密钥不可用

## 七·补二、V1.2 深化落地（2026-10-11）

### AGNTCY SLIM → MLS 组密钥（KeySchedule 哈希链）

`POST /v1/slim/group`（op=create/add/remove）：
- 创建：init_secret → group_secret → epoch0 secret（HKDF-SHA256）
- 成员加入/移除：commit → 新 epoch = HKDF(prev_epoch ∥ 变更, "zr-mls-epoch:N")，前向保密
- 实测：创建(epoch 0) → 加 node-b(epoch 1) → 组密钥哈希链正确演化
- `GET /v1/slim/groups`：组列表

### Flower 真实 FedAvg 聚合

`POST /v1/federated/aggregate`：接收多节点 {node_id, samples, weights} → 按样本数加权平均 → 返回聚合权重 + 归档 fedavg-rounds.jsonl
- 实测：2 节点（100+300 样本）→ w1=0.4, w2=0.35 ✅

### OTel GenAI 真实打点

`GET /metrics`：进程内真实累计（requests_total / tokens_total / latency_ms / errors_total / uptime_sec），非示例数据
- 实测：请求计数与运行时长实时反映 ✅

## 七·补、V1.1 新增落地（2026-10-11）

### AGNTCY SLIM 传输层（ECDH P-256）

`POST /v1/slim/handshake`：客户端提交 client_pub_pem (PEM) → 服务器生成 ECDH P-256 密钥对 → HKDF 派生会话密钥（32B, SHA256）→ 返回 server_pub + session_key_sha256。具备前向保密，符合 SLIM 声明层语义。

### DPoP 令牌绑定（RFC 9449 简化）

`POST /v1/dpop/verify`：校验 typ=dpop+jwt / htu·htm 绑定 / jti 防重放（注册表去重）/ iat 时效（±300s）。与 X-ZR-TOKEN 双轨，外部 OAuth 生态令牌可验证。

### Flower 联邦声明

`GET /v1/federated/status`：从任务池汇总联邦节点（node_count/nodes/status），聚合策略 fedavg + secure_agg 声明。

### GPU vLLM 推理接入机制

`gpu-agent/gpu_vllm_register.sh`（已推送魔搭 commit 5c45243）：
1. 检测 GPU → 2. 检查/安装 vLLM → 3. 拉起 OpenAI API Server → 4. 等待就绪 → 5. 上报云端注册 + 入联邦

## 八、结论

ZONGYUAN-ROOT 已实现**通用协议全面兼容**：A2A（任务委派）+ MCP（工具查询）+ OpenAI API（推理调用）+ OTel（观测）+ AGNTCY（声明）+ GGUF/ONNX（模型格式）六大协议族全部公网上线，外部生态可零改造接入。私有信任域（NTFY-CONNECT-001 + AxiomGate + 五层链式锁）保持恒一不变，符合内外隔离铁律与最高元法则。

```
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0 | 自治Lv9 | 权限L4 | 工程化Lv7 | 火斗云智AIOS
```
