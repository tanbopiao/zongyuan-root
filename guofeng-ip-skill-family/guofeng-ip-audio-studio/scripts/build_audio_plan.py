#!/usr/bin/env python3
"""
国风IP音频工坊 v1.0 - 分镜JSON → 四轨生产计划(配音/BGM/音效/字幕)
用法:
  python3 build_audio_plan.py --storyboard ./storyboard.json [--output ./audio_plan.json]
  python3 build_audio_plan.py --validate ./audio_plan.json
说明: 读取分镜JSON，按 config 生成配音/BGM/音效/字幕四轨生产计划JSON;
      所有通道按 priority 顺序调度; 失败显式标注，禁止虚构补全。
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "guofeng-ip-audio-studio_config.json"

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def split_subtitle_lines(narration, max_chars=16):
    """将旁白拆分为单行≤max_chars的字幕行，保留停顿标记位置。"""
    # 先把停顿标记提取出来，避免拆行时打断
    pause_pattern = re.compile(r"（[\d.]+s停顿）")
    parts = []
    last = 0
    for m in pause_pattern.finditer(narration):
        if m.start() > last:
            parts.append(("text", narration[last:m.start()]))
        parts.append(("pause", m.group()))
        last = m.end()
    if last < len(narration):
        parts.append(("text", narration[last:]))

    # 按行切分文本部分，每行≤max_chars
    lines = []
    for kind, content in parts:
        if kind == "pause":
            lines.append({"type": "pause", "text": content})
        else:
            chunk = content.strip()
            while len(chunk) > max_chars:
                # 优先在标点处切分
                cut = max(
                    chunk.rfind("，", 0, max_chars),
                    chunk.rfind("。", 0, max_chars),
                    chunk.rfind("；", 0, max_chars),
                    chunk.rfind("：", 0, max_chars),
                    chunk.rfind("、", 0, max_chars),
                )
                if cut <= 0:
                    cut = max_chars
                lines.append({"type": "text", "text": chunk[: cut + 1].strip()})
                chunk = chunk[cut + 1 :]
            if chunk:
                lines.append({"type": "text", "text": chunk})
    return lines


def build_plan(storyboard, cfg):
    voice_default = cfg["voice_profiles"]["default"]["voice"]
    voice_epic = cfg["voice_profiles"]["narrator_epic"]["voice"]
    bgm_map = cfg["bgm_library"]["emotion_mapping"]
    channel = cfg["audio_channel_priority"][0]["channel"]
    host_env = cfg["audio_channel_priority"][1].get("host_env", "AUDIO_HOST")

    tracks = {
        "narration_tracks": [],
        "bgm_tracks": [],
        "sfx_tracks": [],
        "subtitle_tracks": [],
    }

    for ep in storyboard.get("episodes", []):
        for sc in ep.get("scenes", []):
            sid = sc.get("scene_id", "UNKNOWN")
            narration = sc.get("narration", "")
            duration = sc.get("duration", 10)
            emotion = sc.get("bgm_emotion", "epic")
            sfx = sc.get("sound_effect", "")

            # 配音轨
            tracks["narration_tracks"].append({
                "scene_id": sid,
                "voice": voice_default,
                "voice_fallback": voice_epic,
                "text": narration[:500],
                "duration_sec": duration,
                "channel": channel,
                "host_env": host_env,
                "tts_endpoint": "/tts/generate",
                "output_file": f"audio/{sid}.mp3",
                "status": "pending",
            })

            # BGM轨
            bgm_name = bgm_map.get(emotion, cfg["bgm_library"]["default"])
            tracks["bgm_tracks"].append({
                "scene_id": sid,
                "emotion": emotion,
                "track": bgm_name,
                "volume": cfg["three_layer_mix"]["layer_2_bgm"]["volume"],
                "duck_factor": cfg["three_layer_mix"]["layer_2_bgm"]["duck_factor"],
                "output_file": f"bgm/{sid}_bgm.mp3",
                "status": "pending",
            })

            # 音效轨
            tracks["sfx_tracks"].append({
                "scene_id": sid,
                "sfx": sfx,
                "volume": cfg["three_layer_mix"]["layer_1_ambient"]["volume"],
                "output_file": f"sfx/{sid}_sfx.wav" if sfx else "",
                "status": "pending" if sfx else "skipped",
            })

            # 字幕轨
            sub_lines = split_subtitle_lines(
                narration, cfg["subtitle_spec"]["single_line_max_chars"]
            )
            tracks["subtitle_tracks"].append({
                "scene_id": sid,
                "format": cfg["subtitle_spec"]["format"],
                "min_display_ms": cfg["subtitle_spec"]["min_display_ms"],
                "position": cfg["subtitle_spec"]["position"],
                "lines": sub_lines,
                "output_file": f"subtitles/{sid}.srt",
                "status": "pending",
            })

    plan = {
        "project": storyboard.get("project", ""),
        "topic": storyboard.get("topic", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "did": DID,
        "trace": TRACE,
        "mix_architecture": cfg["three_layer_mix"],
        "sync_spec": cfg["sync_spec"],
        "output_spec": cfg["output_spec"],
        "tracks": tracks,
        "l0_laws": cfg["l0_laws"],
    }
    return plan


def validate_plan(plan):
    errors = []
    tracks = plan.get("tracks", {})
    for key in ("narration_tracks", "bgm_tracks", "sfx_tracks", "subtitle_tracks"):
        if key not in tracks:
            errors.append(f"缺少 tracks.{key}")
    for nt in tracks.get("narration_tracks", []):
        if not nt.get("scene_id") or not nt.get("text"):
            errors.append(f"配音轨缺字段: {nt.get('scene_id','?')}")
    for st in tracks.get("subtitle_tracks", []):
        for line in st.get("lines", []):
            if line.get("type") == "text" and len(line.get("text", "")) > 16:
                errors.append(f"{st.get('scene_id')} 字幕行超16字: {line.get('text')}")
    return errors


def main():
    ap = argparse.ArgumentParser(description="国风IP音频工坊 - 四轨生产计划生成")
    ap.add_argument("--storyboard", type=str, default="", help="分镜JSON路径")
    ap.add_argument("--output", type=str, default="./audio_plan.json", help="输出计划JSON路径")
    ap.add_argument("--validate", type=str, default="", help="校验既有音频计划JSON")
    args = ap.parse_args()

    if args.validate:
        with open(args.validate, encoding="utf-8") as f:
            plan = json.load(f)
        errs = validate_plan(plan)
        if errs:
            print(json.dumps({"status": "INVALID", "errors": errs}, ensure_ascii=False, indent=2))
            sys.exit(1)
        print(json.dumps({"status": "VALID", "tracks_count": {
            k: len(v) for k, v in plan.get("tracks", {}).items()
        }}, ensure_ascii=False, indent=2))
        return

    if not args.storyboard:
        print("ERR: --storyboard 必填", file=sys.stderr)
        sys.exit(1)

    with open(args.storyboard, encoding="utf-8") as f:
        sb = json.load(f)

    cfg = load_config()
    plan = build_plan(sb, cfg)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    counts = {k: len(v) for k, v in plan["tracks"].items()}
    print(json.dumps({
        "status": "OK",
        "output": str(out),
        "tracks": counts,
        "voice_default": cfg["voice_profiles"]["default"]["voice"],
        "channel_priority": [c["channel"] for c in cfg["audio_channel_priority"]],
        "did": DID,
        "trace": TRACE,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
