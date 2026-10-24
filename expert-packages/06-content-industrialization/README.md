# 内容工业化生产专家（Content Industrialization Expert）

面向外部企业与开发者的通用内容生产流水线能力包，把"企划→剧本→视觉→音频→合成→质检→归档"七阶段做成可编排、可追溯、可门禁的工程化流水线。零云成本、零内部依赖、纯本地 JSON 台账。

## 能做什么
- **阶段看板状态机**：七阶段任意前进/回退，每个项目一张进度看板。
- **资产台账**：剧本/分镜/画面/音频/字幕/成片统一登记，带版本/负责人/依赖/SHA256 锚定。
- **声画合一校验**：音视频时长对齐、字幕 cue 不重叠且可读时长充足；ffprobe 缺失自动降级为声明值模式。
- **免费额度预算管控**：多家生成 API 日额度本地记账、剩余预警、免费优先调度排序。
- **稳态治理**：剧本/角色设定/风格基准哈希锚定，变更必须版本升级而非覆盖。
- **质检门禁**：成片归档前六道硬检查，任一未过即 BLOCK_ARCHIVE。

## 适用场景
MCN/短视频团队排产、短剧/动画工作室流水线治理、品牌内容工厂质检、多供应商免费额度调度、关键资产防漂移审计。

## 安装
```bash
# 依赖：python3（标准库）；ffprobe 可选（未装时声画校验自动降级）
git clone <本仓库> && cd 06-content-industrialization
```

## 接入（3 步）
1. 复制 `config.example.json` 为 `config.json`，填入 `ledger_path` / `manifest_path` / `quota_state_path` 与 `did`。
2. 登记资产并推进阶段：
   ```bash
   python3 scripts/pipeline_board.py --ledger ledger.jsonl --register \
       --asset-id SCRIPT-001 --type script --stage SCRIPT --version v1.0 --owner alice
   python3 scripts/pipeline_board.py --ledger ledger.jsonl --advance --to QC
   ```
3. 归档前跑质检门禁（未过禁止归档）：
   ```bash
   python3 scripts/qc_gate.py --ledger ledger.jsonl --manifest manifest.json
   ```

## 产物
- `ledger.jsonl`：append-only 资产台账 + 阶段事件流。
- `manifest.json`：成片清单（视频/音频时长 + 字幕 cue）。
- `quota.json`：各供应商日额度剩余状态。
- 看板 / 校验 / 门禁结果：结构化 JSON，可直接进 CI 或定时任务。

## 自检
```bash
bash examples/run_demo.sh   # 一键跑完登记→声画校验→额度→门禁→看板
```

## 许可与溯源
Apache-2.0。能力提炼自生产级内容流水线工程经验（DID-BR-000002 · Ω₀⊂⊙∞⊂Ω），对外使用时 DID 由采用方参数化配置。
