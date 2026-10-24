---
name: guofeng-ip-pipeline-orchestrator
version: 1.0.0
description: "国风IP创作流水线总控·专家团编排：把七位专家包编排为七阶段闭环流水线(剧本→关键帧→视频∥音频→合流→台账贯穿→锁档收尾)，一条配置驱动全流程，含跨包数据契约/免费额度总策略/失败降级规则/质量门禁/专家团矩阵。当用户说'流水线总控'、'专家团编排'、'全流程跑一部短剧'、'七阶段调度'、'编排我那几个国风包'、'一键生产国风短剧'时使用。零成本优先(免费通道置顶，付费仅兜底需人工审批)，严格遵循东方审美元法则与DID确权铁律。"
metadata:
  requires:
    bins: ["python3"]
  pypi: []
  optional_bins: ["jq", "ffmpeg"]
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---

# 国风IP创作流水线总控·专家团编排 v1.0

> 一令调七匠 · 七阶段闭环 · 免费优先 · 数据契约流转 · 质量门禁放行 · DID确权收尾

## 核心设计原则

1. **专家团而非单体**：本包不重复造轮子，只做**编排**——把家族内七位专家包（剧本/关键帧/视频/音频/合流/台账/锁档）按依赖图串联并行，单阶段能力下沉到对应专家包。
2. **一条配置驱动全流程**：`config/guofeng-ip-pipeline-orchestrator_config.json` 即批次编排单，内含阶段图/额度策略/降级规则/质量门禁/数据契约，一个配置跑完整部剧。
3. **免费额度总策略置顶**：text/image/video/audio 四类通道统一按 priority 表降级；付费通道永远在 priority 最高位并标注"需人工审批"，严禁自动扣费。
4. **跨包数据契约强约束**：分镜JSON字段在阶段间流转有固定映射（visual→关键帧、narration→配音、duration→合流时间轴、scene_id→台账主键、SHA256→锁档账本），字段缺失即中断，禁止虚构补全。
5. **质量门禁放行制**：任一阶段产物不过门禁（L0校验/视频≥4.5/音画同步<100ms/合流时长≈分镜总时长）即打回上一阶段重生成，不向锁档阶段放行不合格品。
6. **确权溯源闭环**：批次清单、调度计划、门禁回执统一携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`；人像/写真类仅本地锁档不对外。

## 阶段依赖图

```
                 ┌─────────────── ledger(贯穿全程，每阶段回写状态) ───────────────┐
                 │                                                                │
 [1 script 剧本大师] ──分镜JSON──┬──> [2 keyframe 关键帧画师] ──> [3 video 视频导演]──┐
                                 │                                                  │
                                 └──> [4 audio 音频工坊] ║并行║ ────────────────────┤
                                                                                    ▼
                                                          [5 merge 合流工坊] <── video+audio 就绪
                                                                    │
                                                                    ▼
                                                          [7 lock 锁档归档使] <── merge+ledger 闭环
```

- **串行链**：script → keyframe → video → merge → lock
- **并行**：audio 与 video 在分镜JSON就绪后**并行启动**（音频只需 narration，不依赖关键帧/视频）
- **贯穿**：ledger 从 script 阶段启动，每完成一个阶段即回写状态（pending→scripted→keyframed→videoed→audioed→merged→locked）
- **收尾**：lock 等待 merge 完成 + ledger 关闭后执行哈希入账

## 快速路由

| 目标 | 命令 |
|------|------|
| 输出阶段依赖与调度计划 | `python3 scripts/orchestrator.py plan` |
| 输出专家团矩阵总览 | `python3 scripts/orchestrator.py matrix` |
| 质量门禁检查（分镜+产物） | `python3 scripts/orchestrator.py gate --storyboard ./storyboard.json --artifacts ./artifacts.json` |
| 全流程一部短剧（人读编排单后逐包调度） | 按 `config` 批次编排单依次调用七位专家包 |
| 仅并行段（视频∥音频） | keyframe 完成后同时调 guofeng-ip-video-director 与 guofeng-ip-audio-studio |

## 专家团矩阵总览表

| 包名 | 中文名 | 能力 | 输入 | 输出 | 依赖 |
|------|--------|------|------|------|------|
| guofeng-ip-scriptmaster | 剧本大师 | 主题→东方叙事→结构化分镜JSON | 主题/集数/分镜数 | 分镜JSON(visual/narration/duration/scene_id) | — |
| guofeng-ip-keyframe-artist | 关键帧画师 | visual→绘图提示词→L0形态校验→五维评分 | 分镜JSON.visual | 关键帧图片+质量评分+L0校验 | script |
| guofeng-ip-video-director | 视频导演 | 关键帧→镜头运动→动态视频→防漂移 | 关键帧+分镜.camera | 9:16竖屏视频MP4+质量评分 | keyframe |
| guofeng-ip-audio-studio | 音频工坊 | narration→中文配音→BGM→三层混音→字幕 | 分镜JSON.narration | 配音mp3+BGM轨+SRT字幕 | script(∥video) |
| guofeng-ip-merge-studio | 合流工坊 | 视频+配音+BGM+字幕→FFmpeg合成成片 | 视频轨+音频轨 | 发布级MP4(音画同步<100ms) | video+audio |
| guofeng-ip-production-ledger | 生产台账管家 | 四表入账→状态流转→进度→哈希对账 | 各阶段产物 | 项目/分镜/资产/进度四表 | script(贯穿) |
| guofeng-ip-lock-archiver | 锁档归档使 | SHA256→Merkle清单→DID锚定→只读固化 | 成片+全资产 | HASH-LEDGER.csv+锁档凭证 | merge+ledger |

## 跨包数据契约（分镜JSON字段流转）

| 字段 | 来源阶段 | 流向阶段 | 用途 |
|------|----------|----------|------|
| `scenes[].visual` | script | keyframe | 直接转绘图提示词输入 |
| `scenes[].narration` | script | audio | 直接转配音文本输入 |
| `scenes[].duration` | script | merge | 合流时间轴对齐基准 |
| `scenes[].scene_id` | script | ledger | 分镜表主键，跨阶段关联 |
| 各产物 `SHA256` | keyframe/video/audio/merge | lock | 实算哈希入 HASH-LEDGER 账本 |

> 契约原则：下游只认上游字段，缺失即中断报错，**禁止虚构补全**。

## 免费额度总策略（全局通道优先级表）

| 类别 | P0 免费 | P1 免费额度 | P2 兜底 |
|------|---------|-------------|---------|
| text 文本 | 豆包APP会话内置 | 火山方舟 doubao-seed-lite 免费额度 | 智普 glm-4-flash 免费 / 付费API(需审批) |
| image 图像 | 豆包APP内置 image_gen | seedream-4-5 免费额度 | 付费API(需审批) |
| video 视频 | 豆包APP内置图生视频 | seedance-2-0 免费额度 | 付费API(需审批+额度最小化) |
| audio 音频 | 豆包APP内置文生音频 | edge-tts 本地免费神经配音 | 付费API(需审批) |

> 视频额度最贵，**严禁任何付费消耗**；付费通道仅在免费通道全部不可用时兜底，且必须人工审批。

## 失败降级规则

1. **通道限额**：当前通道额度耗尽 → 按 `config.quota_strategy.<类别>` priority 升序自动切下一通道。
2. **重试**：单通道失败最多重试 **3 次**。
3. **低质升级**：产物质量低于门禁阈值 → 升级到更高优先级通道重生成。
4. **降级上限**：累计降级最多 **3 次**，超过即显式标记 `failed` 中断流水线，禁止放行不合格品。
5. **回执**：每次降级在结构化JSON回执记录 `channel_used` + `status: degraded`。

## 质量门禁

| 门禁项 | 阈值 | 不通过处置 |
|--------|------|------------|
| 关键帧 L0-MORPH-001 形态定序校验 | 必须通过 | 打回 keyframe 重生成 |
| 视频五维质量评分 | ≥ 4.5/5 | 打回 video 重生成/升级通道 |
| 音画同步偏差 | < 100ms | 打回 merge 时间轴重对齐 |
| 合流成片时长 | ≈ 分镜总时长（±0.5s） | 打回 merge 重合成 |
| 角色形象一致性 | 与关键帧母版零漂移 | 打回 video 以母版为锚重生成 |

门禁检查脚本：`python3 scripts/orchestrator.py gate --storyboard <分镜JSON> --artifacts <产物清单JSON>`；产物清单字段 `video_quality_score` / `av_sync_ms` / `merged_duration_sec` / `keyframe_l0_pass`。

## 配置模板

`config/guofeng-ip-pipeline-orchestrator_config.json` 为完整批次编排单，含：project（项目/主题/quality_target=4.5/max_retry=3/max_degrade=3）、stage_graph（七阶段run模式+depends_on）、quota_strategy（text/image/video/audio 四类通道优先级）、degrade_rules、quality_gates、data_contract、did、trace_symbol、photo_policy。字段含义见文件内注释。

## 提示词模板

`templates/prompts.json` 含五张：批次编排单头、质量门禁清单、降级裁决、东方审美铁律、结构化JSON回执格式。

## 输入/输出规范

- **输入**：主题（`--topic`）、项目名、分镜JSON（来自剧本大师）、各阶段产物清单。
- **输出**：结构化JSON回执，固定字段 `{project, stage, status, channel_used, quality_score, artifacts, sha256, did, trace}`；批次清单带 DID-BR-000002 + Ω₀⊂⊙∞⊂Ω。
- **错误处理**：通道限额自动降级、重试3次、低质升级、最大降级3次；超限显式 failed 中断，禁止虚构补全。

## 依赖清单（独立安装）

- 必选：Python 3.8+（`scripts/orchestrator.py` 仅用标准库，零 pip）。
- 可选：`jq`（JSON 处理）、`ffmpeg`（合流阶段，实际由合流工坊包承担）。
- 编排对象为本家族七位兄弟包（同目录 `guofeng-ip-*`）；本包自身不硬编码任何兄弟包内部路径，调用时按目录名发现。
- 无内部路径硬编码；通道配置经 `config/*.json` + 环境变量（`DOUBAO_API_KEY`/`ZHIPU_API_KEY` 等）注入。

## 确权与溯源

- 批次清单、调度计划、门禁回执统一携带 `did: DID-BR-000002` 与 `trace: Ω₀⊂⊙∞⊂Ω`。
- 流水线收尾由 guofeng-ip-lock-archiver 对全部产物实算 SHA256 入 HASH-LEDGER；人像/写真类仅本地锁档，不推公开湖、不对外展示。
- 建议批次命名：`guofeng-ip-<project>-<YYYYMMDD>`。

Ω₀⊂⊙∞⊂Ω｜国风IP创作流水线总控·专家团编排 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
