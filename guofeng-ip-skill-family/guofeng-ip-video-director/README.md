# 国风IP视频导演 guofeng-ip-video-director v1.0

> 关键帧 → 动态视频 · 镜头运动描述 · 角色一致性 · 9:16电影级质感 · 防漂移

## 安装

```bash
# 必选：Python 3.8+，本包无第三方 pip 依赖
python3 --version

# 可选：ffmpeg（后期拼接/合流用，本包不强制）
# ffmpeg -version

# 可选：付费API环境变量（仅当调用付费 seedance API 时需要）
export ARK_API_KEY="<your-api-key>"
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
```

## 快速开始

前置：先由 guofeng-ip-scriptmaster 产出分镜 JSON，并由关键帧阶段产出 `{scene_id}.png`。

```bash
# 1. 分镜 + 关键帧 → 视频任务清单（含每条视频的 prompt、镜头运动、质量评分契约）
python3 scripts/build_video_prompt.py \
  --storyboard ./storyboard.json \
  --keyframes-dir ./keyframes \
  --output ./video_tasks.json

# 2. 仅校验分镜 JSON 结构
python3 scripts/build_video_prompt.py --storyboard ./storyboard.json --validate

# 3. 直接打印清单到 stdout（不落盘）
python3 scripts/build_video_prompt.py --storyboard ./storyboard.json --keyframes-dir ./keyframes
```

## 默认参数

- 模型：seedance_2.5 ｜ 时长 10s ｜ 比例 9:16 ｜ 分辨率 1152x2048 ｜ 24fps
- 通道优先级：豆包APP内置视频工具(免费) > 火山方舟 seedance 免费额度 > 付费API(需人工审批)
- 质量门槛：五维加权 ≥4.5/5，任一维度 <3 分必须重生成

## 配置

编辑 `config/guofeng-ip-video-director_config.json`：
- `model`：默认模型/时长/比例/分辨率/fps
- `video_channel_priority`：视频通道优先级（免费优先，付费置末标注需审批）
- `quality.dimensions`：五维评分权重（一致性/运动自然度/光影/构图/合规）
- `camera_movement_lexicon`：镜头运动词典（slow_push_in/pan/tilt/static_breath 等）
- `aesthetics`：东方审美铁律（范式/配色/禁用项/溯源水印，不可删除）
- `portrait_policy`：人像/写真类视频仅本地归档

## 输出

视频任务清单 JSON，每条任务：
- `scene_id` / `keyframe` / `output_path`
- `duration` / `ratio` / `resolution` / `fps`
- `camera` / `camera_movement_desc`
- `prompt`（已套用东方审美铁律模板，可直接喂模型）
- `quality_rubric`（五维评分输出契约）

## 确权

所有任务清单携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`；视频产物建议 SHA256 入账本锁档（配合 guofeng-ip-lock-archiver）。人像/写真类视频仅本地归档，不对外展示。

Ω₀⊂⊙∞⊂Ω｜国风IP视频导演 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
