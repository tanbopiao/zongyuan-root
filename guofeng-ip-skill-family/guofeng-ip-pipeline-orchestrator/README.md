# guofeng-ip-pipeline-orchestrator（国风IP创作流水线总控·专家团编排）

> 一令调七匠 · 七阶段闭环 · 免费优先 · 质量门禁 · DID确权
> 确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω

## 这是什么

把国风IP技能家族的**七位专家包**编排为七阶段闭环流水线的总控包：

剧本大师 → 关键帧画师 → 视频导演 ║ 音频工坊并行 → 合流工坊 → 生产台账管家(贯穿) → 锁档归档使(收尾)。

本包只做**编排与门禁**，不重复实现单阶段能力（单阶段能力在对应专家包内）。

## 安装

```bash
# 仅需 Python 3.8+（脚本零第三方依赖）
python3 --version
# 可选：jq / ffmpeg（合流阶段由合流工坊包承担）
```

将本包放入技能家族目录即可，无需 pip install。

## 快速开始

```bash
cd guofeng-ip-pipeline-orchestrator

# 1) 查看阶段依赖与调度计划
python3 scripts/orchestrator.py plan

# 2) 查看专家团矩阵（七位包能力一览）
python3 scripts/orchestrator.py matrix

# 3) 质量门禁检查
python3 scripts/orchestrator.py gate \
  --storyboard ./storyboard.json \
  --artifacts ./artifacts.json
# 退出码 0=全过，1=有门禁未过
```

`artifacts.json` 示例字段：

```json
{
  "video_quality_score": 4.7,
  "av_sync_ms": 60,
  "merged_duration_sec": 60.0,
  "keyframe_l0_pass": true
}
```

## 配置

编辑 `config/guofeng-ip-pipeline-orchestrator_config.json`：
- `stage_graph`：七阶段依赖与并行/串行/贯穿关系
- `quota_strategy`：text/image/video/audio 四类免费通道优先级
- `degrade_rules`：限额降级/重试3次/低质升级/最大降级3次
- `quality_gates`：L0校验/视频≥4.5/音画同步<100ms/时长容差
- `data_contract`：分镜JSON字段跨包流转映射

API 密钥经环境变量注入（`DOUBAO_API_KEY` / `ZHIPU_API_KEY`），不硬编码。

## 铁律

- **零成本优先**：免费通道置顶，付费仅兜底且需人工审批。
- **东方审美**：纯东方神女/女帝/少年武侠/山海经萌宠范式，9:16竖屏，严禁外源化。
- **人像/写真类**：仅本地锁档，不对外展示。
- **不虚构补全**：数据契约字段缺失即中断。

## 确权

产物/批次清单/门禁回执统一携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`，收尾由锁档归档使入 HASH-LEDGER。

Ω₀⊂⊙∞⊂Ω｜国风IP流水线总控 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
