#!/usr/bin/env python3
"""内容生产阶段看板 v1.0 —— 七阶段状态机 + 资产台账登记（纯标准库）

阶段: PLANNING -> SCRIPT -> VISUAL -> AUDIO -> SYNTH -> QC -> ARCHIVED
任意阶段可前进/回退；资产（剧本/分镜/画面/音频/成片）统一登记。

用法:
  # 登记一条资产
  python3 scripts/pipeline_board.py --ledger examples/ledger.jsonl \
      --register --asset-id SCRIPT-001 --type script --stage SCRIPT \
      --version v1.0 --owner alice --hash <sha256> --desc "项目X 第1集剧本"

  # 推进阶段（项目级）
  python3 scripts/pipeline_board.py --ledger examples/ledger.jsonl \
      --advance --project PROJ-X --to QC

  # 看板总览
  python3 scripts/pipeline_board.py --ledger examples/ledger.jsonl --board
"""
import os, sys, json, hashlib, time, argparse
from pathlib import Path
from typing import List, Dict

STAGES = ["PLANNING", "SCRIPT", "VISUAL", "AUDIO", "SYNTH", "QC", "ARCHIVED"]
STAGE_INDEX = {s: i for i, s in enumerate(STAGES)}
ASSET_TYPES = ["script", "storyboard", "visual", "audio", "subtitle", "final"]


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_ledger(path: Path) -> List[Dict]:
    rows = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def append_event(path: Path, event: Dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def cmd_register(args) -> int:
    if args.type not in ASSET_TYPES:
        print(json.dumps({"status": "ERROR", "reason": f"unknown type {args.type}; expect one of {ASSET_TYPES}"},
                         ensure_ascii=False))
        return 2
    if args.stage not in STAGES:
        print(json.dumps({"status": "ERROR", "reason": f"unknown stage {args.stage}; expect one of {STAGES}"},
                         ensure_ascii=False))
        return 2
    h = args.hash or sha256_text(args.asset_id + args.version + (args.desc or ""))
    event = {
        "event": "ASSET_REGISTERED",
        "ts": now_iso(),
        "project": args.project,
        "asset_id": args.asset_id,
        "type": args.type,
        "stage": args.stage,
        "version": args.version,
        "owner": args.owner,
        "deps": args.deps or [],
        "hash": h,
        "desc": args.desc or "",
        "did": args.did,
    }
    append_event(Path(args.ledger), event)
    print(json.dumps({"status": "OK", "event": event}, ensure_ascii=False, indent=1))
    return 0


def cmd_advance(args) -> int:
    if args.to not in STAGES:
        print(json.dumps({"status": "ERROR", "reason": f"unknown stage {args.to}"}, ensure_ascii=False))
        return 2
    event = {
        "event": "STAGE_ADVANCED",
        "ts": now_iso(),
        "project": args.project,
        "to_stage": args.to,
        "reason": args.reason or "",
        "did": args.did,
    }
    append_event(Path(args.ledger), event)
    print(json.dumps({"status": "OK", "event": event}, ensure_ascii=False, indent=1))
    return 0


def cmd_board(args) -> int:
    rows = load_ledger(Path(args.ledger))
    assets = {}
    current_stage = "PLANNING"
    for r in rows:
        if r.get("event") == "ASSET_REGISTERED":
            # 同一 asset_id 以最新版本为准（版本升级而非覆盖）
            assets[r["asset_id"]] = r
        elif r.get("event") == "STAGE_ADVANCED":
            current_stage = r.get("to_stage", current_stage)
    by_stage = {s: [] for s in STAGES}
    for a in assets.values():
        by_stage.get(a["stage"], by_stage.setdefault(a["stage"], [])).append(
            {"asset_id": a["asset_id"], "type": a["type"], "version": a["version"],
             "owner": a["owner"], "hash": a["hash"][:12]})
    summary = {
        "project": args.project,
        "current_stage": current_stage,
        "stage_index": STAGE_INDEX.get(current_stage, 0),
        "asset_count": len(assets),
        "by_stage": by_stage,
        "updated_at": now_iso(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser(description="内容生产阶段看板 / 资产台账")
    ap.add_argument("--ledger", required=True, help="台账 jsonl 路径")
    ap.add_argument("--project", default="PROJ-X")
    ap.add_argument("--did", default="<YOUR_DID>")
    ap.add_argument("--register", action="store_true", help="登记资产")
    ap.add_argument("--advance", action="store_true", help="推进项目阶段")
    ap.add_argument("--board", action="store_true", help="看板总览")
    ap.add_argument("--asset-id", default="")
    ap.add_argument("--type", default="")
    ap.add_argument("--stage", default="")
    ap.add_argument("--version", default="v1.0")
    ap.add_argument("--owner", default="tbd")
    ap.add_argument("--hash", default="")
    ap.add_argument("--deps", default="", help="逗号分隔的依赖 asset_id")
    ap.add_argument("--desc", default="")
    ap.add_argument("--to", default="", help="advance 目标阶段")
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    if args.register:
        if not args.asset_id or not args.type or not args.stage:
            print(json.dumps({"status": "ERROR", "reason": "--asset-id/--type/--stage required for --register"},
                             ensure_ascii=False))
            return 2
        args.deps = [d for d in (args.deps or "").split(",") if d]
        return cmd_register(args)
    if args.advance:
        if not args.to:
            print(json.dumps({"status": "ERROR", "reason": "--to required for --advance"}, ensure_ascii=False))
            return 2
        return cmd_advance(args)
    if args.board:
        return cmd_board(args)
    print(json.dumps({"status": "ERROR", "reason": "one of --register/--advance/--board required"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    sys.exit(main())
