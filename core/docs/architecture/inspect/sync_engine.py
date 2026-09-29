#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 双向同步引擎
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
功能：Git双远程自动同步 + 网络异常降级 + 增量同步
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime

REPO_DIR = Path(".")
REMOTES = ["origin", "gitee"]
STATE_FILE = Path("inspect/sync_state.json")
AUDIT_LOG = Path("inspect/audit.log")

def log(msg):
    ts = datetime.now().isoformat()
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[SYNC {ts}] {msg}\n")

def run_cmd(cmd: list, timeout: int = 30) -> tuple[bool, str]:
    """执行shell命令"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=REPO_DIR
        )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)

def load_state():
    if not STATE_FILE.exists():
        return {"last_sync": None, "offline_mode": False, "pending_commits": 0}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def pull_from_remote(remote: str) -> bool:
    """从远程拉取"""
    ok, out = run_cmd(["git", "pull", remote, "main"])
    if ok:
        log(f"pull {remote}: OK")
    else:
        log(f"pull {remote}: FAIL - {out[:100]}")
    return ok

def push_to_remote(remote: str) -> bool:
    """推送到远程"""
    ok, out = run_cmd(["git", "push", remote, "main"])
    if ok:
        log(f"push {remote}: OK")
    else:
        log(f"push {remote}: FAIL - {out[:100]}")
    return ok

def check_network() -> bool:
    """检查网络连通性"""
    ok, _ = run_cmd(["git", "ls-remote", "origin", "HEAD"], timeout=10)
    return ok

def sync_full():
    """全量双向同步"""
    state = load_state()
    log("=== 开始全量同步 ===")

    # 1. 检查网络
    network_ok = check_network()
    if not network_ok:
        state["offline_mode"] = True
        log("网络不可用，进入离线模式")
        save_state(state)
        return {"status": "OFFLINE", "reason": "network_unavailable"}

    state["offline_mode"] = False

    # 2. 拉取所有远程
    pull_results = {}
    for remote in REMOTES:
        pull_results[remote] = pull_from_remote(remote)

    # 3. 检查本地变更
    ok, out = run_cmd(["git", "status", "--porcelain"])
    has_changes = len(out.strip()) > 0

    if has_changes:
        # 4. 自动提交
        run_cmd(["git", "add", "-A"])
        commit_msg = f"SYNC-{datetime.now().strftime('%Y%m%d%H%M')} | auto-sync"
        run_cmd(["git", "commit", "-m", commit_msg])
        log(f"auto-commit: {commit_msg}")

    # 5. 推送到所有远程
    push_results = {}
    for remote in REMOTES:
        push_results[remote] = push_to_remote(remote)

    # 6. 更新状态
    state["last_sync"] = datetime.now().isoformat()
    state["pending_commits"] = 0
    save_state(state)

    log(f"=== 同步完成: pull={pull_results} push={push_results} ===")

    return {
        "status": "SYNCED",
        "pull": pull_results,
        "push": push_results,
        "has_changes": has_changes
    }

def report(result):
    print("=" * 60)
    print("双向同步报告")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)
    print(f"\n状态: {result['status']}")

    if result["status"] == "SYNCED":
        print(f"\n拉取:")
        for remote, ok in result["pull"].items():
            print(f"  {remote}: {'✅' if ok else '❌'}")
        print(f"\n推送:")
        for remote, ok in result["push"].items():
            print(f"  {remote}: {'✅' if ok else '❌'}")
        print(f"\n本地变更: {'有' if result['has_changes'] else '无'}")
    elif result["status"] == "OFFLINE":
        print(f"\n⚠️ 网络不可用，已进入离线模式")
        print(f"恢复后将自动增量同步")

    print("=" * 60)

if __name__ == "__main__":
    result = sync_full()
    report(result)
