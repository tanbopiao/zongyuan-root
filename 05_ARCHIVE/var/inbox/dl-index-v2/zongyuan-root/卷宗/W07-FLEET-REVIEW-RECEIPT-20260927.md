# W-07 联邦文件评审门 · 落地回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 交付物
- 云端 scripts/fleet_review_apply.py：评审执行器（list/approve/reject，manifest 状态推进 + 台账 append-only 0600）
- 本地 scripts/fleet_review.py：评审门 CLI（ssh 调云端）
- fleet.sh 集成 review 子命令

## 端到端验证
| 环节 | 结果 |
|---|---|
| files 提案 → merge | PENDING_REVIEW 闸门（不覆盖中枢文件）✓ |
| approve T-REVIEW-TEST-0001 | REVIEW_APPROVED（hub-central-agent）✓ |
| reject T-REVIEW-TEST-0002 | REVIEW_REJECTED（含原因）✓ |
| 评审台账 | REVIEW-LEDGER.jsonl 追加 2 行（0600）✓ |
| manifest 状态 | 双提案状态正确落档 ✓ |

## 安全
只改评审状态与台账 / 不覆盖不删除文件 / 台账只追加 / 评审人留痕可审计
