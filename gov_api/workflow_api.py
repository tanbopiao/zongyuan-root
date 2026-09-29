#!/usr/bin/env python3
"""
工作流编辑器后端持久化API V1.0
P1优化：工作流编辑器后端持久化
功能：保存/加载/删除/列表/模板库/执行记录
"""
import os
import json
import time
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
WORKFLOW_DIR = os.path.join(DATA_DIR, 'workflows')
WORKFLOW_FILE = os.path.join(WORKFLOW_DIR, 'workflows.json')
TEMPLATE_FILE = os.path.join(WORKFLOW_DIR, 'templates.json')
EXEC_LOG_FILE = os.path.join(WORKFLOW_DIR, 'executions.jsonl')

# 确保目录存在
os.makedirs(WORKFLOW_DIR, exist_ok=True)

# 内置工作流模板
DEFAULT_TEMPLATES = [
    {
        'id': 'tpl_policy_analysis',
        'name': '政策智能分析流程',
        'description': '自动检索政策→AI分析要点→生成摘要报告',
        'category': '政策分析',
        'icon': '📋',
        'nodes': [
            {'id': 'n1', 'type': 'start', 'name': '开始', 'x': 50, 'y': 150},
            {'id': 'n2', 'type': 'policy', 'name': '政策检索', 'x': 250, 'y': 150, 'prompt': '检索最新政策'},
            {'id': 'n3', 'type': 'ai', 'name': 'AI分析', 'x': 450, 'y': 150, 'prompt': '分析政策要点和影响', 'model': 'doubao'},
            {'id': 'n4', 'type': 'doc', 'name': '生成报告', 'x': 650, 'y': 150, 'prompt': '生成政策分析报告'},
            {'id': 'n5', 'type': 'end', 'name': '结束', 'x': 850, 'y': 150}
        ],
        'connections': [
            {'from': 'n1', 'to': 'n2'},
            {'from': 'n2', 'to': 'n3'},
            {'from': 'n3', 'to': 'n4'},
            {'from': 'n4', 'to': 'n5'}
        ]
    },
    {
        'id': 'tpl_doc_generation',
        'name': '公文智能写作流程',
        'description': '需求输入→AI起草→合规检查→格式润色',
        'category': '公文写作',
        'icon': '✍️',
        'nodes': [
            {'id': 'n1', 'type': 'start', 'name': '开始', 'x': 50, 'y': 150},
            {'id': 'n2', 'type': 'ai', 'name': 'AI起草', 'x': 250, 'y': 150, 'prompt': '根据需求起草公文', 'model': 'zhipu'},
            {'id': 'n3', 'type': 'logic', 'name': '合规检查', 'x': 450, 'y': 150, 'condition': 'result.length > 100'},
            {'id': 'n4', 'type': 'doc', 'name': '格式润色', 'x': 650, 'y': 80, 'prompt': '公文格式标准化'},
            {'id': 'n5', 'type': 'notify', 'name': '通知', 'x': 650, 'y': 220, 'prompt': '合规检查未通过'},
            {'id': 'n6', 'type': 'end', 'name': '结束', 'x': 850, 'y': 150}
        ],
        'connections': [
            {'from': 'n1', 'to': 'n2'},
            {'from': 'n2', 'to': 'n3'},
            {'from': 'n3', 'to': 'n4'},
            {'from': 'n3', 'to': 'n5'},
            {'from': 'n4', 'to': 'n6'},
            {'from': 'n5', 'to': 'n6'}
        ]
    },
    {
        'id': 'tpl_citizen_service',
        'name': '群众办事智能引导流程',
        'description': '需求识别→指南匹配→预约办理→满意度反馈',
        'category': '办事服务',
        'icon': '🧭',
        'nodes': [
            {'id': 'n1', 'type': 'start', 'name': '开始', 'x': 50, 'y': 150},
            {'id': 'n2', 'type': 'ai', 'name': '需求识别', 'x': 250, 'y': 150, 'prompt': '识别群众办事需求', 'model': 'zhipu'},
            {'id': 'n3', 'type': 'guide', 'name': '指南匹配', 'x': 450, 'y': 150},
            {'id': 'n4', 'type': 'data', 'name': '预约办理', 'x': 650, 'y': 150},
            {'id': 'n5', 'type': 'notify', 'name': '满意度反馈', 'x': 850, 'y': 150},
            {'id': 'n6', 'type': 'end', 'name': '结束', 'x': 1050, 'y': 150}
        ],
        'connections': [
            {'from': 'n1', 'to': 'n2'},
            {'from': 'n2', 'to': 'n3'},
            {'from': 'n3', 'to': 'n4'},
            {'from': 'n4', 'to': 'n5'},
            {'from': 'n5', 'to': 'n6'}
        ]
    },
    {
        'id': 'tpl_data_report',
        'name': '数据智能分析报表流程',
        'description': '数据采集→清洗分析→可视化→生成报表',
        'category': '数据分析',
        'icon': '📊',
        'nodes': [
            {'id': 'n1', 'type': 'start', 'name': '开始', 'x': 50, 'y': 150},
            {'id': 'n2', 'type': 'data', 'name': '数据采集', 'x': 250, 'y': 150},
            {'id': 'n3', 'type': 'ai', 'name': '智能分析', 'x': 450, 'y': 150, 'prompt': '分析数据趋势和异常', 'model': 'doubao-reasoning'},
            {'id': 'n4', 'type': 'logic', 'name': '异常检测', 'x': 650, 'y': 150, 'condition': 'anomaly_count > 0'},
            {'id': 'n5', 'type': 'doc', 'name': '生成报表', 'x': 850, 'y': 80},
            {'id': 'n6', 'type': 'notify', 'name': '告警通知', 'x': 850, 'y': 220},
            {'id': 'n7', 'type': 'end', 'name': '结束', 'x': 1050, 'y': 150}
        ],
        'connections': [
            {'from': 'n1', 'to': 'n2'},
            {'from': 'n2', 'to': 'n3'},
            {'from': 'n3', 'to': 'n4'},
            {'from': 'n4', 'to': 'n5'},
            {'from': 'n4', 'to': 'n6'},
            {'from': 'n5', 'to': 'n7'},
            {'from': 'n6', 'to': 'n7'}
        ]
    }
]


def _load_json(filepath, default=None):
    """安全加载JSON"""
    if default is None:
        default = {}
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'[Workflow API] 加载失败 {filepath}: {e}')
        return default


def _save_json(filepath, data):
    """安全保存JSON"""
    try:
        tmp_path = filepath + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
        return True
    except Exception as e:
        print(f'[Workflow API] 保存失败 {filepath}: {e}')
        return False


def init_templates():
    """初始化模板库"""
    if not os.path.exists(TEMPLATE_FILE):
        _save_json(TEMPLATE_FILE, {'templates': DEFAULT_TEMPLATES, 'updated_at': time.time()})
        print(f'[Workflow API] 模板库已初始化: {len(DEFAULT_TEMPLATES)}个模板')


def init_workflows():
    """初始化工作流存储"""
    if not os.path.exists(WORKFLOW_FILE):
        _save_json(WORKFLOW_FILE, {'workflows': [], 'updated_at': time.time()})


# 初始化
init_templates()
init_workflows()


def list_workflows(user_id='default', category=None):
    """获取工作流列表"""
    data = _load_json(WORKFLOW_FILE, {'workflows': []})
    workflows = data.get('workflows', [])
    # 按用户过滤
    user_workflows = [w for w in workflows if w.get('user_id', 'default') == user_id]
    # 按分类过滤
    if category:
        user_workflows = [w for w in user_workflows if w.get('category') == category]
    # 按更新时间排序
    user_workflows.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
    return {
        'total': len(user_workflows),
        'workflows': [
            {
                'id': w['id'],
                'name': w['name'],
                'description': w.get('description', ''),
                'category': w.get('category', '未分类'),
                'icon': w.get('icon', '🔧'),
                'node_count': len(w.get('nodes', [])),
                'connection_count': len(w.get('connections', [])),
                'created_at': w.get('created_at'),
                'updated_at': w.get('updated_at'),
                'exec_count': w.get('exec_count', 0)
            }
            for w in user_workflows
        ]
    }


def get_workflow(workflow_id, user_id='default'):
    """获取单个工作流详情"""
    data = _load_json(WORKFLOW_FILE, {'workflows': []})
    for w in data.get('workflows', []):
        if w['id'] == workflow_id and w.get('user_id', 'default') == user_id:
            return w
    return None


def save_workflow(workflow_data, user_id='default'):
    """保存工作流（新增或更新）"""
    data = _load_json(WORKFLOW_FILE, {'workflows': []})
    workflows = data.get('workflows', [])

    workflow_id = workflow_data.get('id')
    now = time.time()

    if workflow_id:
        # 更新现有工作流
        for i, w in enumerate(workflows):
            if w['id'] == workflow_id and w.get('user_id', 'default') == user_id:
                workflows[i].update({
                    'name': workflow_data.get('name', w['name']),
                    'description': workflow_data.get('description', w.get('description', '')),
                    'category': workflow_data.get('category', w.get('category', '未分类')),
                    'icon': workflow_data.get('icon', w.get('icon', '🔧')),
                    'nodes': workflow_data.get('nodes', w.get('nodes', [])),
                    'connections': workflow_data.get('connections', w.get('connections', [])),
                    'updated_at': now
                })
                data['workflows'] = workflows
                data['updated_at'] = now
                _save_json(WORKFLOW_FILE, data)
                return {'success': True, 'id': workflow_id, 'action': 'updated'}
        # 没找到，作为新增
        workflow_id = 'wf_' + uuid.uuid4().hex[:12]

    # 新增工作流
    workflow_id = workflow_id or 'wf_' + uuid.uuid4().hex[:12]
    new_workflow = {
        'id': workflow_id,
        'user_id': user_id,
        'name': workflow_data.get('name', '未命名工作流'),
        'description': workflow_data.get('description', ''),
        'category': workflow_data.get('category', '未分类'),
        'icon': workflow_data.get('icon', '🔧'),
        'nodes': workflow_data.get('nodes', []),
        'connections': workflow_data.get('connections', []),
        'created_at': now,
        'updated_at': now,
        'exec_count': 0
    }
    workflows.append(new_workflow)
    data['workflows'] = workflows
    data['updated_at'] = now
    _save_json(WORKFLOW_FILE, data)
    return {'success': True, 'id': workflow_id, 'action': 'created'}


def delete_workflow(workflow_id, user_id='default'):
    """删除工作流"""
    data = _load_json(WORKFLOW_FILE, {'workflows': []})
    workflows = data.get('workflows', [])
    original_count = len(workflows)
    workflows = [w for w in workflows if not (w['id'] == workflow_id and w.get('user_id', 'default') == user_id)]
    if len(workflows) == original_count:
        return {'success': False, 'error': '工作流不存在或无权删除'}
    data['workflows'] = workflows
    data['updated_at'] = time.time()
    _save_json(WORKFLOW_FILE, data)
    return {'success': True, 'id': workflow_id}


def list_templates(category=None):
    """获取模板列表"""
    data = _load_json(TEMPLATE_FILE, {'templates': DEFAULT_TEMPLATES})
    templates = data.get('templates', DEFAULT_TEMPLATES)
    if category:
        templates = [t for t in templates if t.get('category') == category]
    return {
        'total': len(templates),
        'templates': [
            {
                'id': t['id'],
                'name': t['name'],
                'description': t.get('description', ''),
                'category': t.get('category', ''),
                'icon': t.get('icon', '🔧'),
                'node_count': len(t.get('nodes', [])),
                'connection_count': len(t.get('connections', []))
            }
            for t in templates
        ]
    }


def get_template(template_id):
    """获取模板详情"""
    data = _load_json(TEMPLATE_FILE, {'templates': DEFAULT_TEMPLATES})
    for t in data.get('templates', DEFAULT_TEMPLATES):
        if t['id'] == template_id:
            return t
    return None


def apply_template(template_id, user_id='default'):
    """应用模板（创建工作流副本）"""
    template = get_template(template_id)
    if not template:
        return {'success': False, 'error': '模板不存在'}
    # 创建工作流副本
    workflow_data = {
        'name': template['name'] + ' (副本)',
        'description': template.get('description', ''),
        'category': template.get('category', '未分类'),
        'icon': template.get('icon', '🔧'),
        'nodes': template.get('nodes', []),
        'connections': template.get('connections', [])
    }
    return save_workflow(workflow_data, user_id)


def record_execution(workflow_id, exec_data, user_id='default'):
    """记录工作流执行"""
    # 更新执行计数
    data = _load_json(WORKFLOW_FILE, {'workflows': []})
    for w in data.get('workflows', []):
        if w['id'] == workflow_id:
            w['exec_count'] = w.get('exec_count', 0) + 1
            w['last_exec_at'] = time.time()
            break
    _save_json(WORKFLOW_FILE, data)

    # 记录执行日志
    log_entry = {
        'exec_id': 'exec_' + uuid.uuid4().hex[:12],
        'workflow_id': workflow_id,
        'user_id': user_id,
        'status': exec_data.get('status', 'completed'),
        'duration_ms': exec_data.get('duration_ms', 0),
        'node_count': exec_data.get('node_count', 0),
        'error': exec_data.get('error'),
        'executed_at': time.time()
    }
    try:
        with open(EXEC_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f'[Workflow API] 执行日志记录失败: {e}')
    return log_entry


def get_stats(user_id='default'):
    """获取工作流统计"""
    data = _load_json(WORKFLOW_FILE, {'workflows': []})
    workflows = [w for w in data.get('workflows', []) if w.get('user_id', 'default') == user_id]
    templates = _load_json(TEMPLATE_FILE, {'templates': DEFAULT_TEMPLATES}).get('templates', DEFAULT_TEMPLATES)

    # 分类统计
    categories = {}
    total_nodes = 0
    total_connections = 0
    total_execs = 0
    for w in workflows:
        cat = w.get('category', '未分类')
        categories[cat] = categories.get(cat, 0) + 1
        total_nodes += len(w.get('nodes', []))
        total_connections += len(w.get('connections', []))
        total_execs += w.get('exec_count', 0)

    return {
        'total_workflows': len(workflows),
        'total_templates': len(templates),
        'total_nodes': total_nodes,
        'total_connections': total_connections,
        'total_executions': total_execs,
        'categories': categories,
        'recent_workflows': sorted(workflows, key=lambda x: x.get('updated_at', 0), reverse=True)[:5]
    }


# API路由处理函数
def handle_workflow_api(path, method, params, body=None):
    """处理工作流API请求
    返回: (status_code, response_data)
    """
    user_id = params.get('user_id', ['default'])[0] if params else 'default'

    # GET /api/gov/workflow/list - 工作流列表
    if path == '/api/gov/workflow/list' and method == 'GET':
        category = params.get('category', [''])[0] if params else ''
        return 200, list_workflows(user_id, category or None)

    # GET /api/gov/workflow/get - 获取工作流详情
    elif path == '/api/gov/workflow/get' and method == 'GET':
        workflow_id = params.get('id', [''])[0] if params else ''
        if not workflow_id:
            return 400, {'error': 'id参数必填'}
        workflow = get_workflow(workflow_id, user_id)
        if not workflow:
            return 404, {'error': '工作流不存在'}
        return 200, workflow

    # POST /api/gov/workflow/save - 保存工作流
    elif path == '/api/gov/workflow/save' and method == 'POST':
        if not body:
            return 400, {'error': '请求体不能为空'}
        result = save_workflow(body, user_id)
        return 200 if result['success'] else 500, result

    # POST /api/gov/workflow/delete - 删除工作流
    elif path == '/api/gov/workflow/delete' and method == 'POST':
        workflow_id = (body or {}).get('id', '')
        if not workflow_id:
            return 400, {'error': 'id参数必填'}
        result = delete_workflow(workflow_id, user_id)
        return 200 if result['success'] else 404, result

    # GET /api/gov/workflow/templates - 模板列表
    elif path == '/api/gov/workflow/templates' and method == 'GET':
        category = params.get('category', [''])[0] if params else ''
        return 200, list_templates(category or None)

    # GET /api/gov/workflow/template/get - 获取模板详情
    elif path == '/api/gov/workflow/template/get' and method == 'GET':
        template_id = params.get('id', [''])[0] if params else ''
        if not template_id:
            return 400, {'error': 'id参数必填'}
        template = get_template(template_id)
        if not template:
            return 404, {'error': '模板不存在'}
        return 200, template

    # POST /api/gov/workflow/template/apply - 应用模板
    elif path == '/api/gov/workflow/template/apply' and method == 'POST':
        template_id = (body or {}).get('template_id', '')
        if not template_id:
            return 400, {'error': 'template_id参数必填'}
        result = apply_template(template_id, user_id)
        return 200 if result['success'] else 404, result

    # GET /api/gov/workflow/stats - 统计信息
    elif path == '/api/gov/workflow/stats' and method == 'GET':
        return 200, get_stats(user_id)

    # POST /api/gov/workflow/exec/log - 记录执行
    elif path == '/api/gov/workflow/exec/log' and method == 'POST':
        workflow_id = (body or {}).get('workflow_id', '')
        if not workflow_id:
            return 400, {'error': 'workflow_id参数必填'}
        result = record_execution(workflow_id, body or {}, user_id)
        return 200, result

    return None  # 未匹配


print(f'[Workflow API] 初始化完成: {len(DEFAULT_TEMPLATES)}个内置模板')
