#!/usr/bin/env python3
"""
Agent 执行内核
双内核架构 - 从执行内核
职责：从调度内核拉取任务、状态机执行、LLM推理、工具调用、快照提交
端口：8030
不依赖LangGraph，用Python原生状态机实现（后续可升级LangGraph）
"""
import json
import hashlib
import hmac
import time
import os
import uuid
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Redis Checkpoint支持
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        print('[执行内核] Redis Checkpoint已连接')
    except Exception as e:
        print(f'[执行内核] Redis连接失败: {e}，使用内存状态')
        redis_client = None
        REDIS_AVAILABLE = False

# 配置
SCHEDULER_URL = 'http://127.0.0.1:8032'
AI_PROXY_URL = 'http://127.0.0.1:8021'
EXECUTOR_ID = f"AGENT-EXEC-{uuid.uuid4().hex[:8]}"
SCHEDULER_SECRET = 'zongyuan-root-scheduler-secret-v1'
DID = 'DID-BR-000002'
TRACE_MARK = 'Ω₀⊂⊙∞⊂Ω'
PORT = 8033
POLL_INTERVAL = 5  # 任务轮询间隔（秒）
MAX_EXECUTION_TIME = 300  # 单任务最大执行时间（秒），超时自动熔断

# 持久化
STATE_DIR = '/opt/ZONGYUAN-ROOT/kernel/executor_state_2'
STATE_FILE = os.path.join(STATE_DIR, 'executor_state_2.json')
os.makedirs(STATE_DIR, exist_ok=True)

# 执行状态
current_mission = None
is_running = False
executor_lock = threading.Lock()

def save_executor_state_2():
    """持久化执行内核状态（文件+Redis双写）"""
    state = {
        'executor_id': EXECUTOR_ID,
        'current_mission': current_mission,
        'updated_at': time.time()
    }
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp, STATE_FILE)
    # Redis双写
    if redis_client:
        try:
            redis_client.setex(f'executor:{EXECUTOR_ID}:state', 3600, json.dumps(state, ensure_ascii=False))
        except:
            pass

def save_checkpoint(mission_id, iteration, node, output, drift_risk=False):
    """保存任务执行检查点到Redis（断点续跑）"""
    if not redis_client:
        return
    try:
        checkpoint = {
            'mission_id': mission_id,
            'iteration': iteration,
            'node': node,
            'output': output,
            'drift_risk': drift_risk,
            'executor_id': EXECUTOR_ID,
            'timestamp': time.time()
        }
        redis_client.setex(f'checkpoint:{mission_id}', 86400, json.dumps(checkpoint, ensure_ascii=False))
    except:
        pass

def load_checkpoint(mission_id):
    """从Redis加载任务检查点"""
    if not redis_client:
        return None
    try:
        data = redis_client.get(f'checkpoint:{mission_id}')
        if data:
            return json.loads(data)
    except:
        pass
    return None

def load_executor_state_2():
    """启动时恢复状态，标记未完成任务为失败"""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        mission = state.get('current_mission')
        if mission and mission.get('status') == 'running':
            # 上次执行中断，通知调度内核标记为interrupted
            mission_id = mission['mission_id']
            try:
                requests.post(
                    f'{SCHEDULER_URL}/kernel/mission/interrupt',
                    json={'mission_id': mission_id, 'reason': 'executor_restart_recovery'},
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                print(f'[执行内核] 恢复：任务{mission_id}已标记为interrupted')
            except:
                pass
        return state
    except Exception as e:
        print(f'[执行内核] 状态恢复失败: {e}')
        return None

def sha256_hash(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest().upper()

def sign_request(body):
    timestamp = str(int(time.time()))
    signature = hmac.new(
        SCHEDULER_SECRET.encode(),
        f"{timestamp}:{body}".encode(),
        hashlib.sha256
    ).hexdigest()
    return {'X-Signature': signature, 'X-Timestamp': timestamp}

def call_llm(message, model='zhipu', prompt_type='general'):
    """调用AI Proxy进行LLM推理"""
    try:
        resp = requests.post(
            f'{AI_PROXY_URL}/chat',
            json={'message': message, 'model': model, 'prompt_type': prompt_type},
            headers={'Content-Type': 'application/json'},
            timeout=120
        )
        data = resp.json()
        return data.get('result', ''), None
    except Exception as e:
        return '', str(e)

def drift_check(output, core_goal):
    """增强版语义漂移校验：多维检查输出质量与相关性"""
    if not output or not output.strip():
        return True, '输出为空，判定为漂移'

    output_lower = output.lower()
    scores = {}
    warnings = []

    # 1. 长度合理性检查
    output_len = len(output)
    if output_len < 20:
        return True, f'输出过短({output_len}字符)，可能未完成任务'
    if output_len > 50000:
        warnings.append(f'输出过长({output_len}字符)，可能包含冗余内容')
    scores['length'] = min(1.0, output_len / 500)

    # 2. 拒绝/错误模式检测
    reject_patterns = ['无法回答', '抱歉', '不能帮助', '无法提供', '不支持', '没有相关', '我不知道']
    for pattern in reject_patterns:
        if pattern in output:
            warnings.append(f'检测到拒绝模式: {pattern}')
            scores['reject'] = 0.3
            break
    else:
        scores['reject'] = 1.0

    # 3. 关键词覆盖率（中文分词简化版：按2-4字滑动窗口）
    goal_clean = core_goal.replace('的', '').replace('了', '').replace('和', '').replace('与', '')
    goal_terms = set()
    for n in [2, 3, 4]:
        for i in range(len(goal_clean) - n + 1):
            term = goal_clean[i:i+n]
            if len(term.strip()) >= 2:
                goal_terms.add(term)

    if goal_terms:
        matched = sum(1 for term in goal_terms if term in output)
        coverage = matched / len(goal_terms)
        scores['keyword_coverage'] = coverage
        if coverage < 0.1:
            warnings.append(f'关键词覆盖率低({coverage:.1%})，输出可能偏离目标')

    # 4. 任务相关性评分（基于核心名词出现）
    core_nouns = [w for w in core_goal.split() if len(w) >= 2 and w not in ['的', '了', '和', '与', '是', '在']]
    if core_nouns:
        noun_hits = sum(1 for n in core_nouns if n in output)
        scores['relevance'] = noun_hits / len(core_nouns)
    else:
        scores['relevance'] = 0.5

    # 5. 输出结构完整性（是否包含分析/结论/建议等结构词）
    structure_indicators = ['分析', '总结', '结论', '建议', '首先', '其次', '最后', '1.', '2.', '一、', '二、']
    structure_hits = sum(1 for s in structure_indicators if s in output)
    scores['structure'] = min(1.0, structure_hits / 3)

    # 综合评分
    weights = {'length': 0.15, 'reject': 0.25, 'keyword_coverage': 0.3, 'relevance': 0.2, 'structure': 0.1}
    total_score = sum(scores.get(k, 0.5) * w for k, w in weights.items())

    drift_report = f'漂移评分:{total_score:.2f} | ' + ' | '.join(f'{k}:{v:.2f}' for k, v in scores.items())
    if warnings:
        drift_report += ' | 警告: ' + '; '.join(warnings)

    # 判定：综合评分<0.3判定为漂移
    is_drift = total_score < 0.3
    return is_drift, drift_report

def execute_mission(mission):
    """执行任务的状态机"""
    global current_mission
    mission_id = mission['mission_id']
    core_goal = mission['core_goal']
    max_iter = mission['max_iter']
    constraints = mission.get('constraints', {})
    start_time = time.time()

    # 持久化任务状态
    with executor_lock:
        current_mission = mission
        save_executor_state_2()

    print(f'[执行内核] 开始执行任务 {mission_id}: {core_goal[:50]}...')

    # 状态机节点
    iteration = 0
    full_output = ''
    drift_risk = False
    drift_report = ''

    # 节点1: 任务理解
    iteration += 1
    heartbeat(mission_id, iteration, 'understanding')
    understand_prompt = f"""任务目标：{core_goal}
约束条件：{json.dumps(constraints, ensure_ascii=False)}
请分析这个任务，给出执行计划（分步骤）。"""
    plan, err = call_llm(understand_prompt)
    if err:
        print(f'[执行内核] 任务理解失败: {err}')
    full_output += f'【执行计划】\n{plan}\n\n'
    save_checkpoint(mission_id, iteration, 'understanding', full_output)

    # 节点2: 核心推理执行
    iteration += 1
    heartbeat(mission_id, iteration, 'reasoning')
    execute_prompt = f"""任务目标：{core_goal}
执行计划：{plan}
请按照计划执行任务，输出完整结果。"""
    result, err = call_llm(execute_prompt)
    if err:
        print(f'[执行内核] 核心执行失败: {err}')
        result = f'执行过程中出现错误: {err}'
    full_output += f'【执行结果】\n{result}\n\n'
    save_checkpoint(mission_id, iteration, 'reasoning', full_output)

    # 节点3: 漂移校验
    iteration += 1
    heartbeat(mission_id, iteration, 'drift_check')
    drift_risk, drift_report = drift_check(result, core_goal)
    if drift_risk:
        full_output += f'【漂移告警】{drift_report}\n\n'
    save_checkpoint(mission_id, iteration, 'drift_check', full_output, drift_risk)

    # 节点4: 结果优化（如果未漂移且迭代未超限）
    if not drift_risk and iteration < max_iter:
        iteration += 1
        heartbeat(mission_id, iteration, 'optimizing')
        optimize_prompt = f"""原始结果：{result}
请对结果进行优化完善，使其更专业、更完整。"""
        optimized, err = call_llm(optimize_prompt)
        if not err:
            full_output += f'【优化结果】\n{optimized}\n\n'
            result = optimized
        save_checkpoint(mission_id, iteration, 'optimizing', full_output, drift_risk)

    # 节点5: 快照提交
    iteration += 1
    snapshot = {
        'mission_id': mission_id,
        'core_goal': core_goal,
        'output': full_output,
        'iteration': iteration,
        'drift_risk': drift_risk,
        'executor_id': EXECUTOR_ID,
        'finished_at': time.time()
    }
    snapshot_hash = sha256_hash(snapshot)

    # 提交到调度内核确权（带HMAC签名）
    try:
        commit_body = json.dumps({
            'mission_id': mission_id,
            'snapshot_hash': snapshot_hash,
            'output': full_output,
            'drift_risk': drift_risk,
            'drift_report': drift_report,
            'iteration': iteration
        }, ensure_ascii=False)
        resp = requests.post(
            f'{SCHEDULER_URL}/kernel/snapshot/commit',
            data=commit_body.encode('utf-8'),
            headers={**{'Content-Type': 'application/json; charset=utf-8'}, **sign_request(commit_body)},
            timeout=10
        )
        commit_result = resp.json()
        print(f'[执行内核] 快照提交成功: 区块#{commit_result.get("data",{}).get("block_height","?")}')
    except Exception as e:
        print(f'[执行内核] 快照提交失败: {e}')

    elapsed = time.time() - start_time
    with executor_lock:
        current_mission = None
        save_executor_state_2()

    print(f'[执行内核] 任务完成 {mission_id} | 迭代:{iteration} | 漂移:{drift_risk} | 耗时:{elapsed:.1f}s')
    return full_output

def heartbeat(mission_id, iteration, status):
    """向调度内核发送心跳（带HMAC签名）"""
    try:
        hb_body = json.dumps({
            'mission_id': mission_id,
            'iteration': iteration,
            'status': status,
            'resource_usage': {'executor': EXECUTOR_ID}
        }, ensure_ascii=False)
        requests.post(
            f'{SCHEDULER_URL}/kernel/heartbeat',
            data=hb_body.encode('utf-8'),
            headers={**{'Content-Type': 'application/json; charset=utf-8'}, **sign_request(hb_body)},
            timeout=5
        )
    except:
        pass

def mission_poller():
    """后台线程：轮询调度内核获取任务"""
    global current_mission, is_running
    print(f'[执行内核] 任务轮询线程启动 | ExecutorID:{EXECUTOR_ID}')
    while is_running:
        try:
            with executor_lock:
                has_current = current_mission is not None
            if not has_current:
                resp = requests.get(
                    f'{SCHEDULER_URL}/kernel/mission/get',
                    params={'executor_id': EXECUTOR_ID},
                    timeout=5
                )
                data = resp.json()
                if data.get('code') == 0 and data.get('data'):
                    mission = data['data']
                    with executor_lock:
                        current_mission = mission
                        save_executor_state_2()
                    # 在新线程中执行任务，异常时确保状态清理并通知调度内核
                    def safe_execute(m):
                        try:
                            execute_mission(m)
                        except Exception as e:
                            import traceback
                            err_msg = traceback.format_exc()
                            print(f'[执行内核] 任务执行异常: {e}\n{err_msg}')
                            # 写入错误日志文件
                            try:
                                log_line = time.ctime() + ' | ' + m['mission_id'] + ' | ' + str(e) + '\n' + err_msg + '\n---\n'
                                with open(os.path.join(STATE_DIR, 'error.log'), 'a') as f:
                                    f.write(log_line)
                            except:
                                pass
                            # 通知调度内核标记任务为error
                            try:
                                err_body = json.dumps({'mission_id': m['mission_id'], 'reason': f'executor_error: {str(e)}[:200]'}, ensure_ascii=False)
                                requests.post(f'{SCHEDULER_URL}/kernel/mission/interrupt',
                                    data=err_body.encode('utf-8'),
                                    headers={**{'Content-Type': 'application/json; charset=utf-8'}, **sign_request(err_body)},
                                    timeout=5)
                            except:
                                pass
                            with executor_lock:
                                current_mission = None
                                save_executor_state_2()
                    t = threading.Thread(target=safe_execute, args=(mission,), daemon=True)
                    t.start()
        except Exception as e:
            pass  # 调度内核不可用时静默重试
        time.sleep(POLL_INTERVAL)

class ExecutorHandler(BaseHTTPRequestHandler):
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

        if path == '/agent/status':
            with executor_lock:
                mission = current_mission
            self._send(200, {
                'code': 0,
                'data': {
                    'executor_id': EXECUTOR_ID,
                    'status': 'busy' if mission else 'idle',
                    'current_mission': mission['mission_id'] if mission else None,
                    'scheduler_url': SCHEDULER_URL
                }
            })

        elif path == '/agent/health':
            self._send(200, {'code': 0, 'status': 'healthy', 'executor': EXECUTOR_ID, 'port': PORT})

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

        if path == '/agent/mission/execute':
            # 直接提交任务执行（绕过调度内核，用于测试）
            core_goal = data.get('core_goal', '')
            if not core_goal:
                self._send(400, {'code': 1, 'error': 'core_goal不能为空'})
                return
            # 创建一个临时任务直接执行
            mission = {
                'mission_id': f"DIRECT-{int(time.time())}",
                'core_goal': core_goal,
                'constraints': data.get('constraints', {}),
                'max_iter': data.get('max_iter', 5)
            }
            with executor_lock:
                if current_mission:
                    self._send(429, {'code': 1, 'error': '执行内核正忙，请稍后重试'})
                    return
                current_mission = mission
            t = threading.Thread(target=execute_mission, args=(mission,), daemon=True)
            t.start()
            self._send(200, {'code': 0, 'data': {'mission_id': mission['mission_id'], 'status': 'started'}})

        else:
            self._send(404, {'code': 1, 'error': 'not found'})

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    is_running = True
    # 启动时恢复状态（标记上次未完成任务为interrupted）
    load_executor_state_2()
    poller = threading.Thread(target=mission_poller, daemon=True)
    poller.start()
    server = HTTPServer(('0.0.0.0', PORT), ExecutorHandler)
    print(f'Agent 执行内核启动 | 端口:{PORT} | ExecutorID:{EXECUTOR_ID}')
    print(f'调度内核:{SCHEDULER_URL} | AI Proxy:{AI_PROXY_URL}')
    print(f'{TRACE_MARK}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        is_running = False
        print('\n执行内核停止')
