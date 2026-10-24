#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guofeng-ip-pipeline-orchestrator 轻量调度脚本
  --plan    输出阶段依赖与调度计划 JSON
  --gate    质量门禁检查（基于分镜JSON + 产物清单）
  --matrix  输出专家团矩阵 JSON
零依赖（仅标准库）。确权：DID-BR-000002 / Ω₀⊂⊙∞⊂Ω
"""
import argparse, json, os, sys

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

# 七兄弟专家包矩阵（与同家族兄弟包一一对应）
EXPERT_MATRIX = [
    {"package": "guofeng-ip-scriptmaster",       "name_cn": "剧本大师",     "ability": "主题→东方叙事→结构化分镜JSON",        "input": "主题/集数/分镜数",   "output": "分镜JSON(visual/narration/duration/scene_id)", "depends_on": []},
    {"package": "guofeng-ip-keyframe-artist",    "name_cn": "关键帧画师",   "ability": "visual→绘图提示词→L0形态校验→五维评分", "input": "分镜JSON.visual",    "output": "关键帧图片+质量评分+L0校验结果",            "depends_on": ["script"]},
    {"package": "guofeng-ip-video-director",    "name_cn": "视频导演",     "ability": "关键帧→镜头运动→动态视频→防漂移",      "input": "关键帧+分镜.camera", "output": "9:16竖屏视频MP4+质量评分",                  "depends_on": ["keyframe"]},
    {"package": "guofeng-ip-audio-studio",       "name_cn": "音频工坊",     "ability": "narration→中文配音→BGM→三层混音→字幕", "input": "分镜JSON.narration","output": "配音mp3+BGM轨+SRT字幕",                     "depends_on": ["script"]},
    {"package": "guofeng-ip-merge-studio",      "name_cn": "合流工坊",     "ability": "视频+配音+BGM+字幕→FFmpeg合成成片",    "input": "视频轨+音频轨",     "output": "发布级MP4(音画同步<100ms)",                 "depends_on": ["video", "audio"]},
    {"package": "guofeng-ip-production-ledger",   "name_cn": "生产台账管家", "ability": "四表入账→状态流转→进度→哈希对账",      "input": "各阶段产物",        "output": "项目/分镜/资产/进度四表",                   "depends_on": ["script"]},
    {"package": "guofeng-ip-lock-archiver",      "name_cn": "锁档归档使",   "ability": "SHA256→Merkle清单→DID锚定→只读固化",   "input": "成片+全资产",       "output": "HASH-LEDGER.csv+锁档凭证",                  "depends_on": ["merge", "ledger"]},
]

# 阶段调度图：标注并行/串行/贯穿
STAGE_GRAPH = [
    {"id": "script",   "run": "serial",   "runnable_when": "project start"},
    {"id": "keyframe", "run": "serial",   "runnable_when": "script done"},
    {"id": "video",    "run": "serial",   "runnable_when": "keyframe done"},
    {"id": "audio",    "run": "parallel", "runnable_when": "script done", "parallel_with": "video"},
    {"id": "merge",    "run": "serial",   "runnable_when": "video done AND audio done"},
    {"id": "ledger",   "run": "throughout","runnable_when": "script start", "write_back": "every stage"},
    {"id": "lock",     "run": "serial",   "runnable_when": "merge done AND ledger closed"},
]

GATE_RULES = {
    "keyframe_l0_check": True,
    "video_quality_min": 4.5,
    "av_sync_max_ms": 100,
    "merge_duration_tolerance_sec": 0.5,
}


def cmd_plan(_args):
    plan = {
        "batch": "guofeng-ip-pipeline",
        "stage_graph": STAGE_GRAPH,
        "topo_order": ["script", "keyframe", "video||audio", "merge", "ledger(throughout)", "lock"],
        "parallel_groups": [["video", "audio"]],
        "did": DID, "trace": TRACE,
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))


def cmd_matrix(_args):
    out = {"expert_matrix": EXPERT_MATRIX, "did": DID, "trace": TRACE}
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_gate(args):
    """质量门禁检查：读取分镜JSON(算总时长)与产物清单JSON，逐项核验。"""
    results = []
    storyboard = {}
    if args.storyboard and os.path.exists(args.storyboard):
        with open(args.storyboard, encoding="utf-8") as f:
            storyboard = json.load(f)

    # 计算分镜总时长
    expected_total = 0.0
    if storyboard:
        for ep in storyboard.get("episodes", []):
            for sc in ep.get("scenes", []):
                expected_total += float(sc.get("duration", 0))
    results.append({"check": "storyboard_total_duration", "expected_sec": expected_total,
                    "status": "ok" if expected_total > 0 else "missing"})

    artifacts = {}
    if args.artifacts and os.path.exists(args.artifacts):
        with open(args.artifacts, encoding="utf-8") as f:
            artifacts = json.load(f)

    qs = float(artifacts.get("video_quality_score", 0) or 0)
    results.append({"check": "video_quality>=4.5", "value": qs,
                    "pass": qs >= GATE_RULES["video_quality_min"]})

    sync = float(artifacts.get("av_sync_ms", 9999) or 9999)
    results.append({"check": "av_sync<100ms", "value_ms": sync,
                    "pass": sync < GATE_RULES["av_sync_max_ms"]})

    merged = float(artifacts.get("merged_duration_sec", 0) or 0)
    if expected_total > 0:
        diff = abs(merged - expected_total)
        results.append({"check": "merge_duration≈storyboard_total",
                        "merged_sec": merged, "expected_sec": expected_total,
                        "diff_sec": round(diff, 3),
                        "pass": diff <= GATE_RULES["merge_duration_tolerance_sec"]})

    l0 = artifacts.get("keyframe_l0_pass", None)
    results.append({"check": "keyframe_L0-MORPH-001", "pass": bool(l0)})

    overall = all(r.get("pass", True) for r in results)
    receipt = {"gate": "guofeng-ip-quality-gate", "overall_pass": overall,
               "checks": results, "did": DID, "trace": TRACE}
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    sys.exit(0 if overall else 1)


def main():
    ap = argparse.ArgumentParser(description="国风IP流水线总控·专家团编排")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan", help="输出阶段依赖与调度计划JSON")
    sub.add_parser("matrix", help="输出专家团矩阵JSON")
    g = sub.add_parser("gate", help="质量门禁检查")
    g.add_argument("--storyboard", help="分镜JSON路径")
    g.add_argument("--artifacts", help="产物清单JSON路径(video_quality_score/av_sync_ms/merged_duration_sec/keyframe_l0_pass)")
    args = ap.parse_args()
    {"plan": cmd_plan, "matrix": cmd_matrix, "gate": cmd_gate}[args.cmd](args)


if __name__ == "__main__":
    main()
