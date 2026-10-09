# 02_SKILLS · 技能·算子·脚本

> DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 7 大类收敛目录之一（初始建立 2026-10-09）

## 定位

仓库 7 大类收敛结构的 `02_SKILLS` 目录：承载**技能（skill）/ 算子（operator）/ 脚本（script）**类资产。
当前仓库内技能/算子仍散布于多个既有目录，为保兼容**不迁移既有文件**，本目录采用「注册表索引」方式归位。

## 内容

- `SKILLS-LEDGER.json` —— 技能/算子注册表（name / type / source_path / description / status）
- （后续）新形态技能/算子直接落在本目录下，并追加注册表条目

## 归位规则

1. **新增**技能/算子/脚本 → 优先放入 `02_SKILLS/`，并登记到 `SKILLS-LEDGER.json`
2. **既有**分散资产 → 在注册表中登记 source_path 指向原路径，**不移动文件**
3. 形态判定：
   - 可复用、有明确输入/输出的封装 → 算子（operator）
   - 面向特定任务的执行流程说明 → 技能（skill）
   - 一次性/日常维护命令 → 脚本（script）

## 现存技能/算子索引

详见 `SKILLS-LEDGER.json`，已登记仓库内主要算子：真值引擎（truth_pipeline/truth_recall/truth_generator）、记忆（memory_optimizer/maintain_memory_chain）、进化闭环（evolve_closed_loop/value_cycle）、自愈（ance_self_heal）、调度（autonomous_scheduler）、云端同步（sync_agent/auto_report_sync）等。