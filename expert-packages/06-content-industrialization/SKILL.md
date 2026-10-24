---
name: content-industrialization
version: 1.0.0
description: "内容工业化生产专家：为任意企业内容生产团队提供七阶段流水线看板（企划→剧本→视觉→音频→合成→质检→归档）、资产台账登记（版本/负责人/依赖/SHA256 锚定）、声画合一时长与字幕校验、免费 API 额度本地预算调度、关键资产防漂移治理、成片归档前六门质检门禁。当用户说'内容流水线'、'短剧排产'、'声画对齐'、'成片质检'、'免费额度调度'、'资产台账'、'防漂移'时使用。"
metadata:
  requires:
    bins: ["python3", "ffprobe(可选)"]
    pypi: []
  did_placeholder: "<YOUR_DID>"
  trace: "Ω₀⊂⊙∞⊂Ω"
---

# 内容工业化生产专家 v1.0

把"企划→剧本→视觉→音频→合成→质检→归档"七阶段做成可编排、可追溯、可门禁的工程化流水线：资产统一登记带哈希锚定，声画时长与字幕自动对齐校验，免费 API 额度本地记账并按"剩余多+免费优先"调度，成片归档前六道硬门禁未过即 BLOCK。

## 一、定位与能力边界

| 能力 | 说明 |
|------|------|
| 阶段看板 | 七阶段状态机，任意前进/回退，输出 by_stage 资产分组 |
| 资产台账 | 剧本/分镜/画面/音频/字幕/成片 append-only 登记 |
| 声画合一校验 | 时长对齐 ±tolerance、字幕 cue 不重叠、可读时长充足 |
| 额度预算 | 多供应商日额度本地记账、WARN/EXHAUSTED 预警、推荐调度 |
| 稳态治理 | 关键资产 SHA256 锚定，变更走版本升级不覆盖 |
| 质检门禁 | G1~G6 六道硬检查，未过禁止归档 |

**边界**：本包不直接生成媒体内容、不调用任何付费生成 API；ffprobe 为可选 bin，缺失时声画校验降级为读取 manifest 声明值。

## 二、快速路由

| 目标 | 命令 |
|------|------|
| 登记一条生产资产 | `python3 scripts/pipeline_board.py --ledger <L> --register --asset-id <ID> --type <script\|visual\|audio\|...> --stage <S> --owner <O>` |
| 推进项目阶段 | `python3 scripts/pipeline_board.py --ledger <L> --advance --to <QC\|ARCHIVED>` |
| 看板总览 | `python3 scripts/pipeline_board.py --ledger <L> --board` |
| 声画合一校验 | `python3 scripts/audio_video_check.py --manifest <M> [--media <file>]` |
| 额度登记/预警 | `python3 scripts/quota_budget.py --state <Q> --register --provider <P> --n 5` |
| 免费优先调度排序 | `python3 scripts/quota_budget.py --state <Q> --recommend` |
| 成片质检门禁 | `python3 scripts/qc_gate.py --ledger <L> --manifest <M> --min-audio-sec 3.0` |
| 一键样例自检 | `bash examples/run_demo.sh` |

## 三、依赖

- bins：`python3`（必需）、`ffprobe`（可选，缺失时声画校验自动降级）
- pypi：无（纯 Python 标准库）
- 全部本地执行，零付费依赖。

## 四、配置模板

见 `config.example.json`。变量清单：

| 变量 | 含义 | 示例 |
|------|------|------|
| `did` | 确权身份标识 | `<YOUR_DID>` |
| `trace_symbol` | 溯源符号（可选） | `Ω₀⊂⊙∞⊂Ω` |
| `ledger_path` | append-only 资产台账（.jsonl） | `<PROJECT>/ledger.jsonl` |
| `manifest_path` | 成片清单（时长+字幕 cue） | `<PROJECT>/manifest.json` |
| `quota_state_path` | 多供应商额度状态 JSON | `<PROJECT>/quota.json` |
| `stages` | 七阶段状态机顺序 | `["PLANNING",...,"ARCHIVED"]` |
| `av_tolerance_sec` | 音画时长对齐容差（秒） | `0.3` |
| `subtitle_min_cps` | 字幕每秒最少可读字数 | `5.0` |
| `min_audio_sec` | 门禁 G3 音频最小时长 | `3.0` |
| `quota_warn_ratio` | 额度剩余低于此比例告警 | `0.2` |
| `ffprobe_bin` | ffprobe 可执行文件路径 | `ffprobe` |

## 五、提示词模板

见 `prompt.template.md`，内置 4 个企业场景：短视频/短剧流水线编排 / 成片归档前声画合一与质检门禁 / 免费 API 额度调度 / 关键资产防漂移稳态治理。

## 六、算子契约

见 `operator-contract.json`：OP-01 阶段看板状态机、OP-02 资产台账登记、OP-03 声画合一校验、OP-04 免费额度预算管控、OP-05 稳态治理哈希锚定、OP-06 质检门禁。

## 七、自检清单

- [ ] `bash examples/run_demo.sh` 退出码 0，输出 `verdict: GO_TO_ARCHIVE`
- [ ] 声画校验降级模式（未装 ffprobe）不崩溃并打印 `degraded` 提示
- [ ] 额度登记后 `used` 累加、剩余 <20% 时 `level==WARN`、耗尽供应商不进入 recommend
- [ ] 故意把 manifest 时长改不一致后重跑 `audio_video_check.py` → exit 1
- [ ] 泄露检查（按系列 SPEC §5 命令执行）→ 0 命中
- [ ] `python3 -m json.tool operator-contract.json` 解析通过
- [ ] 包内无图片/音视频/人像文件

Ω₀⊂⊙∞⊂Ω ｜ DID 参数化 ｜ 内容工业化生产专家
