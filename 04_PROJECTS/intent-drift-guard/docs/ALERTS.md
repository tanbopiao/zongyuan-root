# 故障告警与日志说明 (ALERTS) · intent-drift-guard v1.0

## 1. 日志文件布局（`{workdir}/logs/`）

| 文件 | 内容 | 说明 |
|---|---|---|
| `events.jsonl` | 全链路事件（每行一条 JSON） | 主日志，含阈值超限+熔断+自愈+运维 |
| `L1.jsonl` / `L2.jsonl` / `L3.jsonl` | 按级别分片 | 运维 grep 快速定位 |
| `trajectory.jsonl` | 推理语义轨迹链 | 每步: step/ts/similarity/distance/drift/text_sha/events |

行格式：`{"ts","level","type","detail":{...}}`（level ∈ L1/L2/L3/BLOCK/SELFHEAL/ALERT/OPS）。

## 2. 事件类型总表（告警语义与处置）

### L1 预警级（自动纠偏，人工无需介入）
| type | 触发 | 自动动作 | 恢复 |
|---|---|---|---|
| `semantic_drift` | 语义距离 > 0.3 | 重锚定 + 自动接续 | `reanchor_passed`（连续3稳定步清连续计数） |
| `align_below_warn` | 相似度 < 0.75 | 同上 | 同上 |
| `step_limit_exceeded` | 推理 > 20 步 | 重锚定+断点 | 同上 |
| `resource_near_limit` | 资源 ≥ 80% 上限 | 断点暂停(`checkpoint`) | 每指标仅预警一次 |
| `resource_limit_exceeded` | 资源 ≥ 100% 上限 | 断点暂停 | — |
| `context_saturated_reanchor` | 上下文 ≥ 90% | 裁剪至 60%，保留核心目标 | 立即 |
| `quota_near_limit`（扩展） | 平台积分 ≥ 80% 预算（边沿触发） | 预警留痕，停开新任务 | `quota_refilled`（额度回填自动解除） |
| `fuse_level1` | 熔断器一级记录 | 日志留痕 | — |
| `streak_cleared_by_stability` | 稳定步达标 | 清"连续一级"计数 | — |

**升级规则**：连续 2 次 L1（其间无稳定步解除）→ 自动升 L2（`l1_escalated`）。

### L2 限制级（暂停业务 + 锁工具 + 只读观测）
| type | 触发 | 人工动作 |
|---|---|---|
| `dead_loop_detected` | 连续 3 次重复动作 | `guard.manual_confirm()` 或 `guard.backup_flow()` |
| `child_severe_deviation` | 父子相似度 < 0.6 | 拦截已自动；确认后恢复 |
| `dispatch_simplified_blocked` / `dispatch_constraint_omitted` | 下发缺字段/省略父约束 | 重新下发完整目标JSON |
| `quota_critical`（扩展） | 平台积分 ≥ 95% 预算（边沿触发） | 转自有服务器继续；回填后仍须 `manual_confirm()`/`backup_flow()` |
| `fuse_level2` / `l2_recovered` | 二级记录/恢复 | 恢复即清连续计数 |

**升级规则**：连续 3 次 L2 → 自动升 L3（`l2_escalated`）。

### L3 终止级（终止全部任务 + 回收资源 + 故障报告）
| type | 触发 | 恢复 |
|---|---|---|
| `resource_severe_overflow` | 资源 ≥ 150% 上限 | `guard.repair_completed()`（唯一入口） |
| `malicious_invalid_execution` | 业务侧直报 `report_malicious()` | 同上 |
| `fuse_level3` / `l3_repaired` | 三级记录/人工修复 | 修复后重启任务链路 |

故障报告：`{workdir}/reports/fault_*.json`，字段含
`drift_trajectory`（漂移轨迹）、`abnormal_nodes`（异常节点）、`resource_usage`（资源消耗）、
`fuse_totals`、`cause`、`recovery_required`。

### BLOCK 拦截（不计熔断次数，仅拦截该次动作）
`tool_param_violation`（入参违反禁用/数值约束）｜ `tool_result_out_of_range`（出参脱离目标域）

### SELFHEAL / ALERT / OPS
| type | 含义 |
|---|---|
| `heal_ok` | 自愈成功（场景/动作/次数） |
| `heal_failed_workorder` | 自愈失败 → 生成 `workorders/wo_*.json`（severity=P2, status=OPEN）并告警 |
| `embedding_backend_degraded` | BGE-m3 不可用降级 lexical（含标定系数），如实留痕 |
| `quota_refilled` | 平台额度回填（OPS级）：一级自动解除，二级按方案仍人工/备用流程恢复 |
| `mounted` / `unmounted` / `enable` / `disable` | 挂载与启停审计 |

## 3. 工单格式（`workorders/wo_<场景>_<ts>.json`）

```json
{"workorder_type":"INTENT_DRIFT_SELFHEAL_FAILED", "scenario":"...",
 "failed_action":"...", "attempts":2, "detail":{...}, "severity":"P2",
 "status":"OPEN", "assigned":"人工处置(无法自动自愈)"}
```

## 4. 面板数据接口（预留可视化）

`GET http://127.0.0.1:<port>/metrics` →
```json
{"gauges": {"semantic.last_similarity": 0.83, "semantic.step": 7,
            "fuse.L1_total": 1, "fuse.L2_total": 0, "fuse.L3_total": 0,
            "quota.百度搭子.ratio": 0.8},
 "counters": {"event.semantic_drift": 1, "fuse.L1": 1}}
```
核心四指标齐备：相似度 / 推理步数 / 资源消耗（`guard.stats()["resources"]`）/ 熔断次数；
积分面板：`guard.stats()["quota"]`（各平台 budget/used/ratio/level + 阈值档位）。

## 5. 常用排查命令

```bash
grep '"level":"L3"' {workdir}/logs/events.jsonl | tail      # 最近三级事件
tail -f {workdir}/logs/L2.jsonl                             # 二级实时观测
python3 -c "import json;print(json.load(open('{workdir}/logs/trajectory.jsonl'.replace(chr(10),'')))"  # 轨迹
ls {workdir}/workorders/                                    # 待处置工单
```

## 6. 告警升级路径（建议）

`heal_failed_workorder` → 工单系统 P2；`L2` 持续 > 10 分钟 → 通知值班；
`L3` → 立即人工介入（任务已自动终止，资源已回收，读 fault 报告排查）。

## 7. 已知 P0 问题（跨系统，非本模块产生）

| 问题 | 影响 | 处置 |
|---|---|---|
| 元极推理 API `/api/yuanji/v1/chat` 的 `usage.input_tokens`/`output_tokens` **恒返回 0** | 体系级 token 计量失明，积分消耗无法从响应统计（归因分析 CREDIT-BURN 根因#3） | 服务端回填 usage 计数；服务代码在云端（不在本仓），需云端授权后打补丁，修复前以本模块资源账+积分台账兜底 |
