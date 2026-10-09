#!/bin/bash
# 自动政策配图生成脚本
# 每周日凌晨3点执行，扫描新政策并生成配图

cd /opt/ZONGYUAN-ROOT

# 生成待生成任务列表
python3 << 'PYEOF'
import json, os

with open('/opt/ZONGYUAN-ROOT/gov_api/data/policies.json') as f:
    policies = json.load(f)

index_file = '/opt/ZONGYUAN-ROOT/gov_api/data/policy_images/index.json'
if os.path.exists(index_file):
    with open(index_file) as f:
        images = json.load(f)
else:
    images = []

policy_dir = '/www/wwwroot/huodouai.com/gov-ai/images/policy/'
exist_ids = set()
for img in images:
    pid = img.get('id', '')
    if os.path.exists(os.path.join(policy_dir, f'policy_{pid}.png')):
        exist_ids.add(pid)

tasks = []
for p in policies:
    pid = p.get('id', '')
    if pid and pid not in exist_ids:
        title = p.get('title', p.get('name', ''))
        category = p.get('category', '')
        prompt = '扁平化插画，蓝色主色调，政务专业风格，' + category + '主题，' + title + '，简洁现代，适合政府网站展示'
        tasks.append({'id': pid, 'prompt': prompt})

with open('/tmp/policy_images_auto.json', 'w') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print(f'自动扫描完成，待生成: {len(tasks)}张')
PYEOF

# 执行批量生成
if [ -s /tmp/policy_images_auto.json ]; then
    python3 batch_task_scheduler.py       --tasks /tmp/policy_images_auto.json       --output /www/wwwroot/huodouai.com/gov-ai/images/policy/       --type image       --concurrency 3 >> /opt/ZONGYUAN-ROOT/logs/auto_policy_images.log 2>&1
    
    # 更新索引
    python3 << 'PYEOF2'
import json, os

index_file = '/opt/ZONGYUAN-ROOT/gov_api/data/policy_images/index.json'
with open(index_file) as f:
    images = json.load(f)

policy_dir = '/www/wwwroot/huodouai.com/gov-ai/images/policy/'
existing_ids = set(img.get('id', '') for img in images)

for f in os.listdir(policy_dir):
    if f.startswith('policy_') and f.endswith('.png'):
        pid = f.replace('policy_', '').replace('.png', '')
        if pid not in existing_ids:
            images.append({
                'id': pid,
                'title': '',
                'image': f'/gov-ai/images/policy/{f}',
                'status': 'success'
            })

with open(index_file, 'w') as f:
    json.dump(images, f, ensure_ascii=False, indent=2)

print(f'索引更新完成，总记录: {len(images)}')
PYEOF2
fi

echo "自动配图任务完成: $(date)" >> /opt/ZONGYUAN-ROOT/logs/auto_policy_images.log
