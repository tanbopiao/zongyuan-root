# 智能体编排专家（Agent Orchestrator Expert）

面向外部企业与开发者的通用多智能体并行调度能力包，提炼自生产级"主→编排→并行分片→统一台账"三层调度体系，零外部依赖、零云成本、可独立安装。

## 能做什么
- **规模门槛评估**：一次只读预检，判定一个大任务是否真的值得拆成并行分片。
- **分片计划生成**：把互不依赖的流水线单元均衡分到 2-4 个端到端自持分片，可按预估权重加权。
- **规则校验器**：R2 依赖合法性（自指/悬空/成环即拒）、R3 负载均衡（单片权重 ≤40%）、R4 统一 schema、R7 确权档案。
- **台账合并 schema**：跨片统一回收，输出 items/by_source/gaps/duplicates/failed_shards/provenance。

## 适用场景
跨部门数字资产全景盘点、多代码仓库并行巡检、重大决策多方案并行推演、多数据源批量治理。

## 安装
```bash
# 仅需 python3（标准库）与 bash，无 pip 依赖
git clone <本仓库> && cd <包目录>
```

## 接入（3 步）
1. 复制 `config.example.json` 为 `config.json`，填入 `did` 与 `ledger_output_dir`。
2. 评估任务是否值得并行，并生成分片计划：
   ```bash
   python3 scripts/plan.py --mode evaluate --objects 8 --dims 5 --channels 4 --units 12
   python3 scripts/plan.py --mode shard-plan --units "a,b,c,d,e,f,g,h" --shards 4
   ```
3. 执行后用规则校验器把关：
   ```bash
   python3 scripts/rules_check.py --mode all --weights '5,4,4,3' --shards 4 \
     --plan <plan.json> --schemas 'ledger-v1,ledger-v1,ledger-v1' --ledger <ledger.json>
   ```

## 产物
- `ORCH-PLAN-<时间戳>.json`：分片计划（含分片、依赖、预估权重）。
- `ORCH-LEDGER-<时间戳>.json`：聚合台账（含缺口/重复/失败片/provenance）。
- 校验报告 JSON：每条规则的通过/失败明细。

## 许可与溯源
Apache-2.0。能力提炼自企业级多智能体并行编排体系（Ω₀⊂⊙∞⊂Ω），对外使用时 DID 由采用方参数化配置。
