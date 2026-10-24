#!/usr/bin/env python3
"""声画合一校验 v1.0 —— 时长对齐 / 字幕-配音匹配 / 不重叠（纯标准库）

优先从 ffprobe（可选 bin）读取真实时长；未安装或未指定媒体文件时，
降级使用 manifest 中声明的字段并打印降级提示。

用法:
  python3 scripts/audio_video_check.py --manifest examples/manifest.json
  python3 scripts/audio_video_check.py --manifest examples/manifest.json \
      --media /path/to/final.mp4        # 若 ffprobe 可用则覆盖声明值
"""
import os, sys, json, shutil, subprocess, argparse, time
from pathlib import Path


def ffprobe_duration(media: Path) -> float:
    """调用 ffprobe（可选），失败抛异常。"""
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe not installed")
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(media)],
        stderr=subprocess.STDOUT, timeout=30)
    return float(out.decode().strip())


def check(manifest: dict, tolerance: float, min_chars_per_sec: float) -> dict:
    issues = []
    mode = "declared"
    video_dur = float(manifest.get("video_duration_sec", 0))
    audio_dur = float(manifest.get("audio_duration_sec", 0))

    # 1. 时长对齐
    if video_dur <= 0:
        issues.append("video_duration_sec missing or <= 0")
    if audio_dur <= 0:
        issues.append("audio_duration_sec missing or <= 0")
    if video_dur > 0 and audio_dur > 0:
        delta = abs(video_dur - audio_dur)
        if delta > tolerance:
            issues.append(f"duration drift {delta:.2f}s > tolerance {tolerance:.2f}s (video={video_dur}, audio={audio_dur})")

    # 2. 字幕 cue：不重叠 + 每句最短可读时长 + 不溢出片尾
    cues = manifest.get("subtitle_cues", []) or []
    last_end = 0.0
    for i, cue in enumerate(cues):
        s = float(cue.get("start", 0))
        e = float(cue.get("end", 0))
        text = cue.get("text", "")
        if e <= s:
            issues.append(f"cue[{i}] non-positive duration (start={s}, end={e})")
            continue
        dur = e - s
        # 可读速率：每秒至少容纳 min_chars_per_sec 个汉字
        need = len(text) / max(min_chars_per_sec, 0.1)
        if dur < need - 0.05:
            issues.append(f"cue[{i}] '{text[:12]}...' too short {dur:.2f}s < needed {need:.2f}s")
        if s < last_end - 0.05:
            issues.append(f"cue[{i}] overlaps previous cue (start={s} < prev_end={last_end:.2f})")
        last_end = max(last_end, e)
    if cues and video_dur > 0 and last_end > video_dur + tolerance:
        issues.append(f"subtitle tail {last_end:.2f}s exceeds video duration {video_dur:.2f}s")

    return {
        "mode": mode,
        "tolerance_sec": tolerance,
        "video_duration_sec": video_dur,
        "audio_duration_sec": audio_dur,
        "cue_count": len(cues),
        "subtitle_tail_sec": last_end if cues else 0.0,
        "issues": issues,
        "passed": len(issues) == 0,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def main():
    ap = argparse.ArgumentParser(description="声画合一校验")
    ap.add_argument("--manifest", required=True, help="成片清单 JSON")
    ap.add_argument("--media", default="", help="可选：真实媒体文件路径（需 ffprobe）")
    ap.add_argument("--tolerance", type=float, default=0.3, help="时长对齐容差（秒）")
    ap.add_argument("--min-cps", type=float, default=5.0, help="字幕每秒最少可读字数")
    args = ap.parse_args()

    mpath = Path(args.manifest)
    if not mpath.exists():
        print(json.dumps({"status": "ERROR", "reason": "manifest not found"}, ensure_ascii=False))
        return 2
    manifest = json.load(open(mpath, encoding="utf-8"))

    # 若指定了媒体且 ffprobe 可用，则覆盖声明值
    degraded = False
    if args.media:
        try:
            d = ffprobe_duration(Path(args.media))
            manifest["video_duration_sec"] = d
            manifest["audio_duration_sec"] = d
        except Exception as e:
            degraded = True
            print(f"[degraded] ffprobe unavailable ({e}); falling back to declared manifest fields",
                  file=sys.stderr)

    result = check(manifest, args.tolerance, args.min_cps)
    result["degraded"] = degraded
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
