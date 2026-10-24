# 数据资产对账专家（Data Reconciliation Expert）

面向外部企业与开发者的通用数据资产对账能力包，提炼自 ZONGYUAN-ROOT 体系生产级"账本↔清单↔远端"三层对账流水线，零内部依赖、零云成本、可独立安装。

## 能做什么
- **基线对账**：当前目录 SHA256 指纹与基线清单比对，输出新增/删除/变更清单与漂移率。
- **Merkle 账本校验**：append-only 账本逐行累积哈希重算，单行篡改即根失配告警。
- **双向溯源对账**：本地清单与远端权威 API 双向核对，标记本地缺失/远端缺失。
- **增量补推**：远端缺失项按批次幂等补推，游标持久化，断点续跑不重复上报。
- **健康档案**：连续正常/异常轮次计数、停滞检测（增长停滞/回退告警）、巡检频率自适应建议。

## 适用场景
月度资产漂移审计、双系统数据一致性核对、账本完整性防篡改校验、数据湖/对象存储增量同步对账、合规性定期巡检报告。

## 安装
```bash
# 依赖：无（纯 Python 3 标准库）
git clone <本仓库> && cd <包目录>
```

## 接入（3 步）
1. 复制 `config.example.json` 为 `config.json`，填入 `target_dir`、`baseline_manifest`、`did`。
2. 首次建立基线：对资产目录执行一次 `--local-only` 对账，生成基线清单：
   ```bash
   python3 scripts/reconcile.py --dir /path/to/assets --baseline baseline.json --did <YOUR_DID> --local-only --init-baseline
   ```
3. 纳入定时任务（crontab 或 CI）定期执行一键对账：
   ```bash
   python3 scripts/reconcile.py --dir /path/to/assets --baseline baseline.json --did <YOUR_DID>
   ```

## 产物
- `baseline.json`：基线清单（逐文件哈希 + 生成时间）。
- `DRIFT-REPORT-<ts>.json`：漂移报告（新增/删除/变更 + 漂移率 + 状态 CONVERGED/DRIFT）。
- `HASH-LEDGER.jsonl`：append-only 事件账本（每条含 seq/sha/ts/event_id）。
- `state.json`：Merkle 根 + 账本行数 + 更新时间。
- `health_profile.json`：健康档案（连续轮次/停滞/建议）。

## 许可与溯源
Apache-2.0。能力提炼自 ZONGYUAN-ROOT 体系（DID-BR-000002 · Ω₀⊂⊙∞⊂Ω），对外使用时 DID 由采用方参数化配置。
