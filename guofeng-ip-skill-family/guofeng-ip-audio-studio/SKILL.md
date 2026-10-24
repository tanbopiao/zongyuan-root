---
name: guofeng-ip-audio-studio
version: 1.0.0
description: "国风IP音频工坊：分镜JSON→中文配音(沉稳女声/史诗旁白)→东方古风BGM情绪匹配→三层混音(环境音0.15+BGM0.35人声避让+旁白1.0动态压缩)→SRT字幕轨(单行≤16字/底部安全区)→mp3/wav音轨输出。当用户说'配音'、'音频生成'、'BGM匹配'、'混音'、'字幕轨'、'音画同步'、'TTS旁白'时使用。零成本优先(豆包APP内置>edge-tts免费>付费API需审批)，严格遵循东方审美铁律。"
metadata:
  requires:
    bins: ["python3"]
  pypi: []
  optional_bins: ["ffmpeg"]
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---

# 国风IP音频工坊 v1.0

> 华夏声韵 · 东方古风管弦 · 三层混音 · 音画同频百毫秒

## 核心设计原则

1. **纯东方声韵**：中文配音（默认zh-CN-XiaoxiaoNeural沉稳女声，备选zh-CN-YunjianNeural史诗战斗旁白），东方古风BGM（古琴/古筝/编钟/弦乐），严禁外文配音/西式管弦/电子/异质音乐风格。
2. **三层混音稳态架构**：环境音底层(音量0.15) + BGM中层(音量0.35，人声避让duck_factor=0.3，旁白结束200ms恢复) + 旁白顶层(音量1.0，动态压缩)，保证人声绝不被BGM淹没。
3. **零成本通道优先**：豆包APP内置text_to_audio(免费会话额度) > 服务器edge-tts(完全免费) > 付费API(最高优先级号+需人工审批标注)。edge-tts配音零成本。
4. **字幕不遮主体**：SRT字幕轨单行≤16字、最小显示800ms、底部安全区、规避玄女主体/金赤双翼/关键符文。
5. **音画同频**：音画同步误差<100ms；停顿标记规范（0.3s停顿）（0.5s停顿）（1.0s停顿）匹配镜头呼吸节奏。

## 快速路由

| 目标 | 命令 |
|------|------|
| 分镜JSON→四轨生产计划 | `python3 scripts/build_audio_plan.py --storyboard ./storyboard.json --output ./audio_plan.json` |
| 校验既有音频计划 | `python3 scripts/build_audio_plan.py --validate ./audio_plan.json` |
| 查看配音通道优先级 | 见 `config/guofeng-ip-audio-studio_config.json` 的 audio_channel_priority |
| BGM情绪映射查询 | tension→dark_low_drone / epic→grand_orchestral / sorrow→melancholy_zither / awakening→rising_harp_strings |

## 配置模板

`config/guofeng-ip-audio-studio_config.json` 全文见同目录文件，关键字段：

- **audio_channel_priority**：音频通道优先级数组，priority 数字越小越优先；免费通道置顶，付费API priority=9 并标注"需人工审批"。
- **voice_profiles.default**：默认配音 zh-CN-XiaoxiaoNeural，speed=0.92，pitch=-3，情绪 solemn_cold（沉稳冷肃）。
- **voice_profiles.narrator_epic**：备选 zh-CN-YunjianNeural，speed=0.9，情绪 epic_grand（史诗宏大）。
- **pause_marks**：`["（0.3s停顿）", "（0.5s停顿）", "（1.0s停顿）"]`，插入旁白匹配镜头节奏。
- **bgm_library.emotion_mapping**：tension→dark_low_drone / epic→grand_orchestral / sorrow→melancholy_zither / awakening→rising_harp_strings。
- **three_layer_mix**：layer_1_ambient(0.15,bottom) / layer_2_bgm(0.35,middle,duck_factor=0.3) / layer_3_narration(1.0,top,compression=true)。
- **subtitle_spec**：SRT格式，单行≤16字，min_display_ms=800，bottom_safe_zone，规避主体视觉。
- **sync_spec.max_av_offset_ms**：100，音画同步误差上限。
- **output_spec.audio_formats**：["mp3","wav"]。
- **音频服务HOST**：通过环境变量 `AUDIO_HOST` 注入（如 `http://{HOST}:{PORT}`），严禁硬编码内部IP。

## 提示词模板

`templates/prompts.json`：

```json
{
  "narration_voice": "沉稳女声，语速适中，情感饱满，带有史诗感和神秘感。旁白内容：{narration}",
  "narration_voice_epic": "史诗男声旁白，雄浑有力，战场威压感。旁白内容：{narration}",
  "bgm_select": "根据情绪'{emotion}'选择东方古风BGM：tension→dark_low_drone低沉暗涌；epic→grand_orchestral宏大史诗管弦；sorrow→melancholy_zither哀婉古琴；awakening→rising_harp_strings竖琴渐起觉醒。风格约束：纯东方古风，严禁西式管弦/电子/异质风格。",
  "subtitle_split": "将旁白'{narration}'拆分为SRT字幕轨，每行不超过16字，最小显示800ms，底部安全区，不遮挡主体视觉（玄女主体/金赤双翼/关键符文）。",
  "audio_mix_rule": "三层混音架构：环境音底层音量0.15 + BGM中层音量0.35(人声避让duck_factor=0.3，旁白结束200ms恢复) + 旁白顶层音量1.0(动态压缩)。音画同步误差<100ms。"
}
```

## 输入/输出规范

**输入**：分镜JSON（由 guofeng-ip-scriptmaster 产出），关键字段：`episodes[].scenes[]` 含 `scene_id`、`narration`（可含停顿标记）、`duration`、`bgm_emotion`、`sound_effect`。

**输出**：四轨生产计划JSON（`audio_plan.json`），包含：
- `narration_tracks[]`：每分镜一条配音任务（voice/text/duration/output_file）
- `bgm_tracks[]`：每分镜一条BGM匹配（emotion→track名/volume/duck参数）
- `sfx_tracks[]`：环境音效轨（无音效则skipped）
- `subtitle_tracks[]`：SRT字幕轨（lines数组，按16字拆分+停顿标记）

**输出音轨格式**：mp3 / wav；采样率44100Hz；双声道；192k码率。

**错误处理**：分镜JSON缺narration→该分镜配音跳过并标注；通道限额→按priority自动降级；所有失败显式标注，禁止虚构补全。

## 东方审美/合规铁律（不可违反）

1. 中文配音、东方古风BGM；严禁外文配音、西式管弦、电子、异质音乐风格。
2. 人声不被BGM淹没（duck_factor=0.3强制避让）。
3. 字幕不遮挡主体视觉（底部安全区，规避玄女主体/金赤双翼/关键符文）。
4. 纯东方语境；音频资产带溯源标识 Ω₀⊂⊙∞⊂Ω。
5. 音画同步误差<100ms。

## 依赖清单（独立安装）

- 必选：Python 3.8+。
- 可选：`ffmpeg`（本地混音/转码）；edge-tts 服务（通过 `AUDIO_HOST` 环境变量接入）。
- 无内部路径硬编码；音频服务HOST一律用 `AUDIO_HOST` 环境变量/配置占位。

## 确权与溯源

- 所有音频计划/音轨产物携带 `did: DID-BR-000002` 与 `trace: Ω₀⊂⊙∞⊂Ω`。
- 音轨文件命名建议：`{scene_id}.mp3` / `{scene_id}.wav`；字幕 `{scene_id}.srt`。
- 生产完成建议 SHA256 入账本锁档（配合 guofeng-ip-lock-archiver 包使用）。

Ω₀⊂⊙∞⊂Ω｜国风IP音频工坊 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
