---
name: system-health-inspection
version: 1.0.0
description: "体系健康巡检专家：为任意企业系统提供多探针健康检查（HTTP端点/端口存活/日志异常/磁盘水位/数据新鲜度）、风险分级门禁（低/中/高/严重）、加权健康评分(0-100)、结构化JSON报告+webhook告警、健康档案连续轮次/停滞检测/巡检频率自适应建议。当用户说'健康巡检'、'系统探测'、'发布门禁'、'健康评分'、'告警上报'、'停滞检测'时使用。"
metadata:
  requires:
    bins: ["python3", "bash"]
    pypi: []
  did_placeholder: "<YOUR_DID>"
  trace: "Ω₀⊂⊙∞⊂Ω"
---

# 体系健康巡检专家 v1.0

为任意企业系统提供**多探针探测 → 风险分级门禁 → 加权评分 → 结构化报告 → 健康档案**的一体化巡检能力：一次运行即得逐探针状态与总评分，任一严重探针失败即整体 FAIL 并拦截发布，连续轮次档案支持停滞检测与巡检频率自适应。

## 一、定位与能力边界

| 能力 | 说明 |
|------|------|
| 多探针探测 | HTTP 端点（状态码/延迟）、TCP 端口、日志错误计数、磁盘水位、数据新鲜度 |
| 风险分级门禁 | 每探针按 low/medium/high/critical 分级，critical 一票否决拦截发布 |
| 加权健康评分 | 探针通过率加权 0-100 分，逐探针权重可配 |
| 巡检报告 | 结构化 JSON（逐探针 status/detail/score + 总分 + 门禁结论）+ 可选 webhook |
| 健康档案 | 连续正常/异常轮次、停滞检测（评分连续 N 轮不提升告警）、自适应频率建议 |
| 定时化 | 一条命令跑全量巡检，正常静默一行/异常详细，crontab 友好 |

**边界**：本包聚焦系统健康探测、风险门禁、评分与告警；不做数据资产清单/账本/远端一致性对账（那是对账专家的领域）。探针全部参数化到 config，未配置的探针自动跳过。

## 二、快速路由

| 目标 | 命令 |
|------|------|
| 一键全量巡检（探测+评分+门禁+报告+档案） | `python3 scripts/health_check.py --config <config.json> --did <YOUR_DID>` |
| 巡检报告写入 JSON 文件 | `python3 scripts/health_check.py --config <config.json> --json-out report.json` |
| 健康档案快照查看 | `python3 scripts/profile_view.py --profile health_profile.json` |
| 异常时推送告警到 webhook | `python3 scripts/health_check.py --config <config.json> --webhook <WEBHOOK_URL>` |
| CI 发布门禁（FAIL 则非零退出） | `python3 scripts/health_check.py --config <config.json> || echo "发布拦截"` |

## 三、依赖

- bins：`python3`、`bash`
- pypi：无（纯 Python 标准库，HTTP 探测用 urllib）
- 全部本地执行，零付费依赖；webhook 上报为可选。

## 四、配置模板

见 `config.example.json`。变量清单：

| 变量 | 含义 | 示例 |
|------|------|------|
| `did` | 巡检确权身份 | `<YOUR_DID>` |
| `trace_symbol` | 溯源符号（可选） | `Ω₀⊂⊙∞⊂Ω` |
| `pass_threshold` | 评分及格线（>= 且无 high 失败 → PASS） | `80.0` |
| `fail_threshold` | 评分不及格线（< 则 FAIL） | `50.0` |
| `stall_threshold` | 评分停滞判定连续轮数 | `3` |
| `report_webhook` | 报告上报端点（空则不上报） | `<WEBHOOK_URL>` |
| `probes[]` | 探针数组，每探针含 name/type/weight/severity + 类型专属参数 | 见 config.example.json |

## 五、提示词模板

见 `prompt.template.md`，内置 4 个企业场景：发布前健康门禁 / 生产环境定时巡检告警 / 数据管道新鲜度监控 / 巡检频率自适应调优。

## 六、算子契约

见 `operator-contract.json`：OP-01 HTTP 探测、OP-02 TCP 端口、OP-03 日志扫描、OP-04 磁盘水位、OP-05 数据新鲜度、OP-06 风险门禁与评分、OP-07 健康档案与停滞检测。

## 七、自检清单

- [ ] `python3 scripts/health_check.py --config examples/config.json --did SELFCHECK-001` 退出码 0 且 `score==100.0` 且 `verdict==PASS`
- [ ] `python3 scripts/health_check.py --config examples/config.fail.json --did SELFCHECK-001` 退出码 1 且 `verdict==FAIL` 且 `critical_filled` 含 `etl-freshness`
- [ ] `python3 scripts/profile_view.py --profile examples/health_profile.json` 输出合法 JSON
- [ ] 泄露检查（按系列 SPEC §5 命令执行）→ 0 命中
- [ ] `operator-contract.json` 可被 `python3 -m json.tool` 解析

Ω₀⊂⊙∞⊂Ω ｜ DID 参数化 ｜ 体系健康巡检专家
