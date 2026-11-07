# 目录结构与各层职责

```
design-system/
├─ README.md                      # 五条铁律、落地顺序、禁止清单
├─ STRUCTURE.md                   # 本文件：目录职责与规则
├─ CHANGELOG.md                   # 版本变更账（人读）
├─ package.json                   # 构建、lint、审计脚本
├─ tokens/
│  ├─ tokens.json                 # ★ 唯一源头：色彩/间距/字体/圆角/阴影/动效
│  ├─ tokens.schema.json          # 结构约束，CI 校验
│  └─ build/                      # 生成物（css vars / ts 常量 / aigc 映射），禁止手改
├─ foundation/                    # 基础规范（人读文档，每篇对应一组 token）
│  ├─ color.md
│  ├─ typography.md
│  ├─ spacing.md
│  ├─ motion.md
│  └─ accessibility.md            # 对比度、焦点环、最小点击区
├─ components/
│  ├─ _template/                  # 新组件必须复制此结构
│  │  ├─ Component.tsx
│  │  ├─ Component.stories.tsx
│  │  ├─ Component.spec.ts
│  │  ├─ Component.md
│  │  └─ meta.json                # 版本/负责人/状态/依赖 token 清单
│  ├─ primitives/                 # 无业务含义的原子组件
│  │  ├─ button/
│  │  ├─ input/
│  │  ├─ table/
│  │  ├─ tag/
│  │  ├─ modal/
│  │  └─ tooltip/
│  └─ domain/                     # 体系业务组件
│     ├─ task-card/               # 任务卡
│     ├─ operator-status-panel/   # 算子状态面板
│     ├─ lock-receipt-card/       # 锁档回执卡
│     ├─ log-panel/               # 日志/回执流
│     └─ approval-dialog/         # 人工审批二次确认
├─ patterns/                      # 组合范式，比组件高一层
│  ├─ layout/                     # 栅格、页面外壳、侧边导航
│  ├─ flows/                      # 长任务进度流、审批流、锁档确认流、告警熔断
│  └─ templates/                  # 仪表盘、工单列表、审计日志页
├─ content/
│  ├─ terms.json                  # 术语字典（AxiomGate/锁档/收敛/Merkle 等统一写法）
│  ├─ messages.json               # 回执、告警、成功失败话术
│  └─ style-guide.md              # 中英文混排、数字与单位、标点规范
├─ governance/
│  ├─ design-system-rules.md      # 准入、审批、巡检、废弃规则
│  ├─ rfc-template.md             # 新增/变更提案模板
│  └─ review-checklist.md         # 合并前必查项
├─ automation/
│  ├─ lint-no-hardcode.js         # 扫硬编码色值/px
│  ├─ audit-tokens.js             # 扫不存在的 token 引用
│  ├─ sync-aigc-prompts.ts        # token → AIGC 提示词映射
│  └─ ci.yml                      # 三道门禁
├─ aigc/
│  ├─ prompt-tokens.json          # 生成物：视觉提示词词表（黑金/勃艮第红/冷蓝青黑）
│  └─ visual-rules.md             # 东方审美铁律到设计语言的映射
├─ docs/                          # 文档站（组件预览 + 规范页）
├─ examples/                      # 可运行示例页，验证模板可拼装
└─ archive/                       # 废弃版本锁档，只读留痕
```

## 各层规则

| 目录 | 能放什么 | 不能放什么 | 谁维护 |
|---|---|---|---|
| `tokens/` | 原子值、语义别名 | 具体组件样式 | 设计系统负责人 |
| `foundation/` | 规范解释、示例、对比度说明 | 代码实现 | 设计 |
| `components/primitives/` | 无业务语义的原子件 | 业务文案、接口调用 | 设计系统 + 前端 |
| `components/domain/` | 体系业务组件 | 单页临时组件 | 业务线提案 + 审批 |
| `patterns/` | 组合范式、页面骨架 | 具体页面 | 设计系统 |
| `content/` | 术语、话术、文案规范 | 营销文案 | 内容 + 设计 |
| `governance/` | 规则、模板、检查表 | 规范正文 | 体系治理 |
| `automation/` | 校验脚本、CI | 业务逻辑 | 工程 |
| `archive/` | 历史版本、废弃说明 | 在用资产 | 体系治理 |

## 组件目录内强制结构

每个组件必须有五件套，缺一不进交付：

- `meta.json`：`id` / `version` / `status(alpha|beta|stable|deprecated)` / `owner` / `tokensUsed[]` / `a11yNotes`
- 组件实现、story、spec、`.md` 规格说明。
- `status=deprecated` 时必须写替代组件与下线时间。

## 命名规范

- Token：`{类别}.{角色}.{变体}`，如 `color.semantic.text.primary`、`space.inset.lg`。
- 组件：目录名与组件名一致，用大驼峰文件名（`TaskCard.tsx`）。
- 版本：语义版本，Token 破坏性变更升 major 并全局通告。
