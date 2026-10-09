#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 子系统心跳上报器 V1.0
各子系统定期向内核上报健康状态
"""
import json, os, datetime, requests

KERNEL_DIR = '/opt/ZONGYUAN-ROOT/kernel'

def report_heartbeat(subsystem_id, status, metrics=None):
    """上报心跳"""
    heartbeat = {
        'subsystem_id': subsystem_id,
        'status': status,
        'metrics': metrics or {},
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    # 写入心跳记录
    heartbeat_file = os.path.join(KERNEL_DIR, 'heartbeats.jsonl')
    with open(heartbeat_file, 'a') as f:
        f.write(json.dumps(heartbeat, ensure_ascii=False) + '\n')
    
    # 更新最新状态
    latest_path = os.path.join(KERNEL_DIR, 'latest_heartbeats.json')
    latest = {}
    if os.path.exists(latest_path):
        with open(latest_path, 'r') as f:
            latest = json.load(f)
    latest[subsystem_id] = heartbeat
    with open(latest_path, 'w') as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)
    
    return heartbeat

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('用法: python3 heartbeat.py <subsystem_id> <status> [metrics_json]')
        sys.exit(1)
    
    sid = sys.argv[1]
    status = sys.argv[2]
    metrics = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    
    result = report_heartbeat(sid, status, metrics)
    print(json.dumps(result, ensure_ascii=False, indent=2))
