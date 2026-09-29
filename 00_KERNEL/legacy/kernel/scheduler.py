#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 统一中枢调度执行器 V1.0
接收内核调度指令，分发到各子系统执行
"""
import json, os, sys, hashlib, datetime, requests

KERNEL_DIR = '/opt/ZONGYUAN-ROOT/kernel'
DID = 'DID-BR-000002'

def load_protocol():
    with open(os.path.join(KERNEL_DIR, 'homology_protocol.json'), 'r') as f:
        return json.load(f)

def execute_command(target, action, params, priority='P2'):
    """执行调度指令"""
    protocol = load_protocol()
    subsystem = protocol['subsystem_registry'].get(target)
    
    if not subsystem:
        return {'success': False, 'error': f'子系统 {target} 未注册'}
    
    cmd_id = f"ZR-CMD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
    
    # 根据子系统类型执行
    if target == 'gov_platform':
        base_url = f"http://127.0.0.1:{subsystem['api_port']}{subsystem['api_prefix']}"
        result = dispatch_to_gov(base_url, action, params)
    else:
        result = {'success': False, 'error': f'不支持的子系统: {target}'}
    
    # 记录调度日志
    log_entry = {
        'command_id': cmd_id,
        'target': target,
        'action': action,
        'params': params,
        'priority': priority,
        'result': result,
        'executed_at': datetime.datetime.now().isoformat()
    }
    
    log_path = os.path.join(KERNEL_DIR, 'scheduling_logs.jsonl')
    with open(log_path, 'a') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    return {'command_id': cmd_id, 'result': result}

def dispatch_to_gov(base_url, action, params):
    """分发到政务中台"""
    action_map = {
        'health_check': ('GET', '/api/gov/health', None),
        'get_stats': ('GET', '/api/workbench/v11/stats', None),
        'list_policies': ('GET', '/api/gov/policies', params),
        'create_appointment': ('POST', '/api/gov/appointments/create', params),
        'trigger_evolution': ('POST', '/api/gov/evolution/trigger', params),
    }
    
    if action not in action_map:
        return {'success': False, 'error': f'未知动作: {action}'}
    
    method, path, data = action_map[action]
    url = base_url + path
    
    try:
        if method == 'GET':
            resp = requests.get(url, params=params, timeout=10)
        else:
            resp = requests.post(url, json=data, timeout=10)
        return {'success': True, 'status_code': resp.status_code, 'data': resp.json()}
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: python3 scheduler.py <target> <action> [params_json]')
        sys.exit(1)
    
    target = sys.argv[1]
    action = sys.argv[2]
    params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    
    result = execute_command(target, action, params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
