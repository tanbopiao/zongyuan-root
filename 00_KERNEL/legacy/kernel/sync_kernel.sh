#!/bin/bash
# 云服务器内核状态同步脚本
# 定期将云服务器运行状态写入内核

KERNEL_FILE=/opt/ZONGYUAN-ROOT/kernel/kernel_state.json

python3 << 'PYEOF'
import json, os, datetime, subprocess

kernel_file = '/opt/ZONGYUAN-ROOT/kernel/kernel_state.json'
with open(kernel_file) as f:
    kernel = json.load(f)

# 更新云服务器实时状态
kernel['cloud_server']['last_sync'] = datetime.datetime.now().isoformat()

# 统计systemd服务
try:
    result = subprocess.run(['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager'], capture_output=True, text=True)
    zongyuan_services = [l for l in result.stdout.split('\n') if 'zongyuan' in l.lower()]
    kernel['cloud_server']['running_services'] = len(zongyuan_services)
except:
    pass

# 统计配图数量
try:
    result = subprocess.run(['ls', '/www/wwwroot/huodouai.com/gov-ai/images/policy/policy_*.png'], capture_output=True, text=True)
    count = len([l for l in result.stdout.split('\n') if l.strip()])
    kernel['gov_platform']['policy_images'] = count
except:
    pass

with open(kernel_file, 'w') as f:
    json.dump(kernel, f, ensure_ascii=False, indent=2)

print(f'内核同步完成: {datetime.datetime.now()}')
PYEOF
