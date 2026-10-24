# 国风IP合流工坊 · guofeng-ip-merge-studio v1.0

> 声画合一 · 多轨混音 · 字幕随镜 · 本地零成本 · 发布级成片
> 确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω

## 能力

把"视频轨 + 配音轨 + BGM轨 + （可选）环境音轨 + SRT字幕轨"用本地FFmpeg合并为可直接发布的成片MP4：

- 原视频音轨降 0.3 作为背景
- 旁白配音顶层 1.0，BGM中层 0.35（旁白时 duck 至 0.3），环境音底层 0.15
- amix 多轨混音（normalize=0，保留动态）
- 输出：mp4 / h264 / aac 192k / 44100Hz / 2声道
- 字幕：烧录(硬)或 mov_text 软字幕轨(可开关)；单行 ≤16 字，底部安全区，避开主体
- 质量校验：时长≈分镜总时长、aac音轨存在、分辨率不变、音画同步<100ms

## 安装

依赖（全部免费开源）：

- **ffmpeg / ffprobe**（必选，需含 libass 以支持字幕烧录）
- **Python 3.8+**（必选，跑 merge_cmd.py）

```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y ffmpeg python3

# macOS (Homebrew)
brew install ffmpeg python@3

# Windows
# 从 https://ffmpeg.org/download.html 下载，加入 PATH；Python 从 python.org 安装
```

校验安装：

```bash
ffmpeg -version
ffprobe -version
python3 --version
```

## 快速开始

### 1. 只生成命令（不执行，dry-run）

```bash
cd guofeng-ip-merge-studio
python3 scripts/merge_cmd.py \
  --video  ./in/scene01.mp4 \
  --narration ./in/narration01.mp3 \
  --bgm    ./in/bgm_epic.mp3 \
  --srt    ./in/sub01.srt \
  --output ./out/scene01_final.mp4
```

打印出完整 ffmpeg 命令，可人工审阅后再执行。

### 2. 直接执行合流（烧录字幕）

```bash
python3 scripts/merge_cmd.py \
  --video  ./in/scene01.mp4 \
  --narration ./in/narration01.mp3 \
  --bgm    ./in/bgm_epic.mp3 \
  --srt    ./in/sub01.srt \
  --burn-sub \
  --output ./out/scene01_final.mp4 \
  --run --check
```

### 3. 软字幕轨（播放器可开关，不烧录到画面）

```bash
python3 scripts/merge_cmd.py \
  --video V.mp4 --narration N.mp3 --bgm B.mp3 \
  --srt sub.srt --soft-sub \
  --output out.mp4 --run
```

### 4. 读取 config 覆盖默认混音/编码参数

```bash
python3 scripts/merge_cmd.py \
  --config config/guofeng-ip-merge-studio_config.json \
  --video V.mp4 --narration N.mp3 --bgm B.mp3 \
  --srt sub.srt --output out.mp4 --run --check
```

## 配置说明

见 `config/guofeng-ip-merge-studio_config.json`：

- `audio_mix`：各轨音量与 duck 参数
- `output_spec`：容器/编码/码率/采样率/声道
- `subtitle`：字体/颜色/位置/单行字数上限/避开主体
- `quality_check`：时长容差、期望编码
- `compliance`：成片发布级别与人像类仅本地规则
- `service.host_placeholder = "{HOST}"`：远端合流服务地址占位（默认本地ffmpeg，启用远端需人工审批）

## 合规与确权

- 成片元数据/清单统一携带：`DID-BR-000002` + `Ω₀⊂⊙∞⊂Ω`。
- **人像/写真类成片**：仅本地归档锁档，不对外展示、不推公开湖。
- 发布级成片建议先配合 `guofeng-ip-lock-archiver` 做 SHA256 哈希入账。

## 目录结构

```
guofeng-ip-merge-studio/
├── SKILL.md
├── README.md
├── config/
│   └── guofeng-ip-merge-studio_config.json
├── templates/
│   └── prompts.json          # ffmpeg占位符模板 + ffprobe校验命令
└── scripts/
    └── merge_cmd.py          # 输入各轨路径 → 输出ffmpeg命令(可--run执行/--check校验)
```

Ω₀⊂⊙∞⊂Ω｜国风IP合流工坊 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
