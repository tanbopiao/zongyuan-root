---
name: data-reconciliation
version: 1.0.0
description: "数据资产对账专家：为任意企业数据资产提供基线清单对账（新增/删除/变更 + 漂移率）、append-only 账本 Merkle 完整性校验、本地清单与远端权威 API 双向溯源对账与增量补推、健康档案与停滞检测的一体化对账引擎。当用户说'数据对账'、'资产清单核对'、'漂移检测'、'账本校验'、'双向溯源'、'增量补全'、'健康巡检'时使用。"
metadata:
  requires:
    bins: ["python3", "bash"]
    pypi: []
  did_placeholder: "<YOUR_DID>"
  trace: "Ω₀⊂⊙∞⊂Ω"
---

# 数据资产对账专家 v1.0

为任何企业数据资产目录提供**基线清单对账 → Merkle 账本校验 → 双向溯源对账 → 增量补推 → 健康档案**的全流程对账能力：一次扫描即得新增/删除/变更清单与漂移率，账本只追加不改写，与远端权威 API 双向核对缺失即补全，连续轮次健康档案支持停滞检测与巡检频率自适应。

## 一、定位与能力边界

| 能力 | 说明 |
|------|------|
| 基线对账 | 当前目录指纹 vs 基线清单，输出新增/删除/变更 + 漂移率 |
| Merkle 账本校验 | append-only 账本逐行累积哈希重算，比对存储根，防中间篡改 |
| 双向溯源对账 | 本地清单 vs 远端权威 API 双向比对，本地缺失/远端缺失双向标记 |
| 增量补推 | 远端缺失项按批次幂等补推，成功落游标，断点续跑不重复 |
| 健康档案 | 连续正常/异常轮次计数 + 停滞检测 + 巡检频率自适应建议 |
| 对账报告 | 结构化 JSON 报告 + 可选上报端点（webhook） |

**边界**：本包不提供区块链上链/司法公证；远端对账端点由采用方自备（HTTP GET/POST 通用协议），本地纯标准库运行，零网络依赖（无端点配置时自动跳过远端算子）。

## 二、快速路由

| 目标 | 命令 |
|------|------|
| 一键对账（扫描+基线比对+账本校验+远端对账+报告） | `python3 scripts/reconcile.py --dir <资产目录> --baseline <基线.json> --did <YOUR_DID>` |
| 仅基线漂移检测 | `python3 scripts/reconcile.py --dir <资产目录> --baseline <基线.json> --local-only` |
| Merkle 账本完整性校验 | `python3 scripts/ledger_verify.py --ledger <账本.jsonl> --state <状态.json>` |
| 远端双向对账+补推 | `python3 scripts/remote_audit.py --manifest <清单.json> --config config.json --dry-run` |
| 健康档案快照 | `python3 scripts/remote_audit.py --profile --config config.json` |

## 三、依赖

- bins：`python3`、`bash`
- pypi：无（纯 Python 标准库）
- 全部本地执行，零付费依赖；远端算子仅在配置 `remote_audit_url` 时启用。

## 四、配置模板

见 `config.example.json`。变量清单：

| 变量 | 含义 | 示例 |
|------|------|------|
| `did` | 确权身份标识（自有 DID 或身份 ID） | `<YOUR_DID>` |
| `trace_symbol` | 溯源符号（可选） | `Ω₀⊂⊙∞⊂Ω` |
| `target_dir` | 被对账资产目录 | `<ASSET_DIR>` |
| `baseline_manifest` | 基线清单 JSON 路径 | `<BASELINE>.json` |
| `ledger_path` | append-only 账本路径（.jsonl） | `<LEDGER>.jsonl` |
| `remote_audit_url` | 远端权威 API 基址（空则跳过远端算子） | `<API_BASE_URL>` |
| `remote_headers` | 远端请求头（如鉴权） | `{"X-DID": "<YOUR_DID>"}` |
| `report_webhook` | 对账报告上报端点（可选） | `<WEBHOOK_URL>` |
| `batch_size` | 增量补推每轮上限 | `20` |
| `stall_threshold` | 停滞判定连续轮数 | `2` |

## 五、提示词模板

见 `prompt.template.md`，内置 3 个企业场景：月度资产漂移审计 / 双系统数据一致性核对 / 增量补全断点续跑。

## 六、算子契约

见 `operator-contract.json`：OP-01 目录指纹扫描、OP-02 基线对账、OP-03 Merkle 账本校验、OP-04 双向溯源对账、OP-05 增量补推、OP-06 健康档案。

## 七、自检清单

- [ ] `python3 scripts/reconcile.py --dir examples/sample-assets --baseline examples/baseline.json --did <YOUR_DID> --local-only` 退出码 0 且 `drift == 0`
- [ ] 在 examples 内新增一个文件后重跑 → `drift == 1` 且 `added` 含该文件
- [ ] `python3 scripts/ledger_verify.py --ledger examples/ledger.jsonl --state examples/state.json` 输出 `consistent: true`
- [ ] `python3 scripts/remote_audit.py --manifest examples/manifest.json --dry-run --did <YOUR_DID>` 退出码 0（无端点配置时跳过远端算子）
- [ ] 泄露检查（按系列 SPEC §5 命令执行）→ 0 命中
- [ ] `operator-contract.json` 可被 `python3 -m json.tool` 解析

Ω₀⊂⊙∞⊂Ω ｜ DID 参数化 ｜ 数据资产对账专家
