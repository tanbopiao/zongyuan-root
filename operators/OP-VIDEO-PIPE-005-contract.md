# OP-VIDEO-PIPE-005｜视频合音流水线算子

> 算子编号：OP-VIDEO-PIPE-005
> 归属体系：昆仑洞天 IP 量产流水线
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
读取连续关键帧序列，调用图生视频模型生成短视频，自动匹配 BGM/环境音效，输出标准化竖屏短片，并归档至对应剧集目录。

### 输入
```json
{
  "op_name": "OP-VIDEO-PIPE-005",
  "keyframes_dir": "/assets/keyframes/EP01/",
  "output_dir": "/assets/videos/",
  "model": "seedance-2.0-fast",
  "duration_sec": 10,
  "ratio": "9:16",
  "bgm_path": "/assets/audio/epic-ambient.wav",
  "voiceover_text": "",
  "max_retries": 2
}
```

### 执行流程
```
Step1  读取 keyframes_dir 下按命名排序的关键帧（KF-EP01-01.jpg → KF-EP01-02.jpg ...）
Step2  校验帧序列完整性：连续编号、无缺失、数量≥2
Step3  选取首帧作为视频生成参考图（后续帧用于镜头连续性描述）
Step4  调用图生视频 API：
        - 参考图：首帧
        - prompt：从分镜清单读取该集动作描述
        - duration：10秒
        - ratio：9:16
Step5  生成成功 → 保存为 {ep}_shot{id}.mp4
Step6  音频合成：
        - 加载 bgm_path 背景音乐
        - 如有 voiceover_text，调用 TTS 生成旁白
        - BGM 音量降低至 -18dB，旁白叠加在主轨道
        - 淡入淡出 0.5秒
Step7  合成最终视频：视频画面 + 音频轨道
Step8  写入 .meta.json（含关键帧列表、BGM来源、生成参数）
Step9  触发 OP-ARCHIVE-001 归档新视频资产
Step10 输出报告 JSON
```

### 禁止项
- ❌ 禁止跳过帧序列校验直接生成
- ❌ 禁止视频时长超过参数指定秒数
- ❌ 禁止 BGM 音量盖过旁白（旁白为主，BGM为辅）
- ❌ 禁止覆盖已存在的成片视频
- ❌ 禁止在视频中添加水印、字幕条（原始成片保持干净）

### 输出报告
```json
{
  "op_name": "OP-VIDEO-PIPE-005",
  "run_timestamp": "2026-10-10T23:30:00+08:00",
  "summary": {
    "ep": "EP01",
    "keyframes_used": 3,
    "video_duration_sec": 10,
    "bgm_mixed": true,
    "voiceover_mixed": false,
    "archive_triggered": true
  },
  "output_file": "/assets/videos/EP01_shot01.mp4",
  "failed_frames": [],
  "status": "success"
}
```

---

## 二、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | 3帧连续，无旁白 | 生成10秒视频，BGM自动混合，无旁白轨 |
| TC-02 | 3帧+旁白文本 | 视频+BGM+TTS旁白，旁白音量高于BGM |
| TC-03 | 关键帧缺失（编号跳号） | 报错 frame_sequence_error，不生成 |
| TC-04 | 视频生成失败 | 重试2次后仍失败，记录 error，不崩溃 |
| TC-05 | 已有同名视频 | skipped，不重复生成 |
| TC-06 | 时长精确 | 输出视频时长=10秒±0.5秒 |
| TC-07 | 归档自动触发 | 新视频进入 OP-ARCHIVE-001 账本 |

---

## 三、技术约束
- 视频生成 API（seedance-2.0-fast）需在工作任务沙箱内调用
- 音频合成可用 ffmpeg 命令行（沙箱预装）
- BGM 默认 -18dB，旁白 0dB，淡入淡出 0.5秒
- 输出格式：MP4（H.264 + AAC）
- 成片 privacy_level 默认 private（待审核后再公开）
