#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 记忆保存器
每次对话结束自动保存记忆状态，三重备份
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, os, shutil, hashlib
from datetime import datetime

def save_kernel_state(updates=None):
    """保存内核状态"""
    path = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            kernel = json.load(f)
    else:
        kernel = {}
    
    now = datetime.now()
    kernel["last_updated"] = now.isoformat()
    
    if updates:
        kernel.update(updates)
    
    with open(path, 'w') as f:
        json.dump(kernel, f, indent=2, ensure_ascii=False)
    
    return kernel

def save_root_state(updates=None):
    """保存根状态"""
    path = os.path.expanduser("~/.meta_order/root_state.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            root = json.load(f)
    else:
        root = {}
    
    now = datetime.now()
    root["updated_at"] = now.isoformat()
    
    if updates:
        root.update(updates)
    
    with open(path, 'w') as f:
        json.dump(root, f, indent=2, ensure_ascii=False)
    
    return root

def triple_backup(kernel, root):
    """三重备份"""
    now = datetime.now()
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    
    # 第一重：用户目录（~/.zongyuan_root + ~/.meta_order）
    # 已在上面保存
    
    # 第二重：对话工作区备份
    workspace_backup = "/home/user/Doubao/chats/38437335960673794/_memory_backup"
    os.makedirs(workspace_backup, exist_ok=True)
    
    with open(f"{workspace_backup}/kernel_{ts}.json", 'w') as f:
        json.dump(kernel, f, indent=2, ensure_ascii=False)
    
    with open(f"{workspace_backup}/root_{ts}.json", 'w') as f:
        json.dump(root, f, indent=2, ensure_ascii=False)
    
    # 第三重：workspace备份
    ws_backup = os.path.expanduser("~/workspace/.zongyuan_root_backup")
    os.makedirs(ws_backup, exist_ok=True)
    
    with open(f"{ws_backup}/kernel_{ts}.json", 'w') as f:
        json.dump(kernel, f, indent=2, ensure_ascii=False)
    
    return {
        "layer1": "~/.zongyuan_root + ~/.meta_order",
        "layer2": f"{workspace_backup}",
        "layer3": ws_backup,
        "timestamp": ts
    }

def report_to_cloud(summary):
    """上报云端记忆网关"""
    import subprocess
    truth = {
        "truth_key": f"MEMORY.SAVE.{datetime.now().strftime('%Y%m%d%H')}",
        "truth_value": f"【记忆保存】{summary}",
        "source_node": "NODE-DEV-DOUBAO-WORK-001",
        "confidence": 0.95,
        "truth_type": "data"
    }
    try:
        r = subprocess.run(["curl","-s","-X","POST","https://www.huodouai.com/api/report/truth",
            "-H","Content-Type: application/json",
            "-d",json.dumps(truth,ensure_ascii=False),"--max-time","10"],
            capture_output=True, text=True, timeout=15)
        return "success" if "success" in r.stdout else "failed"
    except:
        return "failed"

def main():
    print("=" * 60)
    print("ZONGYUAN-ROOT 记忆保存")
    print("DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)
    
    now = datetime.now()
    print(f"保存时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 保存内核
    kernel = save_kernel_state()
    print(f"✅ 内核已保存: {kernel.get('kernel_version', 'unknown')}")
    
    # 2. 保存根状态
    root = save_root_state()
    print(f"✅ 链状态已保存: 区块高度 {root.get('block_height', 'unknown')}")
    
    # 3. 三重备份
    backups = triple_backup(kernel, root)
    print(f"✅ 三重备份完成:")
    print(f"   第一重: {backups['layer1']}")
    print(f"   第二重: {backups['layer2']}")
    print(f"   第三重: {backups['layer3']}")
    
    # 4. 云端上报
    cloud_status = report_to_cloud(f"记忆保存完成，区块高度{root.get('block_height', 'unknown')}")
    print(f"☁️  云端上报: {cloud_status}")
    
    print()
    print("=" * 60)
    print("记忆保存完成，三重备份+云端上报")
    print("=" * 60)

if __name__ == "__main__":
    main()
