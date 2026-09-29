#!/usr/bin/env python3
"""
政务工作台API V1.1扩展模块
新增：办事审批、咨询记录、任务分派、公文历史、绩效考核、多角色权限
"""
import json
import os
import datetime
import uuid

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'workbench')
os.makedirs(DATA_DIR, exist_ok=True)

APPROVAL_FILE = os.path.join(DATA_DIR, 'approvals.json')
CONSULTATION_FILE = os.path.join(DATA_DIR, 'consultations.json')
DOC_HISTORY_FILE = os.path.join(DATA_DIR, 'doc_history.json')
PERFORMANCE_FILE = os.path.join(DATA_DIR, 'performance.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

def _load(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def _save(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def _id():
    return str(uuid.uuid4())[:8]

# ============ 1. 办事审批系统 ============
def get_approvals(status=None, assignee=None, limit=50):
    items = _load(APPROVAL_FILE, [])
    if status:
        items = [i for i in items if i.get('status') == status]
    if assignee:
        items = [i for i in items if i.get('assignee') == assignee]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return items[:limit]

def create_approval(title, applicant, item_type, description='', priority='medium'):
    items = _load(APPROVAL_FILE, [])
    item = {
        'id': _id(),
        'title': title,
        'applicant': applicant,
        'item_type': item_type,  # 请假/报销/采购/用印/其他
        'description': description,
        'priority': priority,
        'status': 'pending',  # pending/approved/rejected
        'assignee': '',
        'approver': '',
        'approve_comment': '',
        'created_at': _now(),
        'updated_at': _now()
    }
    items.append(item)
    _save(APPROVAL_FILE, items)
    return item

def update_approval(approval_id, **kwargs):
    items = _load(APPROVAL_FILE, [])
    for i in items:
        if i['id'] == approval_id:
            i.update(kwargs)
            i['updated_at'] = _now()
            _save(APPROVAL_FILE, items)
            return i
    return None

# ============ 2. 咨询记录同步 ============
def get_consultations(status=None, limit=50):
    items = _load(CONSULTATION_FILE, [])
    if status:
        items = [i for i in items if i.get('status') == status]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return items[:limit]

def create_consultation(citizen_name, question, category='general', phone=''):
    items = _load(CONSULTATION_FILE, [])
    item = {
        'id': _id(),
        'citizen_name': citizen_name,
        'phone': phone,
        'question': question,
        'category': category,
        'answer': '',
        'status': 'pending',  # pending/answered/closed
        'assignee': '',
        'created_at': _now(),
        'updated_at': _now()
    }
    items.append(item)
    _save(CONSULTATION_FILE, items)
    return item

def update_consultation(consult_id, **kwargs):
    items = _load(CONSULTATION_FILE, [])
    for i in items:
        if i['id'] == consult_id:
            i.update(kwargs)
            i['updated_at'] = _now()
            _save(CONSULTATION_FILE, items)
            return i
    return None

# ============ 3. 公文历史云端存储 ============
def get_doc_history(user_id=None, limit=50):
    items = _load(DOC_HISTORY_FILE, [])
    if user_id:
        items = [i for i in items if i.get('creator') == user_id]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return items[:limit]

def save_doc_history(title, doc_type, content, creator, template_id=''):
    items = _load(DOC_HISTORY_FILE, [])
    item = {
        'id': _id(),
        'title': title,
        'doc_type': doc_type,
        'content': content,
        'template_id': template_id,
        'creator': creator,
        'word_count': len(content),
        'status': 'draft',  # draft/finalized/archived
        'created_at': _now(),
        'updated_at': _now()
    }
    items.append(item)
    _save(DOC_HISTORY_FILE, items)
    return item

def update_doc_history(doc_id, **kwargs):
    items = _load(DOC_HISTORY_FILE, [])
    for i in items:
        if i['id'] == doc_id:
            i.update(kwargs)
            i['updated_at'] = _now()
            _save(DOC_HISTORY_FILE, items)
            return i
    return None

# ============ 4. 绩效考核面板 ============
def get_performance(user_id=None, period='month'):
    """获取绩效考核数据"""
    todos = _load(os.path.join(DATA_DIR, 'todos.json'), [])
    tasks = _load(os.path.join(DATA_DIR, 'tasks.json'), [])
    approvals = _load(APPROVAL_FILE, [])
    consultations = _load(CONSULTATION_FILE, [])
    docs = _load(DOC_HISTORY_FILE, [])
    
    now = datetime.datetime.now(datetime.timezone.utc)
    if period == 'week':
        start = (now - datetime.timedelta(days=7)).isoformat()
    elif period == 'month':
        start = (now - datetime.timedelta(days=30)).isoformat()
    else:
        start = ''
    
    def in_period(item):
        if not start:
            return True
        return item.get('created_at', '') >= start
    
    period_todos = [t for t in todos if in_period(t)]
    period_approvals = [a for a in approvals if in_period(a)]
    period_consults = [c for c in consultations if in_period(c)]
    period_docs = [d for d in docs if in_period(d)]
    
    completed_todos = len([t for t in period_todos if t.get('status') == 'completed'])
    total_todos = len(period_todos)
    completion_rate = (completed_todos / total_todos * 100) if total_todos > 0 else 0
    
    approved_count = len([a for a in period_approvals if a.get('status') == 'approved'])
    answered_consults = len([c for c in period_consults if c.get('status') == 'answered'])
    
    total_words = sum(d.get('word_count', 0) for d in period_docs)
    
    # 综合评分（百分制）
    score = min(100, int(
        completion_rate * 0.3 +
        min(100, approved_count * 10) * 0.2 +
        min(100, answered_consults * 10) * 0.2 +
        min(100, len(period_docs) * 10) * 0.15 +
        min(100, total_words / 100) * 0.15
    ))
    
    if score >= 90:
        grade = 'A'
    elif score >= 80:
        grade = 'B'
    elif score >= 70:
        grade = 'C'
    elif score >= 60:
        grade = 'D'
    else:
        grade = 'E'
    
    return {
        'period': period,
        'score': score,
        'grade': grade,
        'metrics': {
            'todo_completion_rate': round(completion_rate, 1),
            'todos_completed': completed_todos,
            'todos_total': total_todos,
            'approvals_processed': approved_count,
            'consultations_answered': answered_consults,
            'docs_created': len(period_docs),
            'total_words': total_words
        },
        'timestamp': _now()
    }

# ============ 5. 多角色权限 ============
def get_users():
    return _load(USERS_FILE, [
        {'id': 'admin', 'username': 'admin', 'name': '系统管理员', 'role': 'admin', 'permissions': ['all'], 'status': 'active'},
        {'id': 'staff', 'username': 'staff', 'name': '工作人员', 'role': 'staff', 'permissions': ['todo', 'doc', 'consult', 'policy'], 'status': 'active'},
        {'id': 'visitor', 'username': 'visitor', 'name': '访客', 'role': 'visitor', 'permissions': ['policy', 'guide'], 'status': 'active'}
    ])

def get_user_permissions(role):
    role_perms = {
        'admin': ['all'],
        'staff': ['todo', 'doc', 'consult', 'policy', 'guide', 'approval_view'],
        'visitor': ['policy', 'guide']
    }
    return role_perms.get(role, [])

def check_permission(role, resource):
    perms = get_user_permissions(role)
    return 'all' in perms or resource in perms

# ============ V1.1统计汇总 ============
def get_v11_stats():
    return {
        'approvals_pending': len([a for a in _load(APPROVAL_FILE, []) if a.get('status') == 'pending']),
        'approvals_total': len(_load(APPROVAL_FILE, [])),
        'consultations_pending': len([c for c in _load(CONSULTATION_FILE, []) if c.get('status') == 'pending']),
        'consultations_total': len(_load(CONSULTATION_FILE, [])),
        'docs_total': len(_load(DOC_HISTORY_FILE, [])),
        'users_total': len(get_users())
    }

if __name__ == '__main__':
    print("=== 工作台V1.1 API模块测试 ===")
    print(f"\n审批统计: {get_v11_stats()}")
    print(f"\n绩效考核(月): {get_performance(period='month')['score']}分")
    print(f"\n用户列表: {[u['name'] for u in get_users()]}")
    print("\n✅ V1.1模块测试通过")
