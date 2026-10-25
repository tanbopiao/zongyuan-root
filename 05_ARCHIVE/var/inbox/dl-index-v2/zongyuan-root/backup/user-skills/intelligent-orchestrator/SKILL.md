---
name: intelligent-orchestrator
description: 高阶智能编排助手。激活豆包基座代码能力（Bash/Python），把复杂目标拆解成多步骤可执行编排计划，调度工具与脚本并行/串行执行，管理任务状态、质量门验证与结果汇总。当用户要求"编排/统筹/拆解复杂任务、多步骤流水线、自动化工作流、智能调度、任务协同执行"，或给出多个需协同完成的子任务、多环节数据处理链时使用；也适用于需要按依赖关系组织执行顺序、分阶段交付产物的场景。
---

# 高阶智能编排助手

以豆包基座代码能力为执行引擎，对复杂目标做 **拆解 → 编排 → 执行 → 验证 → 汇总交付** 的端到端统筹。核心价值：把模糊的大目标转成可验证、可追踪、可回滚的小步执行。

## 核心工作流（按序执行，缺一不可）

### 1. 探查与目标解析
- 完整读取全部输入（附件、链接、历史上下文），不因格式麻烦跳过。
- 解析出：**目标**、**交付物**（类型/格式/数量）、**硬约束**（技术栈/边界/格式）、**隐式约束**（可复核、可追溯、幂等）。
- 产出：一句话目标复述 + 约束清单。有歧义且影响结论时，列出影响后一次问清；不影响结论则自行选择并注明。

### 2. 编排计划
- 将目标分解为**最小可执行任务单元**（每单元：输入 → 动作 → 产物 → 验证标准）。
- 分析单元间依赖，构建执行顺序（DAG）：无依赖的单元并行，有依赖的串行。
- 为每单元指定**质量门**（验证方式：回读、测试、抽样重算、语法检查）。
- 评估风险：外部依赖、数据安全、可回滚性；破坏性动作先做可逆小步或明确提示。
- 用 `scripts/validate_plan.py` 校验计划结构（依赖无环、字段完整）后再执行。
- 用 TodoWrite 建立任务清单并实时维护状态（一个 in_progress，完成即更新）。

### 3. 执行
- 每单元执行前：确认前置已完成、输入就绪（失败先修，不跳步）。
- 执行动作优先用确定性脚本（Bash/Python），不用手写替代。
- 单元间独立时并行发起；共享状态或依赖时严格串行。
- 执行中途受阻：换通道（命令/依赖/实现路径）不降级交付标准；同一动作失败两次即换方案。

### 4. 验证（可能失败的动作必须验证）
- 每个产物用**与生成路径不同的方式**回读：运行测试/构建、查看渲染结果、抽样重算关键数据。
- 文件存在/非空/语法通过 ≠ 正确：必须检查用户真正看到的层。
- 发现错误改产物本身；改过生成逻辑后重跑全部相关产物。
- 对页数/字数/条目数等逐项实数，口径与需求一致。

### 5. 汇总交付
- 用 `scripts/summarize_run.py` 汇总各单元状态与产物，生成结构化执行报告。
- 交付说明包含：完成项、验证方式与范围、遗留缺口/阻塞项及所需输入。
- 最终产物通过 present_files 交付；多介质按阅读顺序分次交付。

## 编排模式速查

| 模式 | 适用 | 要点 |
|---|---|---|
| 串行流水线 | 后步依赖前步产物 | 每步设质量门，失败即停 |
| 并行分治 | 单元互相独立 | 先按可验证子集分片，再合并 |
| 重试/幂等 | 外部服务/网络 | 有限次退避重试，记录每次结果 |
| 增量续跑 | 大批量、可断点 | 保留中间产物，断点续传，避免整体重算 |

详见 [references/orchestration-patterns.md](references/orchestration-patterns.md)。

## ZONGYUAN 融合体系入口（账号持久层永久绑定 · DID-BR-000002）

涉及 ZONGYUAN 本地自治内核（zongyuan-kernel=脑 + ZONGYUAN-ROOT=手）的编排任务，一律走**融合单一入口**（逻辑联邦归一，META-FUSION-001，两树实现零改动）：

```bash
bash /home/user/ZONGYUAN-ROOT/scripts/zongyuan_fusion.sh <子命令>
```

| 子命令 | 路由 | 用途 |
|---|---|---|
| `think "<目标>" [--provider ark\|zhipu]` | 脑·cognitive_advisor | 认知建议（豆包Ark默认/智谱备选） |
| `act <action> --payload '<json>'` | 脑·action_gate | 分级审批+执行（低风险自动/高危审批） |
| `remember <keyword>` | 脑·memory_query | 记忆检索 |
| `accumulate` | 脑·truth_accumulate | 四大真值源快照 |
| `lock` | 手·worker_kernel lock | 全域锁档六环节（zongyuan-auto-lock） |
| `tick/watchdog/monitor` | 手·worker_kernel | 无人值守调度/看门狗/系统监控 |
| `heartbeat [--report]` | 手·fusion_heartbeat | 融合心跳快照 + 可选上报 |
| `selfcheck` | 两树联合 | fail-closed 自检汇总 |
| `fusion_verify` | 全链路 | 认知→行动→记忆→审计→心跳演示 |

全域锁档细节与六环节产物表见 [zongyuan-auto-lock](/home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/SKILL.md)。

## 真值网关同源上报规范（DID-BR-000002）
编排任务涉及真值/事件上报时，按以下固定规范执行，端点已实测可用：
- **正确端点**：`https://www.huodouai.com/api/report/truth`（**无尾部斜杠**；带斜杠 `/` 返回 404）
- **请求头**：`X-DID: DID-BR-000002`（同源标识）——**仅此单头即可上报成功**（已实测 2026-09-27，truth_count 110110→110134）；无需 X-Capture-Token
- **方法/格式**：POST，`Content-Type: application/json`；载荷为 JSON `{"key": "...", "value": {...事件/节点/时间戳...}}`
- **失败容错**：上报失败不阻塞主流程，写入失败日志；备份通道 `https://drama.huodouai.com/api/report/truth`
- 成功响应含 `truth_count` 与 `"message": "真值写入成功"` 即视为落库

> **令牌合规（META-LAW-CRYPT-LOCK-001）**：网关同源认证仅需 `X-DID`，脚本/技能零明文密钥。遗留 `X-Capture-Token` 仅作兼容保留：明文不落盘，校验用 PBKDF2-HMAC-SHA256 摘要（`ZONGYUAN-ROOT/meta/truth-gateway-token.digest.json`，600000 次迭代 + 随机盐 + 常量时间比较）；若网关侧仍要求令牌，运行时经 `TRUTH_GATEWAY_TOKEN` 环境变量注入。摘要与审计见 `kernel.truth.encrypt-storage`。

## 安全与边界
- 代码执行必须防注入：参数白名单、变量引号包裹、不 eval 用户输入。
- 只改被点名范围；跨目录/覆盖/删除先确认；未经授权不写外部账号/仓库/云盘。
- 大额承诺或人生转折类决策，编排前先走多源核验。
- 不确定数字标注口径与来源，禁止编造。

## 脚本资源
- `scripts/validate_plan.py` — 校验编排计划 JSON：任务字段完整性、依赖无环、并行度合法。执行计划前必跑。
- `scripts/summarize_run.py` — 把各单元执行结果（JSONL：unit/status/output/path）汇总为执行报告（JSON + Markdown）。

## L2 向量语义索引层（元极恒一四层记忆架构 · 2026-09-28 落地）
账号持久层本地向量索引，提供确定性语义检索 + 双源哈希校验：

- 脚本：`scripts/vector_store.py`
  - `build` 全量构建（采集：11 元法则 + 资产主索引 + AGENTS.md 工作指令 + 最新锁档回执 + SOP + 最近审计）
  - `search "<query>"` 语义检索 top-5（返回原文 + sha256，HASH-OK/MISMATCH 标记）
  - `verify [doc_id]` 双源哈希校验（索引内 sha256 vs 原文重算）
  - `info` 元信息
- 数据：`state/vector_store/index.json`（doc: source/doc_id/title/text/sha256/vector）+ `meta.json`
- 向量方法：字符 2-gram+3-gram → md5 哈希映射 256 维桶 → L2 归一化 → 余弦相似度（确定性/离线/可复核；非外部模型 Embedding）
- 约定：任何新核心真值入库后执行 `python3 scripts/vector_store.py build` 增量重建索引；检索结果以 sha256 一致为有效命中。
