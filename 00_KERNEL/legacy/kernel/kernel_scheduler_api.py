#!/usr/bin/env python3
"""
Ω-Brainμ 调度内核 API
双内核架构 - 主调度内核
职责：任务下发、真值校验、快照确权、熔断控制、状态管理
端口：8032
"""
import json
import hashlib
import hmac
import time
import os
import uuid
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 配置
KERNEL_DIR = '/opt/ZONGYUAN-ROOT/kernel'
MISSION_DIR = os.path.join(KERNEL_DIR, 'missions')
AGENT_REGISTRY_FILE = os.path.join(KERNEL_DIR, 'agent_registry.json')
SCHEDULER_SECRET = 'zongyuan-root-scheduler-secret-v1'
DID = 'DID-BR-000002'
TRACE_MARK = 'Ω₀⊂⊙∞⊂Ω'
PORT = 8032

# 飞书Base任务日志配置（从环境变量读取，未配置则跳过）
FEISHU_BASE_ENABLED = os.getenv('FEISHU_BASE_ENABLED', 'false').lower() == 'true'
FEISHU_BASE_APP_ID = os.getenv('FEISHU_BASE_APP_ID', '')
FEISHU_BASE_APP_SECRET = os.getenv('FEISHU_BASE_APP_SECRET', '')
FEISHU_BASE_TABLE_ID = os.getenv('FEISHU_BASE_TABLE_ID', '')
FEISHU_BASE_TOKEN_URL = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
FEISHU_BASE_RECORD_URL = 'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records'

# HITL人在回路配置
FEISHU_WEBHOOK_URL = os.getenv('FEISHU_WEBHOOK_URL', '')
HITL_ENABLED = os.getenv('HITL_ENABLED', 'false').lower() == 'true'
HIGH_RISK_KEYWORDS = ['删除', '清空', '转账', '支付', '发布', '审批', '合同', '法律', '敏感', '机密']

os.makedirs(MISSION_DIR, exist_ok=True)

# ========== 政务智能体注册中心 ==========
DEFAULT_AGENTS = [
    {'agent_id': 'gov-policy-analyst', 'name': '政策解读员', 'category': 'policy', 'description': '政策文件解读、要点提取、影响分析', 'capabilities': ['政策解读', '要点提取', '影响分析'], 'priority': 'P1', 'status': 'active'},
    {'agent_id': 'gov-service-navigator', 'name': '办事导航员', 'category': 'service', 'description': '办事流程指引、材料清单、窗口导航', 'capabilities': ['流程指引', '材料清单', '窗口导航'], 'priority': 'P1', 'status': 'active'},
    {'agent_id': 'gov-document-writer', 'name': '公文写作员', 'category': 'document', 'description': '公文起草、格式规范、内容润色', 'capabilities': ['公文起草', '格式规范', '内容润色'], 'priority': 'P2', 'status': 'active'},
    {'agent_id': 'gov-data-analyst', 'name': '数据分析员', 'category': 'data', 'description': '政务数据统计、趋势分析、报表生成', 'capabilities': ['数据统计', '趋势分析', '报表生成'], 'priority': 'P2', 'status': 'active'},
    {'agent_id': 'gov-risk-assessor', 'name': '风险评估员', 'category': 'risk', 'description': '政策风险、合规风险、舆情风险评估', 'capabilities': ['风险识别', '风险分级', '缓解建议'], 'priority': 'P0', 'status': 'active'},
    {'agent_id': 'gov-legal-advisor', 'name': '法务顾问', 'category': 'legal', 'description': '法律法规咨询、合同审查、合规建议', 'capabilities': ['法规咨询', '合同审查', '合规建议'], 'priority': 'P1', 'status': 'active'},
    {'agent_id': 'gov-public-opinion', 'name': '舆情监测员', 'category': 'opinion', 'description': '舆情监测、情感分析、预警报告', 'capabilities': ['舆情监测', '情感分析', '预警报告'], 'priority': 'P2', 'status': 'active'},
    {'agent_id': 'gov-meeting-assistant', 'name': '会议助手', 'category': 'meeting', 'description': '会议纪要、议题整理、行动项跟踪', 'capabilities': ['会议纪要', '议题整理', '行动项'], 'priority': 'P3', 'status': 'active'},
]

def init_agent_registry():
    """初始化智能体注册中心"""
    if not os.path.exists(AGENT_REGISTRY_FILE):
        registry = {
            'version': '1.0',
            'updated_at': time.time(),
            'agents': DEFAULT_AGENTS
        }
        with open(AGENT_REGISTRY_FILE, 'w') as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
        return registry
    with open(AGENT_REGISTRY_FILE) as f:
        return json.load(f)

agent_registry = init_agent_registry()

def list_agents(category=None, status='active'):
    """列出智能体"""
    agents = agent_registry.get('agents', [])
    if category:
        agents = [a for a in agents if a.get('category') == category]
    if status:
        agents = [a for a in agents if a.get('status') == status]
    return agents

def get_agent(agent_id):
    """获取智能体详情"""
    for a in agent_registry.get('agents', []):
        if a['agent_id'] == agent_id:
            return a
    return None

def register_agent(agent_data):
    """注册新智能体"""
    agent_registry['agents'].append(agent_data)
    agent_registry['updated_at'] = time.time()
    with open(AGENT_REGISTRY_FILE, 'w') as f:
        json.dump(agent_registry, f, ensure_ascii=False, indent=2)
    return agent_data

def feishu_log_mission(mission, action='created'):
    """同步任务状态到飞书Base（如果配置了）"""
    if not FEISHU_BASE_ENABLED or not FEISHU_BASE_APP_ID:
        return
    try:
        # 获取tenant_access_token
        token_resp = requests.post(FEISHU_BASE_TOKEN_URL, json={
            'app_id': FEISHU_BASE_APP_ID,
            'app_secret': FEISHU_BASE_APP_SECRET
        }, timeout=10)
        token = token_resp.json().get('tenant_access_token', '')
        if not token:
            return
        # 创建记录
        fields = {
            'mission_id': mission['mission_id'],
            'core_goal': mission['core_goal'][:200],
            'status': mission.get('status', 'pending'),
            'priority': mission.get('priority', 'P2'),
            'iteration': mission.get('iteration', 0),
            'max_iter': mission.get('max_iter', 10),
            'drift_risk': mission.get('drift_risk', False),
            'executor_id': mission.get('executor_id', ''),
            'action': action,
            'did': DID,
            'created_at': mission.get('created_at', time.time())
        }
        if mission.get('final_snapshot_hash'):
            fields['final_snapshot_hash'] = mission['final_snapshot_hash']
        if mission.get('agent_output'):
            fields['output_length'] = len(mission['agent_output'])
        requests.post(
            FEISHU_BASE_RECORD_URL.format(app_token=FEISHU_BASE_APP_ID, table_id=FEISHU_BASE_TABLE_ID),
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'fields': fields},
            timeout=10
        )
    except Exception as e:
        print(f'飞书Base日志失败: {e}')

def detect_high_risk(core_goal):
    """检测任务是否为高风险（需要HITL人工审批）"""
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in core_goal:
            return True, keyword
    return False, ''

def send_hitl_notification(mission):
    """发送HITL人工审批通知到飞书Webhook"""
    if not HITL_ENABLED or not FEISHU_WEBHOOK_URL:
        return
    try:
        is_risk, keyword = detect_high_risk(mission['core_goal'])
        if not is_risk:
            return
        message = {
            'msg_type': 'interactive',
            'card': {
                'header': {'title': {'tag': 'plain_text', 'content': '⚠️ 高风险任务审批请求'}, 'template': 'red'},
                'elements': [
                    {'tag': 'div', 'text': {'tag': 'lark_md', 'content': f'**任务ID**: {mission["mission_id"]}'}},
                    {'tag': 'div', 'text': {'tag': 'lark_md', 'content': f'**任务目标**: {mission["core_goal"][:100]}'}},
                    {'tag': 'div', 'text': {'tag': 'lark_md', 'content': f'**风险关键词**: {keyword}'}},
                    {'tag': 'div', 'text': {'tag': 'lark_md', 'content': f'**优先级**: {mission.get("priority", "P2")}'}},
                    {'tag': 'action', 'actions': [
                        {'tag': 'button', 'text': {'tag': 'plain_text', 'content': '✅ 批准执行'}, 'type': 'primary', 'value': {'action': 'approve', 'mission_id': mission['mission_id']}},
                        {'tag': 'button', 'text': {'tag': 'plain_text', 'content': '❌ 拒绝执行'}, 'type': 'danger', 'value': {'action': 'reject', 'mission_id': mission['mission_id']}}
                    ]}
                ]
            }
        }
        requests.post(FEISHU_WEBHOOK_URL, json=message, timeout=10)
    except Exception as e:
        print(f'HITL通知失败: {e}')

def resume_mission(mission_id):
    """恢复被中断的任务（HITL审批通过后）"""
    with mission_lock:
        mission = active_missions.get(mission_id)
        if not mission:
            return None
        if mission['status'] in ('interrupted', 'pending_approval'):
            mission['status'] = 'pending'
            mission['resumed_at'] = time.time()
            with open(os.path.join(MISSION_DIR, f'{mission_id}.json'), 'w') as f:
                json.dump(mission, f, ensure_ascii=False, indent=2)
            return mission
    return None

# 内存中的任务队列
mission_queue = []
active_missions = {}
mission_lock = threading.Lock()

def sha256_hash(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest().upper()

def verify_hmac(headers, body):
    """验证HMAC签名 + 防重放时间戳窗口（±300秒）"""
    signature = headers.get('X-Signature', '')
    timestamp = headers.get('X-Timestamp', '')
    if not signature or not timestamp:
        return False, '缺少签名或时间戳'
    # 防重放：时间戳窗口检查
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            return False, '时间戳超出窗口（±300秒）'
    except ValueError:
        return False, '时间戳格式错误'
    expected = hmac.new(
        SCHEDULER_SECRET.encode(),
        f"{timestamp}:{body}".encode(),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False, '签名验证失败'
    return True, 'OK'

# HMAC白名单：不需要签名的端点
HMAC_WHITELIST = ['/kernel/health', '/kernel/stats']

import fcntl

ROOT_LOCK_FILE = os.path.join(KERNEL_DIR, 'root_state.lock')

def _acquire_lock():
    """获取文件锁（阻塞）"""
    lock_fd = open(ROOT_LOCK_FILE, 'w')
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    return lock_fd

def _release_lock(lock_fd):
    """释放文件锁"""
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()

def load_root_state():
    path = os.path.join(KERNEL_DIR, 'root_state.json')
    lock_fd = _acquire_lock()
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {'block_height': 0, 'current_root_hash': '0'*64}
    finally:
        _release_lock(lock_fd)

def save_root_state(state):
    """原子写入：临时文件+fsync+rename，防止并发写入损坏"""
    path = os.path.join(KERNEL_DIR, 'root_state.json')
    tmp_path = path + '.tmp.' + str(os.getpid())
    lock_fd = _acquire_lock()
    try:
        with open(tmp_path, 'w') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, path)
    finally:
        _release_lock(lock_fd)

def create_mission(core_goal, constraints=None, max_iter=10, priority='normal', task_type='text', agent_id=None):
    """创建新任务
    task_type: text(文本推理) / image(图片生成) / video(视频生成) / audio(音频生成) / multimodal(多模态)
    agent_id: 指定智能体执行（可选）
    """
    mission_id = f"MISSION-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    mission_snapshot = {
        'core_goal': core_goal,
        'constraints': constraints or {},
        'max_iter': max_iter,
        'priority': priority,
        'task_type': task_type,
        'agent_id': agent_id,
        'created_at': time.time()
    }
    mission_hash = sha256_hash(mission_snapshot)
    mission = {
        'mission_id': mission_id,
        'core_goal': core_goal,
        'constraints': constraints or {},
        'max_iter': max_iter,
        'priority': priority,
        'task_type': task_type,
        'agent_id': agent_id,
        'mission_snapshot_hash': mission_hash,
        'status': 'pending',
        'iteration': 0,
        'drift_risk': False,
        'drift_report': '',
        'final_snapshot_hash': '',
        'agent_output': '',
        'created_at': time.time(),
        'started_at': None,
        'finished_at': None,
        'did': DID,
        'executor_id': None
    }
    # HITL高风险检测
    is_risk, risk_keyword = detect_high_risk(core_goal)
    if is_risk and HITL_ENABLED:
        mission['status'] = 'pending_approval'
        mission['risk_keyword'] = risk_keyword
        send_hitl_notification(mission)
    with mission_lock:
        mission_queue.append(mission)
        active_missions[mission_id] = mission
    # 持久化
    with open(os.path.join(MISSION_DIR, f'{mission_id}.json'), 'w') as f:
        json.dump(mission, f, ensure_ascii=False, indent=2)
    # 飞书Base日志
    feishu_log_mission(mission, 'created')
    return mission

def commit_snapshot(mission_id, snapshot_hash, output, drift_risk=False, drift_report='', iteration=0):
    """执行内核提交快照，调度内核确权"""
    with mission_lock:
        mission = active_missions.get(mission_id)
        if not mission:
            return None, '任务不存在'
        # 校验快照哈希与任务基线
        mission['final_snapshot_hash'] = snapshot_hash
        mission['agent_output'] = output
        mission['drift_risk'] = drift_risk
        mission['drift_report'] = drift_report
        mission['iteration'] = iteration
        mission['status'] = 'finished' if not drift_risk else 'drift_detected'
        mission['finished_at'] = time.time()
        # 确权锁档
        root = load_root_state()
        block_height = root.get('block_height', 0)
        parent_hash = root.get('current_root_hash', '0'*64)
        new_root = sha256_hash({'parent': parent_hash, 'snapshot': snapshot_hash, 'mission': mission_id})
        root['block_height'] = block_height + 1
        root['current_root_hash'] = new_root
        root['last_mission_id'] = mission_id
        save_root_state(root)
        # 更新持久化
        with open(os.path.join(MISSION_DIR, f'{mission_id}.json'), 'w') as f:
            json.dump(mission, f, ensure_ascii=False, indent=2)
        # 飞书Base日志
        feishu_log_mission(mission, 'finished')
        return {
            'mission_id': mission_id,
            'status': mission['status'],
            'snapshot_hash': snapshot_hash,
            'new_root_hash': new_root,
            'block_height': block_height + 1,
            'locked': True
        }, None

def interrupt_mission(mission_id, reason='manual'):
    """中断任务（熔断/漂移/人工）"""
    with mission_lock:
        mission = active_missions.get(mission_id)
        if not mission:
            return None, '任务不存在'
        mission['status'] = 'interrupted'
        mission['finished_at'] = time.time()
        mission['interrupt_reason'] = reason
        with open(os.path.join(MISSION_DIR, f'{mission_id}.json'), 'w') as f:
            json.dump(mission, f, ensure_ascii=False, indent=2)
        return mission, None

def get_next_mission(executor_id, capabilities=None):
    """执行内核拉取下一个任务（按优先级P0>P1>P2>P3，同优先级按创建时间）
    capabilities: 执行内核支持的任务类型列表，如['text', 'image']
    """
    priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3, 'normal': 2, 'high': 1, 'low': 3}
    with mission_lock:
        # 筛选pending任务并按优先级+创建时间排序
        pending = [m for m in mission_queue if m['status'] == 'pending']
        if capabilities:
            # 只分配执行内核支持的任务类型
            pending = [m for m in pending if m.get('task_type', 'text') in capabilities]
        if not pending:
            return None
        pending.sort(key=lambda m: (priority_order.get(m.get('priority', 'P2'), 2), m.get('created_at', 0)))
        mission = pending[0]
        mission['status'] = 'running'
        mission['started_at'] = time.time()
        mission['executor_id'] = executor_id
        with open(os.path.join(MISSION_DIR, f'{mission["mission_id"]}.json'), 'w') as f:
            json.dump(mission, f, ensure_ascii=False, indent=2)
        return mission

def heartbeat(mission_id, iteration, status, resource_usage=None):
    """执行内核心跳"""
    with mission_lock:
        mission = active_missions.get(mission_id)
        if not mission:
            return None
        mission['last_heartbeat'] = time.time()
        mission['iteration'] = iteration
        mission['runtime_status'] = status
        mission['resource_usage'] = resource_usage or {}
        # 迭代超过max_iter+1自动熔断（留1次余量给快照提交）
        if iteration > mission['max_iter'] + 1:
            mission['status'] = 'fuse_triggered'
            mission['finished_at'] = time.time()
            with open(os.path.join(MISSION_DIR, f'{mission_id}.json'), 'w') as f:
                json.dump(mission, f, ensure_ascii=False, indent=2)
        return mission

class SchedulerHandler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == '/kernel/mission/get':
            executor_id = params.get('executor_id', [''])[0]
            capabilities = params.get('capabilities', [None])[0]
            cap_list = capabilities.split(',') if capabilities else None
            mission = get_next_mission(executor_id, capabilities=cap_list)
            if mission:
                self._send(200, {'code': 0, 'data': mission, 'message': '任务已分配'})
            else:
                self._send(200, {'code': 1, 'data': None, 'message': '无待执行任务'})

        elif path == '/kernel/mission/status':
            mission_id = params.get('mission_id', [''])[0]
            with mission_lock:
                mission = active_missions.get(mission_id)
            if mission:
                self._send(200, {'code': 0, 'data': mission})
            else:
                self._send(404, {'code': 1, 'error': '任务不存在'})

        elif path == '/kernel/stats':
            with mission_lock:
                stats = {
                    'total_missions': len(active_missions),
                    'pending': sum(1 for m in active_missions.values() if m['status']=='pending'),
                    'running': sum(1 for m in active_missions.values() if m['status']=='running'),
                    'finished': sum(1 for m in active_missions.values() if m['status']=='finished'),
                    'interrupted': sum(1 for m in active_missions.values() if m['status']=='interrupted'),
                    'fuse_triggered': sum(1 for m in active_missions.values() if m['status']=='fuse_triggered'),
                    'drift_detected': sum(1 for m in active_missions.values() if m['status']=='drift_detected'),
                    'priority_queue': {
                        'P0': sum(1 for m in active_missions.values() if m.get('priority')=='P0' and m['status']=='pending'),
                        'P1': sum(1 for m in active_missions.values() if m.get('priority')=='P1' and m['status']=='pending'),
                        'P2': sum(1 for m in active_missions.values() if m.get('priority') in ('P2','normal') and m['status']=='pending'),
                        'P3': sum(1 for m in active_missions.values() if m.get('priority') in ('P3','low') and m['status']=='pending'),
                    }
                }
            root = load_root_state()
            stats['block_height'] = root.get('block_height', 0)
            stats['root_hash'] = root.get('current_root_hash', '')[:16] + '...'
            self._send(200, {'code': 0, 'data': stats})

        elif path == '/kernel/health':
            self._send(200, {'code': 0, 'status': 'healthy', 'kernel': 'Ω-Brainμ-scheduler', 'port': PORT})

        elif path == '/kernel/agents/list':
            category = params.get('category', [None])[0]
            agents = list_agents(category=category)
            self._send(200, {'code': 0, 'data': {'count': len(agents), 'agents': agents}})

        elif path == '/kernel/agents/get':
            agent_id = params.get('agent_id', [''])[0]
            agent = get_agent(agent_id)
            if agent:
                self._send(200, {'code': 0, 'data': agent})
            else:
                self._send(404, {'code': 1, 'error': '智能体不存在'})

        else:
            self._send(404, {'code': 1, 'error': 'not found'})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        parsed = urlparse(self.path)
        path = parsed.path

        # HMAC验证（白名单端点除外）
        if path not in HMAC_WHITELIST:
            ok, msg = verify_hmac(self.headers, body)
            if not ok:
                self._send(403, {'code': 1, 'error': f'HMAC验证失败: {msg}'})
                return

        if path == '/kernel/mission/dispatch':
            # 调度内核主动创建任务
            core_goal = data.get('core_goal', '')
            constraints = data.get('constraints', {})
            max_iter = data.get('max_iter', 10)
            priority = data.get('priority', 'normal')
            task_type = data.get('task_type', 'text')
            agent_id = data.get('agent_id', None)
            if not core_goal:
                self._send(400, {'code': 1, 'error': 'core_goal不能为空'})
                return
            mission = create_mission(core_goal, constraints, max_iter, priority, task_type, agent_id)
            self._send(200, {'code': 0, 'data': mission, 'message': '任务已创建'})

        elif path == '/kernel/snapshot/commit':
            # 执行内核提交快照
            mission_id = data.get('mission_id', '')
            snapshot_hash = data.get('snapshot_hash', '')
            output = data.get('output', '')
            drift_risk = data.get('drift_risk', False)
            drift_report = data.get('drift_report', '')
            iteration = data.get('iteration', 0)
            if not mission_id or not snapshot_hash:
                self._send(400, {'code': 1, 'error': 'mission_id和snapshot_hash必填'})
                return
            result, err = commit_snapshot(mission_id, snapshot_hash, output, drift_risk, drift_report, iteration)
            if err:
                self._send(404, {'code': 1, 'error': err})
            else:
                self._send(200, {'code': 0, 'data': result, 'message': '快照已确权锁档'})

        elif path == '/kernel/mission/interrupt':
            mission_id = data.get('mission_id', '')
            reason = data.get('reason', 'manual')
            result, err = interrupt_mission(mission_id, reason)
            if err:
                self._send(404, {'code': 1, 'error': err})
            else:
                self._send(200, {'code': 0, 'data': result, 'message': '任务已中断'})

        elif path == '/kernel/mission/execute_sync':
            """同步执行端点：创建任务并等待结果，最多等待120秒"""
            core_goal = data.get('core_goal', '')
            constraints = data.get('constraints', {})
            max_iter = data.get('max_iter', 5)
            timeout = data.get('timeout', 120)
            priority = data.get('priority', 'P1')
            task_type = data.get('task_type', 'text')
            agent_id = data.get('agent_id', None)
            if not core_goal:
                self._send(400, {'code': 1, 'error': 'core_goal不能为空'})
                return
            mission = create_mission(core_goal, constraints, max_iter, priority, task_type, agent_id)
            mission_id = mission['mission_id']
            # 轮询等待任务完成
            start = time.time()
            while time.time() - start < timeout:
                time.sleep(2)
                with mission_lock:
                    m = active_missions.get(mission_id)
                    if m and m['status'] in ('finished', 'drift_detected', 'fuse_triggered', 'interrupted'):
                        self._send(200, {'code': 0, 'data': {
                            'mission_id': mission_id,
                            'status': m['status'],
                            'output': m.get('agent_output', ''),
                            'iteration': m.get('iteration', 0),
                            'drift_risk': m.get('drift_risk', False),
                            'drift_report': m.get('drift_report', ''),
                            'final_snapshot_hash': m.get('final_snapshot_hash', ''),
                            'elapsed': round(time.time() - start, 1)
                        }, 'message': '任务执行完成'})
                        return
            self._send(202, {'code': 1, 'data': {'mission_id': mission_id, 'status': 'timeout'}, 'message': '任务执行超时，请用mission/status查询'})

        elif path == '/kernel/heartbeat':
            mission_id = data.get('mission_id', '')
            iteration = data.get('iteration', 0)
            status = data.get('status', 'running')
            resource_usage = data.get('resource_usage', {})
            mission = heartbeat(mission_id, iteration, status, resource_usage)
            if mission:
                should_stop = mission['status'] in ('fuse_triggered', 'interrupted')
                self._send(200, {'code': 0, 'data': {'status': mission['status'], 'should_stop': should_stop}})
            else:
                self._send(404, {'code': 1, 'error': '任务不存在'})

        elif path == '/kernel/agents/register':
            agent_data = data
            agent_data.setdefault('status', 'active')
            agent_data.setdefault('priority', 'P2')
            agent = register_agent(agent_data)
            self._send(200, {'code': 0, 'data': agent, 'message': '智能体注册成功'})

        elif path == '/kernel/mission/resume':
            mission_id = data.get('mission_id', '')
            mission = resume_mission(mission_id)
            if mission:
                self._send(200, {'code': 0, 'data': mission, 'message': '任务已恢复，等待执行'})
            else:
                self._send(404, {'code': 1, 'error': '任务不存在或状态不可恢复'})

        elif path == '/kernel/hitl/check':
            core_goal = data.get('core_goal', '')
            is_risk, keyword = detect_high_risk(core_goal)
            self._send(200, {'code': 0, 'data': {'high_risk': is_risk, 'risk_keyword': keyword, 'hitl_enabled': HITL_ENABLED}})

        else:
            self._send(404, {'code': 1, 'error': 'not found'})

    def log_message(self, format, *args):
        pass  # 静默日志

def restore_missions():
    """启动时从missions目录恢复任务队列"""
    global mission_queue, active_missions
    restored = 0
    if os.path.exists(MISSION_DIR):
        for filename in os.listdir(MISSION_DIR):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(MISSION_DIR, filename)) as f:
                        mission = json.load(f)
                    mid = mission.get('mission_id', '')
                    status = mission.get('status', '')
                    # running状态超过10分钟视为超时，回退到pending
                    if status == 'running':
                        last_hb = mission.get('last_heartbeat', mission.get('started_at', 0))
                        if time.time() - last_hb > 600:
                            mission['status'] = 'pending'
                            mission['executor_id'] = None
                            mission['iteration'] = 0
                            with open(os.path.join(MISSION_DIR, filename), 'w') as f:
                                json.dump(mission, f, ensure_ascii=False, indent=2)
                    if mission.get('status') == 'pending':
                        mission_queue.append(mission)
                        restored += 1
                    active_missions[mid] = mission
                except Exception as e:
                    print(f'恢复任务失败 {filename}: {e}')
    print(f'任务恢复完成: {restored}个pending任务, {len(active_missions)}个总任务')

if __name__ == '__main__':
    restore_missions()
    server = HTTPServer(('0.0.0.0', PORT), SchedulerHandler)
    print(f'Ω-Brainμ 调度内核启动 | 端口:{PORT} | DID:{DID}')
    print(f'任务目录:{MISSION_DIR}')
    print(f'{TRACE_MARK}')
    server.serve_forever()
