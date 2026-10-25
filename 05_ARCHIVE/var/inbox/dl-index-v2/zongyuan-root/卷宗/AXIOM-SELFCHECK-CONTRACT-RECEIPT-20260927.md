# 元极恒一本体公理自检契约 · 执行回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27 ｜ CONTRACT-OP-V1.0 ｜ T-1785227700-00001

## 执行结果
- 调度：ALL_DONE exit 0 ｜ 算子 SELF_CHECK_AXIOM SUCCESS
- 判定：**AXIOM_VALID**（6/6 PASS）
- 报告：var/log/self_check_axiom_report.json ｜ 账本追加 1 行

## 六项自检明细
锚点 PASS ｜ 账本 PASS ｜ 公理文档(444只读) PASS ｜ OPA三层策略 PASS ｜ 熔断总线 PASS ｜ 镜像根 PASS

## 契约依赖补齐（本轮落地）
1. meta_laws/CORE-AXIOMS.md（契约路径，444 只读）
2. policy/zongyuan_root_policy.rego（OPA 三层相变：allow 白名单 + layer_lock 越层拦截）
3. MIRROR-STATE.json（镜像根 match=true，444）
4. SYSTEM-STATE.json 根目录软链（兼容契约路径）
5. manifest 注册 SELF_CHECK_AXIOM（白名单 5 算子）
6. 用户契约规范化（补 ontology_signature/contract_utc/scheduling_policy 以过调度器校验，保留 op_id 与 6 项语义）

## 判定规则落实
全过 → AXIOM_VALID；单项失败 → AXIOM_DEVIATION+WARNING；核心锚点篡改 → PARTIAL_LOCK（自检为只读审计，无写操作，无需回滚）
