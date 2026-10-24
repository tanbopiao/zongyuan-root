# 国风IP音频工坊 guofeng-ip-audio-studio v1.0

> 分镜JSON → 中文配音 → 东方古风BGM → 三层混音 → SRT字幕轨 → mp3/wav音轨

## 安装

```bash
# 必选：Python 3.8+
# 可选：ffmpeg（本地混音/转码）
# edge-tts 服务通过环境变量接入，无需本地安装
export AUDIO_HOST="http://{HOST}:{PORT}"
```

## 快速开始

```bash
# 1. 从分镜JSON生成四轨生产计划（配音/BGM/音效/字幕）
python3 scripts/build_audio_plan.py \
  --storyboard ./storyboard.json \
  --output ./audio_plan.json

# 2. 校验既有音频计划JSON
python3 scripts/build_audio_plan.py --validate ./audio_plan.json

# 3. 按计划执行配音（接入 edge-tts 服务或豆包APP内置通道）
#    配音轨: audio/{scene_id}.mp3
#    BGM轨:  bgm/{scene_id}_bgm.mp3
#    字幕轨: subtitles/{scene_id}.srt
```

## 配置

编辑 `config/guofeng-ip-audio-studio_config.json`：
- `audio_channel_priority`：音频通道优先级（免费优先：app_builtin_tts > edge_tts_server > paid_api需审批）
- `voice_profiles`：默认沉稳女声 zh-CN-XiaoxiaoNeural / 备选史诗旁白 zh-CN-YunjianNeural
- `bgm_library.emotion_mapping`：情绪→BGM映射（tension/epic/sorrow/awakening）
- `three_layer_mix`：三层混音音量与避让参数
- `subtitle_spec`：SRT字幕规格（单行≤16字/800ms/底部安全区）

## 核心能力

| 能力 | 说明 |
|------|------|
| 中文配音 | 默认zh-CN-XiaoxiaoNeural沉稳女声，备选zh-CN-YunjianNeural史诗旁白 |
| BGM匹配 | 东方古风，情绪映射 tension/epic/sorrow/awakening |
| 三层混音 | 环境音0.15 + BGM0.35(人声避让duck=0.3) + 旁白1.0(动态压缩) |
| SRT字幕 | 单行≤16字，最小800ms，底部安全区，不遮挡主体 |
| 音画同步 | 误差<100ms；停顿标记（0.3s/0.5s/1.0s停顿） |
| 输出格式 | mp3 / wav，44100Hz，双声道，192k |

## 零成本通道

1. **豆包APP内置text_to_audio**（免费会话额度，priority=0）
2. **服务器edge-tts**（完全免费零成本，priority=1，通过 `AUDIO_HOST` 环境变量接入）
3. **付费API**（priority=9，需人工审批，仅前两级不可用时兜底）

## 确权

所有产物携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`；生产完成后建议 SHA256 入账本锁档（配合 guofeng-ip-lock-archiver）。

Ω₀⊂⊙∞⊂Ω｜国风IP音频工坊 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
