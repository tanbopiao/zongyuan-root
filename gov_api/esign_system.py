#!/usr/bin/env python3
"""
电子签章系统模块
功能：签章生成、签章验证、签章记录管理
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import hashlib
import datetime
import uuid

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data/esign'
os.makedirs(DATA_DIR, exist_ok=True)

def _load_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

def _save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_seal(user_id, seal_name, seal_type='official'):
    """创建电子签章"""
    seals = _load_json('seals.json', {})
    seal_id = 'SEAL-' + uuid.uuid4().hex[:8].upper()
    seal = {
        'seal_id': seal_id,
        'user_id': user_id,
        'seal_name': seal_name,
        'seal_type': seal_type,  # official公章, personal私章, contract合同章
        'created_at': datetime.datetime.now().isoformat(),
        'status': 'active',
        'seal_hash': hashlib.sha256(f'{seal_id}{seal_name}{user_id}'.encode()).hexdigest()
    }
    seals[seal_id] = seal
    _save_json('seals.json', seals)
    return seal

def sign_document(user_id, document_id, document_content, seal_id):
    """对文档进行电子签章"""
    seals = _load_json('seals.json', {})
    records = _load_json('sign_records.json', {})
    
    if seal_id not in seals:
        return {'error': '签章不存在', 'code': 404}
    
    seal = seals[seal_id]
    if seal['status'] != 'active':
        return {'error': '签章已失效', 'code': 403}
    
    # 计算文档哈希
    doc_hash = hashlib.sha256(document_content.encode('utf-8')).hexdigest()
    
    # 生成签章记录
    record_id = 'SIGN-' + uuid.uuid4().hex[:8].upper()
    sign_time = datetime.datetime.now().isoformat()
    
    # 签章数据（包含文档哈希+签章哈希+时间戳）
    sign_data = f'{doc_hash}:{seal["seal_hash"]}:{sign_time}'
    sign_hash = hashlib.sha256(sign_data.encode()).hexdigest()
    
    record = {
        'record_id': record_id,
        'user_id': user_id,
        'document_id': document_id,
        'document_hash': doc_hash,
        'seal_id': seal_id,
        'seal_name': seal['seal_name'],
        'sign_time': sign_time,
        'sign_hash': sign_hash,
        'status': 'signed',
        'verify_count': 0
    }
    
    records[record_id] = record
    _save_json('sign_records.json', records)
    
    return {
        'success': True,
        'record_id': record_id,
        'document_hash': doc_hash,
        'sign_hash': sign_hash,
        'sign_time': sign_time,
        'seal_name': seal['seal_name']
    }

def verify_signature(record_id, document_content=None):
    """验证电子签章"""
    records = _load_json('sign_records.json', {})
    
    if record_id not in records:
        return {'valid': False, 'error': '签章记录不存在', 'code': 404}
    
    record = records[record_id]
    
    # 如果提供了文档内容，验证文档哈希
    if document_content:
        doc_hash = hashlib.sha256(document_content.encode('utf-8')).hexdigest()
        if doc_hash != record['document_hash']:
            return {'valid': False, 'error': '文档内容已被篡改', 'document_hash_match': False}
    
    # 更新验证次数
    record['verify_count'] = record.get('verify_count', 0) + 1
    record['last_verify_time'] = datetime.datetime.now().isoformat()
    records[record_id] = record
    _save_json('sign_records.json', records)
    
    return {
        'valid': True,
        'record_id': record_id,
        'document_hash': record['document_hash'],
        'sign_hash': record['sign_hash'],
        'sign_time': record['sign_time'],
        'seal_name': record['seal_name'],
        'verify_count': record['verify_count'],
        'status': record['status']
    }

def get_user_seals(user_id):
    """获取用户的签章列表"""
    seals = _load_json('seals.json', {})
    user_seals = [s for s in seals.values() if s['user_id'] == user_id]
    return {'seals': user_seals, 'total': len(user_seals)}

def get_sign_records(user_id=None, document_id=None, limit=50):
    """获取签章记录"""
    records = _load_json('sign_records.json', {})
    result = list(records.values())
    
    if user_id:
        result = [r for r in result if r['user_id'] == user_id]
    if document_id:
        result = [r for r in result if r['document_id'] == document_id]
    
    result.sort(key=lambda x: x['sign_time'], reverse=True)
    return {'records': result[:limit], 'total': len(result)}

def get_stats():
    """获取签章统计"""
    seals = _load_json('seals.json', {})
    records = _load_json('sign_records.json', {})
    
    seal_types = {}
    for s in seals.values():
        t = s.get('seal_type', 'unknown')
        seal_types[t] = seal_types.get(t, 0) + 1
    
    return {
        'total_seals': len(seals),
        'total_signs': len(records),
        'seal_types': seal_types,
        'active_seals': len([s for s in seals.values() if s['status'] == 'active'])
    }

# 初始化示例数据
if not os.path.exists(os.path.join(DATA_DIR, 'seals.json')):
    create_seal('admin', '政务中台公章', 'official')
    create_seal('admin', '合同专用章', 'contract')
    print('电子签章系统初始化完成')
