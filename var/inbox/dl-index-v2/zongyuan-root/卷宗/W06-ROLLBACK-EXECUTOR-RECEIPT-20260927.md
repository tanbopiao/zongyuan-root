# W-06 契约回滚执行器 · 落地回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 交付物
- tools/rollback_executor.py（回滚执行器 V1.0，白名单+DID/签名全校验+账本append-only）
- tools/operator_dispatcher.py 接入（失败且 rollback_plan.enabled → 自动生成回滚契约执行）
- physical_operator/fail_probe.sh（OP-DEMO-FAIL-001 失败模拟算子，测试用）
- manifest 注册 OP-DEMO-FAIL-001 + self_sha256 按调度器算法重算

## 端到端验证（T-ROLLBACK-TEST-0002）
| 环节 | 结果 |
|---|---|
| 主算子 OP-DEMO-FAIL-001 | exit 1（预期失败） |
| 自动生成回滚契约 | T-ROLLBACK-TEST-0002-RB-33922Z ✓ |
| 回滚执行 OP-DEMO-PROBE-001 | SUCCESS exit 0 |
| 回执 | ROLLBACK_DONE（rollback_of 正确指向） |
| 账本 | 主任务 + 回滚任务两行追加（RB 标记） |
| 归档 | 主/回滚契约+回执 3 文件入 task_finished |

## 安全铁律落实
回滚 op_id 白名单 / DID+签名+版本校验 / 不执行任意 shell / 失败不阻塞主流程 / 账本只追加
