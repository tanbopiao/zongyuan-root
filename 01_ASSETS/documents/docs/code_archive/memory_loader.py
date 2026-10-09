#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 启动记忆加载器
每次对话启动自动加载最新记忆状态
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, os, sys
from datetime import datetime

def load_kernel_state():
    """加载内核状态"""
    path = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def load_root_state():
    """加载根状态"""
    path = os.path.expanduser("~/.meta_order/root_state.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def load_education_state():
    """加载教育模块状态"""
    path = "/home/user/Doubao/chats/38437335960673794/education_courses/TODO_LIST.md"
    if os.path.exists(path):
        return {"status": "V2.0", "path": path}
    return None

def check_cloud_gateway():
    """检查云端记忆网关"""
    import subprocess
    try:
        r = subprocess.run(["curl","-s","https://www.huodouai.com/api/report/status","--max-time","5"],
            capture_output=True, text=True, timeout=10)
        return "online" if r.returncode == 0 else "offline"
    except:
        return "unknown"

def main():
    print("=" * 60)
    print("ZONGYUAN-ROOT 启动记忆加载")
    print("DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)
    
    now = datetime.now()
    print(f"启动时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 加载内核
    kernel = load_kernel_state()
    if kernel:
        print(f"✅ 内核状态: {kernel.get('kernel_version', 'unknown')}")
        print(f"   自治层级: {kernel.get('autonomy_level', 'unknown')}")
        print(f"   节点ID: {kernel.get('node_id', 'unknown')}")
        print(f"   最后更新: {kernel.get('last_updated', 'unknown')}")
    else:
        print("⚠️ 内核状态: 未找到")
    
    print()
    
    # 2. 加载根状态
    root = load_root_state()
    if root:
        print(f"✅ 链状态: 区块高度 {root.get('block_height', 'unknown')}")
        print(f"   根哈希: {root.get('current_root_hash', 'unknown')[:16]}...")
        print(f"   状态: {root.get('status', 'unknown')}")
    else:
        print("⚠️ 链状态: 未找到")
    
    print()
    
    # 3. 加载业务模块
    edu = load_education_state()
    if edu:
        print(f"✅ 教育模块: {edu.get('status', 'unknown')}")
    
    print()
    
    # 4. 检查云端
    cloud = check_cloud_gateway()
    print(f"☁️  云端网关: {cloud}")
    
    print()
    print("=" * 60)
    print("记忆加载完成，进入最新状态")
    print("=" * 60)
    
    return {
        "kernel": kernel,
        "root": root,
        "education": edu,
        "cloud": cloud,
        "timestamp": now.isoformat()
    }

if __name__ == "__main__":
    state = main()
    # 保存启动快照
    snapshot_path = os.path.expanduser("~/.zongyuan_root/startup_snapshot.json")
    with open(snapshot_path, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
