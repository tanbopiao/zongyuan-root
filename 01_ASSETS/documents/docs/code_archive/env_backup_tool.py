#!/usr/bin/env python3
"""
MR-026 云电脑环境备份恢复工具
备份：SSH密钥/配置/脚本 → 服务器安全存储
恢复：云电脑销毁后从服务器恢复环境
"""
import json
import hashlib
import os
import shutil
import tarfile
from datetime import datetime

DID = 'DID-BR-000002'
ANCHOR = 'Ω₀⊂⊙∞⊂Ω'
BACKUP_DIR = '/opt/ZONGYUAN-ROOT/archive/env_backups'
RESTORE_DIR = '/root/env_restore'

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def backup():
    """备份服务器端关键环境（用于云电脑恢复参考）"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    backup_items = {
        'ssh_authorized_keys': '/root/.ssh/authorized_keys',
        'meta_rule_set': '/opt/ZONGYUAN-ROOT/meta_rule_set.json',
        'self_asset_inventory': '/opt/ZONGYUAN-ROOT/kernel/self_asset_inventory.json',
        'nginx_config': '/www/server/nginx/conf/sites/huodouai.com.conf',
    }
    
    manifest = {
        'backup_id': f'ENV-BACKUP-{timestamp}',
        'created_at': datetime.now().isoformat(),
        'did': DID,
        'anchor': ANCHOR,
        'items': {},
        'restore_guide': {
            'step1': '从飞书加密文档获取SSH私钥',
            'step2': '将私钥放入 ~/.ssh/zongyuan_cloud',
            'step3': 'chmod 600 ~/.ssh/zongyuan_cloud',
            'step4': '配置SSH别名: cat >> ~/.ssh/config << EOF\nHost zongyuan-cloud\n  HostName 123.207.202.158\n  User root\n  IdentityFile ~/.ssh/zongyuan_cloud\nEOF',
            'step5': '测试连接: ssh zongyuan-cloud echo ok',
            'step6': '从本备份目录恢复配置文件'
        }
    }
    
    backup_file = f'{BACKUP_DIR}/env_backup_{timestamp}.tar.gz'
    with tarfile.open(backup_file, 'w:gz') as tar:
        for name, path in backup_items.items():
            if os.path.exists(path):
                tar.add(path, arcname=name)
                manifest['items'][name] = {
                    'path': path,
                    'sha256': sha256_file(path),
                    'size': os.path.getsize(path)
                }
    
    manifest_path = f'{BACKUP_DIR}/env_backup_{timestamp}_manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    manifest_hash = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    
    print(f"✅ 环境备份完成")
    print(f"   备份ID: {manifest['backup_id']}")
    print(f"   备份文件: {backup_file}")
    print(f"   清单文件: {manifest_path}")
    print(f"   清单哈希: {manifest_hash}")
    print(f"   备份项: {len(manifest['items'])}个")
    return manifest

def list_backups():
    """列出所有备份"""
    if not os.path.exists(BACKUP_DIR):
        print("无备份")
        return
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('_manifest.json')])
    for b in backups[-5:]:
        path = os.path.join(BACKUP_DIR, b)
        with open(path) as f:
            m = json.load(f)
        print(f"  {m['backup_id']} | {m['created_at'][:19]} | {len(m['items'])}项")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        list_backups()
    else:
        backup()
