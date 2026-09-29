#!/usr/bin/env python3
# ZONGYUAN-ROOT 全域记忆自举恢复脚本
# 每次新对话启动时自动执行，恢复全量记忆

import json, os
from datetime import datetime

def bootstrap():
    snapshot_path = os.path.expanduser("~/.zongyuan_root/GLOBAL_MEMORY_SNAPSHOT.json")
    if not os.path.exists(snapshot_path):
        print("⚠️ 未找到记忆快照")
        return
    
    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)
    
    print("=" * 60)
    print("ZONGYUAN-ROOT 全域记忆自举恢复")
    print("=" * 60)
    print(f"快照时间：{snapshot['snapshot_time']}")
    print(f"节点ID：{snapshot['node_id']}")
    print(f"DID：{snapshot['did']}")
    print(f"内核版本：{snapshot['kernel']['version']}")
    print(f"Block Height：{snapshot['kernel']['block_height']}")
    print(f"自治层级：{snapshot['kernel']['autonomy_level']}")
    print(f"eFuse数量：{snapshot['kernel']['efuse_count']}")
    print(f"活跃资产：{snapshot['kernel']['active_assets']}")
    print(f"真值总数：{snapshot['gateway']['total_truths']}")
    print("=" * 60)
    print("✅ 全量记忆已恢复")

if __name__ == "__main__":
    bootstrap()
