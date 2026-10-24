# 飞书协同治理专家（Feishu Governance Expert）

面向外部企业与开发者的通用飞书协同治理能力包，提炼自生产级"Wiki / Drive / Base / Markdown 文本库"四端同步流水线，零内部依赖、零云成本、可独立安装。

## 能做什么
- **本地扫描**：递归 Markdown 文本库，自动提取标题、标签、SHA256、mtime。
- **四端比对**：以文档标题为主键，对齐本地与 Wiki/Drive/Base 三端，输出待推 / 待归档 / 冲突三类清单。
- **统一索引**：by_title / by_tag / by_channel 三维聚合，生成可检索资产地图。
- **Base 对账**：本地清单与多维表格记录双向核对，标记待补录、待归档、已漂移。
- **断点续跑**：增量游标落 state.json，重复执行不重复推送已收敛项。
- **冲突裁决**：同标题双端修改时按 newer_wins / local_wins / remote_wins 策略显式裁决。

## 适用场景
企业知识库向飞书 Wiki 一键归档、多维表格资产注册表定期巡检、跨端文档漂移检测、合规审计前的文档一致性核对、新人入职时的资产地图构建。

## 安装
```bash
# 依赖：无（纯 Python 3 标准库）
git clone <本仓库> && cd 05-feishu-governance
```

## 接入（3 步）
1. 复制 `config.example.json` 为 `config.json`，填入 `local_md_dir`、`did`；如暂不接真实飞书，`lark` 字段留空即可走模拟模式。
2. 跑一次 dry-run 演算，确认三桶清单符合预期：
   ```bash
   python3 scripts/sync_govern.py --config config.json --local-dir /path/to/md \
       --remote-sim sim_remote_state.json --dry-run
   ```
3. 纳入定时任务（crontab/CI）定期对账并生成索引：
   ```bash
   python3 scripts/base_reconcile.py --local-inventory inv.json --base-records base.json
   python3 scripts/index_build.py --local-inventory inv.json --remote-sim sim.json --out index.json
   ```

## 产物
- `SYNC-REPORT.json`：四端双向比对报告（push/pull/conflict + drift + status）。
- `BASE-RECON-REPORT.json`：Base 注册表对账报告（matched/待补录/待归档/已漂移）。
- `index.json`：统一资产索引（by_title/by_tag/by_channel）。
- `sync_state.json`：增量游标（已处理 title 集合 + 最近一轮状态）。

## 许可与溯源
Apache-2.0。能力提炼自生产级飞书四端同步流水线（DID-BR-000002 · Ω₀⊂⊙∞⊂Ω），对外使用时 DID 与 lark 凭证由采用方参数化配置。
