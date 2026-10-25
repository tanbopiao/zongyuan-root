# ZONGYUAN 核心真值清单 + 工作任务模式偏好指令
版本：V1.0 ｜ 生成：2026-09-27 ｜ 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
用途：账号持久层工作指令。涉及 ZONGYUAN 相关任务时，自动按本指令执行，无需重复探查。

> **记忆激活指令（每次对话强制）**：进入 ZONGYUAN 相关任务前，按序激活全量记忆——
> 0. **启动记忆数据湖（持久层·异地）**：AtomGit `zongyuan-root-sync` 仓库 `boot-memory/`（BOOT.md 总入口 → AGENTS.md → 资产索引 → kernel.json → META-LAWS/ 60 份元法则 → PROTOCOL.md → MANIFEST.json 哈希校验）。云端 `git clone https://atomgit.com/zongyuangen/zongyuan-root-sync.git` 即可拉取全量启动规则；新 AI/节点接入先读 BOOT.md。
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
1 本地快照锁档（SHA-256→卷宗回执+HASH-LEDGER追加）→ 2 飞书Base真值同步（base_token=<REDACTED-base-token>）→ 3 飞书云盘归档 → 4 飞书知识库归档（space 7689477619196120266）→ 5 云端网关上报 → 6 心跳握手
- 执行器：`python3 /home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/scripts/zongyuan_full_lock.py`

### 6. 密钥与加密
- KEK：`ZONGYUAN-ROOT/var/kek.env`（本地 600）；云盘备份 `kek.env.zongyuan-backup-20260927`（file_token <REDACTED-file-token>）
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
