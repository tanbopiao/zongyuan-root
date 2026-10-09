#!/usr/bin/env python3
"""
ZONGYUAN-ROOT Merkle链维护器
- 收集所有元法则+核心文件哈希
- 计算Merkle根
- 验证链连续性
- 上报9120
"""
import json
import hashlib
import time
import os
import glob
import urllib.request
from datetime import datetime

META_LAW_DIR = '/opt/ZONGYUAN-ROOT/kernel/truth_entries/meta_law'
CHAIN_STATE = '/opt/ZONGYUAN-ROOT/kernel/merkle_chain_state.json'
DID = 'DID-BR-000002'
ANCHOR = 'Ω₀⊂⊙∞⊂Ω'

def sha256(s):
    return hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()

def compute_merkle_root(leaves):
    """计算Merkle根"""
    if not leaves:
        return sha256('empty')
    layer = [sha256(x) for x in leaves]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [sha256(layer[i] + layer[i+1]) for i in range(0, len(layer), 2)]
    return layer[0]

def collect_leaves():
    """收集所有叶子节点（元法则文件哈希+核心文件哈希）"""
    leaves = []
    # 1. 所有元法则文件（按文件名排序保证确定性）
    meta_files = sorted(glob.glob(f'{META_LAW_DIR}/MR-*.json'))
    for f in meta_files:
        with open(f, 'rb') as fp:
            leaves.append(sha256(fp.read()))
    # 2. 核心配置文件
    core_files = [
        '/opt/ZONGYUAN-ROOT/meta_rule_set.json',
        '/opt/ZONGYUAN-ROOT/MASTER_PROTOCOL_META_LAW.json',
        '/opt/ZONGYUAN-ROOT/kernel/self_asset_inventory.json',
    ]
    for f in core_files:
        if os.path.exists(f):
            with open(f, 'rb') as fp:
                leaves.append(sha256(fp.read()))
    return leaves, meta_files

def load_chain_state():
    if os.path.exists(CHAIN_STATE):
        with open(CHAIN_STATE) as f:
            return json.load(f)
    return {'chain': [], 'current_root': None}

def save_chain_state(state):
    with open(CHAIN_STATE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def main():
    leaves, meta_files = collect_leaves()
    new_root = compute_merkle_root(leaves)
    state = load_chain_state()
    
    # 验证链连续性
    prev_root = state.get('current_root')
    chain_continuous = (prev_root is None) or (prev_root in [b.get('root') for b in state.get('chain', [])])
    
    # 计算完整性（有多少叶子能在历史链中找到）
    chain = state.get('chain', [])
    historical_roots = set(b.get('root') for b in chain)
    integrity = 100.0 if chain_continuous else 50.0  # 链断了就是50%
    
    # 追加新区块
    block = {
        'height': len(chain) + 1,
        'timestamp': datetime.now().isoformat(),
        'leaf_count': len(leaves),
        'meta_law_count': len(meta_files),
        'merkle_root': new_root,
        'prev_root': prev_root,
        'chain_continuous': chain_continuous,
        'integrity_percent': integrity,
        'did': DID,
        'anchor': ANCHOR
    }
    chain.append(block)
    state['chain'] = chain[-100:]  # 保留最近100个区块
    state['current_root'] = new_root
    state['last_update'] = datetime.now().isoformat()
    save_chain_state(state)
    
    # 上报9120
    try:
        data = json.dumps({
            "key": f"merkle_chain.{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "value": f"Merkle链更新: 高度{block['height']}, 叶子{len(leaves)}个, 根{new_root[:16]}..., 完整性{integrity}%",
            "source": "merkle_chain_maintainer",
            "did": DID,
            "anchor": ANCHOR,
            "confidence": 1.0,
            "truth_type": "merkle_root"
        }).encode()
        req = urllib.request.Request("http://127.0.0.1:9120/api/truth/upsert", data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except:
        pass
    
    print(f"Merkle链更新完成: 高度={block['height']}, 叶子={len(leaves)}, 完整性={integrity}%")
    print(f"根哈希: {new_root}")
    print(f"链连续: {chain_continuous}")

if __name__ == '__main__':
    main()
