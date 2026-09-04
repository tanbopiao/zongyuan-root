#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 多Agent并发锁档引擎
支持: 窗口命名空间、向量时钟、冲突检测、双内核同步
用法: python3 multi_agent_lock.py --window A --snapshot-id "DRAMA-OPTIMIZE" --type "optimize" --desc "描述"
"""
import json, time, hashlib, argparse, os, sys

KERNEL_PATH = '/opt/ZONGYUAN-ROOT/kernel.json'
DID = 'DID-BR-000002'
SOVEREIGN = 'Ω-TAN-7-001'
TRACE = 'Ω₀⊂⊙∞⊂Ω'

def load_kernel():
    with open(KERNEL_PATH) as f:
        return json.load(f)

def save_kernel(k):
    with open(KERNEL_PATH, 'w') as f:
        json.dump(k, f, ensure_ascii=False, indent=2)

def get_vector_clock(kernel):
    """获取或初始化向量时钟"""
    if 'vector_clock' not in kernel:
        kernel['vector_clock'] = {'A': 0, 'B': 0, 'C': 0, 'arbiter': 0}
    return kernel['vector_clock']

def increment_clock(kernel, window):
    """递增指定窗口的向量时钟"""
    vc = get_vector_clock(kernel)
    vc[window] = vc.get(window, 0) + 1
    return vc

def detect_conflicts(kernel, new_snap):
    """检测与其他窗口并发快照的冲突"""
    conflicts = []
    vc = kernel.get('vector_clock', {})
    # 检查最近10个快照中是否有并发修改同一模块
    for s in kernel.get('snapshots', [])[-10:]:
        if s.get('window') and s['window'] != new_snap.get('window'):
            if s.get('module') == new_snap.get('module') and s.get('module'):
                conflicts.append({
                    'snapshot_id': s['snapshot_id'],
                    'window': s['window'],
                    'module': s.get('module'),
                    'type': 'concurrent_module_edit'
                })
    return conflicts

def lock_snapshot(window, snapshot_id, snap_type, desc, module=None, extra=None):
    """执行锁档（调用方应已持有kernel_write锁）"""
    kernel = load_kernel()
    
    # 递增向量时钟
    vc = increment_clock(kernel, window)
    
    # 构造带窗口前缀的快照ID
    prefixed_id = f"SNAP-{window}-{snapshot_id}"
    
    # 检查ID是否已存在
    existing_ids = {s['snapshot_id'] for s in kernel.get('snapshots', [])}
    if prefixed_id in existing_ids:
        # 追加时间戳后缀避免重复
        prefixed_id = f"{prefixed_id}-{int(time.time())}"
    
    snap = {
        'snapshot_id': prefixed_id,
        'type': snap_type,
        'window': window,
        'module': module,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        'did': DID,
        'sovereign_root': SOVEREIGN,
        'lock_level': 'META-003',
        'trace_symbol': TRACE,
        'desc': desc,
        'vector_clock': dict(vc),
        'conflicts': []
    }
    if extra:
        snap.update(extra)
    
    # 冲突检测
    snap['conflicts'] = detect_conflicts(kernel, snap)
    
    # 计算哈希
    snap['hash'] = hashlib.sha256(
        json.dumps(snap, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    
    kernel['snapshots'].append(snap)
    kernel['snapshot_count'] = len(kernel['snapshots'])
    kernel['last_updated'] = snap['timestamp']
    kernel['dual_kernel_sync'] = True
    kernel['multi_agent_mode'] = True
    
    save_kernel(kernel)
    return snap

def main():
    parser = argparse.ArgumentParser(description='ZONGYUAN-ROOT 多Agent锁档引擎')
    parser.add_argument('--window', required=True, choices=['A','B','C','arbiter'], help='窗口标识')
    parser.add_argument('--snapshot-id', required=True, help='快照标识（不含前缀）')
    parser.add_argument('--type', required=True, help='快照类型')
    parser.add_argument('--desc', default='', help='描述')
    parser.add_argument('--module', default=None, help='涉及模块（用于冲突检测）')
    args = parser.parse_args()
    
    snap = lock_snapshot(args.window, args.snapshot_id, args.type, args.desc, args.module)
    
    print(f"✅ 锁档成功")
    print(f"  快照ID: {snap['snapshot_id']}")
    print(f"  窗口: {snap['window']}")
    print(f"  向量时钟: {snap['vector_clock']}")
    print(f"  哈希: {snap['hash'][:16]}...")
    print(f"  冲突: {len(snap['conflicts'])}个")
    if snap['conflicts']:
        for c in snap['conflicts']:
            print(f"    ⚠️  与{c['window']}窗口的{c['snapshot_id']}并发修改{c['module']}")
    print(f"  总快照数: {json.load(open(KERNEL_PATH))['snapshot_count']}")

if __name__ == '__main__':
    main()
