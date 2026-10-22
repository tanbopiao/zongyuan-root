#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_shared_brain.py — 简易版共享大脑 · 半自动同步脚本（模式 B）
仅做 4 件轻量任务，无稳态打分 / 自动评审 / 自主进化；合并必须人工放行。

  ① 拉取 Gitee 远端最新 converge 基线（git pull --ff-only）
  ② 导入多维表格导出文件到 sandbox/staging/
  ③ 对比新旧文件差异，计算 SHA256
  ④ 有差异时：写入 truth-ledger.csv + git commit + push（仅 --apply 执行；默认 dry-run 只报告）

用法：
  python3 sync_shared_brain.py --export base_export.csv            # dry-run：只看差异
  python3 sync_shared_brain.py --export base_export.csv --apply    # 人工核对后放行
  python3 sync_shared_brain.py --init-repo                          # 在空目录初始化 shared-brain 仓库
  python3 sync_shared_brain.py --export x.csv --no-pull --no-push   # 离线节点只做本地 diff+存证

退出码：0=无差异或已放行；2=dry-run 且存在待核验差异；1=错误
"""
import argparse
import csv
import datetime
import hashlib
import os
import shutil
import subprocess
import sys

LEDGER = os.path.join("converge", "truth-ledger.csv")
STAGING = os.path.join("sandbox", "staging")
CONVERGE_TABLE = os.path.join("converge", "truth-table.csv")  # 表格台账在真值区的落位
LEDGER_HEADER = ["seq", "timestamp", "node_id", "file_path", "action",
                 "sha256", "summary", "operator", "status", "commit"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def now_ts():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def run(cmd, allow_fail=True):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 and not allow_fail:
        raise RuntimeError("%s -> %s%s" % (" ".join(cmd), p.stdout.strip(), p.stderr.strip()))
    return p


def git_repo_ok():
    return os.path.isdir(os.path.join(".git"))


# ---------- ① 拉取远端基线 ----------
def pull_baseline(no_pull=False):
    if no_pull:
        print("[1/4] 跳过拉取 (--no-pull)")
        return True
    if not git_repo_ok():
        print("[1/4] 非 git 仓库，跳过拉取")
        return True
    r = run(["git", "pull", "--ff-only", "origin", "HEAD"])
    if r.returncode != 0:
        # 本地领先（已有未推提交）不算失败
        if "Already up to date" in (r.stdout + r.stderr) or "Already up to date" in r.stderr:
            print("[1/4] 远端基线已是最新")
            return True
        print("[1/4] ⚠ 拉取失败(不阻断, 离线可继续): %s" % (r.stderr.strip() or r.stdout.strip()))
        return False
    print("[1/4] 已拉取远端 converge 基线")
    return True


# ---------- ② 导入表格导出到 sandbox ----------
def stage_export(export_path):
    print("[2/4] 暂存表格导出 -> %s" % STAGING)
    os.makedirs(STAGING, exist_ok=True)
    if not export_path:
        print("      (未提供 --export, 跳过导入)")
        return None
    if not os.path.exists(export_path):
        raise FileNotFoundError("导出文件不存在: %s" % export_path)
    dst = os.path.join(STAGING, os.path.basename(export_path))
    shutil.copy2(export_path, dst)
    print("      %s -> %s" % (export_path, dst))
    return dst


# ---------- ③ 差异 + SHA256 ----------
def diff_against_converge(staged):
    print("[3/4] 计算差异与 SHA256")
    if not staged:
        return None
    if not os.path.exists(CONVERGE_TABLE):
        return {"kind": "new", "target": CONVERGE_TABLE,
                "new_sha": sha256_file(staged), "staged": staged}
    old_sha, new_sha = sha256_file(CONVERGE_TABLE), sha256_file(staged)
    if old_sha == new_sha:
        print("      无差异 (sha256=%s...)" % new_sha[:16])
        return None
    # 行级差异摘要（CSV）
    added, removed = [], []
    try:
        def rows(p):
            with open(p, newline="", encoding="utf-8-sig") as f:
                return {tuple(r) for r in csv.reader(f)}
        old_rows, new_rows = rows(CONVERGE_TABLE), rows(staged)
        added = sorted(new_rows - old_rows)[:20]
        removed = sorted(old_rows - new_rows)[:20]
    except Exception as e:
        print("      (行级 diff 解析失败: %s, 仅做整体哈希比对)" % e)
    print("      有差异: %s... -> %s... | 新增行 %d / 移除行 %d"
          % (old_sha[:16], new_sha[:16], len(added), len(removed)))
    return {"kind": "update", "target": CONVERGE_TABLE,
            "old_sha": old_sha, "new_sha": new_sha,
            "staged": staged, "added": added, "removed": removed}


# ---------- ④ 账本 + 提交（仅 --apply） ----------
def ledger_next_seq():
    if not os.path.exists(LEDGER):
        return 1
    with open(LEDGER, encoding="utf-8") as f:
        rows = [r for r in csv.reader(f) if r and r[0].isdigit()]
    return (max(int(r[0]) for r in rows) + 1) if rows else 1


def append_ledger(diff, node_id, operator):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    is_new = not os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(LEDGER_HEADER)
        w.writerow([
            ledger_next_seq(), now_ts(), node_id, diff["target"].replace(os.sep, "/"),
            "merge", diff["new_sha"],
            ("新增表格台账" if diff["kind"] == "new"
             else "表格台账更新(新增%d/移除%d行)" % (len(diff.get("added", [])), len(diff.get("removed", [])))),
            operator, "merged", "",
        ])
    print("[4/4] 账本已追加: seq 详见 %s" % LEDGER)


def apply_change(diff, node_id, operator, no_push=False):
    # 落位: staging -> converge
    os.makedirs(os.path.dirname(CONVERGE_TABLE), exist_ok=True)
    shutil.copy2(diff["staged"], CONVERGE_TABLE)
    append_ledger(diff, node_id, operator)
    if not git_repo_ok():
        print("      非 git 仓库, 仅本地落位 (git init 后可推送 Gitee)")
        return
    run(["git", "add", CONVERGE_TABLE, LEDGER])
    msg = "sync: %s %s sha256=%s..." % (
        os.path.basename(CONVERGE_TABLE), diff["kind"], diff["new_sha"][:12])
    run(["git", "commit", "-m", msg], allow_fail=False)
    print("      commit: %s" % msg)
    # 回填该变更提交的短哈希（独立小提交，避免 amend 导致哈希漂移）
    h = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    if h:
        with open(LEDGER, encoding="utf-8") as f:
            lines = f.read().splitlines()
        if lines:
            last = lines[-1].rstrip("\n").split(",")
            if len(last) == len(LEDGER_HEADER) and not last[-1]:
                last[-1] = h
                lines[-1] = ",".join(last)
                with open(LEDGER, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                run(["git", "add", LEDGER])
                run(["git", "commit", "-m", "ledger: backfill commit %s" % h],
                    allow_fail=False)
    if not no_push:
        pr = run(["git", "push", "origin", "HEAD"])
        print("      push: %s" % ("OK" if pr.returncode == 0 else
                                  "FAILED(%s)" % (pr.stderr.strip() or pr.stdout.strip())))


# ---------- 仓库初始化（照搬目录规范） ----------
def init_repo():
    dirs = ["converge/rule", "sandbox", "archive"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(LEDGER):
        with open(LEDGER, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(LEDGER_HEADER)
    print("目录骨架已就绪: %s" % ", ".join(dirs + [LEDGER]))
    if not git_repo_ok():
        run(["git", "init", "-b", "converge"])
        print("git 已初始化在 converge 分支（唯一真值源），请配置 Gitee 远端后推送。")


def main():
    ap = argparse.ArgumentParser(description="简易版共享大脑 半自动同步 (默认 dry-run 人工放行)")
    ap.add_argument("--export", help="多维表格导出的 CSV 文件路径")
    ap.add_argument("--apply", action="store_true", help="人工核对后放行: 写账本+commit+push")
    ap.add_argument("--init-repo", action="store_true", help="初始化 shared-brain 目录骨架")
    ap.add_argument("--node", default="local-node", help="节点标识 (默认 local-node)")
    ap.add_argument("--operator", default="sync_shared_brain.py", help="操作人标识")
    ap.add_argument("--no-pull", action="store_true", help="跳过拉取远端基线")
    ap.add_argument("--no-push", action="store_true", help="提交但不推送")
    args = ap.parse_args()

    if args.init_repo:
        init_repo()
        return 0

    print("== 共享大脑同步 (mode=%s) ==" % ("APPLY" if args.apply else "DRY-RUN"))
    pull_baseline(args.no_pull)                      # ①
    staged = stage_export(args.export)               # ②
    diff = diff_against_converge(staged)             # ③
    if diff is None:
        print("== 无待处理变更 ==")
        return 0
    if args.apply:                                   # ④ 人工放行
        apply_change(diff, args.node, args.operator, args.no_push)
        print("== 已放行并存证 ==")
        return 0
    print("== DRY-RUN: 存在待核验差异 (--apply 放行) ==")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR: %s" % e, file=sys.stderr)
        sys.exit(1)
