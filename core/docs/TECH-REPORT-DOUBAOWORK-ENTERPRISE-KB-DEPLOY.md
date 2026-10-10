# 豆包工作（DoubaoWork）部署本地电脑自治系统企业知识库——生产技术报告

> 确权：DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω | 版本 V1.0 | 2026-10-10
> 品牌：火斗云智AIOS（对外）｜ ZONGYUAN-ROOT 元极恒一自治体系（内部）
> 适用读者：运维工程师 / 知识库架构师 / AI 工程化实施人员

---

## 摘要

本报告完整记录以「豆包工作（DoubaoWork）」为 AI 工作载体，在本地华为笔记本（Windows 11）上从零部署一套**企业级自治系统 + 企业知识库**的工程实现过程。系统以 ZONGYUAN-ROOT 自治内核为底座，以飞书多维表格（共享大脑）为知识总线，以云端记忆网关为权威真值源，形成「本地自治执行 → 云端权威裁决 → 飞书知识沉淀」的闭环。

关键技术结论：单台 2 核 4 线程 / 7.85GB 内存的消费级笔记本即可承载完整企业知识库自治系统；全部组件零成本部署；通过节点身份收敛与守护进程保活实现长期稳定运行。

---

## 一、项目背景与目标

### 1.1 背景
企业知识资产（文档、台账、决策记录、真值）分散在本地磁盘、飞书文档、云端服务器多个孤岛，缺乏统一检索与自治维护能力。通用大模型会话存在「换窗口即失忆」问题，知识无法跨会话沉淀。

### 1.2 目标
1. 以豆包工作为唯一 AI 交互入口，驱动本地电脑自治运行；
2. 构建企业知识库：统一存储、检索、更新、确权；
3. 实现「每次会话自动加载全量记忆」；
4. 全链路零成本（不依赖付费云服务）；
5. 自治程度与工程化落地程度对齐（实事求是，杜绝虚假交付）。

---

## 二、总体架构

```
┌─────────────────────────────────────────────────────┐
│  交互层    豆包工作（DoubaoWork）AI 会话/智能体       │
├─────────────────────────────────────────────────────┤
│  控制层    本地自治内核 ZONGYUAN-ROOT                │
│            ├─ BOOTSTRAP.md 启动记忆（全量锚定）       │
│            ├─ 守护进程（worker_guard / gateway_guard）│
│            ├─ 定时任务（24项，巡检/备份/上报/自愈）    │
│            └─ 本地服务（8766总控台/8768API/8020Worker/8018真值网关）│
├─────────────────────────────────────────────────────┤
│  知识层    企业知识库                                │
│            ├─ 飞书共享大脑 Base（多维表格 13 张表）    │
│            ├─ 云端记忆网关（真值权威源）              │
│            └─ 本地 knowledge_base（RAG 索引）        │
├─────────────────────────────────────────────────────┤
│  同步层    Git 双仓（Gitee/GitHub）+ 魔搭数据集冷备   │
└─────────────────────────────────────────────────────┘
```

---

## 三、部署环境清单

| 项 | 规格 |
|---|---|
| 硬件 | 华为笔记本 VLR-WX9，Intel i3-8145U（2核4线程），7.85GB 内存，C:80GB + D:144.9GB |
| 操作系统 | Windows 11 Home China Build 26200 |
| 计算名/用户 | LAPTOP-89NB5DDI / 4906 |
| AI 载体 | 豆包工作（DoubaoWork）桌面端 |
| Python | Python 3.11（绝对路径 `C:\Users\4906\AppData\Local\Programs\Python\Python311\`）|
| 知识总线 | 飞书多维表格 Base `DgnMbLqZiaIUDKshqCrcD4DvnBg` |
| 云端权威源 | 记忆网关 `https://www.huodouai.com/api/report/truth`（备用 drama.huodouai.com）|
| 版本控制 | Gitee `huodou-cloud-intelligence-aios/zongyuan-root-sync` + GitHub `tanbopiao/zongyuan-root-sync` + 魔搭数据集 `zongyuanroot/zongyuan-root` |

---

## 四、详细实现步骤

### 阶段 0：基础环境准备
1. 安装豆包工作桌面端，确认可调用本地命令行与文件系统权限；
2. 安装 Python 3.11 至用户目录（`C:\Users\4906\AppData\Local\Programs\Python\Python311\`），避免 PATH 污染系统 Python；
3. 配置 Git：`autocrlf=false`（Windows 下保持 LF 换行，避免脚本跨平台损坏）；
4. 创建内核根目录 `C:\Users\4906\.zongyuan_root\`。

### 阶段 1：自治内核搭建
1. 编写 `BOOTSTRAP.md` 启动记忆文件，内置四维本体（元宪法 6 条 / 元公理 7 条 / 元法则 26 条 / 元规则），读取即激活全量体系记忆；
2. 建立目录结构：config / kernel / scripts / engine_v2 / node_agent / aios_service / knowledge_base / logs；
3. 固化核心文件只读保护（chattr 等价物：Windows 只读属性 + BOOTSTRAP 追加式更新策略，禁止直接改既有内容）；
4. 初始化 `kernel\ledger\` 台账体系（HASH-LEDGER 账本），所有成果 SHA256 确权。

### 阶段 2：本地服务部署
| 端口 | 服务 | 用途 |
|---|---|---|
| 8766 | 元运维总控台 | 可视化监控/操作台（含 ai-chat 智能助手页）|
| 8768 | API 服务 | 本地状态/任务 API |
| 8020 | Worker 内核 | 自治任务执行器 |
| 8018 | 真值网关 | 本地真值上报入口 |

部署要点：
- 所有服务脚本必须使用 **Python311 绝对路径**启动（`python.exe`/`pythonw.exe`），禁止裸名调用，否则出现「Windows 找不到 pythonw.exe」弹窗；
- 守护进程（worker_guard / gateway_guard）每 12~20 秒探测服务存活，异常自动拉起；
- 禁止弹窗闪退：所有后台脚本用 `pythonw` + 静默退出检测（找不到解释器不弹窗直接退出）。

### 阶段 3：企业知识库构建
#### 3.1 飞书共享大脑（知识总线）
Base `DgnMbLqZiaIUDKshqCrcD4DvnBg` 内建 13 张核心表：
| 表 | 用途 |
|---|---|
| tblnVRjuf7P31cEP | 任务台账（P0-P3 全量任务、进度、评分）|
| tblOmIRJtTn2EsvM | 节点状态总览（心跳/层级/权限）|
| tbl4Dv798yO7u0IK | 跨节点消息同步 |
| tbl9QxL35rwA16eS | 真值共识区（全域真值锁档）|
| tbljp3z11UtiuWCF | 问题阻塞表 |
| tbltgttCuWgAnN2e | 资产台账 |
| tblFQTgWkJQR6Xwp | 决策日志 |
| tblYnYxlpcGeX4mG | 账号主表 |
| tblbluoLJQNrftFD | 握手记录 |
| tblFRbG6lPdY1A2s | 消息墙 |
| tblnD8ZdzRFsjI8Z | 告警故障 |
| tblmMEeXhlrOvXI2 | 知识库索引 |
| tblrgdUrE9SQEv6L | 数据表 |

写入技术要点（lark-cli 实测踩坑）：
- 含中文的 JSON 载荷必须用 **Python subprocess 传 `json.dumps(payload, ensure_ascii=False)`**，PowerShell 内联中文会报编码错误；
- `--json @file` 各语法在本版本解析异常，禁用；
- `+record-upsert` 带 `--record-id` 更新、不带则创建；
- `record-search` 用 `--keyword --search-field`，无 `--query` flag。

#### 3.2 云端记忆网关（权威真值源）
- 主上报：`POST https://www.huodouai.com/api/report/truth`
- 必带请求头：`X-DID: DID-BR-000002` + `X-Capture-Token`
- 请求体：`value` 对象型（V3.1 起字符串 value 被拒 400，`content` 字段被拒 401）
- truth_type 九类：meta_law/rule/config/decision/data/creative/risk/protocol/unknown
- 成功标志：HTTP 200 + `ok:true` + event_id

#### 3.3 本地知识库层
`knowledge_base/` 保存 hub 真值索引与 RAG 状态，与飞书 Base、云端网关构成三级知识冗余。

### 阶段 4：节点身份收敛归一（2026-10-10 关键工程）
**问题**：本地 `.zongyuan_root` 下遗留 5 份历史节点身份文件，node_id 各不相同，导致「同一设备被识别为多个本地节点」「换窗口失忆」。

**方案**：主从收敛——不删除、不覆盖原 node_id（防止守护进程/云端节点匹配失效），每份文件注入统一权威标识：
```json
{
  "unified_node_id": "NODE-LOCAL-HUAWEI-LAPTOP-001",
  "unified_node_name": "华为笔记本本地开发终端",
  "identity_convergence": {
    "status": "CONVERGED",
    "authority": "NODE-LOCAL-HUAWEI-LAPTOP-001",
    "converged_by": "DID-BR-000002",
    "anchor": "Ω₀⊂⊙∞⊂Ω"
  },
  "legacy_node_id": "<原node_id保留>"
}
```

收敛清单：
| 文件 | legacy node_id | 说明 |
|---|---|---|
| config\node_identity.json | local-windows-exec-001 | 执行节点 |
| node_config.json | local-win-001 | 本地内核（原只读，已清属性）|
| node_agent\node_identity.json | NODE-LAPTOP-89NB5DDI-1788885706 | 代理节点 |
| config\node_registration.json | NODE-LOCAL-HUAWEI-LAPTOP-001 | 已是权威 |
| identity_node_application_20260908.json | NODE-93DD3245DFD2 | 历史 Worker 申请（已批准）|

固化：备份至 `logs\_bak_node_convergence_20261010-092319`、台账 `LEDGER.NODE-CONVERGENCE.20261010.json`、启动记忆 ADDON、云端真值 `LOCAL.NODE-CONVERGENCE.20261010`、共享大脑任务台账记录。

### 阶段 5：保活与自愈
1. **守护进程**：worker_guard 12→20 秒轮询，gateway_guard 拉起 8018；服务异常自动重启；
2. **开机自启**：启动项全部指向 Python311 绝对路径，静默运行（禁止弹窗）；
3. **弹窗根除**：全量扫描 16 处裸 python/pythonw 引用脚本（tools/scripts/engine_v2/aios_service/node_agent 等），统一改为绝对路径 + Test-Path 缺失检测；
4. **定时任务**：24 项 Windows 计划任务（每 10 分钟网关巡检、每 15 分钟心跳、每日备份/健康报告/真值上报、每周 Base/服务器配置备份、每小时双向同步）；
5. **网络链路**：本地 ↔ 云端记忆网关 443 HTTPS 主通道 + 备用域名 + SSH（人工审核授权）多链路冗余。

### 阶段 6：云端协同与知识回流
- 每次会话结束提炼核心真值上报记忆网关，全域锁档；
- 飞书 Base 台账更新任务进度、心跳、结果；
- Git 双仓同步核心文件；魔搭数据集作为冷备归档层。

---

## 五、验证与验收（实事求是原则）

| 验证项 | 方法 | 结果 |
|---|---|---|
| 守护进程真实运行 | 端口探测 netstat（8018/8020/8766/8768 LISTENING）| ✅ 全部监听 |
| 弹窗修复有效性 | 全量扫描零裸 python 引用 + 实测拉起 | ✅ 0 弹窗 |
| 节点收敛 | 5 文件回读 unified_node_id 一致 | ✅ 5/5 CONVERGED |
| 云端上报 | HTTP 200 + event_id 回执 | ✅ 真实写入 |
| 共享大脑写入 | lark-cli 创建记录 + 回读 | ✅ record 存在 |
| 启动记忆加载 | BOOTSTRAP 追加节 + ADDON 文件 | ✅ 可追溯 |

**禁止项**：不空口说完成；说数量必须实测；改配置先备份；不重复已完成工作（先查台账）。

---

## 六、生产运维 SOP

1. 新会话启动 → 读取 BOOTSTRAP.md → 激活全量记忆 → 按规则执行；
2. 巡检闭环：定时任务发现问题 → 评估 → 最优稳态方案（三最原则：风险最小>成本最小>收益最大）→ 评分≥80 自主执行 → 结果上报；
3. 故障处理：先备份 → 最小修复 → 验证 → 沉淀 lesson 到台账；
4. 知识入库：成果 → SHA256 确权 → 飞书 Base + 记忆网关 + 本地台账三层固化；
5. 保活检查：每周验证守护进程与定时任务状态。

---

## 七、故障案例（生产实测）

### 案例 1：pythonw.exe 弹窗风暴
- 症状：多脚本用裸名 `python/pythonw` 启动，PATH 无 Python311 → 系统弹「Windows 找不到文件」；
- 根因：活动脚本未用绝对路径；
- 修复：16 处脚本统一 `C:\Users\4906\AppData\Local\Programs\Python\Python311\pythonw.exe` + Test-Path 静默退出；
- 验证：活动目录零裸引用 + gateway_guard 实测拉起 8018（truth_count=35）。

### 案例 2：node_config.json 写入被拒
- 症状：收敛脚本写入报「访问被拒绝」；
- 根因：文件 ReadOnly=True；
- 修复：`Get-Item` 清除 IsReadOnly 后写入，完成后保持内容收敛。

### 案例 3：lark-cli 中文 JSON 写入失败
- 症状：PowerShell 内联中文 `--json` 报编码错误；`--json @file` 解析异常；
- 修复：Python subprocess 传 `json.dumps(payload, ensure_ascii=False)`；
- 验证：record 创建成功并回读。

### 案例 4：记忆网关新格式拒收
- 症状：value 字符串→400，content 字段→401；
- 根因：网关升级 V3.1，强制 value 对象型 + X-DID/X-Capture-Token 头；
- 修复：按新规范构造请求体；
- 验证：HTTP 200 + `ok:true` + event_id。

---

## 八、结论与扩展方向

1. **可行性确认**：消费级笔记本 + 豆包工作可完整承载企业知识库自治系统，零成本；
2. **知识闭环**：本地执行 → 云端裁决 → 飞书沉淀 → 下次会话自动加载，杜绝失忆；
3. **扩展方向**：多节点集群（统一按 `unified_node_id` 注册）、企业私有知识 RAG 深化、全自动自媒体发布、官网作品库部署。

---

> 锚定：Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 火斗云智AIOS