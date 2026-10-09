#!/bin/bash
# 打包所有政策配图为ZIP，供批量下载

cd /www/wwwroot/huodouai.com/gov-ai/images/policy/

# 创建下载目录
mkdir -p /www/wwwroot/huodouai.com/gov-ai/downloads/

# 打包所有PNG文件
zip -j /www/wwwroot/huodouai.com/gov-ai/downloads/policy_images_all.zip policy_*.png 2>/dev/null

# 生成清单文件
python3 << 'PYEOF'
import json, os

index_file = '/opt/ZONGYUAN-ROOT/gov_api/data/policy_images/index.json'
with open(index_file) as f:
    images = json.load(f)

manifest = {
    'name': '政务中台政策配图全集',
    'generated_at': __import__('datetime').datetime.now().isoformat(),
    'total': len(images),
    'images': images
}

with open('/www/wwwroot/huodouai.com/gov-ai/downloads/policy_images_manifest.json', 'w') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f'清单生成完成: {len(images)}张配图')
PYEOF

echo "ZIP打包完成: $(date)" >> /opt/ZONGYUAN-ROOT/logs/pack_images.log
