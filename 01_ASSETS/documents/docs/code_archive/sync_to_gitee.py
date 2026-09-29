#!/usr/bin/env python3
"""
资产自动同步脚本：云服务器 → Gitee仓库
功能：把S级精品图片同步到Gitee仓库，实现CDN分发
"""
import os
import subprocess
import hashlib
from datetime import datetime

WEB_ROOT = "/www/wwwroot/huodouai.com"
S_GALLERY_DIR = os.path.join(WEB_ROOT, "gallery/s")
TRACKED_FILE = "/opt/auto-evolve/synced_files.txt"

def load_synced():
    """加载已同步的文件列表"""
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_synced(files):
    """保存已同步的文件列表"""
    with open(TRACKED_FILE, 'w') as f:
        for f in sorted(files):
            f.write(f + '\n')

def get_new_files():
    """获取新增的S级精品文件"""
    synced = load_synced()
    new_files = []
    
    if os.path.exists(S_GALLERY_DIR):
        for f in os.listdir(S_GALLERY_DIR):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                if f not in synced:
                    new_files.append(f)
    
    return new_files, synced

def git_commit_and_push():
    """git add + commit + push"""
    os.chdir(WEB_ROOT)
    
    # add new files
    subprocess.run(['git', 'add', 'gallery/s/'], capture_output=True)
    
    # check if there are changes
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if not result.stdout.strip():
        return False, "无新变更"
    
    # commit
    commit_msg = f"auto-sync: S级精品 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True)
    
    # push
    result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
    if result.returncode == 0:
        return True, "推送成功"
    else:
        return False, f"推送失败: {result.stderr[:100]}"

def main():
    print(f"=== 资产同步到Gitee {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # 获取新文件
    new_files, synced = get_new_files()
    print(f"新增S级文件: {len(new_files)} 个")
    
    if not new_files:
        print("无新文件需要同步")
        return
    
    # 执行git同步
    success, msg = git_commit_and_push()
    
    if success:
        # 更新已同步列表
        synced.update(new_files)
        save_synced(synced)
        print(f"✅ {msg}，已同步 {len(new_files)} 个文件")
        print(f"   累计同步: {len(synced)} 个文件")
    else:
        print(f"❌ {msg}")
    
    print("=== 同步完成 ===")

if __name__ == '__main__':
    main()
