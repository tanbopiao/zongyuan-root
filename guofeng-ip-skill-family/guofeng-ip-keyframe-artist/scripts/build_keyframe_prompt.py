#!/usr/bin/env python3
"""
国风IP关键帧画师 v1.0 - 分镜JSON → 绘图提示词清单构建工具
用法:
  python3 build_keyframe_prompt.py --storyboard ./storyboard.json [--output ./keyframe_tasks.json]
  python3 build_keyframe_prompt.py --validate ./keyframe_tasks.json
  python3 build_keyframe_prompt.py --score ./keyframe_tasks.json
说明: 从分镜visual字段构建可执行的东方审美绘图提示词；
      注入L0-MORPH-001形态校验后缀与角色一致性锚点；
      输出关键帧任务清单，供image_gen通道调用。
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "guofeng_ip_keyframe_artist_config.json"
PROMPTS_PATH = ROOT / "templates" / "prompts.json"

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_prompt(visual, cfg, prompts_tpl, character_anchor=None):
    """从visual描述构建完整绘图提示词"""
    base = prompts_tpl["keyframe_base"].format(visual=visual)
    suffix = prompts_tpl["l0_morph_suffix"]
    prompt = base + suffix

    if character_anchor:
        anchor_text = prompts_tpl["character_consistency_anchor"].format(**character_anchor)
        prompt = anchor_text + " " + prompt

    return prompt


def extract_character_anchors(scenes):
    """从分镜中提取角色一致性锚点（简化版：按角色名聚合）"""
    anchors = {}
    for sc in scenes:
        # 简化：从visual中粗提取角色名占位；实际生产由上游剧本大师注入character字段
        char = sc.get("character", "")
        if char and char not in anchors:
            anchors[char] = {
                "character_name": char,
                "face_shape": sc.get("face_shape", "鹅蛋脸"),
                "hair_style": sc.get("hair_style", "乌黑长发及腰"),
                "costume_style": sc.get("costume_style", "华夏正统汉服"),
                "main_color": sc.get("main_color", "冷蓝青黑"),
                "lighting_tone": sc.get("lighting_tone", "强烈轮廓光/霞光"),
            }
    return anchors


def build_tasks(storyboard, cfg, prompts_tpl):
    """遍历分镜，构建关键帧任务清单"""
    gen = cfg["generation"]
    tasks = []

    all_scenes = []
    for ep in storyboard.get("episodes", []):
        for sc in ep.get("scenes", []):
            all_scenes.append(sc)

    anchors = extract_character_anchors(all_scenes)

    for ep in storyboard.get("episodes", []):
        for sc in ep.get("scenes", []):
            scene_id = sc.get("scene_id", f"E{ep.get('episode',1)}S{sc.get('shot','1')}")
            visual = sc.get("visual", "")
            if not visual:
                tasks.append({
                    "scene_id": scene_id,
                    "prompt": "",
                    "visual_source": "",
                    "status": "skipped_empty_visual",
                    "note": "visual字段为空，跳过",
                })
                continue

            char = sc.get("character", "")
            anchor = anchors.get(char) if char else None
            prompt = build_prompt(visual, cfg, prompts_tpl, anchor)

            tasks.append({
                "scene_id": scene_id,
                "prompt": prompt,
                "visual_source": visual,
                "output_path": f"./keyframes/{scene_id}.png",
                "ratio": gen["default_ratio"],
                "width": gen["default_width"],
                "height": gen["default_height"],
                "model": gen["default_model"],
                "l0_morph_check": gen["l0_morph_check"],
                "drift_threshold": gen["drift_threshold"],
                "quality_target": gen["quality_target"],
                "character_anchor": anchor,
                "negative_prompt": prompts_tpl.get("refusal_negative", ""),
                "status": "pending_generation",
            })

    return tasks


def validate_tasks(tasks):
    """校验关键帧任务清单完整性"""
    errors = []
    for t in tasks:
        sid = t.get("scene_id", "?")
        status = t.get("status", "")
        if status.startswith("skipped"):
            continue
        if not t.get("prompt"):
            errors.append(f"{sid}: prompt为空且未标记skipped")
        if t.get("l0_morph_check") is False:
            errors.append(f"{sid}: L0-MORPH-001校验被关闭")
        dt = t.get("drift_threshold")
        if dt is not None and dt < 0.88:
            errors.append(f"{sid}: drift_threshold={dt} < 0.88")
    return errors


def score_summary(tasks):
    """输出质量评分汇总（占位：实际评分由模型/人工完成）"""
    summary = {
        "total_tasks": len(tasks),
        "pending": sum(1 for t in tasks if t.get("status") == "pending_generation"),
        "skipped": sum(1 for t in tasks if t.get("status", "").startswith("skipped")),
        "passed": sum(1 for t in tasks if t.get("quality_pass") is True),
        "failed": sum(1 for t in tasks if t.get("quality_pass") is False),
        "quality_target": 4.5,
        "drift_threshold": 0.88,
        "note": "实际质量评分由图像理解模型执行五维打分(见templates/prompts.json quality_score_prompt)",
    }
    return summary


def main():
    ap = argparse.ArgumentParser(description="国风IP关键帧画师")
    ap.add_argument("--storyboard", type=str, default="", help="输入分镜JSON路径")
    ap.add_argument("--output", type=str, default="./keyframe_tasks.json", help="输出关键帧任务清单")
    ap.add_argument("--validate", type=str, default="", help="校验既有关键帧任务清单")
    ap.add_argument("--score", type=str, default="", help="输出质量评分汇总")
    args = ap.parse_args()

    cfg = load_json(CONFIG_PATH)
    prompts_tpl = load_json(PROMPTS_PATH)

    if args.validate:
        tasks = load_json(args.validate)
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks["tasks"]
        errs = validate_tasks(tasks)
        if errs:
            print(json.dumps({"status": "INVALID", "errors": errs}, ensure_ascii=False, indent=2))
            sys.exit(1)
        print(json.dumps({"status": "VALID", "tasks": len(tasks)}, ensure_ascii=False, indent=2))
        return

    if args.score:
        tasks = load_json(args.score)
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks["tasks"]
        summary = score_summary(tasks)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    if not args.storyboard:
        print("ERR: --storyboard 必填", file=sys.stderr)
        sys.exit(1)

    sb = load_json(args.storyboard)
    tasks = build_tasks(sb, cfg, prompts_tpl)

    output = {
        "project": sb.get("project", ""),
        "topic": sb.get("topic", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "did": DID,
        "trace": TRACE,
        "l0_laws": ["L0-MORPH-001"],
        "quality_target": cfg["generation"]["quality_target"],
        "drift_threshold": cfg["generation"]["drift_threshold"],
        "tasks": tasks,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "OK",
        "output": str(out),
        "total_tasks": len(tasks),
        "pending": sum(1 for t in tasks if t.get("status") == "pending_generation"),
        "skipped": sum(1 for t in tasks if t.get("status", "").startswith("skipped")),
        "image_channel_priority": [c["channel"] for c in cfg["provider"]["image_channel_priority"]],
        "did": DID,
        "trace": TRACE,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
