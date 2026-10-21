# OPA 策略护栏实接 · 落地回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-28

## 交付物
- tools/opa_policy_enforcer.py：策略执行器（rego 为策略单一来源，解析 op_whitelisted + layer_lock，fail-closed）
- tools/operator_dispatcher.py：validate 后接入 OPA 放行（拒绝 → OPA_DENIED / LAYER_LOCK_TRIGGERED，落账本+归档）
- policy/zongyuan_root_policy.rego（444，上轮已建）现为调度器实际执行策略

## 三链路实测
| 契约 | 判定 | 结果 |
|---|---|---|
| T-OPA-ALLOW-0001（合法 OP-DEMO-PROBE-001） | 放行 | ALL_DONE exit 0 ✓ |
| T-OPA-LOCK-0001（kind=logic_layer_direct 越层） | 拦截 | LAYER_LOCK_TRIGGERED（轻锁档）✓ |
| T-OPA-BLOCK-0001（非法 op_id） | 首层拦截 | manifest 白名单 CONTRACT_VALIDATE_ERROR（双层闸门）✓ |

## 安全
fail-closed（rego 缺失即拒绝）；越层直连触发轻锁档+账本审计；策略单一来源=rego 文件；账本 3 条追加留痕
