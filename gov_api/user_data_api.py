#!/usr/bin/env python3
"""
用户数据持久化API模块 V1.0
- 办事预约（appointments）
- 收藏政策（favorites）
- 用户行为记录（user_actions）
数据存储：JSON文件，支持多用户
"""
import json, os, uuid, datetime

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data'
APPOINTMENTS_FILE = os.path.join(DATA_DIR, 'appointments.json')
FAVORITES_FILE = os.path.join(DATA_DIR, 'favorites.json')
ACTIONS_FILE = os.path.join(DATA_DIR, 'user_actions.json')

def _load(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def _save(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============ 办事预约 ============
def get_appointments(user_id=None, status=None):
    data = _load(APPOINTMENTS_FILE, [])
    if user_id:
        data = [a for a in data if a.get('user_id') == user_id]
    if status:
        data = [a for a in data if a.get('status') == status]
    return sorted(data, key=lambda x: x.get('created_at', ''), reverse=True)

def create_appointment(user_id, guide_id, guide_title, name, phone, date, time_slot, remark=''):
    data = _load(APPOINTMENTS_FILE, [])
    appointment = {
        'id': 'APT-' + uuid.uuid4().hex[:8].upper(),
        'user_id': user_id or 'anonymous',
        'guide_id': guide_id,
        'guide_title': guide_title,
        'name': name,
        'phone': phone,
        'date': date,
        'time_slot': time_slot,
        'remark': remark,
        'status': 'pending',  # pending/confirmed/completed/cancelled
        'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    data.append(appointment)
    _save(APPOINTMENTS_FILE, data)
    return appointment

def update_appointment(apt_id, **kwargs):
    data = _load(APPOINTMENTS_FILE, [])
    for a in data:
        if a['id'] == apt_id:
            a.update(kwargs)
            a['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _save(APPOINTMENTS_FILE, data)
            return a
    return None

def get_appointment_stats():
    data = _load(APPOINTMENTS_FILE, [])
    return {
        'total': len(data),
        'pending': sum(1 for a in data if a.get('status') == 'pending'),
        'confirmed': sum(1 for a in data if a.get('status') == 'confirmed'),
        'completed': sum(1 for a in data if a.get('status') == 'completed'),
        'cancelled': sum(1 for a in data if a.get('status') == 'cancelled'),
    }

# ============ 收藏政策 ============
def get_favorites(user_id=None):
    data = _load(FAVORITES_FILE, {})
    if user_id:
        return data.get(user_id, [])
    # 返回所有用户的收藏统计
    return {uid: len(favs) for uid, favs in data.items()}

def toggle_favorite(user_id, policy_id, policy_title, category=''):
    data = _load(FAVORITES_FILE, {})
    if user_id not in data:
        data[user_id] = []
    user_favs = data[user_id]
    existing = next((f for f in user_favs if f.get('policy_id') == policy_id), None)
    if existing:
        user_favs.remove(existing)
        data[user_id] = user_favs
        _save(FAVORITES_FILE, data)
        return {'favorited': False, 'favorites': user_favs}
    else:
        fav = {
            'policy_id': policy_id,
            'title': policy_title,
            'category': category,
            'favorited_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        user_favs.append(fav)
        data[user_id] = user_favs
        _save(FAVORITES_FILE, data)
        return {'favorited': True, 'favorites': user_favs}

def is_favorited(user_id, policy_id):
    data = _load(FAVORITES_FILE, {})
    user_favs = data.get(user_id, [])
    return any(f.get('policy_id') == policy_id for f in user_favs)

# ============ 用户行为记录 ============
def record_action(user_id, action_type, target_id, target_type, metadata=None):
    data = _load(ACTIONS_FILE, [])
    action = {
        'id': 'ACT-' + uuid.uuid4().hex[:8].upper(),
        'user_id': user_id or 'anonymous',
        'action_type': action_type,  # view/search/favorite/appointment/download
        'target_id': target_id,
        'target_type': target_type,  # policy/guide/doc
        'metadata': metadata or {},
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    data.append(action)
    # 只保留最近10000条
    if len(data) > 10000:
        data = data[-10000:]
    _save(ACTIONS_FILE, data)
    return action

def get_action_stats():
    data = _load(ACTIONS_FILE, [])
    stats = {}
    for a in data:
        atype = a.get('action_type', 'unknown')
        stats[atype] = stats.get(atype, 0) + 1
    return {'total_actions': len(data), 'by_type': stats}

print('✅ user_data_api.py 模块创建完成')
print('   - 办事预约: get/create/update/stats')
print('   - 收藏政策: get/toggle/is_favorited')
print('   - 行为记录: record/stats')
