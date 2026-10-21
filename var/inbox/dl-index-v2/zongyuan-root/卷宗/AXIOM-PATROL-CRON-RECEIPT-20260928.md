# 公理自检周期巡检 · 双端上线回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-28

## 本地（Worker 执行面）
- scripts/axiom_patrol_timer.sh：每 6 小时投递新公理自检契约至 task_inbox（幂等防堆积，契约→调度→OPA→执行全链路）
- cron：`0 */6 * * *`
- 端到端实测：T-AXIOM-PATROL-1790545749 → ALL_DONE → **AXIOM_VALID**（SELF_CHECK_AXIOM SUCCESS）；inbox 无残留

## 云端（中枢）
- scripts/cloud_axiom_check.sh：每小时校验 Ω-Brainμ 锚点（did_binding/trace_symbol）+ OPA 策略冒烟（allow=True / layer_lock=True）
- cron：`30 * * * *`
- 实测：**AXIOM_VALID** anchor=PASS allow=True lock=True，结果追加 var/log/cloud_axiom_check.log

## 巡检覆盖
本地：公理 6 项全量（锚点/账本/公理文档/OPA/熔断总线/镜像根）
云端：锚点 + OPA 双冒烟（fail-closed 执行器）
