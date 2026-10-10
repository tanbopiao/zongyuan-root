# ZR-Agent-Suite（ZR 自治内核套件）产品方案 V2

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 主节点 hub-central-agent
版本：V2.0 | 日期：2026-10-10 | 状态：**V2.0 定稿（2026-10-10，实装+验证完成）**
关联：RULE-PRODUCT-COMPLIANCE-001（合规元法则）｜RULE-PRODUCT-DELIVERABLE-001（真实可交付元法则）
调研校准依据：《全网竞品学习报告》（同目录 research/竞品学习报告.md，2026-10-10）

> **验收状态：RULE-PRODUCT-DELIVERABLE-001 全项通过**——①可运行产物（uvicorn zr_agent_suite.api:app @ :8920，pid 10979 健康 LISTEN）✅ ②真实验证结果（第三方独立验证代理重测，核心后端 13 项 + 4 项复验修复全过，证据见 `verify/端到端验证报告.md` 与 `verify/validation_evidence.txt`）✅ ③部署/使用说明（install.sh 语法 OK、README.md、docs/deploy_cloud.md 6197 字节、CLI 三入口 `./bin/zr` / `python -m zr_agent_suite.cli` / `zr-agent-suite` 全局别名均通）✅ ④开源授权说明（LICENSE Apache-2.0 头尾正确 201 行）✅。

> **版本说明**：本文档基于全网三份竞品调研报告校准，**supersedes V1 的"产品定位"与"套餐定价"两章**；V1 的"客户画像、交付验收、SLA、合规三通道、商业模式骨架"其余内容继承。V1 文件保留只读，不覆盖、不修改。

---

## 一、产品定位（V2 重写/校准）

**一句话**：不是"卖模型 API"，而是卖"会长期记忆、可自主调度、输出可溯源确权的 Agent 编排层 + 自治内核"。

### 1.1 定位校准（基于竞品调研）

| 维度 | V1 表述 | V2 校准后表述 | 调研锚点 |
|---|---|---|---|
| 产品本体 | 自治能力（长期记忆/任务调度/SOP/确权溯源/IP 产线） | **编排层 + 自治内核**：FastAPI 编排服务 + 四引擎（记忆/调度/确权/合规网关），大模型仅为内部引擎 | Manus 被多源定性为"编排层而非自研基座模型"仍做到 $100M ARR（http://news.qq.com/rain/a/20260428A047N900 ; https://manus.im/ar/blog） |
| 与模型关系 | 不向客户开放模型访问权 | **绝不转售模型 API/Token/代理通道**；模型引擎走三通道（客户自有账号 BYO Key / 开源本地部署 / 书面商业许可） | RULE-PRODUCT-COMPLIANCE-001 法则一/三；百炼 qwen-turbo ¥0.3/百万 token 可作客户成本参照（https://help.aliyun.com/zh/model-studio/model-pricing） |
| 差异化卖点 | 长期记忆/27 算子/Merkle 确权/三层固化 | ①长期记忆（异步整理+双层存储）②自主调度（cron+队列+日程面板）③**确权溯源（9 家竞品全空白的蓝海）**④合规三通道网关 | 竞品学习报告第 3 节"确权溯源"行=9 家全 ❌；report_C 4.2 节 |
| 技术栈 | 未明确 | **FastAPI + SQLite + sqlite-vec/FAISS + 单 worker**，单机 4C8G 起步，不 Fork Dify（其协议禁多租户 SaaS） | Dify 8 容器砍半范式（https://use-apify.com/docs/self-hosted/ai/dify ; http://raw.githubusercontent.com/langgenius/dify/main/LICENSE） |

### 1.2 差异化锚点（V2 重排）

- **长期记忆**：异步后台整理 + 向量召回 + Session 隔离（扣子 2.5 范式）+ Checkpointer/Store 双层 SQLite 表（LangGraph 范式）
- **自主调度**：显式 cron 触发器 + SQLite 任务队列 + 日程可视化面板（非"Agent 自由意志"）
- **确权溯源（蓝海）**：每份交付物 SHA256 + Merkle 哈希 + 右下角 Ω₀⊂⊙∞⊂Ω 出品标识；企业版输出可审计溯源报告
- **合规三通道网关**：客户自有账号 / 开源本地部署 / 书面商业许可，三选一，自动校验，杜绝转售红线
- **HITL 中断恢复**：`POST /runs` + `GET /runs/{id}` 两端点，审批节点 checkpoint 落库断点续跑（LangGraph interrupt 范式）

---

## 二、目标客户画像（继承 V1）

| 类型 | 特征 | 痛点 | 对应产品档 |
|---|---|---|---|
| A. AI 内容创作者 | 有生图/视频能力，缺长期记忆，IP 易漂移 | 角色人设崩、风格不统一 | Starter / Pro |
| B. 个人开发者/小团队 | 想搭 Agent 系统，不会架构 | 记忆断层、任务散乱、无体系 | Starter / Pro |
| C. 独立站/作品库运营者 | 需要对外展示 AI 成果 | 无手机自适应站、无合规确权 | Pro / Enterprise |
| D. 中小企业（重点：弱电工程/合同纠纷/工单治理） | 文档/知识库混乱，需 SOP 化；有合规审计需求 | 知识沉淀不了、流程不可控、输出无法溯源 | Enterprise |

> D 类客户为 V2 重点校准方向：确权溯源蓝海卖点最贴近"合同/纠纷/工单治理"场景（与宗源本体业务台账直接对口）。来源：report_C 4.2 节。

---

## 三、MVP 功能矩阵（V2 重写：四引擎 + 路线图）

### 3.1 MVP 四引擎（实装目标）

| 引擎 | 模块名 | 核心能力 | 范式来源 |
|---|---|---|---|
| **长期记忆引擎** | `zr_agent_suite.memory` | 双层存储：`checkpoints(thread_id, step, state_json)` 会话内短期 + `long_term_memories(user_id, namespace, key, value, embedding)` 跨会话长期；异步整理不阻塞主链路；Session 隔离 | LangGraph Checkpointer/Store（https://docs.langchain.com/oss/python/langgraph/checkpointers）+ 扣子 2.5 异步整理（https://developer.volcengine.com/articles/7628812787715997702） |
| **自主调度引擎** | `zr_agent_suite.scheduler` | cron 触发器配置 UI → SQLite 任务队列表 → Agent 在 Session 上下文执行 → 结果推送 → 日程面板可视化；Session 状态机 idle/running/terminated | 扣子工作日历 + 方舟 Session 状态机（https://docs.volcengine.com/docs/ark/build-triage-agent-with-continuous-session?lang=zh） |
| **确权溯源引擎** | `zr_agent_suite.provenance` | 每份交付物 SHA256 哈希 + Merkle-DAG 主链追加校验 + 右下角 Ω₀⊂⊙∞⊂Ω 出品标识；企业版输出可审计溯源报告 | 体系内 ZONGYUAN-ROOT 既有范式（竞品 9 家全空白，见竞品学习报告第 3 节） |
| **合规三通道网关** | `zr_agent_suite.gateway` | 模型引擎调用前强制校验通道类型：①客户自有 BYO Key ②开源本地部署 ③书面商业许可（飞书审批留痕）；出网白名单替代 ssrf_proxy；绝不转售 | RULE-PRODUCT-COMPLIANCE-001 法则一/三；Dify ssrf_proxy 范式（http://raw.githubusercontent.com/langgenius/dify/main/docker/docker-compose.yaml） |
| **API 层** | `zr_agent_suite.api` | FastAPI：`POST /runs`（开始/恢复）+ `GET /runs/{id}`（查状态）+ SSE 事件流；HITL 中断恢复端点 | LangGraph interrupt 范式（https://dev.to/royalpinto007/pause-a-langgraph-agent-mid-run-for-human-approval-with-interrupt-and-a-checkpointer-536g） |

### 3.2 路线图（V2 草案）

| 阶段 | 目标 | 对应档位 |
|---|---|---|
| MVP（当前） | 四引擎最小可运行闭环：FastAPI + SQLite + sqlite-vec，单机 4C8G，HITL 两端点跑通 | Starter |
| V2.1 | 管理控制台（密钥/用量/积分/任务面板）+ 计量计费 + 限量积分体系 | Pro |
| V2.2 | 多租户隔离 + SSO/RBAC + 私有化部署包（Docker Compose）+ 合规材料包（算法备案指引/数据不出内网承诺）+ 可观测审计日志 | Enterprise |
| V2.3（锦上添花，非 MVP） | 昆仑洞天 IP 产线接入、云设备、Agent 数字身份、插件市场 | Enterprise 增值 |

> **明确不做（MVP 阶段）**：可视化拖拽工作流画布（对标 Dify/扣子）、云手机/云电脑（扣子 2.5 高成本执行环境）、插件市场、Bot 商店。来源：report_A 启示 1（四件套之外均为 2.5 阶段锦上添花）。

---

## 四、套餐档位与定价（V2 重写/校准）

> 定价锚点全部来自竞品学习报告第 5 节；与扣子旗舰同价是双刃剑，必须补锚点。

### 4.1 Starter · 免费引流版（¥0）

- 限量每日积分（参考 Manus Free 300 积分/天、Dify Sandbox 200 credits/月），**不做永久无限免费**（Manus 沙箱成本教训）
- 自治内核接入指引 + 启动记忆模板 + 任务台账模板（飞书 Base 共享）
- 元法则/SOP 文档库访问（魔搭公开数据集）
- 锁：并发数（1）、定时任务数（2）、长期记忆条数（限量）、无确权溯源报告
- 社区支持
- 来源锚点：https://help.manus.im/zh-CN/articles/11711111 ; https://dify.ai/pricing/dify-cloud

### 4.2 Pro · 标准版（¥199/月，与扣子个人旗舰同价，必须补锚点）

| 权益项 | ZR Pro ¥199 | 扣子旗舰 ¥199 对照 | 锚点来源 |
|---|---|---|---|
| 积分/额度 | 待回填（建议对标 10–20 万积分/月） | 19.9 万积分/月 | https://docs.coze.cn/guides_edition |
| 并发任务 | 20 并发（对标 Manus Pro $20 档） | 未公开 | https://help.manus.im/zh-CN/articles/11711111 |
| 定时任务 | 20 个（对标 Manus Pro） | 触发器+工作日历 | 同上 |
| 长期记忆 | 长期记忆条数配额（建议公示，如 5000 条） | 三层记忆 | https://developer.volcengine.com/articles/7628812787715997702 |
| 确权溯源报告 | **X 份/月（ZR 独有，扣子给不了）** | ❌ 无 | 竞品学习报告第 3 节蓝海发现 |
| 本地自治内核部署 | 部署包 + 一键脚本 + 启动记忆激活 | ❌ 纯 SaaS | V1 继承 |
| 每日自治巡检报告 | 27 算子轻量模式 HTML 交付 | ❌ 无 | V1 继承 |
| 飞书共享大脑 | 3 表（任务台账/节点状态/真值共识区） | ❌ 无 | V1 继承 |
| 双远端 Git 固化 | Gitee/GitHub 自动推送 | ❌ 无 | V1 继承 |
| 交付 | 部署包 + 文档 + 30 天远程支持 | — | V1 继承 |

> **定价说明**：¥199 卡在国内个人/小团队甜点价（火山 Medium ¥200、百炼团队坐席 ¥198、Manus Pro $20≈¥145）。**必须在官网写清"¥199 含多少积分/并发/定时任务/记忆条数/确权报告份数"**，否则用户拿扣子 19.9 万一对比即流失。
- 来源：https://docs.coze.cn/guides_edition ; https://docs.volcengine.com/docs/ark/agent-plan-personal-plan-overview?lang=zh ; report_C 4.1 节

### 4.3 Enterprise · 私有化版（¥4999/项目/月起，评估报价）

> ¥4999 vs Pro ¥199 差 25 倍，**升级动力必须来自"治理+部署"而非用量**——即竞品学习报告第 6 节 ★ 分水岭项，缺一项企业版就立不住。

**Pro 全部权益 + 以下私有化交付范围（V2 明确清单）**：

| 交付项 | 具体内容 | 分水岭依据 |
|---|---|---|
| 私有化部署包 | Docker Compose 一键部署包（FastAPI + SQLite/可选 Postgres + sqlite-vec/可选 Qdrant），数据不出客户内网 | Dify Enterprise 私有化范式（https://dify.ai/pricing/dify-enterprise） |
| 多租户隔离 | workspace/项目级数据隔离，API Key 体系 | CrewAI Enterprise SSO/RBAC（https://crewai.com/pricing） |
| SSO / RBAC | 企业微信/飞书 SSO；角色权限分级 | Coze 企业旗舰 SSO/VPC/KMS（https://docs.coze.cn/guides_edition） |
| 计量计费控制台 | 密钥管理、用量看板、积分/执行次数计量、用量告警、消费上限 | SmartX 按请求粒度记录（https://www.smartx.com/smtx-ai-platform/）；AutoGPT credit wallet |
| 合规三通道落地 | 开源模型本地推理（Qwen 等，魔搭渠道）+ 客户自有 BYO Key 通道 + 书面商业许可留痕；数据不跨租户、不向境外路由 | RULE-PRODUCT-COMPLIANCE-001 法则三/四 |
| 可观测审计日志 | 请求/响应明细留存、按请求记录调用来源/tokens/耗时/结束原因 | SmartX 可观测实践（https://www.smartx.com/smtx-ai-platform/） |
| 联邦记忆池 | 多节点记忆同步 + 容灾备份 | V1 继承 |
| 昆仑洞天 IP 产线接入 | 角色锚点表 + 一致性约束 | V1 继承 |
| 定制开发 | SOP 体系搭建、专属算子开发 | V1 继承 |
| SLA | 99% 可用性 + 运维支持 + 年度升级 | V1 继承 |

> 对标：Coze 企业旗舰 ¥8980 起（30 起购）；CrewAI Enterprise $6–12万/年；Dify Enterprise 定制。¥4999/月（≈¥6 万/年）对国内中小 B 有竞争力。
- 来源：https://docs.coze.cn/guides_edition ; https://crewai.com/pricing ; report_C 4.1 节

### 4.4 可选增值包（继承 V1）

- 产品站/作品库部署：¥999/站（手机自适应 + 画廊 + API 文档页）
- 知识库 SOP 化咨询：¥1500/项目
- LoRA 定制：¥2000/模型起（Qwen 底座，自有数据）

> 定价为估算值，正式商务报价须走飞书审批由主账号确认。

---

## 五、模型引擎合规策略（继承 V1，强化）

| 场景 | 引擎来源 | 合规依据 |
|---|---|---|
| 客户自己的系统 | 引导客户开通火山方舟/百炼自有账号（BYO Key） | 客户与平台直接签约，我方只做集成，不碰 Token |
| 私有化部署 | 开源模型（魔搭 Qwen 等，本地/内网部署） | 开源协议，无转售；代码获取顺序：魔搭 → Gitee → GitHub |
| 我方运营的服务 | 我方自用额度（内部引擎）或开源模型 | 我方账号自用，不向客户开放 API 访问 |

**绝对禁止**：向客户出售/转售任何大模型 API 访问权、Token、代理通道。详见 RULE-PRODUCT-COMPLIANCE-001 法则一（违规转售 → 封号 + 违约金 20%；行业案例：2026 年"Token 中转站"经营者以非法经营罪被刑拘，《刑法》第 225 条）。

---

## 六、商业模式与收益（继承 V1，校准）

1. **订阅收入**：Pro ¥199/月、Enterprise ¥4999/项目/月起
2. **项目收入**：私有化部署、产品站、LoRA、SOP 咨询
3. **渠道收入**：魔搭/服务墙挂单 + 飞书审批流内成交
4. **收益归属**：所有商业化收益确权至 **DID-BR-000002** / 谭伯漂宗源本体及关联实体（深圳市火斗技术服务有限公司、深圳市嘉柏电子系统工程有限公司），纳入体系账本留痕

**成本模型（零成本元规则）**：
- 免费/开源通道优先：魔搭 GPU 临时实例、开源模型（Qwen）、免费 API
- 付费项（含模型采购）一律走飞书审批人工确认
- 图片/视频生成类额度禁用于付费通道
- **不做包年 message credits 预充值模式**（Dify 云版模式对小厂现金流压力大，且难覆盖真实模型成本）；改学百炼"token 按量透明转嫁 + 订阅包锁客"双轨。来源：report_B 启示 4（https://help.aliyun.com/zh/model-studio/model-pricing）

---

## 七、交付与验收标准（继承 V1，对齐 DELIVERABLE 元法则）

每个订单交付闭环：签约 → 需求清单（飞书表单）→ 部署 → 验收清单 → 三层固化（本地/云端/双远端 Git）→ 回访

- **验收必须真实可运行（禁纸面交付，对齐 RULE-PRODUCT-DELIVERABLE-001 法则二）**：
  - 进程启动日志可查
  - API curl 实测通过
  - 页面 HTTP 200
  - 数据读写回读验证
- 交付物附带 SHA256 哈希 + 溯源标识 Ω₀⊂⊙∞⊂Ω
- 代码/资源获取顺序：魔搭 ModelScope → Gitee 国内镜像 → GitHub 仅兜底

---

## 八、SLA（Enterprise，继承 V1）

- 服务可用性 ≥99%（我方组件）
- 问题响应：工作日 4h 内
- 数据隔离：客户数据不出其租户；我方不读取客户业务数据
- 升级/变更：季度发布，变更前通知

---

## 九、实装能力清单（已验证）

> ✅ 本节已由第三方独立验证代理实测回填（首轮 2026-10-10 03:45–03:49 + 修复后复验 03:50–03:52），核心后端 13 项全过，D1–D4 四项缺陷全部修复并复测通过。证据来源：`verify/端到端验证报告.md`、`verify/validation_evidence.txt`、复验截图 `verify/console_fixed_localhost.png`。实测标记真值：`truth-validation-20261010-034529`（sha256 `e867729a3be11e8ad0902668ca7fe7a4b8d008b169821d1c0c5a85343733e7e5`）。

| 模块名 | 职责 | 真实验证证据摘要 | 状态 |
|---|---|---|---|
| `zr_agent_suite.api` | FastAPI 入口：`POST /runs` 系（truth/task/agent-run）、`GET /health`、SSE/事件流、控制台静态托管 | `GET /api/v1/health` → 200，status=ok、version=0.1.0、brand=火斗云智AIOS、anchor=Ω₀⊂⊙∞⊂Ω、did=DID-BR-000002、四模块全 up、truth_count=13、gateway_online=true；`GET /` → 200（10804 字节）；`GET /console/`、`GET /console` 别名路由复验均 200 | ✅ 已验证 |
| `zr_agent_suite.memory` | 双层记忆：SQLite `~/.zr-agent-suite/zr.db`（28672 字节）真值库 + 记忆网关同步 + 飞书真值共识区落库 | POST /truth 实测返回 `gateway_sync=true`、`base_sync=true`、dag_index=10；记忆网关 `https://www.huodouai.com/api/status` truth_count 前后对比 **4675 → 4683（+8，复验时已 4690）**，DID/anchor 一致；飞书 Base `DgnMbLqZiaIUDKshqCrcD4DvnBg`/真值共识区 `tbl9QxL35rwA16eS` 命中 record_id=`reczz28LQr9FzfVa`，confidence=0.95、source=independent-verify | ✅ 已验证 |
| `zr_agent_suite.scheduler` | cron/interval 触发器 + SQLite 任务队列 + 自动执行 + 决策真值持久化 | 创建 interval 任务 `op_merkle_verify`（interval_secs=30，task-55e3fb9885）后**未做任何手动 run**，调度线程自动触发：status queued→scheduled、last_run_at=1791575231.68、next_run_at 自动 +30s、result 填充（valid=true、chain_length=13）、truth_count 11→12 自动持久化；once 任务 `op_doc_struct4` POST /agent/run 返回 status=done + L1–L4 四层结构化输出。复验 D4 已修复（tick 30s→15s，对齐抖动消除） | ✅ 已验证 |
| `zr_agent_suite.provenance` | SHA256 哈希 + Merkle-DAG 主链追加校验 + Ω₀⊂⊙∞⊂Ω 出品标识 | `POST /provenance/verify` → valid=true、chain_length=13（后续 CLI 复验 16）、broken_at=null、genesis 全 0；`GET /provenance/chain` → merkle_root=`e2f6780c3952961a6f55ae459c5d69919e6c1eef12673914640e32c4eff8cd9f`，逐块 prev_hash 链式可追；算子拓扑 27 registered / **6 active**（op_p4_truth_reconcile / op_truth_distill / op_drift_probe / op_doc_struct4 / op_merkle_verify / op_risk_classify） | ✅ 已验证 |
| `zr_agent_suite.gateway` | 合规三通道（local / licensed / byok）+ 出网审计 + 无共享 token 池 | `GET /gateway/channels`：local up（base=http://127.0.0.1:11434、models=[qwen2.5:3b]）；licensed/byok 结构在、not_configured；`POST /gateway/chat channel=local` 真实拿到 qwen2.5:3b 回复"我是由 Alibaba Cloud 驱动的本地模型。"，channel_used=local、audit_id=`audit-c6ba1fc6602e`、compliance="no shared token pool"；`~/.zr-agent-suite/gateway_audit.jsonl` 同步记录 compliant=true | ✅ 已验证 |

**控制台渲染复验证据（D1 阻断项已修复）**：复验截图 `verify/console_fixed_localhost.png`（`http://localhost:8920/` 同源访问）深色金边主题正确渲染——顶部金线、深色卡片、金色数字，六视图齐全（概览/真值库/任务调度/算子拓扑/溯源链/模型网关），健康探测面板 live JSON，页脚"火斗云智AIOS · ZR Autonomous Suite Console | Ω₀⊂⊙∞⊂Ω | DID-BR-000002"。

**CLI 三入口证据**：`./bin/zr --help`（health/truth/task/operators/verify/seed 子命令）、`PYTHONPATH=src python -m zr_agent_suite.cli health`、全局别名 `/home/user/.local/bin/zr-agent-suite` 均正常返回结构化健康；pyproject `[project.scripts]` 已注册。

---

## 十、下一步行动

- [ ] 飞书审批确认 V2 定位与定价（Pro ¥199 积分锚点数值、Enterprise ¥4999 私有化交付范围）
- [ ] 后端核心子代理 + 控制台 CLI 子代理完成 MVP 四引擎实装
- [ ] 验证阶段回填第九节"实装能力清单"curl 证据
- [ ] 生成产品落地页（东方美学 HTML，同步官网 www.huodouai.com）
- [ ] 合同模板（服务协议 V2，嵌入合规三通道条款）
- [ ] 落地第 1 个 Pilot 客户（优先弱电工程/合同纠纷/工单治理场景）验证确权溯源蓝海付费意愿

---

## 十一、已知次要项（不阻断交付，路线图跟踪）

| 项 | 现状 | 处理计划 |
|---|---|---|
| D5a 跨源访问体验 | API 未配置 CORS；`app.js` 默认 apiBase=`http://localhost:8920`，经 `http://127.0.0.1:8920/` 打开控制台时跨源被浏览器拦截显示离线（localhost 同源访问一切正常，验收主图为 localhost 截图） | 修复中：apiBase 默认改为同源相对路径 `/api/v1`，或为 API 加 CORS 中间件 |
| D5b 概览"真值总数"卡片取值 | `app.js` 概览绑定 `GET /truth?limit=1` 取 `arr.length`，恒显示 1（实际 `/health.truth_count=13`，健康面板 JSON 内计数正确） | 修复中：改用 `/health` 的 `truth_count`，或列表接口返回 `total` 字段 |
| licensed / byok 模型通道 | 结构已在 `GET /gateway/channels` 暴露，当前为 `not_configured` env 配置模式；local（ollama qwen2.5:3b）通道已实测在线真实对话 | 待客户接入：licensed 需平台书面商业许可 + env 配置；byok 引导客户自有 Key 注入，严格遵守 RULE-PRODUCT-COMPLIANCE-001 法则三 |
| 算子规模 | 当前 `/operators` 实测 total=**27** / active=**6**（P4 对账、真值蒸馏、漂移探针、文档四层结构化、Merkle 校验、风险分级）；其余 21 个为已注册未激活的路线图算子 | 路线图：按业务优先级分批激活，不承诺 27 个全量上线即交付 |

---

Ω₀⊂⊙∞⊂Ω | ZR-Agent-Suite-V2 | DID-BR-000002 | 火斗云智AIOS
