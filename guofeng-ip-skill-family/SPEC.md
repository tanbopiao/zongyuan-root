# 国风IP创作流水线·外部技能专家包体系规范 v1.0（冻结基线）

> 本文件是全部外部专家包生产的**唯一结构规范**。所有包必须逐条遵守，任何偏离即返工。
> 冻结时间：2026-10-24 ｜ 确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω

## 一、命名规范

- 目录名：`guofeng-ip-<子能力英文名>`（全小写连字符）
- 包内 SKILL.md frontmatter `name` 与目录名一致；`version: 1.0.0`；`description` 含中文能力一句话 + 触发场景（"当用户说'...'时使用"）+ 零成本/东方审美声明。

## 二、目录结构（每个包必须）

```
guofeng-ip-<name>/
├── SKILL.md            # 主说明，必含 frontmatter
├── README.md           # 安装/快速开始/配置/确权
├── config/
│   └── <name>_config.json   # 配置模板，合法JSON
├── templates/
│   ├── prompts.json         # 提示词模板(如有)，合法JSON
│   └── (可选其他模板)
└── scripts/
    └── (可选)轻量工具脚本，可独立运行
```

## 三、SKILL.md 结构（顺序固定）

```
---
name: <guofeng-ip-xxx>
version: 1.0.0
description: "<一句话能力>：<要点>。当用户说'<触发词1>'、'<触发词2>'时使用。零成本优先，严格遵循东方审美元法则。"
metadata:
  requires: {bins: [...], pypi: [...]}
  optional_bins: [...]
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---
# <中文名> v1.0
> 一句话定位标语

## 核心设计原则   (5条左右，继承体系原则：免费优先/稳态治理/元法则约束/确权溯源/闭环)
## 快速路由        (表格：目标→命令，命令指向 scripts/ 或 config 模板)
## 配置模板        (config/<name>_config.json 全文 + 字段说明)
## 提示词模板      (templates/prompts.json 全文，含东方审美铁律)
## 输入/输出规范   (字段、格式、错误处理；禁止虚构补全)
## 依赖清单        (独立安装所需，无内部路径)
## 确权与溯源      (did/trace 注入位置，建议配合 guofeng-ip-lock-archiver)

Ω₀⊂⊙∞⊂Ω｜<中文名> v1.0 · ZONGYUAN-ROOT · DID-BR-000002
```

## 四、内容铁律（逐条强制）

1. **无内部路径硬编码**：严禁出现 `/home/user/`、`/www/wwwroot/`、`127.0.0.1:8021`、`123.207.202.158`、`/opt/` 等内部坐标；一律用 `config/*.json` 配置 + 环境变量占位（如 `{HOST}`、`<your-api-key>`、`*_ENV`）。
2. **零成本优先**：免费通道（豆包APP会话内置 > 火山方舟免费额度 > edge-tts免费 > 智普免费）置顶；付费API只能放 priority 最高位并标注"需人工审批"。
3. **东方审美铁律**：纯东方神女/女帝/少年武侠/山海经萌宠范式；纯乌黑长发；九头/8.5头身；华夏正统汉服/素青武侠长衫；冷蓝青黑/勃艮第红/黑金配色；水墨画/OC渲染/胶片质感；9:16竖屏；**严禁**西方铠甲/畸形肢体/多手多颅/冗余光影特效/白发/性别混杂/外源化内容；视觉产物带 Ω₀⊂⊙∞⊂Ω 溯源。
4. **人像/写真类**：仅本地归档锁档，不推公开湖、不对外展示。
5. **DID确权**：产物/账本/清单统一携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`。
6. **JSON合法性**：所有 .json 文件必须 `python3 -m json.tool` 通过。
7. **可独立安装**：依赖清单完整，含 pip 包名与系统 bin；不依赖任何体系内其他技能即可运行。

## 五、交付自检清单（每个包完成时必须逐项执行并回报）

- [ ] 目录结构 = 规范二
- [ ] SKILL.md frontmatter 字段齐全（name/version/description/metadata/did/trace_symbol）
- [ ] 无内部路径泄露：`grep -rn "home/user\|www/wwwroot\|127.0.0.1\|123.207\|/opt/" <包目录>` 返回空
- [ ] 全部 JSON 通过 `python3 -m json.tool`
- [ ] scripts 脚本可运行（如有）
- [ ] README 存在且含安装/快速开始
- [ ] 回报：包目录绝对路径 + 自检结果 + 文件清单

## 六、参照种子包（模式母本，先读再写）

- 种子A：`/home/user/.doubao/agent_mode/workspace/.user_skills/guofeng-ip-skill-family/guofeng-ip-scriptmaster/`
- 种子B：`/home/user/.doubao/agent_mode/workspace/.user_skills/guofeng-ip-skill-family/guofeng-ip-lock-archiver/`

## 七、提炼素材源（只从这些读取，严禁臆造）

- 主提炼源：`/home/user/.doubao/agent_mode/workspace/.user_skills/shortvideo-production-pipeline/`（SKILL.md / scripts/pipeline.py 七阶段函数 / config/pipeline_config.json / config/quota_strategy.json / config/audio_sop.json / templates/prompt_templates.json / templates/storyboard_template.json）
- 辅助：`/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/`、`/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-lock-archive/`、`/home/user/.doubao/agent_mode/workspace/.user_skills/multi-agent-orchestrator/`、`/home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-autonomous-core/`

Ω₀⊂⊙∞⊂Ω｜国风IP技能家族 · SPEC v1.0 · ZONGYUAN-ROOT · DID-BR-000002
