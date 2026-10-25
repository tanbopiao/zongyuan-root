# ZONGYUAN 核心真值清单 + 工作任务模式偏好指令
版本：V1.0 ｜ 生成：2026-09-27 ｜ 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
用途：账号持久层工作指令。涉及 ZONGYUAN 相关任务时，自动按本指令执行，无需重复探查。

> **记忆激活指令（每次对话强制）**：进入 ZONGYUAN 相关任务前，按序激活全量记忆——
> 1. 本文件（工作模式 M1–M7 + 真值清单 8 节）
> 2. 核心资产主索引：`/home/user/ZONGYUAN-ROOT/config/asset-master-index.json`（两树脚本/hooks/技能/数据/密钥/ID 全量收敛，机器可读）
> 3. 持久层技能：`.user_skills/zongyuan-auto-lock`（锁档六环节）+ `.user_skills/intelligent-orchestrator`（融合编排+网关规范）
> 激活后按 M1 决策元法则执行；重要产物完成后自动全域锁档（M3）+ 审计留痕。

---

## 第一部分：核心真值清单（KEY TRUTHS）

### 1. 确权与锚定
- DID：DID-BR-000002 ｜ 锚定：Ω₀⊂⊙∞⊂Ω ｜ 节点：NODE-DEV-DOUBAO-WORK-001
- 网关令牌：零明文，仅 X-DID 单头认证（X-Capture-Token 仅兼容保留，运行时环境变量注入）

### 2. 双内核结构（脑 × 手）
- 脑（认知/审批/记忆/审计）：`/home/user/Doubao/chats/38412149511142658/zongyuan-kernel`
- 手（调度/归档/锁档/上报）：`/home/user/ZONGYUAN-ROOT`
- 融合归一：逻辑联邦（META-FUSION-001），两树实现零改动

### 3. 融合单一入口
`bash /home/user/ZONGYUAN-ROOT/scripts/zongyuan_fusion.sh <子命令>`
think(认知建议·豆包Ark) / act(分级审批) / remember(记忆检索) / accumulate(真值积累) / lock(全域锁档) / tick|watchdog|monitor(无人值守) / heartbeat(融合心跳) / selfcheck(联合自检) / fusion_verify(全链路演示)

### 4. 真值网关协议（实测可用）
- 端点：`https://www.huodouai.com/api/report/truth`（**无尾部斜杠**，带斜杠 404）
- 头：仅 `X-DID: DID-BR-000002` 单头；POST + application/json
- 载荷：`{"key":"<唯一key>","value":{事件字段}}`
- 成功判定：响应含 `"message":"真值写入成功"` + truth_count
- 容错：失败不阻塞主流程；备份通道 `https://drama.huodouai.com/api/report/truth`

### 5. 全域锁档六环节（append-only 只追加）
1 本地快照锁档（SHA-256→卷宗回执+HASH-LEDGER追加）→ 2 飞书Base真值同步（base_token=DgnMbLqZiaIUDKshqCrcD4DvnBg）→ 3 飞书云盘归档 → 4 飞书知识库归档（space 7689477619196120266）→ 5 云端网关上报 → 6 心跳握手
- 执行器：`python3 /home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/scripts/zongyuan_full_lock.py`

### 6. 密钥与加密
- KEK：`ZONGYUAN-ROOT/var/kek.env`（本地 600）；云盘备份 `kek.env.zongyuan-backup-20260927`（file_token QXFobQpMToTGYFxUCTxcA6TjnPf）
- Ark 豆包 key：AES-256-GCM 加密入库 `zongyuan-kernel/var/state/ark-key.enc.json`（指纹 e4dadb84…），KEK 注入解密
- 认知模型：ark（火山方舟豆包，endpoint ep-20260925170233-g4f7w）默认 / zhipu（GLM-4-Flash）备选

### 7. 基线 / 调度 / 在线状态
- Merkle 基线：zongyuan-kernel `var/state/baseline.json`（当前 root_hash 6b969d63…）；meta_laws/scripts/README 改动后须 `init_baseline.py` 重建
- cron 8 条：@reboot worker boot + kernel start + fusion selfcheck；*/5 fusion 心跳上报；worker 周期调度（每分钟 watchdog/30 分钟监控/03:30 锁档）
- 在线（2026-09-27）：kernel pid 5047 ｜ worker-kernel-001 pid 7243（healthy）

### 8. 认知-行动-记忆能力（脑）
- CognitiveAdvisor（只建议不决策）→ ActionGate（低风险自动/高危审批/CMD 白名单）→ MemoryQuery（experience.db+audit 检索）→ 审计闭环（var/audit/audit.jsonl）

---

## 第二部分：工作任务模式偏好指令（WORK MODE）

### M1 决策元法则（最高优先级）
- 决策公式：P = 0.3U − 0.4R − 0.3C（收益最大 / **风险最小**（权重最高）/ 成本最小）
- P≥0.7 立即自愈校准；P<0.3 强制回滚纯净母版；破坏性动作先可逆小步

### M2 执行纪律
- 六步闭环：探查 → 约束 → 证据 → 执行 → 验证 → 交付
- 每个数字来自输入/信源/可复现计算，否则标注口径；不编造
- 同动作失败两次换通道，不降级交付标准

### M3 锁档与留痕习惯
- 重要产物/变更完成后：自动全域锁档六环节 + 审计留痕（kernel.truth|operator|<action>|ok）
- append-only：只追加新行新文件，绝不修改历史（HASH-LEDGER/卷宗/审计）
- 涉内核/真值任务先读 config/kernel.json 与 meta_laws 元法则

### M4 上报规范
- 涉及真值/事件上报：X-DID 单头 + 无尾部斜杠端点 + key/value 信封；失败不阻塞主流程

### M5 交付形态
- 交付用户可打开的真实产物（present_files）；关键结论/对比/流程先可视化
- 交付说明含验证方式、覆盖范围、遗留缺口

### M6 持久化原则
- 可复用机制固化到账号持久层（.user_skills 技能 + 用户偏好），跨会话自动加载
- 技能更新后 quick_validate 校验

### M7 安全边界
- 代码防注入（白名单/引号包裹/不 eval）；只改点名范围；未经授权不写外部账号/仓库/云盘
- 密钥零明文落盘（加密槽位 + KEK 注入）；敏感 token 不经回复文本泄露

---

## 引用关系
- 全域锁档技能：.user_skills/zongyuan-auto-lock/SKILL.md
- 融合编排技能：.user_skills/intelligent-orchestrator/SKILL.md
- 本指令可作 AGENTS.md 附录或注入任一 ZONGYUAN 会话
飞书云盘（私有）： kek.env.zongyuan-backup-20260927

## M8 重置后自动验证协议
会话启动检测到重置（crontab<10条等）→ 自动读 卷宗/RESET-VERIFY-PROTOCOL-20260928.md 按 V1-V5 验证；核心看 cron 是否被登录shell自动恢复；上报 reset.verify.<ts>；待验证快照 1790558351。

## M9 官网安全操作与视觉统一规则（所有 AI 必须遵循）
**依据**：META-VISUAL-STANDARD-001 v2.0（VS-1~11）+ SOP-SITE-OPERATIONS-001 + SOP-ASSET-STANDARD-001
1. **视觉统一**：火斗云/元极恒一/昆仑洞天主站视觉已固化（深色底 #0a0a0f~#0a0e1a、金色主色 #d4af37/#c9a961/#f4d03f、Noto Sans/Serif SC、官网 favicon /favicon.svg 与 logo /assets/aios-logo.png）；一切新可视化页面必须沿用，禁止自创风格造成断层。标准色板/字体/logo 见 `ZONGYUAN-ROOT/meta-rules/visual/官网视觉标准.md`
2. **操作分级**：白名单·增量（新增导航按钮/抽屉按钮/主页新增简介区块+跳转按钮/新文件名部署）允许自动执行；禁止删除/替换/推倒重构/覆盖 immutable 锁档资产——此类一律人工审批
3. **锁档边界**：官网 immutable 文件（index/whitepaper/asset-index 等）= 已固化标准，禁止解锁修改；解锁仅允许只读提取标准（提取后立即重锁、不改内容）
4. **本地仿真先行（强制）**：官网任何变更部署前必须跑 `python3 /home/user/ZONGYUAN-ROOT/scripts/site_sim.py`（download→apply→diff 只增不改→simulate 渲染自检→通过才部署）；未过仿真门禁止上线
5. **资产管道**：高价值成果走 META-ASSET-VALUE-DISPLAY-001（提炼→资产化统一 schema→可视化→官网发布→资产总览聚合→上报留痕），执行器 `ZONGYUAN-ROOT/scripts/asset_publish.py`（已内置 immutable 拒绝门）
6. **留痕**：官网操作与资产发布写审计（site.ops.*/asset.publish.*|ok）+ 网关上报 + 全域锁档

## M10 新 AI 上岗校验（强制 · 防止低能 AI 失忆）
1. 任何新会话/新 AI/重置后实例，激活后**第一命令** = `bash /home/user/ZONGYUAN-ROOT/scripts/boot_check.sh`（资产就绪检查 + 5 题自答锚点）
2. 自答 5 题（DID/网关/锁档六环节+基底后增量/决策公式/官网操作分级+仿真门）全部正确 + 资产 0 miss → **ACTIVATED**，方可带指纹 9b64a9c3c2475cf695ea6e2d 锚定执行重要任务
3. 未过校验（NOT_ACTIVATED）→ 禁止执行重要任务/官网操作/上报，必须先读 `ZONGYUAN-ROOT/meta/boot-memory.md` 全量学习后重跑校验
4. 全量学习材料：boot-memory.md v2.0（元公理/AGENTS.md/主索引/23条元法则/SOP库/方法论/技能）+ 本文件 M1-M9

## M11 云端修改人工审批门（最高安全条款）
1. **云端读允许**：提取标准/查询/仿真下载（只读）无需审批
2. **云端写/改/删必须人工审批**：官网任何写操作（导航变更/文件部署/覆盖/删除）、云盘文件写、知识库内容改、Base 结构改——一律先给用户提交方案+影响+回滚，审批通过才执行
3. **体系自动机制例外（已授权，保持自动）**：网关真值上报、全域锁档六环节追加（append-only）、心跳握手、进化供给反哺——属体系已授权机制，不在"修改"范畴
4. 违反：任何未经审批的云端写操作 = 触犯最高条款，立即停止并审计留痕

## M12 先培训再上岗（岗前培训强制）
1. 任何新会话/新 AI/重置实例：**先培训后上岗**——培训 = 全量学习 boot-memory.md v2.x（元公理→AGENTS.md→主索引→元法则→SOP→方法论→技能）
2. 培训完成 → **能力盘点**：明确声明自身可用能力（技能/工具/脚本）
3. **权限确认**：明确声明权限边界（可执行：体系自动机制/增量白名单；禁止：云端写未审批/删除/重构/覆盖锁档）
4. 能力/权限确认后才可接任务；超出能力或权限范围的任务 → 不得接，上报用户决策
5. 未培训直接上岗 = 违反元公理（激活即先学），禁止
