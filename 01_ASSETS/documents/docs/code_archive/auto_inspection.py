#!/usr/bin/env python3
"""
MR-027 元内核自动巡检+飞书推送
每日定时执行，检查元内核状态并推送到飞书
"""
import json
import os
import time
import urllib.request
import urllib.parse
import subprocess
from datetime import datetime

DID = 'DID-BR-000002'
ANCHOR = 'Ω₀⊂⊙∞⊂Ω'
FEISHU_CONFIG = '/opt/ZONGYUAN-ROOT/config/feishu_gateway.json'
LOG_DIR = '/opt/ZONGYUAN-ROOT/logs/inspection'

def get_feishu_token():
    """获取飞书tenant_access_token"""
    with open(FEISHU_CONFIG) as f:
        cfg = json.load(f)
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    data = json.dumps({
        'app_id': cfg['app_id'],
        'app_secret': cfg['app_secret']
    }).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    return resp.get('tenant_access_token')

def send_feishu_message(token, chat_id, content):
    """发送飞书消息"""
    url = f'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id'
    data = json.dumps({
        'receive_id': chat_id,
        'msg_type': 'interactive',
        'content': json.dumps(content)
    }).encode()
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    })
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    return resp

def check_port(port, path='/health'):
    """检查端口服务状态"""
    try:
        url = f'http://127.0.0.1:{port}{path}'
        req = urllib.request.Request(url, method='GET')
        resp = urllib.request.urlopen(req, timeout=3)
        return resp.status == 200
    except:
        return False

def get_system_info():
    """获取系统信息"""
    # 内存
    mem = subprocess.check_output(['free', '-m']).decode().split('\n')[1].split()
    mem_total = int(mem[1])
    mem_used = int(mem[2])
    mem_pct = round(mem_used / mem_total * 100, 1)
    
    # 磁盘
    disk = subprocess.check_output(['df', '-h', '/']).decode().split('\n')[1].split()
    disk_pct = disk[4]
    
    # 服务数量
    services = subprocess.check_output(['ps', 'aux']).decode().count('\n')
    
    # 监听端口
    ports = subprocess.check_output(['ss', '-tlnp']).decode().count('\n')
    
    return {
        'mem_total': mem_total,
        'mem_used': mem_used,
        'mem_pct': mem_pct,
        'disk_pct': disk_pct,
        'services': services,
        'ports': ports
    }

def get_truth_count():
    """获取真值总数"""
    try:
        req = urllib.request.Request('http://127.0.0.1:9120/api/status')
        resp = json.loads(urllib.request.urlopen(req, timeout=3).read())
        return resp.get('truth_count', resp.get('total_truths', '?'))
    except:
        return '?'

def run_inspection():
    """执行巡检"""
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 检查核心服务
    services = {
        '记忆网关(9120)': check_port(9120, '/api/status'),
        '自我识别(9150)': check_port(9150, '/api/self/verify'),
        '本地LLM(8081)': check_port(8081, '/health'),
        'AI代理(8021)': check_port(8021, '/health'),
        '引擎代理(9210)': check_port(9210, '/status'),
        '飞书回调(8060)': check_port(8060, '/health'),
        'Nginx(80/443)': check_port(80, '/') or check_port(443, '/'),
    }
    
    sys_info = get_system_info()
    truth_count = get_truth_count()
    
    # 元法则版本
    try:
        with open('/opt/ZONGYUAN-ROOT/meta_rule_set.json') as f:
            rs = json.load(f)
        rule_version = rs.get('version', '?')
        rule_count = rs.get('total_rules', '?')
    except:
        rule_version = '?'
        rule_count = '?'
    
    # 健康状态判断
    all_ok = all(services.values())
    mem_warn = sys_info['mem_pct'] > 80
    status = '✅ 全部正常' if all_ok and not mem_warn else '⚠️ 存在异常'
    
    # 构建飞书卡片消息
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"🔮 元内核每日巡检 {status}"},
            "template": "green" if all_ok and not mem_warn else "orange"
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**时间**：{timestamp}\n**确权**：{DID} ｜ {ANCHOR}"}},
            {"tag": "hr"},
            {"tag": "div", "text": {"tag": "lark_md", "content": "**📊 核心服务状态**"}},
        ]
    }
    
    service_lines = []
    for name, ok in services.items():
        icon = '✅' if ok else '❌'
        service_lines.append(f"{icon} {name}")
    card['elements'].append({"tag": "div", "text": {"tag": "lark_md", "content": '\n'.join(service_lines)}})
    
    card['elements'].extend([
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md", "content": (
            f"**💻 系统资源**\n"
            f"内存：{sys_info['mem_used']}/{sys_info['mem_total']}MB ({sys_info['mem_pct']}%)\n"
            f"磁盘：{sys_info['disk_pct']}\n"
            f"进程：{sys_info['services']}个 ｜ 端口：{sys_info['ports']}个\n\n"
            f"**📚 元内核数据**\n"
            f"真值总数：{truth_count}\n"
            f"元法则：{rule_version} ({rule_count}条)"
        )}},
        {"tag": "hr"},
        {"tag": "note", "elements": [{"tag": "plain_text", "content": f"ZONGYUAN-ROOT 元极恒一自治体系 ｜ 自动巡检 ｜ {timestamp}"}]}
    ])
    
    # 发送飞书消息
    try:
        with open(FEISHU_CONFIG) as f:
            cfg = json.load(f)
        chat_id = cfg['phase1_capabilities']['bot_notify']['chat_id']
        token = get_feishu_token()
        result = send_feishu_message(token, chat_id, card)
        feishu_status = '✅ 已推送' if result.get('code') == 0 else f"⚠️ {result.get('msg')}"
    except Exception as e:
        feishu_status = f'❌ 推送失败: {e}'
    
    # 保存巡检日志
    log = {
        'timestamp': timestamp,
        'status': status,
        'services': services,
        'system': sys_info,
        'truth_count': truth_count,
        'rule_version': rule_version,
        'rule_count': rule_count,
        'feishu_push': feishu_status
    }
    log_file = f"{LOG_DIR}/inspection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    # 上报9120
    try:
        data = json.dumps({
            'key': f'inspection.daily.{datetime.now().strftime("%Y%m%d")}',
            'value': json.dumps(log, ensure_ascii=False),
            'source': 'auto_inspection',
            'did': DID,
            'anchor': ANCHOR,
            'confidence': 1.0,
            'truth_type': 'inspection_log'
        }).encode()
        req = urllib.request.Request('http://127.0.0.1:9120/api/truth/upsert',
            data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except:
        pass
    
    print(f"✅ 巡检完成: {status}")
    print(f"   飞书推送: {feishu_status}")
    print(f"   日志: {log_file}")
    return log

if __name__ == '__main__':
    run_inspection()
