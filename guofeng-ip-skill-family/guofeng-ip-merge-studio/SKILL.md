---
name: guofeng-ip-merge-studio
version: 1.0.0
description: "国风IP音视频合流工坊：视频轨+配音轨+BGM轨+字幕轨→FFmpeg合并输出可直接发布级成片MP4(原视频音降0.3为背景/amix混音/aac-192k/44100/2ch/h264/mp4)，SRT字幕绑定镜头时间点可开关，音画同步<100ms，单行≤16字不遮挡主体。当用户说'合流'、'音画合一'、'成片合成'、'视频加配音加BGM'、'字幕烧录'、'mp4输出'时使用。零成本本地FFmpeg，严格遵循东方审美元法则与确权铁律。"
metadata:
  requires:
    bins: ["ffmpeg", "ffprobe", "python3"]
  pypi: []
  optional_bins: []
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---

# 国风IP合流工坊 v1.0

> 声画合一 · 多轨混音 · 字幕随镜 · 本地零成本 · 发布级成片

## 核心设计原则

1. **多轨稳态混音**：原视频音轨(0.3背景) + 旁白配音(1.0顶层) + BGM(0.35中层，旁白时duck至0.3) + 环境音(0.15底层)，amix归一化关闭保持各轨原始动态。
2. **发布级输出契约**：容器mp4 / 视频h264 / 音频aac-192k / 44100Hz / 2声道；分辨率与原视频一致；时长≈分镜总时长。
3. **字幕随镜可开关**：SRT字幕轨绑定镜头时间点，支持烧录(硬字幕)与软字幕(mov_text，播放器开关)两种模式；单行≤16字、底部安全区、避开主体(玄女/双翼/符文)。
4. **零成本本地FFmpeg**：纯本地ffmpeg/ffprobe完成合流与校验，零云费用；远端合流服务仅作兜底占位 `{HOST}/video/merge-audio`，启用需人工审批。
5. **确权与分级合规**：成片元数据/清单携带 DID-BR-000002 + Ω₀⊂⊙∞⊂Ω；人像/写真类成片仅本地归档锁档，严禁对外展示。

## 快速路由

| 目标 | 命令 |
|------|------|
| 生成合流命令(只打印不执行) | `python3 scripts/merge_cmd.py --video V.mp4 --narration N.mp3 --bgm B.mp3 --srt sub.srt --out out.mp4` |
| 实际执行合流(带烧录字幕) | `python3 scripts/merge_cmd.py --video V.mp4 --narration N.mp3 --bgm B.mp3 --srt sub.srt --burn-sub --out out.mp4 --run` |
| 软字幕轨(可开关) | `python3 scripts/merge_cmd.py --video V.mp4 --narration N.mp3 --bgm B.mp3 --srt sub.srt --soft-sub --out out.mp4 --run` |
| 四轨(加环境音) | `python3 scripts/merge_cmd.py --video V.mp4 --narration N.mp3 --bgm B.mp3 --env env.wav --out out.mp4 --run` |
| 产出后质量校验 | `python3 scripts/merge_cmd.py ... --out out.mp4 --check` |
| 读取配置覆盖默认值 | `python3 scripts/merge_cmd.py --config config/guofeng-ip-merge-studio_config.json ...` |

## 配置模板

`config/guofeng-ip-merge-studio_config.json`：

```json
{
  "merge_version": "1.0.0",
  "did": "DID-BR-000002",
  "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
  "service": {
    "mode": "local_ffmpeg",
    "host_placeholder": "{HOST}",
    "merge_endpoint": "/video/merge-audio"
  },
  "audio_mix": {
    "original_video_track_volume": 0.3,
    "narration_volume": 1.0,
    "bgm_volume": 0.35,
    "bgm_duck_factor": 0.3,
    "env_ambient_volume": 0.15,
    "amix_normalize": false,
    "sync_tolerance_ms": 100
  },
  "output_spec": {
    "container": "mp4",
    "video_codec": "h264",
    "video_preset": "medium",
    "video_crf": 20,
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "sample_rate": 44100,
    "channels": 2
  },
  "subtitle": {
    "enabled": true,
    "format": "srt",
    "position": "bottom_safe_zone",
    "font_size": 48,
    "color": "#E8D5B7",
    "stroke_color": "#1A1A2E",
    "single_line_max_chars": 16,
    "min_display_ms": 800,
    "avoid_subject": true,
    "toggle_support": true
  },
  "quality_check": {
    "duration_tolerance_sec": 0.5,
    "expect_audio_stream": true,
    "expect_resolution_unchanged": true,
    "expect_video_codec": "h264",
    "expect_audio_codec": "aac"
  },
  "compliance": {
    "release_ready": true,
    "portrait_strictly_local_only": true
  }
}
```

## 提示词/命令模板

`templates/prompts.json` 内含4套参数化ffmpeg占位符模板（基础烧录字幕 / 无字幕 / 四轨含环境音 / 软字幕轨）+ ffprobe质量校验命令。核心模板：

```
ffmpeg -y -i {VIDEO} -i {NARRATION} -i {BGM} \
  -filter_complex "[0:a]volume=0.3[bg];[1:a]volume=1.0[vo];[2:a]volume=0.35[bm];[bg][vo][bm]amix=inputs=3:normalize=0[aout];[0:v]subtitles={SRT}:force_style='FontSize=48,PrimaryColour=&H00B7D5E8,OutlineColour=&H002E1A1A,Alignment=2,MarginV=80'[vout]" \
  -map "[vout]" -map "[aout]" \
  -c:v h264 -preset medium -crf 20 \
  -c:a aac -b:a 192k -ar 44100 -ac 2 {OUTPUT}
```

## 输入/输出规范

- **输入**：
  - `--video`：无声/原声视频MP4（必选）
  - `--narration`：配音/旁白音频（必选，WAV/MP3）
  - `--bgm`：BGM音频（必选）
  - `--env`：环境音（可选，第四轨）
  - `--srt`：SRT字幕文件（可选）
- **输出**：成片MP4，h264/aac-192k/44100/2ch；分辨率与输入视频一致；时长≈分镜总时长。
- **质量校验**（`--check`）：
  1. `ffprobe format=duration` ≈ 分镜总时长（±0.5s）
  2. 音频流 codec_name = aac
  3. 视频流 width/height 与原视频一致
  4. 人工试听：音画同步误差 < 100ms，旁白不被BGM淹没，字幕单行≤16字不遮主体
- **错误处理**：缺轨跳过并WARN；ffmpeg非零退出→直接抛出，禁止虚构成功；字幕文件不存在→降级为无字幕模式并提示。

## 依赖清单（独立安装）

- 必选：`ffmpeg`（含libass用于字幕烧录）、`ffprobe`、Python 3.8+。
- 安装提示（Ubuntu/Debian）：`sudo apt-get install -y ffmpeg`；macOS：`brew install ffmpeg`；Windows：从 ffmpeg.org 下载加入PATH。
- 无任何内部路径硬编码；远端服务地址一律使用 `{HOST}` 占位，通过 config 注入。

## 确权与溯源

- 成片元数据/生产清单携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`。
- 人像/写真类成片：仅本地归档锁档（配合 guofeng-ip-lock-archiver），严禁对外展示、不推公开湖。
- 发布级成片发布前建议先做SHA256哈希登记。

Ω₀⊂⊙∞⊂Ω｜国风IP合流工坊 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
