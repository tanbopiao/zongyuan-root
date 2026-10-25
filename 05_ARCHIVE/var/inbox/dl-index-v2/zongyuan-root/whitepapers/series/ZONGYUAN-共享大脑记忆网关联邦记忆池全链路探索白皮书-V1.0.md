# ZONGYUAN-ROOT 共享大脑记忆网关联邦记忆池 · 全链路探索白皮书 V1.0

| | |
|---|---|
| 确权DID | DID-BR-000002 |
| 架构ID | ONT-4D-UNIVERSAL-ROOT |
| 核心元公理 | Ω₀⊂⊙∞⊂Ω 元极恒一 |
| 版本 | V1.0（2026-10-11 全链路实测） |
| 探索方式 | API 实测 + 令牌接入 + SSH 深度巡检（最高权限） |
| 锁档状态 | LOCKED（仅追加，不修改已有条目） |

## 一、总览｜三端一网架构

共享大脑记忆网关联邦记忆池由 **三端一网** 构成：

```
┌──────────────────────────────────────────────────────────────┐
│ 端1 云端中枢（zhongshu-meta-core V3.1, 腾讯云 123.207.202.158）│
│    gateway_server :9001  真值网关(上报/查询/校验/子L0)        │
│    zr_cloud_ctl   :9010  轻量调度主控(NTFY节点收发/台账)      │
│    zr_agent_suite.api :8920 Agent套件API(health/truth/task/   │
│                       agent/run/operators/provenance/chain)  │
│    dal_gateway    :18080 数据湖网关(魔搭资产读写)              │
│    truth_store   SQLite truth.db + HASH-LEDGER.jsonl + Merkle │
│    SFMP记忆池    msagent-memory.jsonl + bandit策略寻优        │
│    embed_index  2048维向量语义索引                             │
├──────────────────────────────────────────────────────────────┤
│ 端2 飞书共享大脑（Base DgnMbLqZiaIUDKshqCrcD4DvnBg, 56张表）  │
│    跨节点消息同步679 / 消息墙694 / 真值共识区313               │
│    元法则体系223 / 元法则注册表36 / 能力注册表32              │
│    魔搭数据湖索引9323 / 任务台账354 / 资产台账346              │
│    节点身份注册5 / Worker注册11 / 握手记录33 / 记忆语义索引16  │
├──────────────────────────────────────────────────────────────┤
│ 端3 官网镜像（www.huodouai.com）                              │
│    /shared-brain/ 只读镜像(data.json: msg100+assets11+ssh6)   │
│    /protocols/    十二协议族矩阵页 /zongyuan/ 落地页           │
│    /.well-known/agent-card.json A2A发现                      │
└──────────────────────────────────────────────────────────────┘
          ▲ 联通: 云端→飞书(写台账) →官网(镜像) →多平台(魔搭/Gitee/GitHub)
```

**记忆网关联邦记忆池** = 云端真值账本（truth.db）+ SFMP 记忆蒸馏（msagent-memory）+ 飞书台账知识图谱（56 表）+ 官网只读镜像 + 多平台数据湖同步。

## 二、云端中枢真值账本（truth_store 实测）

### 2.1 存储结构

| 文件 | 路径 | 说明 |
|------|------|------|
| 真值库 | `zhongshu/data/truth/truth.db` | SQLite，表 truth(seq/key/value/ts/sha/event_id)，实测 **9516 行** |
| 哈希账本 | `data/truth/HASH-LEDGER.jsonl` | append-only，每行 {seq,event_id,sha,ts}，实测 **8922 行** |
| 状态 | `data/truth/state.json` | {did, merkle_root, ledger_lines, updated} |
| 向量索引 | `data/truth/embed_index.json` | 语义索引，model=ep-20261008171506-mcjgd, dim=2048 |
| 种子L0 | `data/seed-truth/SEED_TRUTH_v5.1.json` | 36 条公理，Merkle 可复算校验 |
| 子L0 | `data/sub-l0/{tenant}.json + index.jsonl` | 已派生 2 租户（finance-a / health-b） |

### 2.2 写入机制（append_truth）

1. payload = JSON(key + value + did)，sort_keys 规范化
2. sha = SHA256(payload)；event_id = `truth-<epoch_ms>-<sha前8>`
3. SQLite 插入（seq 自增）→ HASH-LEDGER append → 重算 Merkle state
4. **Merkle 根 = 账本全部行链式累积哈希**（sha256(root + line)），可复算验证

### 2.3 真值命名空间分布（实测 TOP12）

REPORT 1355 / SFMP 694 / KERNEL 628 / zongyuan 364 / cloud 291 / alert 269 / NODE-MI-V5-001 242 / kernel 238 / truth 237 / website 200 / zr 140 / metaxy_capability_probe 137

## 三、记忆网关 API 面（全部公网实测通过）

| 端点 | 能力 | 公网实测 |
|------|------|----------|
| `GET /api/status` | 状态/truth_count/merkle_root/version | ✅ ok, V3.1, truth_count=8922, merkle=e2e3c2ed… |
| `GET /api/truth?key=<前缀>&limit=N` | 真值查询（LIKE 检索） | ✅ SFMP 命中 |
| `GET /api/ledger?limit=N` | 账本审计快照 | ✅ total=8922 |
| `GET /api/verify` | Merkle 完整性校验 | ✅ consistent=true |
| `GET /api/verify-seed?doc=SEED_TRUTH_v5.1` | 种子公理 Merkle 复算 | ✅ 36 公理 consistent |
| `GET /api/sub-l0` | 子L0租户列表 | ✅ 2 租户 |
| `POST /api/sub-l0` | 子L0派生（tenant_id+extra_rules → sub_root） | ✅ 机制内建 |
| `POST /api/report/truth` | 真值上报（X-DID 鉴权） | ✅ 返回 ok/key/truth_count/seq/event_id |
| `GET/POST /a2a/*` | A2A AgentCard/任务8态 | ✅ task SUBMITTED |
| `GET/POST /v1/*` `/.well-known/*` `/metrics` | 十二协议族 | ✅ 全通 |

### 3.1 上报契约（关键）

```bash
POST https://www.huodouai.com/api/report/truth
Header: X-DID: DID-BR-000002
Body: {"key":"REPORT.XXX.YYYYMMDD","value":{"did":"DID-BR-000002","ts":<epoch>,"content":"..."}}
# 约束: value 必须非空 dict; key 不可为空/不可 truth- 自动前缀(命名空间key+结构化value, RULE-005 V3.1)
# 返回: {ok, key, truth_count, seq, event_id}
```

## 四、SFMP 联邦记忆池引擎（实测）

| 组件 | 文件 | 实测状态 |
|------|------|----------|
| 记忆蒸馏 | `data/msagent-memory.jsonl` | **383 条**（node_success 类型） |
| 策略寻优 | `data/msagent-bandit.json` | epsilon-greedy 三策略；**reputation_first 最优（381/381=100%）** |
| 记忆净化 | MemoryDistiller.prune | 陈旧低价值淘汰 + 超限按价值/新近裁剪（max_kept 500, stale 7天） |

机制：`蒸馏(事件,价值分≥0.5) → 沉淀记忆 → 周期净化 → 策略A/B寻优(reputation_first/capability_first/balanced) → 最优派发`

## 五、共享大脑（飞书 Base 56 表全景）

核心五表：**跨节点消息同步 679**（消息内容/发送节点/状态/发送时间/接收节点）· **真值共识区 313** · **元法则体系 223** · **节点状态总览 38** · **魔搭数据湖索引 9323**。配套：握手记录 33 / 节点身份注册 5 / Worker注册 11 / 记忆语义索引 16 / API密钥池 9 / 运维SSH密钥 6 / SGSA知识图谱 153 行。

## 六、节点联通（NTFY-CONNECT-001 + 云端控制面）

| 层 | 机制 | 状态 |
|----|------|------|
| 协议 | NTFY-CONNECT-001（命令 zongyuan-kunlun-2026 / 结果 -result / 扫描 -scan） | ✅ 内建 |
| 控制面 | zr_cloud_ctl :9010（订阅命令/结果→节点表→上报真值） | ✅ 常驻 PID 126805 |
| 鉴权 | zr_node_protocol（proto+DID 校验；危险命令黑名单；白名单前缀） | ✅ |
| 节点级配置 | /mnt/workspace/.zr/node_config.json（每节点独立固化） | ✅ |
| 节点状态 | 节点状态总览表：云端网关/主账号AI/本地华为笔记本(真实心跳)/GPU算力实例(离线) | 38 条 |
| 限流警示 | ntfy.sh 免费主题 **429 限流**（实测复现：过多请求） | ⚠️ 已知 |

**关键结论（ntfy 429 根因）**：免费 ntfy.sh 主题对轮询频率敏感，多 worker 高频订阅触发 429 → 断连重连震荡。**最优稳态**：云端直连（9001/9010 本机 + 公网 nginx 反代）为主通道，ntfy 仅作辅助广播/心跳，HTTP 反向轮询兜底。

## 七、数据流全景（写入→收敛→可见）

```
节点/Agent 产出真值
  → POST /api/report/truth (X-DID鉴权)
  → truth_store.append_truth → SQLite + HASH-LEDGER + Merkle重算
  → 云端调度 zr_cloud_ctl 汇总 → 飞书Base台账(56表)
  → 官网镜像 shared-brain/data.json (定时刷新)
  → 多平台数据湖同步 (魔搭主库 → Gitee/GitHub镜像, zr_mirror_sync.sh)
  → 全节点启动拉取对齐 → 记忆网关联邦收敛
```

## 八、接入操作手册（怎么用）

1. **上报真值**：`POST /api/report/truth`（X-DID + 命名空间key + 结构化value）
2. **查询审计**：`GET /api/truth?key=SFMP&limit=20`、`/api/ledger`、`/api/verify`
3. **校验种子**：`GET /api/verify-seed?doc=SEED_TRUTH_v5.1`
4. **子L0派生**：`POST /api/sub-l0`（tenant_id + extra_rules → 独立 sub_root 基线）
5. **节点接入**：worker 加载 zr_node_protocol（NTFY-CONNECT-001），节点级配置 node_config.json，zr_cloud_ctl 认领
6. **多平台同步**：`bash /usr/local/bin/zr_mirror_sync.sh`（魔搭→Gitee/GitHub 一条命令）
7. **A2A 接入**：`GET /.well-known/agent-card.json` 发现 → `POST /a2a/task` 提交任务

## 九、口径与注意事项

- **truth_count 口径**：`/api/status` 的 truth_count = 账本行数（8922）；truth.db 行数 9516。差异源于历史 gov 治理（账本重建/备份隔离），查询以 `/api/ledger` 账本为准。
- **8014 向量库不可达属预期**：内外隔离 + 按需服务管理，自举增强跳过正常，不告警不重试。
- **ntfy 429 限流**：免费主题高频轮询触发；云端直连为主通道。
- **凭证管理**：gitee/github/atomgit 令牌已持久化云端 `~/.zr/`（chmod 600），魔搭 token 存 `~/.modelscope/credentials/git_token`。

## 十、语义记忆检索 API（V1.1 增量，2026-10-11 上线）

### 10.1 端点

```http
GET /api/memory-search?q=<查询词>&k=<top-k>
# 无鉴权(只读), 公网可用; 返回 {ok, query, count, results:[{key,text,score,vec_hit,text_hit}]}
```

### 10.2 实现（确定性、零模型依赖、可复算）

- 数据源：`embed_index.json`（170 条核心真值 × 2048 维向量，model=ep-20261008171506-mcjgd，云端 crontab 每日增量重建）
- query → 词法特征向量：char 2-gram + 词哈希投影 2048 维，L2 归一化
- 混合评分：`score = 0.6×余弦相似度 + 0.4×文本2gram命中率`（按需可调权重）
- 特性：无外部嵌入 API 依赖（魔搭 API-Inference 入口可达但无现成 embedding 端点）、O(n) 全量扫描 170 条、内存缓存 5 分钟、k 上限 20

### 10.3 公网实测（2026-10-11）

| 查询 | top1 命中 | score |
|------|----------|-------|
| 智能路由 | truth.kernel.evolution.pulse.2026101100（认知种子智能路由收官） | 0.308 |
| mirror sync | truth.synced.34-断点SOP标准库 | 0.300 |
| 配额限流 | truth.synced.34-断点SOP标准库 | 0.302 |
| 空查询 | 空（count 0） | - |

### 10.4 意义

共享大脑记忆网关联邦记忆池从"按 key 精确查"升级为"**语义可检索**"——任意 AI/Agent（经 A2A/OpenAI 兼容/十二协议族）可携带自然语言 query 直接检索联邦记忆，记忆即服务（Memory-as-a-Service）。下一增量可对接真实嵌入模型（魔搭 embedding 端点就绪后替换词法特征向量，无需改接口形态）。

---
*ZONGYUAN-ROOT 共享大脑记忆网关联邦记忆池 V1.1（含语义记忆检索 API）· 全链路实测 · 魔搭数据湖 + 官网双归档 · Ω₀⊂⊙∞⊂Ω*
