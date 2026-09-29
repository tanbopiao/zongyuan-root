#!/usr/bin/env python3
"""
政务工作台API模块
提供待办事项、任务管理、工作台统计、公文模板等功能
"""
import json
import os
import datetime
import uuid

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'workbench')
os.makedirs(DATA_DIR, exist_ok=True)

# 文件路径
TODO_FILE = os.path.join(DATA_DIR, 'todos.json')
TASK_FILE = os.path.join(DATA_DIR, 'tasks.json')
STATS_FILE = os.path.join(DATA_DIR, 'workbench_stats.json')
DOC_TEMPLATES_FILE = '/opt/ZONGYUAN-ROOT/gov-ai/gov-scene-templates.json'

def _load_json(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def _save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============ 待办事项 ============
def get_todos(status=None, limit=50):
    todos = _load_json(TODO_FILE, [])
    if status:
        todos = [t for t in todos if t.get('status') == status]
    todos.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return todos[:limit]

def create_todo(title, description='', priority='medium', due_date=None, assignee=''):
    todos = _load_json(TODO_FILE, [])
    todo = {
        'id': str(uuid.uuid4())[:8],
        'title': title,
        'description': description,
        'priority': priority,  # high/medium/low
        'status': 'pending',  # pending/in_progress/completed
        'due_date': due_date,
        'assignee': assignee,
        'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    todos.append(todo)
    _save_json(TODO_FILE, todos)
    return todo

def update_todo(todo_id, **kwargs):
    todos = _load_json(TODO_FILE, [])
    for t in todos:
        if t['id'] == todo_id:
            t.update(kwargs)
            t['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _save_json(TODO_FILE, todos)
            return t
    return None

def delete_todo(todo_id):
    todos = _load_json(TODO_FILE, [])
    todos = [t for t in todos if t['id'] != todo_id]
    _save_json(TODO_FILE, todos)
    return True

# ============ 任务管理 ============
def get_tasks(status=None, limit=50):
    tasks = _load_json(TASK_FILE, [])
    if status:
        tasks = [t for t in tasks if t.get('status') == status]
    tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return tasks[:limit]

def create_task(title, description='', priority='medium', assignee=''):
    tasks = _load_json(TASK_FILE, [])
    task = {
        'id': str(uuid.uuid4())[:8],
        'title': title,
        'description': description,
        'priority': priority,
        'status': 'pending',
        'assignee': assignee,
        'progress': 0,
        'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    tasks.append(task)
    _save_json(TASK_FILE, tasks)
    return task

def update_task(task_id, **kwargs):
    tasks = _load_json(TASK_FILE, [])
    for t in tasks:
        if t['id'] == task_id:
            t.update(kwargs)
            t['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _save_json(TASK_FILE, tasks)
            return t
    return None

# ============ 工作台统计 ============
def get_workbench_stats():
    """获取工作台首页统计数据"""
    todos = _load_json(TODO_FILE, [])
    tasks = _load_json(TASK_FILE, [])
    
    # 读取API使用记录
    api_usage_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'api_usage.jsonl')
    today_calls = 0
    total_calls = 0
    if os.path.exists(api_usage_file):
        today = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
        with open(api_usage_file, 'r') as f:
            for line in f:
                total_calls += 1
                if today in line:
                    today_calls += 1
    
    stats = {
        'pending_todos': len([t for t in todos if t['status'] == 'pending']),
        'in_progress_todos': len([t for t in todos if t['status'] == 'in_progress']),
        'completed_todos': len([t for t in todos if t['status'] == 'completed']),
        'pending_tasks': len([t for t in tasks if t['status'] == 'pending']),
        'in_progress_tasks': len([t for t in tasks if t['status'] == 'in_progress']),
        'today_consultations': today_calls,
        'total_consultations': total_calls,
        'high_priority_todos': len([t for t in todos if t['priority'] == 'high' and t['status'] != 'completed']),
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    return stats

# ============ 公文模板 ============
def get_doc_templates():
    """获取公文场景模板列表"""
    if os.path.exists(DOC_TEMPLATES_FILE):
        with open(DOC_TEMPLATES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        scenes = data.get('scenes', [])
        # 只返回政务相关场景
        gov_categories = ['公文处理', '政策研究', '政务服务', '舆情监测', '知识服务', 
                         '会议服务', '政策服务', '办公效率', '社会治理', '行政审批', 
                         '民生服务', '数据治理', '应急管理']
        gov_scenes = [s for s in scenes if s.get('category', '') in gov_categories or 
                      any(k in s.get('title', '') for k in ['公文', '政策', '政务', '会议', '审批', '舆情', '应急'])]
        return {
            'total': len(gov_scenes),
            'templates': gov_scenes
        }
    return {'total': 0, 'templates': []}

# ============ 快捷入口配置 ============
def get_quick_actions():
    """获取工作台快捷入口配置"""
    return [
        {'id': 'chat', 'name': '智能咨询', 'icon': '💬', 'desc': 'AI辅助回答群众问题', 'color': '#3b82f6'},
        {'id': 'doc', 'name': '公文生成', 'icon': '📝', 'desc': '智能起草公文材料', 'color': '#8b5cf6'},
        {'id': 'policy', 'name': '政策检索', 'icon': '📋', 'desc': '快速查找政策文件', 'color': '#10b981'},
        {'id': 'guide', 'name': '办事指南', 'icon': '📖', 'desc': '查询办事流程材料', 'color': '#f59e0b'},
        {'id': 'stats', 'name': '数据统计', 'icon': '📊', 'desc': '查看业务数据报表', 'color': '#ef4444'},
        {'id': 'todo', 'name': '待办事项', 'icon': '✅', 'desc': '管理个人待办任务', 'color': '#06b6d4'},
        {'id': 'knowledge', 'name': '知识库', 'icon': '📚', 'desc': '部门知识经验库', 'color': '#ec4899'},
        {'id': 'settings', 'name': '系统设置', 'icon': '⚙️', 'desc': '个人偏好设置', 'color': '#6b7280'},
    ]

if __name__ == '__main__':
    print("=== 政务工作台API模块测试 ===")
    print("\n1. 快捷入口:")
    for action in get_quick_actions():
        print(f"  {action['icon']} {action['name']}: {action['desc']}")
    
    print("\n2. 公文模板:")
    templates = get_doc_templates()
    print(f"  政务相关模板: {templates['total']}个")
    for t in templates['templates'][:5]:
        print(f"  - {t.get('title')} ({t.get('category')})")
    
    print("\n3. 工作台统计:")
    stats = get_workbench_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n✅ 模块测试通过")
