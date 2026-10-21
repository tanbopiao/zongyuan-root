#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lite_replicate — LITE-REPLICATE-V1 通用技术轻量复刻架构执行器

四环节流水线: SCOUT(ingest) → VERIFY(ingest --verdict) → FORGE(forge) → RUN(status/verify)
零第三方依赖; 单一事实源台账 var/lite-registry.json; 高危动作(发布/删除)不在本工具域内。

用法:
  lite_replicate.py ingest NAME --source URL --paradigm "一句话范式" --verdict reuse|replicate|borrow [--note ...]
  lite_replicate.py forge NAME [--dest DIR]     # 从模板锻造最小复刻工程
  lite_replicate.py verify [NAME|--all]         # 跑在册项目测试(unittest, 零依赖)
  lite_replicate.py status                      # 台账全量状态
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template")
REGISTRY = os.path.join(ROOT, "var", "lite-registry.json")
DEFAULT_DEST = "/workspace/lite"
CST = timezone(timedelta(hours=8))
VERDICTS = {"reuse", "replicate", "borrow"}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _valid_name(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", name))


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def registry() -> dict:
    reg = _load(REGISTRY, {"version": "LITE-REPLICATE-V1", "projects": {}})
    reg.setdefault("projects", {})
    return reg


def cmd_ingest(args) -> int:
    if not _valid_name(args.name):
        print(f"invalid name: {args.name} (lowercase [a-z0-9_-])", file=sys.stderr)
        return 2
    if args.verdict not in VERDICTS:
        print(f"verdict must be one of {sorted(VERDICTS)} (S2红线: 核验失败降级borrow)", file=sys.stderr)
        return 2
    if args.verdict != "borrow" and not args.source:
        print("S2红线: verdict=reuse/replicate 必须带 --source (核验先行)", file=sys.stderr)
        return 2
    reg = registry()
    p = reg["projects"].get(args.name, {"name": args.name, "added": now()})
    p.update({
        "source": args.source,
        "paradigm": args.paradigm,
        "verdict": args.verdict,           # reuse直接复用 / replicate轻量复刻 / borrow仅借鉴
        "note": args.note or p.get("note", ""),
        "scouted_at": now(),
        "status": "verified" if args.verdict else p.get("status", "scouted"),
        "updated": now(),
    })
    reg["projects"][args.name] = p
    reg["updated"] = now()
    _save(REGISTRY, reg)
    print(json.dumps({"ok": True, "project": p}, ensure_ascii=False, indent=2))
    return 0


def _copy_template(src: str, dst: str, name: str) -> list:
    pkg = name.replace("-", "_")
    made = []
    for base, dirs, files in os.walk(src):
        rel = os.path.relpath(base, src).replace("{{PKG}}", pkg)
        outdir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(outdir, exist_ok=True)
        for orig_fn in files:
            out_fn = orig_fn.replace("{{PKG}}", pkg)
            if out_fn.endswith(".tmpl"):
                content = open(os.path.join(base, orig_fn), encoding="utf-8").read()
                content = content.replace("{{NAME}}", name).replace("{{PKG}}", pkg)
                out = os.path.join(outdir, out_fn[:-5])
                with open(out, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                out = os.path.join(outdir, out_fn)
                with open(os.path.join(base, orig_fn), "rb") as f:
                    data = f.read()
                with open(out, "wb") as f:
                    f.write(data)
            made.append(os.path.relpath(out, ROOT))
    return made


def cmd_forge(args) -> int:
    if not _valid_name(args.name):
        print(f"invalid name: {args.name}", file=sys.stderr)
        return 2
    if not os.path.isdir(TEMPLATE):
        print(f"template missing: {TEMPLATE}", file=sys.stderr)
        return 2
    reg = registry()
    p = reg["projects"].get(args.name)
    if p is None:
        # 未过S1/S2直接锻造 → 违反核验先行红线, 拒绝
        print("S2红线拒绝: 未登记(先 ingest 核验裁决后再 forge)", file=sys.stderr)
        return 2
    if p["verdict"] == "borrow":
        print("S2裁决为 borrow(仅借鉴): 不产出复刻工程", file=sys.stderr)
        return 2
    dest = os.path.join(args.dest or DEFAULT_DEST, args.name)
    if os.path.exists(dest) and os.listdir(dest):
        print(f"dest exists and not empty: {dest}", file=sys.stderr)
        return 2
    made = _copy_template(TEMPLATE, dest, args.name)
    p.update({"path": dest, "status": "forged", "updated": now(),
              "sha256_readme": _sha(os.path.join(dest, "README.md")),
              "forged_files": len(made)})
    reg["updated"] = now()
    _save(REGISTRY, reg)
    # 锻造后立即自测(S3出口条件: test全绿)
    rc = _run_tests(dest)
    print(json.dumps({"ok": rc == 0, "path": dest, "files": len(made), "smoke_rc": rc},
                     ensure_ascii=False, indent=2))
    return 0 if rc == 0 else 1


def _run_tests(path: str) -> int:
    if not os.path.isdir(os.path.join(path, "tests")):
        return 0
    p = subprocess.run([sys.executable, "-m", "unittest", "discover",
                        "-s", "tests", "-p", "test_*.py", "-v"],
                       cwd=path, capture_output=True, text=True, timeout=300)
    tail = (p.stdout or "")[-200:] + (p.stderr or "")[-200:]
    print(tail)
    return p.returncode


def cmd_verify(args) -> int:
    reg = registry()
    names = list(reg["projects"]) if args.all else [args.name]
    if not args.all and not args.name:
        print("verify: need NAME or --all", file=sys.stderr)
        return 2
    results, worst = {}, 0
    for n in names:
        p = reg["projects"].get(n)
        if not p or p.get("status") not in ("forged", "shipped"):
            results[n] = "skip (not forged)"
            continue
        path = p.get("path")
        if not path or not os.path.isdir(path):
            results[n] = "missing (path not found)"
            worst = max(worst, 1)
            continue
        rc = _run_tests(path)
        results[n] = "PASS" if rc == 0 else f"FAIL(rc={rc})"
        worst = max(worst, rc if rc else 0)
        p["last_check"] = now()
        p["last_check_ok"] = rc == 0
        p["last_check_fail"] = p.get("last_check_fail", 0) + (1 if rc else 0)
        if rc == 0:
            p["last_check_fail"] = 0
    reg["updated"] = now()
    _save(REGISTRY, reg)
    print(json.dumps({"results": results, "ok": worst == 0}, ensure_ascii=False, indent=2))
    return worst


def cmd_status(args) -> int:
    reg = registry()
    out = {"registry": REGISTRY, "updated": reg.get("updated"), "count": len(reg["projects"]),
           "projects": reg["projects"]}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="lite_replicate", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest", help="S1/S2: 登记吸收源与核验裁决")
    pi.add_argument("name")
    pi.add_argument("--source", default="", help="外源URL (reuse/replicate必填)")
    pi.add_argument("--paradigm", required=True, help="一句话范式")
    pi.add_argument("--verdict", choices=sorted(VERDICTS), required=True)
    pi.add_argument("--note", default="")
    pf = sub.add_parser("forge", help="S3: 模板锻造最小复刻工程")
    pf.add_argument("name")
    pf.add_argument("--dest", default=None)
    pv = sub.add_parser("verify", help="S4: 跑在册项目测试")
    pv.add_argument("name", nargs="?", default=None)
    pv.add_argument("--all", action="store_true")
    ps = sub.add_parser("status", help="台账状态")
    args = ap.parse_args()
    return {"ingest": cmd_ingest, "forge": cmd_forge,
            "verify": cmd_verify, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
