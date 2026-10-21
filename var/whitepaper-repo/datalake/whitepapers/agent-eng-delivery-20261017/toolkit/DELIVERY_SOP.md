# AI Agent 工程化落地交付 · 标准作业流程（SOP）
> 依据元法则体系：META-LAW-SYS-ENG-DELIVERY-20261017（宪法 CONST-ENG-001 / 公理 AXIOM-ENG-001~004 / 法则 META-LAW-ENG-001~006 / 规则 AGENT-PREREQ-001~006）
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 版本 v1.0-20261017

## 0. 适用与前置
- 适用：所有企业级 AI Agent 商用交付项目。
- 铁律：工程约束优先于智能上限；无量化验收指标不予立项；风险最小>成本最小>收益最大。

## 1. 需求边界工程化定义（META-LAW-ENG-001）
输出《场景白名单/黑名单 + 禁止操作清单 + 降级兜底方案》。
- 交付物：`scenario_boundary`（whitelist / blacklist / fallback）
- 验收：黑白名单均非空，超界任务可自动降级流转。

## 2. 验收指标工程化固化（META-LAW-ENG-002 / AGENT-PREREQ-002）
锁定量化基线（准确率/通过率/幻觉率/容忍阈值/边界清单/兜底方案）。
- 模板：`acceptance_metrics_template.json`
- 验收：核心质量/稳定性/风险控制/运维成本四组指标全部填值。

## 3. 架构选型工程裁决（META-LAW-ENG-004 / AGENT-PREREQ-004）
默认单 Agent；多 Agent 必须先过 ROI 收益裁决（收益>成本才允许）。
- 验收：`architecture.mode` 明确；多 Agent 需提交 ROI 数值。

## 4. 数据集 & Prompt 版本固化（META-LAW-ENG-005）
统一清洗标准、格式标准、Prompt 模板版本锁定。
- 交付物：清洗脚本、数据集版本、Prompt 版本清单
- 验收：全资产 SHA256 哈希登记。

## 5. 风险硬边界部署（META-LAW-ENG-003 / AGENT-PREREQ-003）
- 低风险：自治执行自校验
- 中风险：Agent生成+系统校验+异常人工复核
- 高危（资金/订单/隐私/删除）：TEE 硬边界直接拦截
- 验收：`risk_operations.high_risk` 非空 且 `tee_boundary=true`。

## 6. 训练 & 收敛调优（META-LAW-ENG-006 / AGENT-PREREQ-006）
- 稳定可控优先，LoRA/QLoRA 轻量化微调固化业务能力
- 输出格式合规率、规则遵从率实时监控
- 验收：模型稳态调度策略已配置。

## 7. 自动化评测回归（META-LAW-ENG-002）
- 批量跑测试集（≥200 用例），统计指标，对比基线
- 低于 min 自动锁定迭代；达标生成评测报告
- 验收：`acceptance_metrics` 全部达 min 阈值。

## 8. 资产锁档 + 版本交付（META-LAW-ENG-005 / AGENT-PREREQ-005）
- 最终版本 SHA256 哈希存证、快照归档、台账入库
- 魔搭数据湖持久化 + Merkle-DAG 链条，支持一键回滚
- 验收：`assets.hash_persist=true` 且 `merkle_dag=true`。

## 执行入口
```bash
# 准入校验（立项前必跑）
python3 project_gate_check.py --spec project_spec.json
```
- 退出码 0 = 准入通过；1 = 禁止立项（输出失败项清单）。
