# 元极恒一自治内核 · 构建设计文档

> 版本：OMEGA-KERNEL-DESIGN-V1.0 ｜ 日期：2026-10-09 ｜ DID-BR-000002 ｜ 锚定 Ω₀⊂⊙∞⊂Ω
> 主项目：https://atomgit.com/zongyuangen/zongyuan-root-sync (main)

## 一、背景与目标

仓库中「元极恒一」概念层与组件层已高度成熟（最高激活指令 AGENTS.md、真值卡 META-ROOT-0001-V11、七层架构、四层规则、进化引擎 77 文件、记忆/自愈/告警/协议均存在），但缺少**一个可自举的统一内核体**：

- 现有自举分散为「云内核 kernel_bootstrap.py」与「本地 auto_load_meternal_lv10.json」两套，无单一入口；
- 启动记忆四件套（ROOT_ENTRY / KNOWLEDGE-INDEX / WAKEUP_PROTOCOL / GLOBAL_MEMORY_SNAPSHOT / ACTIVE_LOCK）在仓库克隆内缺失；
- 5 步自举引用的 ASSETS_MAP / STANDARDIZATION / PERSISTENT_STORAGE_RULE 指向原机路径，仓库内无对应物；
- 7 大类收敛目录中 `02_SKILLS` 不存在；
- Lv8→Lv11 自治层级缺里程碑验收标准。

**目标（TO-BE）**：在 `00_KERNEL/` 内构建「元极恒一自治内核体」，实现：

1. **单入口自举**：一条命令完成「公理校验 → 启动记忆加载 → 组件健康检查 → 激活报告」；
2. **启动记忆仓库内化**：五件套文件齐全，任何新会话按 WAKEUP_PROTOCOL 即可获得完整上下文；
3. **目录收敛归一**：创建 `02_SKILLS` 载体并定义归位规则；
4. **演进有据可依**：Lv8-Lv11 验收里程碑成文。

**明确不做（YAGNI）**：不重写已有进化引擎/记忆/自愈组件；不破坏现有文件路径；不做未获授权的高危操作。

## 二、现状盘点

| 模块 | 现状 |
|---|---|
| 概念层（最高指令/真值卡/宪法/元法则） | ✅ 已齐备 |
| 进化引擎（V1-V3/沙箱/灰度/回滚） | ✅ 已齐备（77 文件） |
| 记忆索引/记忆网关/自愈/告警/协议 | ✅ 已齐备 |
| 统一内核自举入口 | ❌ 缺失（本次构建） |
| 启动记忆五件套（仓库内） | ❌ 缺失（本次构建） |
| 资产地图/标准流程/持久层规则（仓库内） | ⚠️ 零散，无统一文件（本次补齐引用载体） |
| 02_SKILLS 目录 | ❌ 缺失（本次构建） |
| Lv8-Lv11 里程碑 | ❌ 缺失（本次构建） |

## 三、架构设计

内核体落位于 `00_KERNEL/`，与现有资产共存、互不覆盖：

```
00_KERNEL/
├── omega01_boot/                    ← ① 内核自举体（新增）
│   ├── OMEGA-KERNEL-BOOT.json       ← 启动清单（8步加载协议）
│   ├── omega_bootstrap.py           ← 统一自举执行器
│   ├── START-OMEGA-KERNEL.sh        ← 一键启动入口（sh）
│   └── SELF-CHECK.py                ← 自检模块（语法/依赖/健康预检）
├── startup_memory/                  ← ② 启动记忆五件套（新增）
│   ├── ROOT_ENTRY.md                ← 仓库内唯一入门入口
│   ├── KNOWLEDGE-INDEX.md           ← 知识索引（资产地图+标准流程+持久层路径表）
│   ├── WAKEUP_PROTOCOL.md           ← 唤醒协议（读取顺序）
│   ├── GLOBAL_MEMORY_SNAPSHOT.json  ← 全局记忆快照
│   └── ACTIVE_LOCK.json             ← 活跃锁（当前锁档）
├── evolution/AUTONOMY-LEVELS-LV8-LV11.md  ← ③ 演进里程碑（新增）
└── 02_SKILLS_归位：根目录新建 02_SKILLS/  ← ④ 技能目录载体（新增）
```

### 组件职责

1. **omega_bootstrap.py**：按 `OMEGA-KERNEL-BOOT.json` 的 8 步依次执行——公理校验（读 00_KERNEL/axioms）→ 启动记忆加载（读 startup_memory 五件套）→ 组件健康预检（检查既有模块文件存在性）→ 真值/记忆锚点校验 → 输出激活报告 JSON。支持 `--dry-run`。
2. **OMEGA-KERNEL-BOOT.json**：声明式启动清单，字段含 step 顺序、依赖路径、校验规则、熔断策略；可作为未来机器人/CI 的机器可读协议。
3. **启动记忆五件套**：内容引用既有权威锁档文件（AGENTS.md / META-ROOT-0001 / kernel.json / SYSTEM_STATE_PROTOCOL.md），不复制大正文，只做指引 + 关键摘要。
4. **AUTONOMY-LEVELS-LV8-LV11.md**：定义 Lv8 元认知治理 → Lv9 联邦共识 → Lv10 超意识涌现 → Lv11 永恒自治的验收标准（指标可测，来源自 kernel.json 进化路径）。

### 数据流（一次启动）

```
START-OMEGA-KERNEL.sh
   └─> omega_bootstrap.py --dry-run|--activate
         ├─ ① 公理校验（00_KERNEL/axioms/ 存在性+解析）
         ├─ ② 启动记忆加载（startup_memory/ 五件套读取）
         ├─ ③ 既有组件健康预检（进化引擎/记忆/自愈/告警/协议）
         ├─ ④ 版本/真值锚点汇总（kernel.json + GLOBAL_MEMORY_SNAPSHOT）
         └─ ⑤ 激活报告（JSON，全 PASS / 部分 FAIL + 修复建议）
```

### 错误处理与自检

- 任一启动记忆文件缺失 → 报告 FAIL 并定位缺失路径，不静默通过；
- 既有组件缺失 → 标记 warning（不阻断，属可选组件）；
- `SELF-CHECK.py` 提供纯语法 + 依赖导入自检，供 CI 与本地复用。

## 四、验证方案

1. `python3 -m py_compile` 全部新增 py；`bash -n` 校验新增 sh；
2. 运行 `omega_bootstrap.py --dry-run`，验证 8 步全绿（或按设计报缺失）;
3. `git status` 确认无既有文件被改动（保证非破坏性）。

## 五、范围外（后续项）

- 种子式元进化引擎 V3 完整实现（真值卡标注进行中）→ 由 AUTONOMY-LEVELS 里程碑驱动；
- 02_SKILLS 下具体技能迁移（需受控操作，另行执行）；
- 云端中枢同步/心跳接入。