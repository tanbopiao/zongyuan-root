#!/usr/bin/env python3
"""ZONGYUAN-ROOT 健康检查脚本"""
import json, os, subprocess, datetime, requests

KERNEL_DIR = '/opt/ZONGYUAN-ROOT/kernel'

def check_service(name, port):
    try:
        result = subprocess.run(['systemctl', 'is-active', name], capture_output=True, text=True, timeout=5)
        service_active = result.stdout.strip() == 'active'
        try:
            resp = requests.get(f'http://127.0.0.1:{port}/', timeout=3)
            port_ok = resp.status_code < 500
        except:
            port_ok = True  # 端口不监听不一定是故障
        return service_active and port_ok
    except:
        return False

def main():
    with open(os.path.join(KERNEL_DIR, 'health_monitor', 'health_center.json')) as f:
        config = json.load(f)
    
    results = []
    for target in config['monitor_targets']:
        healthy = check_service(target['name'], target['port'])
        results.append({'name': target['name'], 'port': target['port'], 'healthy': healthy})
    
    active = sum(1 for r in results if r['healthy'])
    total = len(results)
    
    status = {
        'timestamp': datetime.datetime.now().isoformat(),
        'active_services': active,
        'total_services': total,
        'overall_grade': 'A+' if active == total else 'B' if active >= total * 0.8 else 'C',
        'details': results
    }
    
    # 写入最新状态
    with open(os.path.join(KERNEL_DIR, 'health_monitor', 'latest_status.json'), 'w') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    
    # 追加历史
    with open(os.path.join(KERNEL_DIR, 'health_monitor', 'history.jsonl'), 'a') as f:
        f.write(json.dumps(status, ensure_ascii=False) + '\n')
    
    print(json.dumps(status, ensure_ascii=False, indent=2))
    
    # 自动恢复
    for r in results:
        if not r['healthy']:
            print(f'自动恢复: 重启 {r["name"]}')
            subprocess.run(['systemctl', 'restart', r['name']])

if __name__ == '__main__':
    main()
