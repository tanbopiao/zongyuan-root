#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT Git桥接同步中间层
打通：本地内核 ↔ Git仓库(GitHub/Gitee) ↔ 云内核 三向同步链路

功能：
1. 本地资产变更检测
2. GitHub/Gitee双向推送
3. 云内核状态同步
4. 记忆索引自动更新
5. 冲突检测与自愈
"""
import os
import json
import subprocess
import hashlib
import sys
from datetime import datetime

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = BASE_ROOT
GIT_DIR = os.path.join(ENGINE_DIR, ".git")
LOG_FILE = os.path.join(ENGINE_DIR, "log", "git_bridge_sync.log")
INDEX_PATH = os.path.join(ENGINE_DIR, "runtime", "memory_index.json")
KERNEL_PATH = os.path.join(BASE_ROOT, "Ω-Brainμ", "kernel.json")

REMOTES = {
    "github": "https://github.com/tanbopiao/ZONGYUAN-ROOT.git",
    "gitee": "https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT.git"
}


def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    print(msg)


def run_git(args, cwd=None):
    """执行git命令"""
    cmd = ["git"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd or ENGINE_DIR)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def check_local_changes():
    """检测本地变更"""
    ok, out, err = run_git(["status", "--porcelain"])
    if not ok:
        return []
    changes = [line for line in out.split("\n") if line.strip()]
    return changes


def commit_changes(message):
    """提交本地变更"""
    run_git(["add", "-A"])
    ok, out, err = run_git(["commit", "-m", message])
    if ok:
        log(f"本地提交成功: {message}")
        return True
    if "nothing to commit" in err or "nothing to commit" in out:
        log("无变更需要提交")
        return True
    log(f"提交失败: {err}")
    return False


def push_to_remote(remote_name):
    """推送到指定远程"""
    ok, out, err = run_git(["push", remote_name, "main", "--force"])
    if ok:
        log(f"推送{remote_name}成功")
        return True
    log(f"推送{remote_name}失败: {err}")
    return False


def pull_from_remote(remote_name):
    """从远程拉取"""
    ok, out, err = run_git(["pull", remote_name, "main", "--rebase", "--allow-unrelated-histories"])
    if ok:
        log(f"拉取{remote_name}成功")
        return True
    log(f"拉取{remote_name}失败: {err}")
    return False


def sync_kernel_state():
    """同步云内核状态"""
    if not os.path.exists(KERNEL_PATH):
        log("内核文件不存在，跳过内核同步")
        return False
    try:
        with open(KERNEL_PATH, encoding="utf-8") as f:
            kernel = json.load(f)
        kernel["last_sync_time"] = datetime.now().isoformat()
        kernel["sync_remotes"] = list(REMOTES.keys())
        kernel["kernel_hash"] = hashlib.sha256(
            json.dumps(kernel, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        with open(KERNEL_PATH, "w", encoding="utf-8") as f:
            json.dump(kernel, f, ensure_ascii=False, indent=2)
        log("云内核状态同步完成")
        return True
    except Exception as e:
        log(f"内核同步失败: {e}")
        return False


def update_memory_index():
    """更新记忆索引"""
    if not os.path.exists(INDEX_PATH):
        log("记忆索引不存在，跳过更新")
        return False
    try:
        with open(INDEX_PATH, encoding="utf-8") as f:
            idx = json.load(f)
        idx["index_meta"]["index_update_time"] = datetime.now().isoformat()
        idx["index_meta"]["sync_status"] = "GIT_BRIDGE_SYNCED"
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        log("记忆索引更新完成")
        return True
    except Exception as e:
        log(f"索引更新失败: {e}")
        return False


def detect_conflicts():
    """检测合并冲突"""
    ok, out, err = run_git(["diff", "--name-only", "--diff-filter=U"])
    if ok and out.strip():
        conflicts = out.split("\n")
        log(f"检测到冲突文件: {conflicts}")
        return conflicts
    return []


def full_sync():
    """执行完整三向同步"""
    log("=" * 50)
    log("Git桥接同步中间层 - 完整同步开始")
    log("=" * 50)

    result = {
        "local_changes": 0,
        "github_push": False,
        "gitee_push": False,
        "kernel_sync": False,
        "index_update": False,
        "conflicts": [],
        "status": "PENDING"
    }

    # 1. 检测本地变更
    changes = check_local_changes()
    result["local_changes"] = len(changes)
    log(f"本地变更文件数: {len(changes)}")

    # 2. 提交变更
    if changes:
        snap_id = f"SNAP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-GIT-BRIDGE"
        commit_changes(f"{snap_id} Git桥接同步自动提交 {len(changes)}个文件变更")

    # 3. 检测冲突
    conflicts = detect_conflicts()
    result["conflicts"] = conflicts
    if conflicts:
        result["status"] = "CONFLICT"
        log("存在合并冲突，同步中止")
        return result

    # 4. 推送到GitHub
    result["github_push"] = push_to_remote("github")

    # 5. 推送到Gitee
    result["gitee_push"] = push_to_remote("gitee")

    # 6. 同步云内核状态
    result["kernel_sync"] = sync_kernel_state()

    # 7. 更新记忆索引
    result["index_update"] = update_memory_index()

    # 8. 提交内核和索引变更
    final_changes = check_local_changes()
    if final_changes:
        commit_changes(f"sync: 内核状态+记忆索引同步 {datetime.now().isoformat()}")
        push_to_remote("github")
        push_to_remote("gitee")

    all_ok = result["github_push"] and result["gitee_push"]
    result["status"] = "SYNCED" if all_ok else "PARTIAL"

    log("=" * 50)
    log(f"同步完成: {result['status']}")
    log(f"GitHub: {'OK' if result['github_push'] else 'FAIL'}")
    log(f"Gitee: {'OK' if result['gitee_push'] else 'FAIL'}")
    log(f"内核同步: {'OK' if result['kernel_sync'] else 'FAIL'}")
    log(f"索引更新: {'OK' if result['index_update'] else 'FAIL'}")
    log("=" * 50)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT Git桥接同步中间层")
    parser.add_argument("--mode", choices=["full", "push", "pull", "status"], default="full")
    parser.add_argument("--remote", choices=["github", "gitee", "all"], default="all")
    args = parser.parse_args()

    if args.mode == "status":
        changes = check_local_changes()
        print(json.dumps({"local_changes": len(changes), "files": changes}, ensure_ascii=False, indent=2))
    elif args.mode == "push":
        if args.remote in ["github", "all"]:
            push_to_remote("github")
        if args.remote in ["gitee", "all"]:
            push_to_remote("gitee")
    elif args.mode == "pull":
        if args.remote in ["github", "all"]:
            pull_from_remote("github")
        if args.remote in ["gitee", "all"]:
            pull_from_remote("gitee")
    else:
        result = full_sync()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["status"] == "SYNCED" else 1)


if __name__ == "__main__":
    main()
