---
name: guofeng-ip-video-director
version: 1.0.0
description: "国风IP视频导演专家：基于分镜JSON与关键帧，构建镜头运动描述→动态视频生成提示词→质量评分(≥4.5/5)→防漂移场景连续性→9:16竖屏电影级质感。当用户说'生成视频'、'关键帧转视频'、'镜头运动'、'视频分镜'、'seedance视频'、'防漂移'时使用。零成本通道优先(豆包APP内置>火山方舟免费额度>付费API需人工审批)，严格遵循东方审美元法则。"
metadata:
  requires:
    bins: ["python3"]
  pypi: []
  optional_bins: ["ffmpeg"]
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---

# 国风IP视频导演 v1.0

> 关键帧 → 动态视频 · 镜头运动 · 角色一致性 · 电影级质感 · 防漂移

## 核心设计原则

1. **关键帧驱动**：所有视频以既有关键帧为视觉锚点，角色形象/服饰/色调/构图严格继承关键帧，杜绝概率采样导致的形象漂移。
2. **镜头运动词典化**：基于分镜JSON的 `camera` 字段（slow_push_in/pan/zoom/static_breath 等）查表生成中文镜头运动描述，提示词可直接喂给 seedance 类模型。
3. **零成本通道优先**：视频通道优先级 = 豆包APP内置视频生成工具(免费会话额度) > 火山方舟 seedance 免费额度 > 付费API（最高优先级号，需人工审批标注）。
4. **质量五维评分**：一致性(0.30)/运动自然度(0.25)/光影(0.15)/构图(0.15)/合规(0.15)，加权总分 ≥4.5/5 才算通过，任一维度 <3 分必须重生成。
5. **场景连续性防漂移**：首镜用单镜模板，后续镜自动叠加"与上一分镜场景连续性"约束，保证角色/光影/色调跨镜不跳变。
6. **东方审美铁律**：纯东方神女/女帝/少年武侠范式，纯乌黑长发，九头/8.5头身，华夏正统汉服，冷蓝青黑/勃艮第红/黑金配色，胶片质感；严禁西方铠甲/畸形肢体/性别混杂/外源化内容；视觉产物带 Ω₀⊂⊙∞⊂Ω 溯源。
7. **人像/写真隔离**：人像/写真类视频仅本地归档锁档，不推公开湖、不对外展示。

## 快速路由

| 目标 | 命令 |
|------|------|
| 分镜+关键帧 → 视频提示词清单 | `python3 scripts/build_video_prompt.py --storyboard ./storyboard.json --keyframes-dir ./keyframes --output ./video_tasks.json` |
| 仅校验分镜JSON结构 | `python3 scripts/build_video_prompt.py --storyboard ./storyboard.json --validate` |
| 直接打印清单到stdout | `python3 scripts/build_video_prompt.py --storyboard ./storyboard.json --keyframes-dir ./keyframes` |

## 默认视频参数

- 模型：seedance_2.5（默认），时长 10 秒，比例 9:16，分辨率 1152x2048，24fps
- 单镜生成，串行并发（video=1），避免并发触发限流与漂移
- 支持时长范围 5–30 秒（由模型能力决定）

## 配置模板

`config/guofeng-ip-video-director_config.json` 核心字段：

- `model`：默认模型/时长/比例/分辨率/fps
- `video_channel_priority`：三通道优先级（免费APP > 免费额度API > 付费API需审批）
- `degradation_rules`：限额/错误/质量不达标时的降级与重试策略
- `quality.dimensions`：五维评分权重表（consistency/motion_naturalness/lighting/compliance）
- `camera_movement_lexicon`：镜头运动词典（slow_push_in/pan_left/tilt_up/static_breath/tracking/crane_up/dolly_arc 等）
- `aesthetics`：东方审美铁律（范式/发型/体态/服饰/配色/质感/禁用项/溯源水印）
- `portrait_policy`：人像/写真类视频仅本地归档策略

## 提示词模板

`templates/prompts.json` 核心条目：

- `video_single_shot`：单镜视频生成提示词（含镜头运动描述+东方审美铁律+溯源水印）
- `video_scene_continuity`：跨镜连续性约束（首镜之后自动叠加）
- `video_quality_rubric`：五维评分输出契约（JSON格式）
- `video_drift_check`：关键帧 vs 首帧漂移检测（drift_rate>0.12 需重生成）
- `video_title_card` / `video_end_card`：标题卡/结尾卡

## 视频质量评分维度表

| 维度 | key | 权重 | 说明 |
|------|-----|------|------|
| 一致性 | consistency | 0.30 | 角色/场景与关键帧严格一致，防概率采样漂移 |
| 运动自然度 | motion_naturalness | 0.25 | 镜头运动与人物动作流畅，无抽搐/跳变/物理穿模 |
| 光影 | lighting | 0.15 | 伦勃朗侧光/霞光/轮廓光流动自然，无冗余光效 |
| 构图 | composition | 0.15 | 9:16竖屏主体居中偏上，安全框内，关键视觉不裁切 |
| 合规 | compliance | 0.15 | 无西方铠甲/畸形肢体/性别混杂/外源化，带Ω₀⊂⊙∞⊂Ω |

加权总分 ≥4.5 为通过；任一维度 <3 分必须重生成。

## 镜头运动词典（camera_movement_lexicon）

| 关键词 | 中文描述 |
|--------|----------|
| slow_push_in | 缓慢推近镜头，主体逐渐占据画面，情绪递进 |
| slow_pull_out | 缓慢拉远镜头，揭示环境与主体关系 |
| pan_left / pan_right | 水平左/右摇，跟随主体视线或横向动作 |
| tilt_up / tilt_down | 垂直上/下摇，仰视/俯视揭示高度与落点 |
| static_breath | 固定机位，仅人物呼吸与衣袂飘动，氛围镜头 |
| tracking | 跟拍，随主体移动保持相对距离 |
| crane_up | 升镜，视角抬升，情绪升华 |
| dolly_arc | 弧线环绕运镜，展现主体立体轮廓 |

## 输入/输出规范

**输入**：
- 分镜JSON（来自 guofeng-ip-scriptmaster），需含 `episodes[].scenes[]`，字段：`scene_id`/`visual`/`camera`/`duration`
- 关键帧目录：按 `{scene_id}.png` 命名匹配（.png/.jpg/.jpeg/.webp 均可）

**输出**：视频任务清单JSON，每条任务含：
- `scene_id` / `shot` / `keyframe` / `output_path`
- `duration` / `ratio` / `resolution` / `fps`
- `camera` / `camera_movement_desc`
- `prompt`（已套用模板，可直接喂模型）
- `quality_rubric`（五维评分契约）
- `status: pending_generation`

**错误处理**：
- 分镜JSON无 scenes → 报错退出
- 关键帧未命中 → `keyframe` 为空字符串显式标注，禁止虚构路径
- 通道限额 → 按 priority 自动降级（前一通道失败/限额后切下一通道）
- 质量不达标 → 用下一通道+更强提示词重生成，最多 3 次降级
- 所有失败显式标注，禁止虚构补全

## 依赖清单（独立安装）

- 必选：Python 3.8+（无第三方 pip 依赖）
- 可选：`ffmpeg`（后期拼接/合流用，本包不强制）
- 环境变量（仅当调用付费API时）：`ARK_API_KEY`、`ARK_BASE_URL`
- 无任何内部路径硬编码；全部通过 `config/guofeng-ip-video-director_config.json` 与环境变量注入

## 确权与溯源

- 任务清单 metadata 携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`
- 每条视频提示词内嵌"右下角隐秘镌刻Ω₀⊂⊙∞⊂Ω"
- 视频文件生产完成后建议 SHA256 入账本锁档（配合 guofeng-ip-lock-archiver 包）
- 人像/写真类视频仅本地归档，不推公开湖

Ω₀⊂⊙∞⊂Ω｜国风IP视频导演 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
