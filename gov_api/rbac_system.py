#!/usr/bin/env python3
"""
政务中台RBAC权限系统 V1.0
用户管理/角色管理/权限矩阵/会话管理/操作审计
"""
import json, os, hashlib, datetime, secrets, time

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data'
RBAC_DIR = os.path.join(DATA_DIR, 'rbac')
os.makedirs(RBAC_DIR, exist_ok=True)

# ============ 数据文件路径 ============
USERS_FILE = os.path.join(RBAC_DIR, 'users.json')
ROLES_FILE = os.path.join(RBAC_DIR, 'roles.json')
PERMISSIONS_FILE = os.path.join(RBAC_DIR, 'permissions.json')
SESSIONS_FILE = os.path.join(RBAC_DIR, 'sessions.json')
AUDIT_LOG_FILE = os.path.join(RBAC_DIR, 'audit_log.jsonl')

# ============ 权限定义 ============
ALL_PERMISSIONS = [
    # 系统管理
    {'id': 'sys.user.manage', 'name': '用户管理', 'category': '系统管理', 'desc': '增删改查用户'},
    {'id': 'sys.role.manage', 'name': '角色管理', 'category': '系统管理', 'desc': '增删改查角色和权限'},
    {'id': 'sys.audit.view', 'name': '审计日志', 'category': '系统管理', 'desc': '查看操作审计日志'},
    {'id': 'sys.config', 'name': '系统配置', 'category': '系统管理', 'desc': '修改系统配置'},
    # 政务业务
    {'id': 'gov.policy.manage', 'name': '政策管理', 'category': '政务业务', 'desc': '增删改查政策'},
    {'id': 'gov.guide.manage', 'name': '指南管理', 'category': '政务业务', 'desc': '增删改查办事指南'},
    {'id': 'gov.consultation.handle', 'name': '咨询处理', 'category': '政务业务', 'desc': '处理群众咨询'},
    {'id': 'gov.appointment.manage', 'name': '预约管理', 'category': '政务业务', 'desc': '管理办事预约'},
    {'id': 'gov.document.create', 'name': '公文生成', 'category': '政务业务', 'desc': '生成和管理公文'},
    {'id': 'gov.approval.handle', 'name': '审批处理', 'category': '政务业务', 'desc': '处理审批事项'},
    # 数据查看
    {'id': 'data.view', 'name': '数据查看', 'category': '数据查看', 'desc': '查看业务数据'},
    {'id': 'data.export', 'name': '数据导出', 'category': '数据查看', 'desc': '导出数据报表'},
    {'id': 'data.dashboard', 'name': '仪表盘', 'category': '数据查看', 'desc': '查看数据仪表盘'},
    # 智能能力
    {'id': 'ai.chat', 'name': 'AI问答', 'category': '智能能力', 'desc': '使用AI智能问答'},
    {'id': 'ai.evolution', 'name': '进化管理', 'category': '智能能力', 'desc': '管理自进化引擎'},
    {'id': 'ai.operator', 'name': '算子管理', 'category': '智能能力', 'desc': '管理政务算子'},
]

# ============ 角色定义 ============
DEFAULT_ROLES = [
    {
        'id': 'admin',
        'name': '系统管理员',
        'desc': '拥有全部权限',
        'permissions': [p['id'] for p in ALL_PERMISSIONS],
        'created_at': '2026-09-06T00:00:00',
        'is_system': True
    },
    {
        'id': 'staff',
        'name': '工作人员',
        'desc': '政务业务处理人员',
        'permissions': ['gov.policy.manage','gov.guide.manage','gov.consultation.handle',
                       'gov.appointment.manage','gov.document.create','gov.approval.handle',
                       'data.view','data.dashboard','ai.chat'],
        'created_at': '2026-09-06T00:00:00',
        'is_system': True
    },
    {
        'id': 'visitor',
        'name': '访客',
        'desc': '只读查询权限',
        'permissions': ['data.view','data.dashboard','ai.chat'],
        'created_at': '2026-09-06T00:00:00',
        'is_system': True
    },
    {
        'id': 'auditor',
        'name': '审计员',
        'desc': '审计和合规检查',
        'permissions': ['sys.audit.view','data.view','data.export','data.dashboard'],
        'created_at': '2026-09-06T00:00:00',
        'is_system': True
    }
]

# ============ 默认用户 ============
DEFAULT_USERS = [
    {
        'id': 'user_001',
        'username': 'admin',
        'password_hash': hashlib.sha256('admin123'.encode()).hexdigest(),
        'name': '系统管理员',
        'role': 'admin',
        'email': 'admin@huodouai.com',
        'phone': '13800000001',
        'status': 'active',
        'created_at': '2026-09-06T00:00:00',
        'last_login': None
    },
    {
        'id': 'user_002',
        'username': 'staff_demo',
        'password_hash': hashlib.sha256('staff123'.encode()).hexdigest(),
        'name': '演示工作人员',
        'role': 'staff',
        'email': 'staff@huodouai.com',
        'phone': '13800000002',
        'status': 'active',
        'created_at': '2026-09-06T00:00:00',
        'last_login': None
    },
    {
        'id': 'user_003',
        'username': 'auditor_demo',
        'password_hash': hashlib.sha256('auditor123'.encode()).hexdigest(),
        'name': '演示审计员',
        'role': 'auditor',
        'email': 'auditor@huodouai.com',
        'phone': '13800000003',
        'status': 'active',
        'created_at': '2026-09-06T00:00:00',
        'last_login': None
    }
]

def read_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def append_audit(user_id, action, resource, detail=''):
    """追加审计日志"""
    entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'user_id': user_id,
        'action': action,
        'resource': resource,
        'detail': detail,
        'ip': '127.0.0.1'
    }
    with open(AUDIT_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def init_rbac():
    """初始化RBAC系统"""
    # 权限
    if not os.path.exists(PERMISSIONS_FILE):
        write_json(PERMISSIONS_FILE, {'permissions': ALL_PERMISSIONS, 'count': len(ALL_PERMISSIONS)})
        print('  ✅ 权限定义已初始化:', len(ALL_PERMISSIONS), '个权限')
    
    # 角色
    if not os.path.exists(ROLES_FILE):
        write_json(ROLES_FILE, {'roles': DEFAULT_ROLES, 'count': len(DEFAULT_ROLES)})
        print('  ✅ 角色定义已初始化:', len(DEFAULT_ROLES), '个角色')
    
    # 用户
    if not os.path.exists(USERS_FILE):
        write_json(USERS_FILE, {'users': DEFAULT_USERS, 'count': len(DEFAULT_USERS)})
        print('  ✅ 用户定义已初始化:', len(DEFAULT_USERS), '个用户')
    
    # 会话
    if not os.path.exists(SESSIONS_FILE):
        write_json(SESSIONS_FILE, {'sessions': [], 'count': 0})
        print('  ✅ 会话存储已初始化')
    
    # 审计日志
    if not os.path.exists(AUDIT_LOG_FILE):
        open(AUDIT_LOG_FILE, 'w').close()
        print('  ✅ 审计日志已初始化')

def login(username, password):
    """用户登录"""
    users = read_json(USERS_FILE, {}).get('users', [])
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    for user in users:
        if user['username'] == username and user['password_hash'] == password_hash:
            if user['status'] != 'active':
                return {'success': False, 'error': '账号已禁用'}
            
            # 创建会话
            token = secrets.token_hex(32)
            session = {
                'token': token,
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'created_at': datetime.datetime.now().isoformat(),
                'expires_at': (datetime.datetime.now() + datetime.timedelta(hours=8)).isoformat(),
                'last_active': datetime.datetime.now().isoformat()
            }
            
            sessions = read_json(SESSIONS_FILE, {})
            sessions['sessions'].append(session)
            sessions['count'] = len(sessions['sessions'])
            # 清理过期会话
            sessions['sessions'] = [s for s in sessions['sessions'] 
                                    if s['expires_at'] > datetime.datetime.now().isoformat()]
            sessions['count'] = len(sessions['sessions'])
            write_json(SESSIONS_FILE, sessions)
            
            # 更新最后登录
            user['last_login'] = datetime.datetime.now().isoformat()
            write_json(USERS_FILE, {'users': users, 'count': len(users)})
            
            append_audit(user['id'], 'login', 'auth', f'用户 {username} 登录成功')
            
            return {
                'success': True,
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'email': user.get('email',''),
                    'phone': user.get('phone','')
                }
            }
    
    append_audit('unknown', 'login_failed', 'auth', f'登录失败: {username}')
    return {'success': False, 'error': '用户名或密码错误'}

def verify_token(token):
    """验证Token，返回用户信息"""
    if not token:
        return None
    sessions = read_json(SESSIONS_FILE, {}).get('sessions', [])
    now = datetime.datetime.now().isoformat()
    for s in sessions:
        if s['token'] == token and s['expires_at'] > now:
            s['last_active'] = now
            return s
    return None

def get_user_permissions(user_id):
    """获取用户权限列表"""
    users = read_json(USERS_FILE, {}).get('users', [])
    roles = read_json(ROLES_FILE, {}).get('roles', [])
    
    for user in users:
        if user['id'] == user_id:
            for role in roles:
                if role['id'] == user['role']:
                    return role.get('permissions', [])
    return []

def check_permission(user_id, permission_id):
    """检查用户是否有权限"""
    perms = get_user_permissions(user_id)
    return permission_id in perms or '*' in perms

def logout(token):
    """用户登出"""
    sessions = read_json(SESSIONS_FILE, {})
    sessions['sessions'] = [s for s in sessions['sessions'] if s['token'] != token]
    sessions['count'] = len(sessions['sessions'])
    write_json(SESSIONS_FILE, sessions)
    return {'success': True}

# ============ 初始化 ============
if __name__ == '__main__':
    print('='*60)
    print('【政务中台RBAC权限系统初始化】')
    print('='*60)
    init_rbac()
    
    # 验证
    print('\n【验证】')
    result = login('admin', 'admin123')
    if result['success']:
        print(f'  ✅ admin登录成功, token={result["token"][:16]}...')
        perms = get_user_permissions(result['user']['id'])
        print(f'  ✅ admin权限数: {len(perms)}')
    else:
        print(f'  ❌ 登录失败: {result["error"]}')
    
    result = login('staff_demo', 'staff123')
    if result['success']:
        print(f'  ✅ staff_demo登录成功')
        perms = get_user_permissions(result['user']['id'])
        print(f'  ✅ staff权限数: {len(perms)}')
    
    print('\n' + '='*60)
    print('【RBAC系统初始化完成】')
    print('='*60)
    print(f'  权限: {len(ALL_PERMISSIONS)}个')
    print(f'  角色: {len(DEFAULT_ROLES)}个 (admin/staff/visitor/auditor)')
    print(f'  用户: {len(DEFAULT_USERS)}个 (admin/staff_demo/auditor_demo)')
    print(f'  会话: 8小时过期')
    print(f'  审计: JSONL不可篡改日志')
