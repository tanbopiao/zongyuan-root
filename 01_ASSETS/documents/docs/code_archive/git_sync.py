#!/usr/bin/env python3
"""
Git仓库同步通道 (git_sync.py)
ZONGYUAN-ROOT 元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

通过Git仓库实现版本化文本同步：
- 代码/SOP/元规则/配置文件版本管理
- 差异对比和冲突解决
- 分支管理和PR流程
- 回滚到任意历史版本
- 多窗口协作（各自分支，合并时解决冲突）

【配置说明】
使用前需在 git_config.json 中配置：
{
    "repo_url": "https://github.com/your-org/zongyuan-root-sync.git",
    "branch": "main",
    "local_path": "./git_sync_repo",
    "username": "your-username",
    "email": "your-email@example.com",
    "token": "your-personal-access-token"
}

用法：
  python3 git_sync.py --init
  python3 git_sync.py --pull
  python3 git_sync.py --push --message "提交信息"
  python3 git_sync.py --status
  python3 git_sync.py --log --limit 10
  python3 git_sync.py --branch --name <分支名>
  python3 git_sync.py --diff
"""
import json
import os
import subprocess
import argparse
from datetime import datetime

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
CONFIG_FILE = "git_config.json"


def load_config():
    """加载Git配置"""
    if not os.path.exists(CONFIG_FILE):
        print(f"  ⚠ 配置文件不存在: {CONFIG_FILE}")
        print(f"  请创建配置文件，填入Git仓库信息")
        return None
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_git(args, cwd=None, timeout=60):
    """执行Git命令"""
    cmd = ["git"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()


def init_repo(config):
    """初始化Git仓库（克隆或创建）"""
    local_path = config['local_path']

    print(f"[GIT-SYNC] 初始化仓库")
    print(f"  仓库URL: {config['repo_url']}")
    print(f"  本地路径: {local_path}")
    print(f"  分支: {config['branch']}")

    if os.path.exists(local_path):
        print(f"  本地路径已存在，检查是否为Git仓库...")
        ok, out, err = run_git(["status"], cwd=local_path)
        if ok:
            print(f"  ✓ 已是Git仓库，执行pull...")
            return pull(config)
        else:
            print(f"  ⚠ 不是Git仓库，请手动处理")
            return False

    # 克隆仓库
    print(f"  克隆仓库...")
    # 带token的URL
    repo_url = config['repo_url']
    if config.get('token'):
        if 'https://' in repo_url:
            repo_url = repo_url.replace('https://', f"https://{config['username']}:{config['token']}@")

    ok, out, err = run_git(["clone", "-b", config['branch'], repo_url, local_path])
    if ok:
        print(f"  ✓ 克隆成功")
        # 配置用户信息
        run_git(["config", "user.name", config['username']], cwd=local_path)
        run_git(["config", "user.email", config['email']], cwd=local_path)
        return True
    else:
        print(f"  ✗ 克隆失败: {err[:100]}")
        return False


def pull(config):
    """拉取最新代码"""
    local_path = config['local_path']
    print(f"[GIT-SYNC] 拉取最新代码")

    ok, out, err = run_git(["pull", "origin", config['branch']], cwd=local_path)
    if ok:
        print(f"  ✓ 拉取成功")
        if out:
            print(f"  {out[:200]}")
        return True
    else:
        print(f"  ✗ 拉取失败: {err[:100]}")
        # 检查是否有冲突
        if 'CONFLICT' in err or 'conflict' in err:
            print(f"  ⚠ 检测到合并冲突，请手动解决后提交")
        return False


def push(config, message):
    """提交并推送代码"""
    local_path = config['local_path']
    print(f"[GIT-SYNC] 提交并推送")
    print(f"  提交信息: {message}")

    # 检查状态
    ok, status_out, _ = run_git(["status", "--porcelain"], cwd=local_path)
    if not status_out:
        print(f"  ⚠ 没有变更需要提交")
        return True

    print(f"  变更文件:")
    for line in status_out.split('\n')[:10]:
        print(f"    {line}")

    # 添加所有变更
    ok, _, err = run_git(["add", "-A"], cwd=local_path)
    if not ok:
        print(f"  ✗ 添加失败: {err[:100]}")
        return False

    # 提交
    commit_msg = f"[{DID}] {message} | {TRACE_MARK} | {datetime.now().isoformat()}"
    ok, _, err = run_git(["commit", "-m", commit_msg], cwd=local_path)
    if not ok:
        print(f"  ✗ 提交失败: {err[:100]}")
        return False

    # 推送
    ok, out, err = run_git(["push", "origin", config['branch']], cwd=local_path)
    if ok:
        print(f"  ✓ 推送成功")
        return True
    else:
        print(f"  ✗ 推送失败: {err[:100]}")
        return False


def show_status(config):
    """显示仓库状态"""
    local_path = config['local_path']
    print(f"[GIT-SYNC] 仓库状态")

    ok, out, _ = run_git(["status"], cwd=local_path)
    if ok:
        print(out)
    else:
        print(f"  ✗ 获取状态失败")


def show_log(config, limit=10):
    """显示提交历史"""
    local_path = config['local_path']
    print(f"[GIT-SYNC] 提交历史 (最近{limit}条)")

    ok, out, _ = run_git(["log", f"--oneline", f"-{limit}"], cwd=local_path)
    if ok:
        print(out)
    else:
        print(f"  ✗ 获取历史失败")


def create_branch(config, branch_name):
    """创建并切换分支"""
    local_path = config['local_path']
    print(f"[GIT-SYNC] 创建分支: {branch_name}")

    ok, _, err = run_git(["checkout", "-b", branch_name], cwd=local_path)
    if ok:
        print(f"  ✓ 分支创建并切换成功")
        return True
    else:
        print(f"  ✗ 创建失败: {err[:100]}")
        return False


def show_diff(config):
    """显示差异"""
    local_path = config['local_path']
    print(f"[GIT-SYNC] 变更差异")

    ok, out, _ = run_git(["diff"], cwd=local_path)
    if ok:
        if out:
            print(out[:2000])
        else:
            print("  无变更")
    else:
        print(f"  ✗ 获取差异失败")


def main():
    parser = argparse.ArgumentParser(description='Git仓库同步通道')
    parser.add_argument('--init', action='store_true', help='初始化仓库')
    parser.add_argument('--pull', action='store_true', help='拉取最新代码')
    parser.add_argument('--push', action='store_true', help='提交并推送')
    parser.add_argument('--status', action='store_true', help='显示仓库状态')
    parser.add_argument('--log', action='store_true', help='显示提交历史')
    parser.add_argument('--branch', action='store_true', help='创建分支')
    parser.add_argument('--diff', action='store_true', help='显示差异')
    parser.add_argument('--message', type=str, help='提交信息')
    parser.add_argument('--name', type=str, help='分支名')
    parser.add_argument('--limit', type=int, default=10, help='历史条数')

    args = parser.parse_args()

    print("=" * 60)
    print("  Git仓库同步通道")
    print(f"  DID: {DID} | {TRACE_MARK}")
    print("=" * 60)

    config = load_config()
    if not config:
        print("\n  配置模板（保存为 git_config.json）:")
        print(json.dumps({
            "repo_url": "https://github.com/your-org/zongyuan-root-sync.git",
            "branch": "main",
            "local_path": "./git_sync_repo",
            "username": "your-username",
            "email": "your-email@example.com",
            "token": "your-personal-access-token"
        }, indent=2, ensure_ascii=False))
        return

    if args.init:
        init_repo(config)
    elif args.pull:
        pull(config)
    elif args.push:
        if not args.message:
            print("  ✗ 需要指定 --message")
            return
        push(config, args.message)
    elif args.status:
        show_status(config)
    elif args.log:
        show_log(config, args.limit)
    elif args.branch:
        if not args.name:
            print("  ✗ 需要指定 --name")
            return
        create_branch(config, args.name)
    elif args.diff:
        show_diff(config)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
