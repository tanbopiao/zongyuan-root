#!/usr/bin/env python3
"""
国风IP视频导演 v1.0 - 轻量视频提示词构建工具
用法:
  python3 build_video_prompt.py --storyboard <分镜JSON> --keyframes-dir <关键帧目录>
  python3 build_video_prompt.py --storyboard <分镜JSON> --output ./video_tasks.json
说明:
  - 读取分镜JSON(来自 guofeng-ip-scriptmaster)与关键帧目录(按 scene_id 匹配 .png)
  - 基于 visual+camera 字段构建镜头运动描述, 套用 templates/prompts.json 的 video_single_shot 模板
  - 输出视频生成任务清单(每条含 scene_id/keyframe/prompt/duration/ratio/camera/quality_rubric)
  - 零成本通道优先级由 config/guofeng-ip-video-director_config.json 决定, 脚本仅输出清单不直接调API
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "guofeng-ip-video-director_config.json"
PROMPTS_PATH = ROOT / "templates" / "prompts.json"

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_camera_desc(camera_key: str, lexicon: dict) -> str:
    """根据 camera 字段查词典, 未命中返回 key 本身."""
    if not camera_key:
        return lexicon.get("static_breath", "固定机位呼吸镜头")
    return lexicon.get(camera_key, camera_key)


def collect_scenes(storyboard: dict):
    scenes = []
    for ep in storyboard.get("episodes", []):
        for sc in ep.get("scenes", []):
            scenes.append(sc)
    return scenes


def match_keyframe(scene_id: str, keyframes_dir: Path) -> str:
    """按 scene_id 匹配关键帧文件(.png/.jpg), 未命中返回空字符串."""
    if not keyframes_dir or not keyframes_dir.exists():
        return ""
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        cand = keyframes_dir / f"{scene_id}{ext}"
        if cand.exists():
            return str(cand)
    return ""


def build_tasks(storyboard: dict, keyframes_dir: Path, cfg: dict, prompts: dict) -> list:
    camera_lexicon = cfg.get("camera_movement_lexicon", {})
    model_cfg = cfg.get("model", {})
    default_duration = model_cfg.get("default_duration_sec", 10)
    default_ratio = model_cfg.get("ratio", "9:16")
    template = prompts.get("video_single_shot", "")
    continuity_template = prompts.get("video_scene_continuity", "")
    rubric = prompts.get("video_quality_rubric", "")

    tasks = []
    scenes = collect_scenes(storyboard)
    for idx, sc in enumerate(scenes):
        scene_id = sc.get("scene_id", f"shot_{idx+1:02d}")
        visual = sc.get("visual", "")
        camera_key = sc.get("camera", "slow_push_in")
        camera_desc = build_camera_desc(camera_key, camera_lexicon)
        duration = sc.get("duration", default_duration)
        keyframe = match_keyframe(scene_id, keyframes_dir)

        # 首镜用单镜模板, 后续镜叠加连续性模板
        if idx == 0:
            prompt = template.format(
                duration=duration,
                camera_movement=camera_key,
                camera_movement_desc=camera_desc,
                visual=visual,
            )
        else:
            prompt = continuity_template.format(
                camera_movement=camera_key,
                camera_movement_desc=camera_desc,
                visual=visual,
                duration=duration,
            )

        tasks.append({
            "scene_id": scene_id,
            "shot": sc.get("shot", str(idx + 1)),
            "keyframe": keyframe,
            "output_path": f"./videos/{scene_id}.mp4",
            "duration": duration,
            "ratio": default_ratio,
            "resolution": model_cfg.get("resolution", "1152x2048"),
            "fps": model_cfg.get("fps", 24),
            "camera": camera_key,
            "camera_movement_desc": camera_desc,
            "prompt": prompt,
            "quality_rubric": rubric,
            "quality_target": cfg.get("quality", {}).get("min_score", 4.5),
            "status": "pending_generation",
        })
    return tasks


def main():
    ap = argparse.ArgumentParser(description="国风IP视频导演 - 视频提示词清单构建")
    ap.add_argument("--storyboard", required=True, help="分镜JSON文件路径")
    ap.add_argument("--keyframes-dir", default=None, help="关键帧目录(按 scene_id 匹配)")
    ap.add_argument("--output", default=None, help="输出视频任务清单JSON路径")
    ap.add_argument("--validate", action="store_true", help="仅校验分镜JSON结构")
    args = ap.parse_args()

    sb_path = Path(args.storyboard)
    if not sb_path.exists():
        print(f"[ERROR] 分镜文件不存在: {sb_path}", file=sys.stderr)
        sys.exit(1)

    storyboard = load_json(sb_path)
    cfg = load_json(CONFIG_PATH)
    prompts = load_json(PROMPTS_PATH)

    scenes = collect_scenes(storyboard)
    if not scenes:
        print("[ERROR] 分镜JSON中未找到任何 scenes", file=sys.stderr)
        sys.exit(1)

    if args.validate:
        print(json.dumps({
            "valid": True,
            "scene_count": len(scenes),
            "did": DID,
            "trace": TRACE,
        }, ensure_ascii=False, indent=2))
        return

    kf_dir = Path(args.keyframes_dir) if args.keyframes_dir else None
    tasks = build_tasks(storyboard, kf_dir, cfg, prompts)

    result = {
        "project": storyboard.get("project", ""),
        "topic": storyboard.get("topic", ""),
        "channel_priority": [c["channel"] for c in cfg.get("video_channel_priority", [])],
        "model": cfg.get("model", {}),
        "tasks": tasks,
        "metadata": {
            "package": "guofeng-ip-video-director",
            "version": "1.0.0",
            "did": DID,
            "trace": TRACE,
            "task_count": len(tasks),
        },
    }

    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"[OK] 视频任务清单已写入: {args.output} (共 {len(tasks)} 条)")
    else:
        print(out)


if __name__ == "__main__":
    main()
