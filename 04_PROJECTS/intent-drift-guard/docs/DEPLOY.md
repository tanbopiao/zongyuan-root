# 部署说明书 (DEPLOY) · intent-drift-guard v1.0

## 1. 环境依赖

| 项 | 要求 | 说明 |
|---|---|---|
| Python | >= 3.9 | 核心纯标准库，**零必须第三方依赖** |
| BGE-m3 后端（可选，生产推荐） | `pip install -r requirements-bge.txt` | sentence-transformers>=2.7 + torch>=2.0；首次运行需可下载 `BAAI/bge-m3` 或本地模型路径 |
| 网络 | 无硬性要求 | 离线时自动降级 lexical 后端并在事件日志如实标注（见 ALERTS.md 后端降级章节） |
| 磁盘 | ~2MB/任务（日志+锚+报告） | 工作目录 `workdir` 可指定 |

## 2. 安装与验证

```bash
cd 04_PROJECTS/intent-drift-guard
bash scripts/install.sh          # ①Python检查 ②编译检查 ③依赖 ④快速自测
bash scripts/install.sh --bge    # 追加安装 BGE-m3 后端
python3 tests/selftest.py        # 完整自测: 目标 accuracy>=95%, fpr<=5%
```

## 3. 启动 / 停止（面板接口，可选）

```bash
bash scripts/start.sh [工作目录] [端口]     # 默认 ./var 8120
# GET http://127.0.0.1:8120/metrics        # 面板数据接口(JSON)
# 停止: 前台 Ctrl+C / 后台 kill <pid>
```

门面纯嵌入式使用时**无需启动任何进程**（作为库直接挂载）。

## 4. 低侵入挂载（生产接入标准姿势）

```python
from intent_drift_guard import IntentDriftGuard

guard = IntentDriftGuard(
    task_id="order-agent-001",
    natural_goal="核验职称申报材料并生成评审意见；必须逐项对照申报条件；不得超过20页；截止2026-11-30",
    workdir="/var/lib/intent-drift",
    config_path=None,                 # None -> 自动加载 config/thresholds.json
)

# --- 业务链路 4 个钩子(不改业务代码, 按点位调用即可) ---
gate = guard.before_thought(step_text)                    # 每轮推理前
gate = guard.before_tool(tool_name, input_params)         # 每次工具调用前
gate = guard.after_tool(output_text, tokens=n)            # 工具执行后
guard.on_action({"tool": tool_name, "params": input_params})  # 行为指纹登记

# --- 多Agent场景 ---
gate = guard.on_child_dispatch(child_goal_json)           # 下发完整性(禁简省)
gate = guard.on_child_submit(child_output)                # <0.6 拦截

# --- 生命周期 ---
guard.mount(agent); guard.unmount()      # 一键挂载/卸载(属性挂载, 不改agent源码)
guard.enable(); guard.disable()          # 独立启停
```

**Gate 结果处置约定**

| gate.allow | 含义 | 业务侧动作 |
|---|---|---|
| True, action=continue | 放行 | 正常执行 |
| True, action=reanchor | 一级预警中 | 执行 `guard.reanchor()` 后自动接续（无断点） |
| False, action=intercept | 参数/出参越界 | 不执行该调用，按 reason 换参重试 |
| False, action=tools_locked | 二级限制 | 停止执行，等待 `manual_confirm()` 或 `backup_flow()` |
| False, action=terminate | 三级终止 | 已自动回收+生成故障报告；等 `repair_completed()` |

**三级恢复入口**：一级自动（重锚定校验通过即接续）；二级 `guard.manual_confirm(note)` 或
`guard.backup_flow(name)`；三级 `guard.repair_completed(note)`（唯一入口，人工排查后）。

## 5. 阈值配置（动态适配）

- 编辑 `config/thresholds.json` → `ThresholdConfig.reload()` 热更新；或运行时
  `guard.cfg.override({"semantic.max_steps": 15}, source="ops")`。
- 全部变更写入 `guard.cfg.audit`（键/旧值/新值/时间/来源）供审计；
  未知键直接抛 `KeyError`——**配置漂移不可引入未定义阈值**。
- 与方案固定阈值不一致的值视为业务场景定制，仅作用于该 workdir 配置副本。

### 5b. 平台积分/额度台账（扩展，配置 CREDIT-BURN 补齐）

- 阈值：`thresholds.json` → `quota` 段（`warn_ratio=0.8` 一级预警 / `critical_ratio=0.95` 二级只读 / `enable`）。
- 台账：`config/platform_quota.json` → `platforms.<平台> {budget, used, unit, reset}`；
  **`budget>0` 才参与判定**（防未配置误熔断），`used` 由各节点回填或手工更新。
- 挂载后每轮/每阶段调用 `guard.on_quota(platform, used, budget)`；档位跨越才进熔断状态机
  （边沿触发），额度回填一级自动解除、二级按方案人工/备用恢复。
- 平台侧运行须同时遵守 AGENTS.md「LITE 快速激活」节：只轻交互、禁守护循环、自动化回自有服务器。

## 6. 自愈策略配置

`config/self_heal.json`：场景 → 动作（reanchor / break_action_window /
context_trim_keep_goal / checkpoint_pause / block_and_realign_child）+ `max_attempts` +
`on_fail=workorder`。白名单外场景键被拒绝。工单落 `workorders/wo_*.json`（P2/OPEN）。

## 7. 可观测与验收

- 日志：`{workdir}/logs/events.jsonl`（按级别另有 L1/L2/L3.jsonl 分片）
- 轨迹：`{workdir}/logs/trajectory.jsonl`（逐步相似度/距离/事件）
- 面板：`GET /metrics` → `{"gauges": {semantic.last_similarity, fuse.*},
  "counters": {event.*, fuse.*}}`
- 故障报告：`{workdir}/reports/fault_*.json`（漂移轨迹/异常节点/资源消耗）
- 验收基线：`python3 tests/selftest.py` 必须 `accuracy>=95% & fpr<=5%` 且 checks 全 PASS
  （当前实测 100% / 0% / 46全过，见 SELF-TEST-REPORT.md）

## 8. 卸载

`guard.unmount()` 即完全还原（属性摘除，无任何侵入残留）；进程型面板直接 kill。
历史日志/锚/报告为只读留档，删除 workdir 即清理（L1 公理：正常运行期不自动删除）。
