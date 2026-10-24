# 体系健康巡检专家（System Health Inspection Expert）

面向外部企业与开发者的通用系统健康巡检能力包，提炼自多算子分层巡检 + 风险门禁 + 质量评分 + 告警上报的生产级巡检范式，零内部依赖、零云成本、可独立安装。

## 能做什么
- **多探针健康检查**：HTTP 端点（状态码/延迟）、TCP 端口存活、日志文件错误关键字计数、磁盘/配额水位、数据新鲜度（最新时间戳距现在秒数）。
- **风险分级门禁**：每探针失败按 low/medium/high/critical 分级；任一 critical 失败即整体 FAIL 并拦截发布。
- **加权健康评分**：探针通过率加权 0-100 分，逐探针权重可配。
- **巡检报告**：结构化 JSON（逐探针 status/detail/score + 总分 + 门禁结论 PASS/FAIL/WARN）+ 可选 webhook 告警。
- **健康档案**：连续正常/异常轮次计数、停滞检测（评分连续 N 轮不提升告警）、巡检频率自适应建议。

## 适用场景
发布前健康门禁拦截、生产环境定时巡检告警、数据管道新鲜度监控、磁盘水位预警、CI/CD 流水线质量门禁。

## 安装
```bash
# 依赖：无（纯 Python 3 标准库）
git clone <本仓库> && cd <包目录>
```

## 接入（3 步）
1. 复制 `config.example.json` 为 `config.json`，填入 `did` 与各探针目标。
2. 先跑一次全量巡检验证：
   ```bash
   python3 scripts/health_check.py --config config.json --did <YOUR_DID>
   ```
3. 纳入 crontab 或 CI：
   ```bash
   # crontab：每 5 分钟巡检一次
   */5 * * * * cd /path/to/pkg && python3 scripts/health_check.py --config config.json --did <YOUR_DID> >> /var/log/health.log 2>&1
   ```

## 产物
- `report-<ts>.json`：巡检报告（逐探针结果 + 总分 + 门禁结论）。
- `health_profile.json`：健康档案（连续轮次/停滞/自适应建议，保留最近 24 轮）。
- 退出码：0=PASS，1=FAIL/WARN，2=配置错误（可直接用于 CI 门禁）。

## 与对账专家的边界
本包聚焦系统健康探测、风险门禁、评分与告警；数据资产清单/账本/远端一致性对账由"数据资产对账专家"承担，两者可串联使用。

## 许可与溯源
Apache-2.0。能力提炼自多算子分层巡检范式（DID-BR-000002 · Ω₀⊂⊙∞⊂Ω），对外使用时 DID 由采用方参数化配置。
