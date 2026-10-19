#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — AtomGit 双向同步引擎（最小 · 非破坏性实现）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

职责：本地 ↔ AtomGit 双向握手同步（真值库 / 进化产物 / 脚本）。
铁律（元宪法：风险最小 > 成本最小 > 收益最大）：
  1. 非破坏性：仅 fetch + 快进合并(--ff-only) + push；
     禁止 reset --hard / checkout -f / clean -f 等破坏性操作。
  2. 凭据走环境变量 ATOMGIT_TOKEN；
     注入 URL 仅存于进程内存，不落盘、不回显、不写入 .git/config。
  3. 无凭据 / 不可达 / 仓库处于 rebase 中 → 明确记 SKIP，绝不伪造成功。

用法：python3 atomgit_sync_engine.py [--dry-run]
环境：ATOMGIT_REPO(默认 /workspace/atomgit-mirror/zongyuan-root-sync)
      ATOMGIT_REMOTE(默认 origin) / ATOMGIT_TOKEN(可选)
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

REPO = Path(os.environ.get("ATOMGIT_REPO", "/workspace/atomgit-mirror/zongyuan-root-sync"))
REMOTE = os.environ.get("ATOMGIT_REMOTE", "origin")
TOKEN = os.environ.get("ATOMGIT_TOKEN", "")
DRY = "--dry-run" in sys.argv

REPORT_DIR = Path("/workspace/evolution/atomgit_sync")
REPORT_FILE = REPORT_DIR / "report.json"
DID_TAG = "DID-BR-000002"

# 禁止交互式凭据提示导致调度器阻塞
GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true"}


def _git(*args, timeout=90):
    r = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True, timeout=timeout, env=GIT_ENV)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def _endpoint():
    """返回本次使用的远端地址；有 token 则注入（仅内存）。"""
    rc, out, _ = _git("remote", "get-url", REMOTE)
    if rc != 0 or not out:
        return None
    if TOKEN and out.startswith("https://") and "@" not in out:
        return out.replace("https://", f"https://oauth2:{TOKEN}@", 1)
    return out


def _git_dir():
    rc, out, _ = _git("rev-parse", "--git-dir")
    if rc != 0 or not out:
        return None
    p = Path(out)
    return p if p.is_absolute() else (REPO / p)


def _write(report: dict):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def run() -> dict:
    report = {
        "did": DID_TAG,
        "run_at": datetime.now().isoformat(),
        "repo": str(REPO),
        "remote": REMOTE,
        "credentialed": bool(TOKEN),
        "dry_run": DRY,
        "non_destructive": True,
        "status": "unknown",
    }

    # 0. 仓库存在性
    if not (REPO / ".git").exists() and not (REPO / "HEAD").exists():
        report["status"] = "skipped_not_a_git_repo"
        return report

    # 1. rebase / 分离头等特殊态 → 跳过（避免破坏在途操作）
    gd = _git_dir()
    if gd and ((gd / "rebase-merge").exists() or (gd / "rebase-apply").exists()):
        report["status"] = "skipped_rebase_in_progress"
        return report

    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    if rc != 0 or branch in ("", "HEAD"):
        report["status"] = "skipped_detached_head"
        report["branch"] = branch
        return report
    report["branch"] = branch

    url = _endpoint()
    if not url:
        report["status"] = "skipped_no_remote"
        return report

    # 2. 拉取（不合并本地未提交改动）
    rc, o, e = _git("fetch", "--no-tags", url, timeout=120)
    if rc != 0:
        report["status"] = "skipped_fetch_unreachable"
        report["detail"] = (e or o)[-300:]
        return report

    upstream = f"{REMOTE}/{branch}"
    rc, o, e = _git("rev-list", "--left-right", "--count", f"{upstream}...HEAD")
    if rc != 0:
        report["status"] = "skipped_no_upstream"
        report["detail"] = (e or o)[-300:]
        return report
    behind, ahead = (int(x) for x in o.split())

    # 3. 快进合并（仅当可快进；不可快进则跳过，绝不强并）
    if behind > 0:
        if DRY:
            report["status"] = "dry_run_would_fast_forward"
            return report
        rc, o, e = _git("merge", "--ff-only", upstream)
        if rc != 0:
            report["status"] = "skipped_ff_only_blocked"
            report["detail"] = (e or o)[-300:]
            return report

    # 4. 推送本地领先提交
    if ahead > 0:
        if DRY:
            report["status"] = "dry_run_would_push"
            report["ahead"] = ahead
            return report
        rc, o, e = _git("push", url, f"HEAD:{branch}", timeout=180)
        if rc != 0:
            report["status"] = "skipped_push_failed"
            report["detail"] = (e or o)[-300:]
            return report
        report["status"] = "synced"
        report["ahead"] = ahead
        report["behind"] = behind
        return report

    report["status"] = "up_to_date"
    report["ahead"] = 0
    report["behind"] = behind
    return report


def main() -> int:
    try:
        report = run()
    except subprocess.TimeoutExpired:
        report = {"did": DID_TAG, "run_at": datetime.now().isoformat(),
                  "status": "skipped_timeout", "non_destructive": True}
    except Exception as exc:  # 兜底：引擎异常不阻断调度
        report = {"did": DID_TAG, "run_at": datetime.now().isoformat(),
                  "status": "error", "detail": str(exc), "non_destructive": True}
    _write(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # 非破坏性：SKIP 属已知配置态（视为正常），真实错误返回 2
    return 2 if report.get("status") == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
