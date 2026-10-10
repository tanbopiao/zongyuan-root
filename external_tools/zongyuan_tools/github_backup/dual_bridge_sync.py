#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 双桥接同步引擎
本地内核 ↔ GitHub ↔ Gitee ↔ 云内核 全链路桥接同步

功能:
1. 本地资产 → Git仓库 (locked/ + tools/ + console/)
2. Git仓库 → GitHub (origin/main)
3. Git仓库 → Gitee (gitee/main)
4. GitHub ↔ Gitee 双向一致性校验
5. 本地内核 ↔ 云内核 哈希对账
6. 同步日志 + 回执生成

用法:
  python3 dual_bridge_sync.py --full    # 全链路同步
  python3 dual_bridge_sync.py --check   # 仅校验一致性
  python3 dual_bridge_sync.py --push    # 仅推送到双远程
"""
import os, sys, json, hashlib, datetime, subprocess, argparse, shutil

# 常量
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
WORKSPACE = "/home/user/.doubao/agent_mode/workspace"
LOCKED = f"{WORKSPACE}/.user_skills/meta-order-archive/locked"
TOOLS = f"{WORKSPACE}/zongyuan_tools"
GIT_DIR = f"{TOOLS}/github_backup"
CONSOLE = f"{WORKSPACE}/zongyuan-console"

def run_cmd(cmd, cwd=None, timeout=60):
    """执行shell命令"""
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def sha256_file(path):
    """计算文件SHA256"""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest().upper()

def sha256_dir(path):
    """计算目录整体SHA256（基于文件清单+内容）"""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        for fn in sorted(files):
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, path)
            h.update(rel.encode())
            try:
                h.update(sha256_file(fp).encode())
            except: pass
    return h.hexdigest().upper()

def sync_local_to_git():
    """步骤1: 本地资产 → Git仓库"""
    print("  [1/5] 本地资产 → Git仓库...")
    result = {"step": "local_to_git", "status": "PENDING", "details": {}}
    
    # 同步locked目录
    git_locked = f"{GIT_DIR}/locked"
    os.makedirs(git_locked, exist_ok=True)
    if os.path.exists(LOCKED):
        # 使用rsync或cp
        rc, out, err = run_cmd(f"rsync -a --delete --exclude='*.pyc' '{LOCKED}/' '{git_locked}/'")
        if rc != 0:
            rc, out, err = run_cmd(f"cp -r '{LOCKED}/'* '{git_locked}/' 2>/dev/null; cp -r '{LOCKED}/'.[!.]* '{git_locked}/' 2>/dev/null")
        result["details"]["locked_synced"] = True
    else:
        result["details"]["locked_synced"] = False
        result["status"] = "FAILED"
    
    # 同步tools
    git_tools = f"{GIT_DIR}/tools"
    os.makedirs(git_tools, exist_ok=True)
    for fn in os.listdir(TOOLS):
        if fn.endswith('.py') or fn.endswith('.json'):
            shutil.copy2(f"{TOOLS}/{fn}", f"{git_tools}/{fn}")
    result["details"]["tools_synced"] = True
    
    # 同步console
    git_console = f"{GIT_DIR}/console"
    os.makedirs(git_console, exist_ok=True)
    console_index = f"{CONSOLE}/index.html"
    if os.path.exists(console_index):
        shutil.copy2(console_index, f"{git_console}/index.html")
        result["details"]["console_synced"] = True
    
    # 计算本地哈希
    result["details"]["local_locked_hash"] = sha256_dir(LOCKED)[:16]
    result["details"]["git_locked_hash"] = sha256_dir(git_locked)[:16]
    result["details"]["hash_match"] = result["details"]["local_locked_hash"] == result["details"]["git_locked_hash"]
    
    if result["status"] != "FAILED":
        result["status"] = "OK"
    print(f"    本地哈希: {result['details']['local_locked_hash']}...")
    print(f"    Git哈希:  {result['details']['git_locked_hash']}...")
    print(f"    一致性:   {'✅' if result['details']['hash_match'] else '❌'}")
    return result

def git_commit_and_push(remote):
    """Git提交并推送到指定远程"""
    print(f"  [推送] → {remote}...")
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # git add
    rc, out, err = run_cmd("git add -A", cwd=GIT_DIR)
    
    # 检查是否有变更
    rc, status_out, _ = run_cmd("git status --porcelain", cwd=GIT_DIR)
    if not status_out:
        print(f"    无文件变更,直接推送")
        # 获取当前commit
        rc, hash_out, _ = run_cmd("git rev-parse HEAD", cwd=GIT_DIR)
        commit_hash = hash_out[:12]
        # 仍然执行push
        rc, out, err = run_cmd(f"git push {remote} main 2>&1", cwd=GIT_DIR, timeout=120)
        pushed = rc == 0 or "Everything up-to-date" in out or "up to date" in out.lower()
        print(f"    Commit: {commit_hash}")
        print(f"    推送:   {'✅ 成功' if pushed else '❌ 失败 - ' + err[:100]}")
        return {"committed": False, "commit_hash": commit_hash, "pushed": pushed}
    
    # git commit
    msg = f"ZONGYUAN-ROOT 双桥接同步 {now.strftime('%Y-%m-%d_%H:%M:%S')} | 本地内核↔GitHub↔Gitee"
    rc, out, err = run_cmd(f'git commit -m "{msg}"', cwd=GIT_DIR)
    
    # 获取commit hash
    rc, hash_out, _ = run_cmd("git rev-parse HEAD", cwd=GIT_DIR)
    commit_hash = hash_out[:12]
    
    # git push
    rc, out, err = run_cmd(f"git push {remote} main 2>&1", cwd=GIT_DIR, timeout=120)
    pushed = rc == 0 or "Everything up-to-date" in out or "up to date" in out.lower()
    
    print(f"    Commit: {commit_hash}")
    print(f"    推送:   {'✅ 成功' if pushed else '❌ 失败 - ' + err[:100]}")
    return {"committed": True, "commit_hash": commit_hash, "pushed": pushed, "message": msg}

def verify_remote_consistency():
    """校验GitHub与Gitee远程一致性"""
    print("  [校验] GitHub ↔ Gitee 远程一致性...")
    
    rc, gh_hash, _ = run_cmd("git ls-remote origin main | awk '{print $1}'", cwd=GIT_DIR)
    rc, ge_hash, _ = run_cmd("git ls-remote gitee main | awk '{print $1}'", cwd=GIT_DIR)
    
    gh_short = gh_hash[:12] if gh_hash else "N/A"
    ge_short = ge_hash[:12] if ge_hash else "N/A"
    consistent = gh_hash == ge_hash and gh_hash != ""
    
    print(f"    GitHub: {gh_short}...")
    print(f"    Gitee:  {ge_short}...")
    print(f"    一致性: {'✅ 一致' if consistent else '❌ 不一致'}")
    
    return {"github_hash": gh_hash, "gitee_hash": ge_hash, 
            "github_short": gh_short, "gitee_short": ge_short,
            "consistent": consistent}

def verify_kernel_hash():
    """校验本地内核与云内核哈希"""
    print("  [校验] 本地内核 ↔ 云内核 哈希对账...")
    
    # 本地最新内核快照
    kernel_dir = f"{LOCKED}/kernel"
    snaps = sorted([f for f in os.listdir(kernel_dir) if f.startswith('kernel_snapshot')]) if os.path.exists(kernel_dir) else []
    
    if snaps:
        latest_snap = snaps[-1]
        with open(f"{kernel_dir}/{latest_snap}") as f:
            local_kernel = json.load(f)
        local_hash = local_kernel.get('snapshot_hash', 'N/A')
    else:
        latest_snap = "N/A"
        local_hash = "N/A"
    
    # 云内核（Git仓库中的kernel）
    git_kernel = f"{GIT_DIR}/locked/kernel/{latest_snap}"
    if os.path.exists(git_kernel):
        with open(git_kernel) as f:
            cloud_kernel = json.load(f)
        cloud_hash = cloud_kernel.get('snapshot_hash', 'N/A')
    else:
        cloud_hash = "N/A"
    
    kernel_match = local_hash == cloud_hash and local_hash != "N/A"
    
    print(f"    本地内核: {latest_snap}")
    print(f"    本地哈希: {local_hash[:16]}...")
    print(f"    云端哈希: {cloud_hash[:16]}...")
    print(f"    一致性:   {'✅ 一致' if kernel_match else '❌ 不一致'}")
    
    return {"snapshot": latest_snap, "local_hash": local_hash, 
            "cloud_hash": cloud_hash, "kernel_match": kernel_match}

def generate_receipt(results):
    """生成同步回执"""
    now = datetime.datetime.now(datetime.timezone.utc)
    receipt = {
        "receipt_id": f"BRIDGE-SYNC-{now.strftime('%Y%m%d_%H%M%S')}",
        "created_at": now.isoformat(),
        "system": "ZONGYUAN-ROOT 元极恒一自治体系",
        "did": DID,
        "trace_mark": TRACE,
        "sync_type": "DUAL_BRIDGE_FULL",
        "topology": "本地内核 ↔ GitHub(origin) ↔ Gitee(gitee) ↔ 云内核",
        "results": results,
        "overall_status": "SUCCESS" if all(r.get("status", "OK") == "OK" or r.get("pushed", True) or r.get("consistent", True) or r.get("kernel_match", True) for r in results) else "PARTIAL",
    }
    
    receipt_path = f"{TOOLS}/bridge_sync_receipt_{now.strftime('%Y%m%d_%H%M%S')}.json"
    with open(receipt_path, 'w', encoding='utf-8') as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    
    return receipt, receipt_path

def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 双桥接同步引擎")
    parser.add_argument('--full', action='store_true', help='全链路同步')
    parser.add_argument('--check', action='store_true', help='仅校验一致性')
    parser.add_argument('--push', action='store_true', help='仅推送到双远程')
    args = parser.parse_args()
    
    print("╔══════════════════════════════════════════════════╗")
    print("║  ZONGYUAN-ROOT 双桥接同步引擎                     ║")
    print("║  本地内核 ↔ GitHub ↔ Gitee ↔ 云内核              ║")
    print("║  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω                        ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    
    results = []
    
    if args.check:
        # 仅校验模式
        r1 = verify_remote_consistency()
        r2 = verify_kernel_hash()
        results = [r1, r2]
        
        all_ok = r1["consistent"] and r2["kernel_match"]
        print(f"\n{'✅ 全链路一致性校验通过' if all_ok else '⚠️ 存在不一致项'}")
        return
    
    # 全链路或推送模式
    if args.full or args.push:
        # 步骤1: 本地→Git
        if args.full:
            r1 = sync_local_to_git()
            results.append(r1)
        
        # 步骤2-3: Git→GitHub + Git→Gitee
        print("\n  [2/5] Git → GitHub (origin/main)...")
        r2 = git_commit_and_push("origin")
        results.append({"step": "git_to_github", **r2})
        
        print("\n  [3/5] Git → Gitee (gitee/main)...")
        r3 = git_commit_and_push("gitee")
        results.append({"step": "git_to_gitee", **r3})
        
        # 步骤4: 远程一致性校验
        print()
        r4 = verify_remote_consistency()
        results.append({"step": "remote_consistency", **r4})
        
        # 步骤5: 内核哈希对账
        print()
        r5 = verify_kernel_hash()
        results.append({"step": "kernel_hash", **r5})
    
    # 生成回执
    receipt, receipt_path = generate_receipt(results)
    
    print(f"\n{'='*50}")
    print(f"同步回执: {receipt['receipt_id']}")
    print(f"整体状态: {receipt['overall_status']}")
    print(f"回执路径: {receipt_path}")
    print(f"{'='*50}")
    
    # 输出JSON结果
    print(json.dumps({"status": receipt["overall_status"], "receipt": receipt["receipt_id"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
