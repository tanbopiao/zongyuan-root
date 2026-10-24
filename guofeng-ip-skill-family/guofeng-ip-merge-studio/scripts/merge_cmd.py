#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_cmd.py — 国风IP合流工坊 轻量FFmpeg命令生成器

输入：视频/配音/BGM/字幕路径
输出：可直接执行的 ffmpeg 命令行（不实际执行，--run 才执行）

零成本：纯本地FFmpeg，零云费用。
确权：DID-BR-000002 / Ω₀⊂⊙∞⊂Ω
"""
import argparse
import json
import os
import shlex
import subprocess
import sys


def build_cmd(video, narration, bgm, srt, output,
              env=None, soft_sub=False, burn_sub=False,
              orig_vol=0.3, narration_vol=1.0, bgm_vol=0.35, env_vol=0.15,
              audio_bitrate="192k", sample_rate=44100, channels=2,
              font_size=48, crf=20):
    inputs = [video, narration, bgm]
    if env:
        inputs.append(env)
    if soft_sub and srt:
        inputs.append(srt)

    parts = ["ffmpeg", "-y"]
    for f in inputs:
        parts += ["-i", shlex.quote(f)]

    fc = []
    n_inputs = len(inputs)
    # 0:v always video
    fc.append(f"[0:a]volume={orig_vol}[bg]")
    fc.append(f"[1:a]volume={narration_vol}[vo]")
    fc.append(f"[2:a]volume={bgm_vol}[bm]")
    mix_inputs = ["[bg]", "[vo]", "[bm]"]
    if env:
        fc.append(f"[3:a]volume={env_vol}[en]")
        mix_inputs.append("[en]")
    fc.append(
        "".join(mix_inputs) +
        f"amix=inputs={len(mix_inputs)}:normalize=0[aout]"
    )

    vmap = "0:v"
    if burn_sub and srt:
        srt_esc = srt.replace(":", "\\:").replace("'", "\\'")
        fc.append(
            f"[0:v]subtitles='{srt_esc}':force_style="
            f"'FontSize={font_size},PrimaryColour=&H00B7D5E8,"
            f"OutlineColour=&H002E1A1A,Alignment=2,MarginV=80'[vout]"
        )
        vmap = "[vout]"

    filter_complex = ";".join(fc)
    parts += ["-filter_complex", shlex.quote(filter_complex)]
    parts += ["-map", vmap, "-map", "[aout]"]
    if soft_sub and srt:
        sub_idx = n_inputs - 1
        parts += ["-map", f"{sub_idx}:s"]

    parts += [
        "-c:v", "h264", "-preset", "medium", "-crf", str(crf),
        "-c:a", "aac", "-b:a", audio_bitrate,
        "-ar", str(sample_rate), "-ac", str(channels),
    ]
    if soft_sub and srt:
        parts += ["-c:s", "mov_text", "-metadata:s:s:0", "title=中文字幕"]
    parts.append(shlex.quote(output))
    return parts


def quality_check(output):
    """用 ffprobe 做三项质量校验。"""
    print("\n=== 质量校验 ===")
    checks = [
        ("时长", ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                  "-of", "csv=p=0", output]),
        ("音频流编码", ["ffprobe", "-v", "error", "-select_streams", "a",
                       "-show_entries", "stream=codec_name", "-of", "csv=p=0", output]),
        ("分辨率", ["ffprobe", "-v", "error", "-select_streams", "v",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", output]),
    ]
    for name, cmd in checks:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"[OK] {name}: {r.stdout.strip()}")
        except Exception as e:
            print(f"[WARN] {name} 校验失败: {e}")
    print("提示：音画同步误差应 < 100ms；成片时长应 ≈ 分镜总时长(±0.5s)。")


def main():
    ap = argparse.ArgumentParser(description="国风IP合流工坊 FFmpeg命令生成器")
    ap.add_argument("--video", required=True, help="视频轨MP4路径")
    ap.add_argument("--narration", required=True, help="配音/旁白音频路径")
    ap.add_argument("--bgm", required=True, help="BGM音频路径")
    ap.add_argument("--env", default=None, help="可选：环境音轨")
    ap.add_argument("--srt", default=None, help="可选：SRT字幕路径")
    ap.add_argument("--burn-sub", action="store_true", help="烧录字幕到画面")
    ap.add_argument("--soft-sub", action="store_true", help="软字幕轨(播放器可开关)")
    ap.add_argument("--output", required=True, help="输出成片MP4路径")
    ap.add_argument("--orig-vol", type=float, default=0.3)
    ap.add_argument("--bgm-vol", type=float, default=0.35)
    ap.add_argument("--run", action="store_true", help="实际执行ffmpeg(否则只打印命令)")
    ap.add_argument("--check", action="store_true", help="产出后做ffprobe质量校验")
    ap.add_argument("--config", default=None, help="可选：读取config JSON覆盖默认值")
    args = ap.parse_args()

    cfg = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)

    mix = cfg.get("audio_mix", {})
    spec = cfg.get("output_spec", {})
    sub = cfg.get("subtitle", {})

    cmd = build_cmd(
        video=args.video, narration=args.narration, bgm=args.bgm,
        srt=args.srt, output=args.output, env=args.env,
        soft_sub=args.soft_sub, burn_sub=args.burn_sub or (sub.get("enabled") and bool(args.srt)),
        orig_vol=mix.get("original_video_track_volume", args.orig_vol),
        narration_vol=mix.get("narration_volume", 1.0),
        bgm_vol=mix.get("bgm_volume", args.bgm_vol),
        env_vol=mix.get("env_ambient_volume", 0.15),
        audio_bitrate=spec.get("audio_bitrate", "192k"),
        sample_rate=spec.get("sample_rate", 44100),
        channels=spec.get("channels", 2),
        font_size=sub.get("font_size", 48),
    )

    print("# 国风IP合流工坊 · Ω₀⊂⊙∞⊂Ω · DID-BR-000002")
    print(" ".join(cmd))

    if args.run:
        print("\n执行中...")
        subprocess.run(cmd, check=True)
        print(f"[OK] 成片输出: {args.output}")

    if args.check and os.path.exists(args.output):
        quality_check(args.output)


if __name__ == "__main__":
    main()
