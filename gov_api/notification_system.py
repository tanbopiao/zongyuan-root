#!/usr/bin/env python3
"""
政务中台通知推送系统 V1.0
支持：预约确认/变更通知、政策更新推送、工作台待办提醒、系统公告
"""
import json
import os
import hashlib
import datetime

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data/notifications'
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, 'notifications.json')
USER_PREFS_FILE = os.path.join(DATA_DIR, 'user_prefs.json')

os.makedirs(DATA_DIR, exist_ok=True)

NOTIFICATION_TYPES = {
    'appointment': {'name': '预约通知', 'icon': '📅', 'color': '#3b82f6'},
    'policy': {'name': '政策更新', 'icon': '📋', 'color': '#10b981'},
    'todo': {'name': '待办提醒', 'icon': '✅', 'color': '#f59e0b'},
    'system': {'name': '系统公告', 'icon': '🔔', 'color': '#ef4444'},
    'approval': {'name': '审批通知', 'icon': '⚖️', 'color': '#8b5cf6'},
    'consultation': {'name': '咨询回复', 'icon': '💬', 'color': '#06b6d4'},
}

def read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_notifications(user_id='default', unread_only=False, limit=50):
    """获取用户通知列表"""
    data = read_json(NOTIFICATIONS_FILE, {'notifications': [], 'count': 0})
    notifs = data.get('notifications', [])
    # 过滤用户通知（user_id为'all'表示全员通知）
    user_notifs = [n for n in notifs if n.get('user_id') == user_id or n.get('user_id') == 'all']
    if unread_only:
        user_notifs = [n for n in user_notifs if not n.get('read', False)]
    user_notifs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return user_notifs[:limit]

def get_unread_count(user_id='default'):
    """获取未读通知数"""
    notifs = get_notifications(user_id, unread_only=True, limit=999)
    return len(notifs)

def create_notification(user_id, ntype, title, content, link='', extra=None):
    """创建通知"""
    data = read_json(NOTIFICATIONS_FILE, {'notifications': [], 'count': 0})
    notif = {
        'id': 'NOTIF-' + hashlib.md5(f'{user_id}{ntype}{title}{datetime.datetime.now().isoformat()}'.encode()).hexdigest()[:12].upper(),
        'user_id': user_id,
        'type': ntype,
        'type_name': NOTIFICATION_TYPES.get(ntype, {}).get('name', ntype),
        'icon': NOTIFICATION_TYPES.get(ntype, {}).get('icon', '🔔'),
        'color': NOTIFICATION_TYPES.get(ntype, {}).get('color', '#666'),
        'title': title,
        'content': content,
        'link': link,
        'extra': extra or {},
        'read': False,
        'created_at': datetime.datetime.now().isoformat(),
        'read_at': None
    }
    data['notifications'].append(notif)
    data['count'] = len(data['notifications'])
    write_json(NOTIFICATIONS_FILE, data)
    return notif

def mark_as_read(notif_id, user_id='default'):
    """标记单条通知为已读"""
    data = read_json(NOTIFICATIONS_FILE, {'notifications': [], 'count': 0})
    for n in data['notifications']:
        if n['id'] == notif_id and (n['user_id'] == user_id or n['user_id'] == 'all'):
            n['read'] = True
            n['read_at'] = datetime.datetime.now().isoformat()
            break
    write_json(NOTIFICATIONS_FILE, data)
    return True

def mark_all_as_read(user_id='default'):
    """标记全部通知为已读"""
    data = read_json(NOTIFICATIONS_FILE, {'notifications': [], 'count': 0})
    for n in data['notifications']:
        if n['user_id'] == user_id or n['user_id'] == 'all':
            n['read'] = True
            if not n.get('read_at'):
                n['read_at'] = datetime.datetime.now().isoformat()
    write_json(NOTIFICATIONS_FILE, data)
    return True

def delete_notification(notif_id, user_id='default'):
    """删除通知"""
    data = read_json(NOTIFICATIONS_FILE, {'notifications': [], 'count': 0})
    data['notifications'] = [n for n in data['notifications'] if not (n['id'] == notif_id and (n['user_id'] == user_id or n['user_id'] == 'all'))]
    data['count'] = len(data['notifications'])
    write_json(NOTIFICATIONS_FILE, data)
    return True

def get_stats(user_id='default'):
    """获取通知统计"""
    notifs = get_notifications(user_id, limit=999)
    unread = sum(1 for n in notifs if not n.get('read'))
    by_type = {}
    for n in notifs:
        t = n.get('type', 'other')
        by_type[t] = by_type.get(t, 0) + 1
    return {
        'total': len(notifs),
        'unread': unread,
        'read': len(notifs) - unread,
        'by_type': by_type,
        'types': NOTIFICATION_TYPES
    }

def broadcast_system_announcement(title, content, link=''):
    """广播系统公告（全员）"""
    return create_notification('all', 'system', title, content, link)

def notify_appointment(user_id, action, appointment_info):
    """预约相关通知"""
    if action == 'created':
        return create_notification(user_id, 'appointment',
            '预约申请已提交',
            f"您的{appointment_info.get('guide_title','办事')}预约已提交，预约时间：{appointment_info.get('time_slot','')}",
            '/gov-ai/?page=profile')
    elif action == 'confirmed':
        return create_notification(user_id, 'appointment',
            '预约已确认',
            f"您的{appointment_info.get('guide_title','办事')}预约已确认，请按时前往办理",
            '/gov-ai/?page=profile')
    elif action == 'cancelled':
        return create_notification(user_id, 'appointment',
            '预约已取消',
            f"您的{appointment_info.get('guide_title','办事')}预约已取消",
            '/gov-ai/?page=profile')

def notify_policy_update(title, category):
    """政策更新通知（全员）"""
    return create_notification('all', 'policy',
        '新政策发布',
        f"【{category}】{title} 已发布，点击查看详情",
        '/gov-ai/?page=policy')

def notify_todo(staff_id, todo_title, todo_desc):
    """工作台待办提醒"""
    return create_notification(staff_id, 'todo',
        '新待办事项',
        f"{todo_title}：{todo_desc}",
        '/workbench/')

def notify_approval(staff_id, approval_type, item_title):
    """审批通知"""
    return create_notification(staff_id, 'approval',
        '待审批事项',
        f"有新的{approval_type}待审批：{item_title}",
        '/workbench/?page=approvals')

def notify_consultation_reply(user_id, question, answer_preview):
    """咨询回复通知"""
    return create_notification(user_id, 'consultation',
        '咨询已回复',
        f"您的咨询「{question[:20]}...」已回复：{answer_preview[:30]}...",
        '/gov-ai/?page=chat')

# 初始化示例数据
def init_demo_data():
    data = read_json(NOTIFICATIONS_FILE, {'notifications': [], 'count': 0})
    if data.get('count', 0) == 0:
        now = datetime.datetime.now()
        demo_notifs = [
            {'user_id': 'all', 'type': 'system', 'title': '系统升级通知', 'content': '政务中台已升级至V4.1，新增RBAC权限系统和通知推送功能', 'link': ''},
            {'user_id': 'all', 'type': 'policy', 'title': '新政策发布', 'content': '【社会保障】2026年城乡居民基本医疗保险缴费指南已发布', 'link': '/gov-ai/?page=policy'},
            {'user_id': 'default', 'type': 'appointment', 'title': '预约申请已提交', 'content': '您的身份证办理预约已提交，预约时间：2026-09-10 上午', 'link': '/gov-ai/?page=profile'},
            {'user_id': 'default', 'type': 'consultation', 'title': '咨询已回复', 'content': '您的咨询「社保缴费比例」已回复，点击查看详情', 'link': '/gov-ai/?page=chat'},
            {'user_id': 'admin', 'type': 'todo', 'title': '新待办事项', 'content': '有3条群众咨询待回复，2条预约待确认', 'link': '/workbench/'},
            {'user_id': 'admin', 'type': 'approval', 'title': '待审批事项', 'content': '有1条公文发布申请待审批', 'link': '/workbench/?page=approvals'},
        ]
        for d in demo_notifs:
            notif = create_notification(d['user_id'], d['type'], d['title'], d['content'], d['link'])
            notif['created_at'] = (now - datetime.timedelta(minutes=len(demo_notifs)-demo_notifs.index(d)*15)).isoformat()
        # 重新写入时间
        write_json(NOTIFICATIONS_FILE, read_json(NOTIFICATIONS_FILE, {'notifications': [], 'count': 0}))
        print(f'✅ 通知系统初始化完成，已创建{len(demo_notifs)}条示例通知')
    else:
        print(f'⏭️ 通知系统已有{data["count"]}条数据，跳过初始化')

if __name__ == '__main__':
    init_demo_data()
    print('通知统计:', json.dumps(get_stats('default'), ensure_ascii=False, indent=2))
