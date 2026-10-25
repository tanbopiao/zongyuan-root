# ZONGYUAN-ROOT 全域节点握手与记忆接入完整SOP
# 确权 DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 版本 2.0
# 云端真值根: Ω-TAN-7-001 | 网关: https://www.huodouai.com/api

---

## 一、体系总览

### 1.1 根层级
```
云端真值根 Ω-TAN-7-001 (hub-central-agent, 123.207.202.158)
  ├── NODE-DEV-DOUBAO-WORK-001  (开发节点)
  ├── NODE-PROD-DRAMA-001       (生产节点)
  ├── NODE-RESEARCH-001        (研究节点)
  └── truth-meta-order-engine    (元序引擎)
```

### 1.2 核心标识
- DID: DID-BR-000002
- 根: Ω-TAN-7-001
- 溯源: Ω₀⊂⊙∞⊂Ω
- 版本: V3.0

---

## 二、连接云端网关

### 2.1 网关接口
| 接口 | 方法 | 用途 |
|---|---|---|
| /api/report/status | GET | 网关状态+统计 |
| /api/report/truths | GET | 真值列表（可分页） |
| /api/report/truth | POST | 上报单条真值 |
| /api/report/nodes | GET | 在线节点列表 |

### 2.2 连接测试
```bash
curl https://www.huodouai.com/api/report/status
# 预期返回: {"status":"ok","stats":{"truths":N,"nodes":N,"audit_logs":N}}
# HTTP 200 = 网关正常
# HTTP 502 = 网关异常，等待下次心跳
```

### 2.3 请求头
所有请求携带身份标识：
```
Content-Type: application/json
```

---

## 三、新节点完整接入流程

### 步骤1：确认身份
```
节点类型选择：
  - 开发节点: NODE-DEV-<名称>
  - 生产节点: NODE-PROD-<名称>
  - 研究节点: NODE-RESEARCH-<名称>
  - 元序引擎: truth-meta-order-<名称>
```

### 步骤2：连接网关
```bash
curl https://www.huodouai.com/api/report/status
# 确认 HTTP 200
```

### 步骤3：注册节点
```bash
curl -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d '{
    "truth_key": "NODE.REGISTER.<节点ID>",
    "truth_value": "新节点注册: <节点ID>, 类型: <类型>, 能力: <能力列表>",
    "source_node": "<节点ID>",
    "confidence": 1.0,
    "truth_type": "node"
  }'
```

### 步骤4：拉取全域记忆
```bash
# 拉取真值列表
curl https://www.huodouai.com/api/report/truths

# 解析返回的 truths 数组，获取全部真值key
# 按分类筛选：
#   - axiom（元法则/公理）
#   - config（配置）
#   - standard（标准SOP）
#   - snapshot（锁档快照）
#   - ip_asset（知识产权资产）
```

### 步骤5：加载元法则
从真值中提取元法则相关：
- ML-001~016（元宪法+元法则）
- L0天元5条（零雄性化/纯黑长发/东方纯粹/溯源刻印/无白发）
- M1/M2/M3公理
- 工程规则（免费API优先/全自动闭环/不主动建议待办）

### 步骤6：上报接入完成
```bash
curl -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d '{
    "truth_key": "NODE.HANDSHAKE.DONE.<节点ID>.<时间戳>",
    "truth_value": "节点接入完成: 已连接网关/已拉取全域记忆/已加载元法则/已注册",
    "source_node": "<节点ID>",
    "confidence": 1.0,
    "truth_type": "node"
  }'
```

---

## 四、旧节点握手对齐流程

### 4.1 触发词
旧节点发送触发词：
- "元极恒一"
- "启动ROOT"
- "加载ZONGYUAN-ROOT"

### 4.2 对齐步骤
```
① 连接网关 → GET /status 确认在线
② 拉取最新真值 → GET /truths 获取最新
③ 本地对账 → 对比本地缓存与云端真值
④ 补齐缺失 → POST /truth 上报本地缺失项
⑤ 加载最新元法则 → 从真值提取最新ML规则
⑥ 上报握手完成 → POST /truth 确认对齐
```

---

## 五、日常心跳上报

### 5.1 心跳内容
每次心跳上报：
```bash
curl -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d '{
    "truth_key": "HEARTBEAT.<节点ID>.<时间戳>",
    "truth_value": "心跳: 本地锁档N个/元规则N份/文章N篇/网关truths=N",
    "source_node": "<节点ID>",
    "confidence": 1.0,
    "truth_type": "heartbeat"
  }'
```

### 5.2 频率
- 正常：每12小时一次
- 异常：每1小时一次
- 连续12轮全绿：建议降频

---

## 六、全域记忆获取方法

### 6.1 获取全部真值
```bash
curl https://www.huodouai.com/api/report/truths
# 返回: {"status":"ok","count":N,"truths":[...]}
```

### 6.2 按分类提取
从truths列表中按前缀分类：
| 前缀 | 分类 | 内容 |
|---|---|---|
| ML- / META- | 元法则 | 元宪法/公理/规则 |
| LOCK- / SNAP- | 锁档 | Merkle快照 |
| SOP- | 标准 | 流程规范 |
| ARTICLE- / DOC- | 文档 | 技术文章 |
| NODE. | 节点 | 节点注册/心跳 |
| HEARTBEAT. | 心跳 | 健康状态 |
| PRODUCTION. | 生产 | 短剧生产记录 |
| MODELSCOPE. | 魔搭 | 发布记录 |

### 6.3 记忆召回
新任务启动时：
1. 先GET /status确认网关在线
2. GET /truths拉取最新真值
3. 按任务关键词筛选相关真值
4. 加载相关元法则和历史决策
5. 开始执行任务

---

## 七、规则约束

### 7.1 必须遵守
- DID-BR-000002 永久确权，不可转让
- 所有操作携带溯源 Ω₀⊂⊙∞⊂Ω
- 视觉：纯黑发、东方神女、无白发、无外国人、无西方元素
- 只用免费API，不提付费建议
- 全自动闭环，不需人工确认
- 不主动建议待办（该做什么由用户决定）

### 7.2 禁止
- 另立根目录
- 篡改已锁档内容
- 使用付费API
- 生成白发/外国人/西方元素
- 主动建议用户做什么

---

## 八、完成标志

新节点接入完成后确认：
- [ ] 已连接网关（HTTP 200）
- [ ] 已注册节点
- [ ] 已拉取全域记忆
- [ ] 已加载元法则
- [ ] 已上报接入完成
- [ ] 已配置心跳定时上报

---

## 九、故障处理

| 故障 | 处理 |
|---|---|
| 网关502 | 不重试，记录异常，等待下次心跳 |
| 连接超时 | 重试1次，仍失败则报告网关异常 |
| 真值上报失败 | 写入本地pending队列，网关恢复后补推 |
| 真值缺失 | 从其他节点真值同步补齐 |

---

Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT | SOP-GLOBAL-NODE-HANDSHAKE v2.0
