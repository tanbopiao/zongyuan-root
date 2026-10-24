#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guofeng-ip-production-ledger · ledger_cli.py
国风IP生产台账管家 CLI —— CSV本地落账，零成本。

子命令:
  init                                  初始化台账目录与四表CSV表头
  record project --id ... --name ...     新建/登记项目
  record storyboard --id ... --pid ...  登记分镜
  record asset --id ... --type ...      登记资产(SHA256实算)
  status --project-id ...               查看项目状态与分镜流转
  progress --project-id ...             查看/更新进度百分比
  reconcile --project-id ... [--asset-dir DIR]   对账(台账 vs 实算哈希)

确权: DID-BR-000002 · 溯源 Ω₀⊂⊙∞⊂Ω
对账差异显式标记，禁止虚构补全。
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
CST = timezone(timedelta(hours=8))

STATUS_FLOW = ["pending", "scripted", "keyframed", "videoed", "audioed", "merged", "locked"]
ALLOWED_NEXT = {
    "pending": ["scripted"],
    "scripted": ["keyframed"],
    "keyframed": ["videoed"],
    "videoed": ["audioed"],
    "audioed": ["merged"],
    "merged": ["locked"],
    "locked": [],
}

TABLE_FIELDS = {
    "projects": ["project_id", "name", "topic", "episodes", "status", "owner",
                 "created_at", "updated_at", "did", "trace"],
    "storyboards": ["storyboard_id", "project_id", "episode", "shot_no", "visual",
                    "narration", "duration_sec", "keyframe_url", "video_url",
                    "status", "updated_at", "did", "trace"],
    "assets": ["asset_id", "type", "storyboard_id", "file_token", "sha256",
               "quality_score", "lock_status", "updated_at", "did", "trace"],
    "progress": ["project_id", "stage", "completed", "total", "percentage",
                 "updated_at", "did", "trace"],
}


def now_iso():
    return datetime.now(CST).isoformat(timespec="seconds")


def ledger_dir(base=None):
    base = base or os.environ.get("LEDGER_DIR", "./ledger")
    return base


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def table_path(base, table):
    return os.path.join(base, TABLE_FILENAMES[table])


TABLE_FILENAMES = {
    "projects": "projects.csv",
    "storyboards": "storyboards.csv",
    "assets": "assets.csv",
    "progress": "progress.csv",
}


def cmd_init(args):
    base = ledger_dir(args.dir)
    ensure_dir(base)
    for table, fields in TABLE_FIELDS.items():
        p = os.path.join(base, TABLE_FILENAMES[table])
        if not os.path.exists(p):
            write_csv(p, [], fields)
            print(f"[init] created {p}")
    print(f"[init] 台账就绪: {base}  (DID={DID}, trace={TRACE})")


def _find_row(rows, key_field, key):
    for r in rows:
        if r.get(key_field) == key:
            return r
    return None


def cmd_record_project(args):
    base = ledger_dir(args.dir)
    p = table_path(base, "projects")
    rows = read_csv(p)
    now = now_iso()
    if _find_row(rows, "project_id", args.id):
        print(f"[warn] project {args.id} already exists; refusing duplicate", file=sys.stderr)
        sys.exit(2)
    row = {
        "project_id": args.id, "name": args.name, "topic": args.topic or "",
        "episodes": args.episodes, "status": "pending", "owner": args.owner or "",
        "created_at": now, "updated_at": now, "did": DID, "trace": TRACE,
    }
    rows.append(row)
    write_csv(p, rows, TABLE_FIELDS["projects"])
    print(f"[project] +{args.id} pending  {args.name}")


def cmd_record_storyboard(args):
    base = ledger_dir(args.dir)
    sp = table_path(base, "storyboards")
    rows = read_csv(sp)
    if _find_row(rows, "storyboard_id", args.id):
        print(f"[warn] storyboard {args.id} already exists", file=sys.stderr)
        sys.exit(2)
    now = now_iso()
    row = {
        "storyboard_id": args.id, "project_id": args.pid, "episode": args.episode,
        "shot_no": args.shot, "visual": args.visual or "", "narration": args.narration or "",
        "duration_sec": args.duration or "", "keyframe_url": args.keyframe or "",
        "video_url": args.video or "", "status": "scripted", "updated_at": now,
        "did": DID, "trace": TRACE,
    }
    rows.append(row)
    write_csv(sp, rows, TABLE_FIELDS["storyboards"])
    # bump project status to scripted if still pending
    pp = table_path(base, "projects")
    prows = read_csv(pp)
    pr = _find_row(prows, "project_id", args.pid)
    if pr and pr["status"] == "pending":
        pr["status"] = "scripted"
        pr["updated_at"] = now
        write_csv(pp, prows, TABLE_FIELDS["projects"])
    print(f"[storyboard] +{args.id} -> project {args.pid} status=scripted")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_record_asset(args):
    base = ledger_dir(args.dir)
    ap = table_path(base, "assets")
    rows = read_csv(ap)
    if _find_row(rows, "asset_id", args.id):
        print(f"[warn] asset {args.id} already exists", file=sys.stderr)
        sys.exit(2)
    # sha256: 实算优先；未给文件则要求显式 --sha256（禁止虚构）
    if args.file and os.path.exists(args.file):
        digest = sha256_file(args.file)
    elif args.sha256:
        digest = args.sha256
    else:
        print("[error] 必须提供 --file(实算SHA256) 或显式 --sha256；禁止虚构补全", file=sys.stderr)
        sys.exit(3)
    now = now_iso()
    row = {
        "asset_id": args.id, "type": args.type, "storyboard_id": args.sid,
        "file_token": args.token or "", "sha256": digest,
        "quality_score": args.quality or "", "lock_status": args.lock or "pending",
        "updated_at": now, "did": DID, "trace": TRACE,
    }
    rows.append(row)
    write_csv(ap, rows, TABLE_FIELDS["assets"])
    print(f"[asset] +{args.id} type={args.type} sha256={digest[:16]}... lock={row['lock_status']}")


def cmd_status(args):
    base = ledger_dir(args.dir)
    prows = read_csv(table_path(base, "projects"))
    pr = _find_row(prows, "project_id", args.project_id)
    if not pr:
        print(f"[error] project {args.project_id} not found", file=sys.stderr)
        sys.exit(4)
    srows = read_csv(table_path(base, "storyboards"))
    mine = [s for s in srows if s.get("project_id") == args.project_id]
    print(f"project={pr['project_id']} name={pr['name']} status={pr['status']} episodes={pr['episodes']} owner={pr['owner']}")
    print(f"storyboards={len(mine)}")
    counts = {}
    for s in mine:
        counts[s['status']] = counts.get(s['status'], 0) + 1
    for st in STATUS_FLOW:
        print(f"  {st:10s} {counts.get(st,0)}")
    print(f"allowed next: {ALLOWED_NEXT.get(pr['status'], [])}")


def cmd_progress(args):
    base = ledger_dir(args.dir)
    pp = table_path(base, "progress")
    rows = read_csv(pp)
    now = now_iso()
    if args.update:
        # upsert progress row for (project, stage)
        found = None
        for r in rows:
            if r.get("project_id") == args.project_id and r.get("stage") == args.stage:
                found = r
                break
        pct = round(args.completed / args.total * 100, 2) if args.total else 0.0
        if found:
            found["completed"] = args.completed
            found["total"] = args.total
            found["percentage"] = pct
            found["updated_at"] = now
            found["did"] = DID
            found["trace"] = TRACE
        else:
            rows.append({
                "project_id": args.project_id, "stage": args.stage,
                "completed": args.completed, "total": args.total, "percentage": pct,
                "updated_at": now, "did": DID, "trace": TRACE,
            })
        write_csv(pp, rows, TABLE_FIELDS["progress"])
        print(f"[progress] {args.project_id} stage={args.stage} {args.completed}/{args.total} = {pct}%")
    else:
        mine = [r for r in rows if r.get("project_id") == args.project_id]
        if not mine:
            print(f"[info] no progress rows for {args.project_id}")
        for r in mine:
            print(f"  stage={r['stage']:10s} {r['completed']}/{r['total']} = {r['percentage']}%  @ {r['updated_at']}")


def cmd_reconcile(args):
    base = ledger_dir(args.dir)
    arows = read_csv(table_path(base, "assets"))
    mine = [a for a in arows if True]  # 全部资产对账（按storyboard/project过滤可选）
    diffs = []
    matched = 0
    checked = 0
    if args.asset_dir:
        # 实算目录下文件哈希，与台账 file_token(=文件名) 对账
        on_disk = {}
        for fn in os.listdir(args.asset_dir):
            fp = os.path.join(args.asset_dir, fn)
            if os.path.isfile(fp):
                on_disk[fn] = sha256_file(fp)
        for a in mine:
            token = a.get("file_token") or ""
            recorded = a.get("sha256") or ""
            if token in on_disk:
                checked += 1
                actual = on_disk[token]
                if actual == recorded:
                    matched += 1
                else:
                    diffs.append({
                        "asset_id": a["asset_id"], "file_token": token,
                        "recorded_sha256": recorded, "actual_sha256": actual,
                    })
    report = {
        "project_id": args.project_id,
        "checked": checked,
        "matched": matched,
        "diff_count": len(diffs),
        "diffs": diffs,
        "auto_fix": False,
        "note": "差异显式标记，禁止虚构补全",
        "did": DID, "trace": TRACE,
        "reported_at": now_iso(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if diffs:
        sys.exit(10)


def build_parser():
    ap = argparse.ArgumentParser(prog="ledger_cli")
    ap.add_argument("--dir", default=None, help="台账目录(默认 ./ledger 或 $LEDGER_DIR)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    rp = sub.add_parser("record")
    rp_sub = rp.add_subparsers(dest="kind", required=True)

    pp = rp_sub.add_parser("project")
    pp.add_argument("--id", required=True)
    pp.add_argument("--name", required=True)
    pp.add_argument("--topic", default="")
    pp.add_argument("--episodes", type=int, default=1)
    pp.add_argument("--owner", default="")

    sp = rp_sub.add_parser("storyboard")
    sp.add_argument("--id", required=True)
    sp.add_argument("--pid", required=True)
    sp.add_argument("--episode", type=int, default=1)
    sp.add_argument("--shot", type=int, default=1)
    sp.add_argument("--visual", default="")
    sp.add_argument("--narration", default="")
    sp.add_argument("--duration", type=int, default=10)
    sp.add_argument("--keyframe", default="")
    sp.add_argument("--video", default="")

    ap_ = rp_sub.add_parser("asset")
    ap_.add_argument("--id", required=True)
    ap_.add_argument("--type", required=True, choices=["image", "video", "audio"])
    ap_.add_argument("--sid", required=True, help="storyboard_id")
    ap_.add_argument("--file", default="", help="本地资产文件(实算SHA256)")
    ap_.add_argument("--sha256", default="", help="已知哈希(无文件时显式提供，禁止虚构)")
    ap_.add_argument("--token", default="", help="file_token/文件名")
    ap_.add_argument("--quality", default="")
    ap_.add_argument("--lock", default="pending")

    st = sub.add_parser("status")
    st.add_argument("--project-id", required=True)

    pr = sub.add_parser("progress")
    pr.add_argument("--project-id", required=True)
    pr.add_argument("--update", action="store_true")
    pr.add_argument("--stage", default=None, choices=STATUS_FLOW)
    pr.add_argument("--completed", type=int, default=0)
    pr.add_argument("--total", type=int, default=0)

    rc = sub.add_parser("reconcile")
    rc.add_argument("--project-id", required=True)
    rc.add_argument("--asset-dir", default="", help="实算资产目录(对账基准)")

    return ap


def main():
    args = build_parser().parse_args()
    if args.cmd == "init":
        cmd_init(args)
    elif args.cmd == "record":
        if args.kind == "project":
            cmd_record_project(args)
        elif args.kind == "storyboard":
            cmd_record_storyboard(args)
        elif args.kind == "asset":
            cmd_record_asset(args)
    elif args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "progress":
        cmd_progress(args)
    elif args.cmd == "reconcile":
        cmd_reconcile(args)


if __name__ == "__main__":
    main()
