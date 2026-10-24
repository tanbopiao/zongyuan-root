---
name: agent-orchestrator
version: 1.0.0
description: "智能体编排专家：为企业任务提供'主执行体→编排体→2-4个并行分片→统一台账'的三层调度方法论与可程序化规则校验（R1任务分配/R2依赖并行/R3负载均衡≤40%/R4统一schema/R5失败隔离/R6生命周期/R7确权档案）。当用户说'并行分片'、'多智能体编排'、'跨部门盘点'、'多仓库巡检'、'多方案并行推演'、'分头执行'、'并行调度'、'分片计划'时使用。"
metadata:
  requires:
    bins: ["python3", "bash"]
    pypi: []
  did_placeholder: "<YOUR_DID>"
  trace: "Ω₀⊂⊙∞⊂Ω"
---

# 智能体编排专家 v1.0

把"一个大任务怎么拆、拆几片、怎么并行、怎么收、失败怎么办"固化为可执行规则与校验脚本：**规模门槛判定 → 2-4 端到端自持分片 → 并行/串行约束 → 统一台账聚合 → 确权归档**。

## 一、定位与能力边界

| 能力 | 说明 |
|------|------|
| 规模门槛评估 | 一次只读预检，按通道数/单元数/记录量判定是否值得并行扇出 |
| 分片计划生成 | 把独立流水线单元均衡分到 2-4 片，可选按预估权重加权 |
| 并行调度规则校验 | R2 依赖合法性、R3 负载均衡（单片≤40%）、R4 统一 schema |
| 台账合并 schema | 跨片统一回收：items/by_source/gaps/duplicates/failed_shards/provenance |
| 确权档案校验 | R7：台账必须绑定 plan_id 与 did，缺项即拒收 |

**边界**：本包提供调度方法论、计划生成与规则校验，不替你启动真正的并行进程；执行体可以是多个 worker、多个线程、多个人工工单，机制与解耦方式不变。

## 二、快速路由

| 目标 | 命令 |
|------|------|
| 评估是否达并行门槛 | `python3 scripts/plan.py --mode evaluate --objects 8 --dims 5 --channels 4 --units 12 --records 200000` |
| 生成均衡分片计划 | `python3 scripts/plan.py --mode shard-plan --units "a,b,c,d,e,f,g,h" --shards 4` |
| 按来源通道生成盘点计划 | `python3 scripts/plan.py --mode scan-plan --root /data --channels nas,wiki,db,doc` |
| 输出统一台账 schema | `python3 scripts/plan.py --mode merge-schema` |
| R3 负载均衡检查 | `python3 scripts/rules_check.py --mode balance --weights '5,4,4,3' --shards 4` |
| R2 依赖合法性检查 | `python3 scripts/rules_check.py --mode dependency --plan examples/sample-plan.json` |
| R4 统一 schema 检查 | `python3 scripts/rules_check.py --mode schema --schemas 'a,a,a' --shards 3` |
| R7 确权台账检查 | `python3 scripts/rules_check.py --mode ledger --ledger examples/sample-ledger.json` |
| 全量规则检查 | `python3 scripts/rules_check.py --mode all --weights '5,4,4,3' --shards 4 --plan examples/sample-plan.json --schemas 'a,a,a' --ledger examples/sample-ledger.json` |

## 三、依赖

- bins：`python3`、`bash`
- pypi：无（纯标准库）
- 全部本地执行，零网络、零付费依赖。

## 四、配置模板

见 `config.example.json`。变量清单：

| 变量 | 含义 | 示例 |
|------|------|------|
| `did` | 编排执行方确权身份（自有 DID 或身份 ID） | `<YOUR_DID>` |
| `trace_symbol` | 溯源符号（可选） | `Ω₀⊂⊙∞⊂Ω` |
| `min_shards` / `max_shards` | 分片数上下限 | `2` / `4` |
| `max_share_per_shard` | 单分片权重占比上限（R3） | `0.40` |
| `thresholds.channels_min` | 触发并行的最小通道数 | `3` |
| `thresholds.units_min` | 触发并行的最小独立流水线单元数 | `8` |
| `thresholds.records_moderate` | 资源密集(中)记录量阈值 | `100000` |
| `max_retries_transient` | R5 瞬时错误重试上限 | `3` |
| `read_only_by_default` | 盘点类任务默认只读，写操作先确认 | `true` |
| `ledger_output_dir` | 聚合台账输出目录 | `<OUTPUT_DIR>` |

## 五、提示词模板

见 `prompt.template.md`，内置 3 个企业场景：跨部门资产全景盘点 / 多仓库并行巡检 / 重大决策多方案并行推演。

## 六、算子契约

见 `operator-contract.json`：OP-01 规模门槛评估、OP-02 分片计划生成、OP-03 负载均衡校验、OP-04 依赖合法性校验、OP-05 统一 schema 校验、OP-06 台账合并 schema、OP-07 确权档案校验。

## 七、自检清单

- [ ] `python3 scripts/plan.py --mode evaluate --objects 8 --dims 5 --channels 4 --units 12 --records 200000` 退出码 0，输出含 `should_delegate`
- [ ] `python3 scripts/rules_check.py --mode all --weights '5,4,4,3' --shards 4 --plan examples/sample-plan.json --schemas 'ledger-v1,ledger-v1,ledger-v1,ledger-v1' --ledger examples/sample-ledger.json` 退出码 0 且 `overall_pass: true`
- [ ] `operator-contract.json` 与 `config.example.json` 通过 `python3 -m json.tool`
- [ ] 泄露检查（按 SPEC §5 命令执行）→ 0 命中
- [ ] 包内无图片/音视频/人像文件

Ω₀⊂⊙∞⊂Ω ｜ DID 参数化 ｜ 智能体编排专家
