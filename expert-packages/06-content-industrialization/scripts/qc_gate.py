#!/usr/bin/env python3
"""质检门禁 v1.0 —— 成片交付前必须通过的硬性检查（纯标准库）

门禁清单：
  G1 剧本资产已登记且有哈希锚定（防漂移）
  G2 视觉资产已登记
  G3 音频资产已登记且时长完整（>= min_audio_sec）
  G4 成片清单中的音画时长对齐（调用 audio_video_check 同套规则）
  G5 全部登记资产均有 owner 与 version
  G6 当前项目阶段必须为 QC 或之后

任一未通过 -> exit 1，禁止归档。

用法:
  python3 scripts/qc_gate.py --ledger examples/ledger.jsonl \
      --manifest examples/manifest.json --project PROJ-X --min-audio-sec 3.0
"""
import os, sys, json, argparse, time
from pathlib import Path

# 复用同包声画校验规则（避免重复实现）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_video_check import check as av_check  # noqa: E402


def load_ledger(path: Path):
    rows = []
    if path.exists():
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser(description="成片质检门禁")
    ap.add_argument("--ledger", required=True, help="资产台账 jsonl")
    ap.add_argument("--manifest", required=True, help="成片清单 JSON")
    ap.add_argument("--project", default="PROJ-X")
    ap.add_argument("--min-audio-sec", type=float, default=3.0)
    ap.add_argument("--tolerance", type=float, default=0.3)
    ap.add_argument("--min-cps", type=float, default=5.0)
    args = ap.parse_args()

    rows = load_ledger(Path(args.ledger))
    assets = {}
    current_stage = "PLANNING"
    for r in rows:
        if r.get("event") == "ASSET_REGISTERED":
            assets[r["asset_id"]] = r
        elif r.get("event") == "STAGE_ADVANCED":
            current_stage = r.get("to_stage", current_stage)

    by_type = {}
    for a in assets.values():
        by_type.setdefault(a.get("type", "?"), []).append(a)

    gates = []

    # G1 剧本
    scripts = by_type.get("script", [])
    g1_ok = bool(scripts) and all(a.get("hash") for a in scripts)
    gates.append({"gate": "G1_SCRIPT_HASH_ANCHORED", "pass": g1_ok,
                  "detail": f"script_assets={len(scripts)}"})

    # G2 视觉
    visuals = by_type.get("visual", [])
    gates.append({"gate": "G2_VISUAL_REGISTERED", "pass": bool(visuals),
                  "detail": f"visual_assets={len(visuals)}"})

    # G3 音频完整
    audios = by_type.get("audio", [])
    audio_dur = 0.0
    manifest = json.load(open(args.manifest, encoding="utf-8")) if Path(args.manifest).exists() else {}
    audio_dur = float(manifest.get("audio_duration_sec", 0))
    g3_ok = bool(audios) and audio_dur >= args.min_audio_sec
    gates.append({"gate": "G3_AUDIO_COMPLETE", "pass": g3_ok,
                  "detail": f"audio_assets={len(audios)}, audio_dur={audio_dur}s, min={args.min_audio_sec}s"})

    # G4 音画对齐
    av = av_check(manifest, args.tolerance, args.min_cps)
    gates.append({"gate": "G4_AV_ALIGNED", "pass": av["passed"], "detail": av["issues"]})

    # G5 owner+version
    g5_ok = all(a.get("owner") and a.get("version") for a in assets.values())
    gates.append({"gate": "G5_OWNER_VERSION_PRESENT", "pass": g5_ok,
                  "detail": f"total_assets={len(assets)}"})

    # G6 阶段
    stage_order = ["PLANNING", "SCRIPT", "VISUAL", "AUDIO", "SYNTH", "QC", "ARCHIVED"]
    g6_ok = stage_order.index(current_stage) >= stage_order.index("QC")
    gates.append({"gate": "G6_STAGE_AT_QC_OR_BEYOND", "pass": g6_ok,
                  "detail": f"current_stage={current_stage}"})

    passed = all(g["pass"] for g in gates)
    report = {
        "project": args.project,
        "passed": passed,
        "gates": gates,
        "asset_count": len(assets),
        "current_stage": current_stage,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "verdict": "GO_TO_ARCHIVE" if passed else "BLOCK_ARCHIVE",
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
