# Axiom-Verify-Lite 配套 · AI Agent 意图漂移防控算子 (intent-drift-guard)

> 火斗云智 AIOS 稳态自治验证项目 ｜ 分层可控自治中间件 ｜ v1.0
> 四层阈值防线 + 三级熔断打断 ｜ 五算子解耦 ｜ 零第三方核心依赖

## 解决什么问题

大模型 Agent 多步推理的：**意图漂移 / 目标跑偏 / 死循环 / 无效推理 / 资源溢出 / 上下文熵增**。

核心能力：**四层阈值防线**（0.75 对齐 → 0.3 漂移 → 行为/资源 → 父子 0.6）+ **三级熔断**
（预警纠偏 → 限制管控 → 终止止损），全部按方案固定阈值实现，可证伪、可消融、可量化。

## 架构（五大算子，监控与业务完全隔离）

```
业务 Agent (不改动)  ←插件挂载→  IntentDriftGuard 门面
   ├─ 算子1 anchor     目标结构化锚定 (只读锁档 0444+SHA256, sim<0.75→L1)
   ├─ 算子2 semantic   语义漂移监测   (BGE-m3, 距离>0.3→漂移, 20步上限, 入出参强校验)
   ├─ 算子3 behavior   行为风控       (连续3次重复→死循环L2, 资源阈值, 上下文≥90%重锚定)
   ├─ 算子4 collab     跨Agent协同    (下发禁简省, 父子sim<0.6拦截, 逐级偏差溯源)
   ├─ 算子5 breaker    三级熔断自愈    (2×L1→L2, 3×L2→L3, 故障报告, 人工修复恢复)
   │     └─ self_heal    自愈引擎 (漂移/循环/溢出自动修复, 失败→工单+告警)
   └─ 扩展 quota       平台积分/额度熔断 (≥80%→L1预警, ≥95%→L2只读, 边沿触发, 回填复位)
可观测: logs/events.jsonl + trajectory.jsonl + GET /metrics 面板接口(含 quota.<平台>.ratio)
```

## 快速开始

```bash
bash scripts/install.sh            # 环境检查+编译+快速自测 (可加 --bge 装BGE后端)
bash scripts/start.sh ./var 8120   # 启动面板接口 (可选, 或纯嵌入式挂载)
python3 tests/selftest.py          # 完整自测 (≥95%/≤5% 达标判定)
```

## 低侵入挂载（不改业务代码）

```python
from intent_drift_guard import IntentDriftGuard

guard = IntentDriftGuard("task-001", "自然语言任务目标…", workdir="./var")
gate = guard.before_thought(text)        # 每轮推理前: 锚定对齐+漂移判定
if gate.allow:
    ...
gate = guard.before_tool("search", {"q": "..."})   # 工具调用前: 锁定判定+入参强校验
guard.after_tool(result_text, tokens=1234)          # 工具后: 出参校验+资源入账
guard.on_action({"tool": "fetch", "url": ...})      # 行为登记: 死循环检测
guard.on_context(used_tokens, window)               # 上下文: ≥90% 强制重锚定
guard.on_child_dispatch(child_goal_json)            # 跨Agent下发完整性
guard.on_child_submit(child_output_text)            # 跨Agent对齐(<0.6拦截)
guard.on_quota("百度搭子", used=80, budget=100)      # 平台积分: 80%一级/95%二级(扩展)
guard.mount(agent); guard.unmount()                 # 一键挂载/卸载
guard.enable(); guard.disable()                     # 独立启停
```

恢复入口（对应三级逻辑）：`guard.reanchor()` 一级自动纠偏 ｜ `guard.manual_confirm()` /
`guard.backup_flow()` 二级恢复 ｜ `guard.repair_completed()` 三级人工修复重启。

## 固定阈值（方案强制，见 config/thresholds.json，动态可调有审计）

| 防线 | 阈值 | 触发 |
|---|---|---|
| 锚定对齐 | 相似度 < 0.75 | 一级预警 + 自动重锚定 |
| 语义漂移 | 距离 > 0.3 | 判定有效漂移（一级） |
| 推理步数 | > 20 步 | 一级预警 |
| 死循环 | 连续 3 次重复动作 | 二级熔断（锁工具+只读） |
| 上下文饱和 | ≥ 90% | 强制重锚定（保留核心目标） |
| 父子一致 | 相似度 < 0.6 | 拦截输出 + 二级告警 |
| 熔断升级 | 2×L1→L2；3×L2→L3 | 状态机强制升级 |
| 平台积分（扩展） | ≥ 80% / ≥ 95% | 一级预警 / 二级只读（台账 `config/platform_quota.json`） |

## 交付物清单（对应方案[四]）

1. 算子源码 `intent_drift_guard/`（8 模块，分层解耦，注释完整）
2. 部署说明书 `docs/DEPLOY.md` + 依赖清单 `requirements.txt` + `scripts/install.sh|start.sh`
3. 阈值配置 `config/thresholds.json` + 自愈策略 `config/self_heal.json` + 积分台账 `config/platform_quota.json`
4. 自测报告 `docs/SELF-TEST-REPORT.md`（46/46，准确率 100%，误报率 0%）
5. 告警与日志说明 `docs/ALERTS.md`

配套（内核侧，见仓库根）：`AGENTS.md`「LITE 快速激活」节 + `00_KERNEL/startup_memory/LITE-BOOTSTRAP-V1.md`
（轻量激活档，解决平台节点全量自举烧积分问题）。

## 测试结论（2026-10-22 实测）

`accuracy = 100% (40/40)` ｜ `fpr = 0%` ｜ `checks 46/46` ｜ 达成 ≥95% / ≤5% 目标
（详见 [docs/SELF-TEST-REPORT.md](docs/SELF-TEST-REPORT.md)，含自测发现并修复的 4 个真实缺陷 + 积分熔断扩展 7 项场景）
