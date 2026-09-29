#!/usr/bin/env python3
"""
ZONGYUAN-ROOT Git桥接同步脚本
方向1: 云内核 -> Git仓库 (push)
方向2: Git仓库 -> 云内核 (pull)
方向3: Git仓库 -> 本地内核 (pull, 在本地执行)
"""
import os, sys, json, hashlib, time, subprocess, shutil

GIT_BRIDGE = "/opt/zongyuan-git-bridge"
CLOUD_KERNEL = "/opt/ZONGYUAN-ROOT/kernel.json"
GITEE_REMOTE = "https://huodou-cloud-intelligence-aios:9407c9b3bb5a9e371d70ee24fe6d08dc@gitee.com/huodou-cloud-intelligence-aios/zongyuan-root-kernel.git"
GITHUB_REMOTE = "https://tanbopiao:github_pat_11BLAHBLAH@github.com/tanbopiao/zongyuan-root-kernel.git"

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=60)
    return r.returncode, r.stdout.strip(), r.stderr.strip()

def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def sync_cloud_to_git():
    """云内核 -> Git仓库"""
    print("[云->Git] 开始同步")
    # 复制云内核到桥接目录
    if os.path.exists(CLOUD_KERNEL):
        shutil.copy2(CLOUD_KERNEL, os.path.join(GIT_BRIDGE, "kernel.json"))
        print("  内核已复制: %s" % sha256_file(CLOUD_KERNEL)[:16])
    
    # 提交并推送
    code, out, err = run("git add -A", GIT_BRIDGE)
    code, out, err = run("git commit -m \"云内核同步 %s | SHA:%s\"" % (time.strftime("%Y%m%d_%H%M%S"), sha256_file(CLOUD_KERNEL)[:16]), GIT_BRIDGE)
    if "nothing to commit" in out:
        print("  无变更，跳过提交")
        return True
    print("  提交: %s" % out.split("\n")[-1] if out else "ok")
    
    # 推送到双远程
    code, out, err = run("git push gitee main", GIT_BRIDGE)
    print("  Gitee推送: %s" % ("成功" if code == 0 else "失败: " + err[:100]))
    code, out, err = run("git push github main", GIT_BRIDGE)
    print("  GitHub推送: %s" % ("成功" if code == 0 else "失败: " + err[:100]))
    return True

def sync_git_to_cloud():
    """Git仓库 -> 云内核"""
    print("[Git->云] 开始同步")
    code, out, err = run("git pull gitee main", GIT_BRIDGE)
    print("  拉取: %s" % ("成功" if code == 0 else "失败: " + err[:100]))
    
    # 复制Git中的内核到云内核
    git_kernel = os.path.join(GIT_BRIDGE, "kernel.json")
    if os.path.exists(git_kernel):
        # 验证JSON合法
        try:
            with open(git_kernel) as f:
                json.load(f)
            shutil.copy2(git_kernel, CLOUD_KERNEL)
            print("  内核已更新: %s" % sha256_file(git_kernel)[:16])
        except json.JSONDecodeError as e:
            print("  JSON不合法，跳过: %s" % e)
            return False
    return True

def status():
    """状态检查"""
    print("=== Git桥接状态 ===")
    print("云内核SHA: %s" % sha256_file(CLOUD_KERNEL)[:16] if os.path.exists(CLOUD_KERNEL) else "云内核不存在")
    git_kernel = os.path.join(GIT_BRIDGE, "kernel.json")
    print("Git内核SHA: %s" % sha256_file(git_kernel)[:16] if os.path.exists(git_kernel) else "Git内核不存在")
    code, out, err = run("git log --oneline -1", GIT_BRIDGE)
    print("最新提交: %s" % out)
    code, out, err = run("git remote -v", GIT_BRIDGE)
    print("远程仓库:\n%s" % out)

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "push":
        sync_cloud_to_git()
    elif action == "pull":
        sync_git_to_cloud()
    elif action == "sync":
        sync_cloud_to_git()
        sync_git_to_cloud()
    else:
        status()
