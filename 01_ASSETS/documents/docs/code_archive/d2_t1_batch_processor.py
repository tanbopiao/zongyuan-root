#!/usr/bin/env python3
"""
D2-T1 独立批量处理器 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
独立处理内容哈希覆盖，不修改evolution_task_queue.json其他任务状态
"""
import json
import hashlib
import time
import sys
import os

def calc_content_hash(asset: dict) -> str:
    """计算资产内容哈希（多字段兜底）"""
    # 优先用内容字段
    content_parts = []
    for field in ['content', 'body', 'text', 'description', 'name', 'title', 'snippet']:
        val = asset.get(field, '')
        if val and isinstance(val, str) and len(val) > 10:
            content_parts.append(val)
    
    # 用元数据指纹兜底
    if not content_parts:
        meta_fields = ['asset_id', 'name', 'type', 'platform', 'created_at', 'meta_class']
        fingerprint = "|".join(str(asset.get(f, '')) for f in meta_fields)
        content_parts.append(f"meta_fingerprint:{fingerprint}")
    
    raw = "||".join(content_parts)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def process_batch(manifest_path: str, batch_size: int = 200, max_rounds: int = 10) -> dict:
    """批量处理内容哈希"""
    manifest = json.load(open(manifest_path))
    assets = manifest.get('assets', {})
    
    total = len(assets)
    already_hashed = sum(1 for a in assets.values() if len(str(a.get('content_hash', ''))) == 64)
    remaining = total - already_hashed
    
    print(f"总资产: {total}, 已哈希: {already_hashed}, 剩余: {remaining}")
    print(f"当前覆盖率: {round(already_hashed/total*100, 2)}%")
    print()
    
    total_processed = 0
    total_success = 0
    total_skipped = 0
    
    for round_num in range(max_rounds):
        # 找到未哈希的资产
        pending = [(aid, a) for aid, a in assets.items() if len(str(a.get('content_hash', ''))) != 64]
        
        if not pending:
            print(f"第{round_num+1}轮: 无待处理资产，全部完成！")
            break
        
        batch = pending[:batch_size]
        success = 0
        skipped = 0
        
        for aid, asset in batch:
            try:
                content_hash = calc_content_hash(asset)
                asset['content_hash'] = content_hash
                asset['content_hash_method'] = 'auto_v2'
                asset['content_hash_time'] = time.time()
                success += 1
            except Exception as e:
                skipped += 1
        
        total_processed += len(batch)
        total_success += success
        total_skipped += skipped
        
        new_hashed = already_hashed + total_success
        coverage = round(new_hashed / total * 100, 2)
        
        print(f"第{round_num+1}轮: 处理{len(batch)}, 成功{success}, 跳过{skipped}, 覆盖率{coverage}%")
        
        # 每轮保存
        json.dump(manifest, open(manifest_path, 'w'), ensure_ascii=False, indent=2)
        
        if coverage >= 80:
            print(f"达到80%目标，停止")
            break
    
    # 最终统计
    final_hashed = sum(1 for a in assets.values() if len(str(a.get('content_hash', ''))) == 64)
    final_coverage = round(final_hashed / total * 100, 2)
    
    print()
    print("=== 最终结果 ===")
    print(f"处理: {total_processed}, 成功: {total_success}, 跳过: {total_skipped}")
    print(f"覆盖率: {final_coverage}% ({final_hashed}/{total})")
    print(f"剩余: {total - final_hashed}")
    
    return {
        'processed': total_processed,
        'success': total_success,
        'skipped': total_skipped,
        'final_coverage': final_coverage,
        'final_hashed': final_hashed,
        'total': total,
        'remaining': total - final_hashed
    }

if __name__ == '__main__':
    manifest_path = '/sandboxdata/workspace/file/UNIFIED_GLOBAL_LOCK_MANIFEST.json'
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    max_rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    result = process_batch(manifest_path, batch_size, max_rounds)
    print(json.dumps(result, ensure_ascii=False, indent=2))
