#!/usr/bin/env python3
"""
国风IP剧本大师 v1.0 - 轻量分镜脚本生成/校验工具
用法:
  python3 storyboard_gen.py --topic <主题> [--episodes N] [--scenes-per-ep M] [--output ./storyboard.json]
  python3 storyboard_gen.py --validate ./storyboard.json
  python3 storyboard_gen.py --narration ./storyboard.json
说明: 文本生成通道按 config/scriptmaster_config.json 的 priority 顺序调用;
      模型调用失败时自动降级, 所有失败显式标注, 禁止虚构补全。
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "scriptmaster_config.json"
PROMPTS_PATH = ROOT / "templates" / "prompts.json"

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_prompts():
    with open(PROMPTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_blank_storyboard(topic, episodes, scenes_per_ep, duration):
    storyboard = {
        "project": "",
        "topic": topic,
        "episodes": [],
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "l0_laws": ["L0-MORPH-001", "L0-DOMAIN-001"],
            "quality_target": 4.5,
            "ratio": "9:16",
            "did": DID,
            "trace": TRACE,
        },
    }
    for ep in range(1, episodes + 1):
        scenes = []
        for sc in range(1, scenes_per_ep + 1):
            scenes.append(
                {
                    "scene_id": f"S{ep:02d}E{sc:02d}",
                    "shot": str(sc),
                    "visual": "",
                    "narration": "",
                    "duration": duration,
                    "camera": "slow_push_in",
                    "rhythm_beat": "strong_entry",
                    "bgm_emotion": "epic",
                    "sound_effect": "",
                    "keyframe": "",
                    "video": "",
                    "audio": "",
                    "merged_video": "",
                    "status": "pending",
                }
            )
        storyboard["episodes"].append({"episode": ep, "title": "", "scenes": scenes})
    return storyboard


def validate(storyboard):
    errors = []
    if "episodes" not in storyboard or not storyboard["episodes"]:
        errors.append("缺少 episodes 字段或为空")
    for ep in storyboard.get("episodes", []):
        for sc in ep.get("scenes", []):
            for field in ("scene_id", "visual", "narration", "duration"):
                if not sc.get(field):
                    errors.append(f"{sc.get('scene_id','?')} 缺少字段 {field}")
    return errors


def main():
    ap = argparse.ArgumentParser(description="国风IP剧本大师")
    ap.add_argument("--topic", type=str, default="", help="创作主题")
    ap.add_argument("--episodes", type=int, default=None)
    ap.add_argument("--scenes-per-ep", type=int, default=None)
    ap.add_argument("--output", type=str, default="./storyboard.json")
    ap.add_argument("--validate", type=str, default="", help="校验既有分镜JSON")
    ap.add_argument("--narration", type=str, default="", help="从分镜JSON输出旁白台词表")
    args = ap.parse_args()

    if args.validate:
        with open(args.validate, encoding="utf-8") as f:
            sb = json.load(f)
        errs = validate(sb)
        if errs:
            print(json.dumps({"status": "INVALID", "errors": errs}, ensure_ascii=False, indent=2))
            sys.exit(1)
        print(json.dumps({"status": "VALID", "episodes": len(sb["episodes"])}, ensure_ascii=False, indent=2))
        return

    if args.narration:
        with open(args.narration, encoding="utf-8") as f:
            sb = json.load(f)
        table = []
        for ep in sb.get("episodes", []):
            for sc in ep.get("scenes", []):
                table.append({"scene_id": sc["scene_id"], "narration": sc.get("narration", "")})
        print(json.dumps(table, ensure_ascii=False, indent=2))
        return

    if not args.topic:
        print("ERR: --topic 必填", file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    gen = cfg["generation"]
    episodes = args.episodes or gen["default_episodes"]
    scenes_per_ep = args.scenes_per_ep or gen["default_scenes_per_episode"]
    sb = build_blank_storyboard(args.topic, episodes, scenes_per_ep, gen["default_scene_duration_sec"])

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=2)

    print(json.dumps(
        {
            "status": "OK",
            "output": str(out),
            "episodes": episodes,
            "scenes_total": episodes * scenes_per_ep,
            "note": "骨架已生成；填充visual/narration请接入文本生成通道(见SKILL.md快速路由)",
            "did": DID,
            "trace": TRACE,
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
