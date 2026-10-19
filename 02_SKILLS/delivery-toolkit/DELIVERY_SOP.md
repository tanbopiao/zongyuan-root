# DELIVERY-SOP · 标准作业流程（8 步）

> provenance: reconstructed from "ZONGYUAN-ROOT 全量记忆激活配置 v1.0-20261017" 第4.1/4.2/4.3节（原始终端全网0命中，按权威描述重建）
> 对齐：CONST-ENG-001 工程约束优先 · META-LAW-FULL-AUTO-DELIVERY-001 五步闭环

## 八步作业流程

| 步 | 动作 | 对应法则/工具 | 门禁 |
|---|---|---|---|
| 1 | **边界前置**：界定目标/范围/依赖/验收前提 | META-LAW-ENG-001 | 边界不清 → 禁入执行 |
| 2 | **准入校验**：跑门禁，缺项拦截 | `project_gate_check.py` | BLOCK 则不得继续 |
| 3 | **风险分级**：标注 P0~P3，高险硬隔离 | META-LAW-ENG-003 | P0/P1 需人工放行 |
| 4 | **复杂度裁决**：收益是否抵复杂度 | META-LAW-ENG-004 | 不抵则拒绝该复杂度 |
| 5 | **锁档存证**：生成 SHA256 | META-LAW-ENG-005 | 无哈希视为未交付 |
| 6 | **量化验收**：按模板填 measured | `acceptance_metrics_template.json` | verdict=PASS 才可放行 |
| 7 | **五步闭环交付**：本地→飞书→网关→魔搭→AtomGit | `full_delivery_pipeline.sh` | 每步可 `--dry-run` 预演 |
| 8 | **归档复盘**：回读校验 + 账本登记 | 记忆网关回读 | 无回读不算完成 |

## 铁律（不可突破）

1. 未过离线仿真/门禁，禁止灰度上线。
2. 无 SHA256 = 未交付；无量化指标 = 未验收。
3. 凭证仅运行时读取，禁止硬编码（第6节）。
4. LLM 输出仅作建议，执行权归硬约束 + 人工多签。

## 常用命令

```bash
# 门禁
python3 project_gate_check.py --name 资产名 --path /path/to/asset --acceptance acceptance_metrics_template.json
# 五步闭环（预演）
./full_delivery_pipeline.sh --name 资产名 --path /path/to/asset --target user/repo \
    --type doc --meta-class META --gateway-key KERNEL.DELIVERY.xxx --gateway-type data --dry-run
```
