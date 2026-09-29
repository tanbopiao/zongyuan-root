#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 政务中台统一API服务
提供：政务AI问答、公文生成、政策搜索、办事指南
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import rbac_system, notification_system, data_analytics_api, esign_system, multi_tenant, ai_model_router, security_middleware, urllib.request, urllib.parse, os, time, re, hashlib
import operator_stats
import evolution_engine
import workbench_api
import workbench_api_v2
import user_data_api
import evolution_engine_v2
from datetime import datetime

# ============ 响应缓存系统 ============
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
CACHE_TTL = 3600
CACHE_MAX_SIZE = 1000

def get_cache_key(prefix, content):
    return hashlib.md5(f"{prefix}:{content}".encode()).hexdigest()

def get_cache(cache_key):
    try:
        cache_file = os.path.join(CACHE_DIR, cache_key + '.json')
        if not os.path.exists(cache_file):
            return None
        with open(cache_file) as f:
            data = json.load(f)
        if time.time() - data['timestamp'] > CACHE_TTL:
            os.remove(cache_file)
            return None
        return data['value']
    except:
        return None

def set_cache(cache_key, value):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        files = os.listdir(CACHE_DIR)
        if len(files) > CACHE_MAX_SIZE:
            for f in files[:len(files)-CACHE_MAX_SIZE]:
                try:
                    os.remove(os.path.join(CACHE_DIR, f))
                except:
                    pass
        cache_file = os.path.join(CACHE_DIR, cache_key + '.json')
        with open(cache_file, 'w') as f:
            json.dump({'timestamp': time.time(), 'value': value}, f, ensure_ascii=False)
    except:
        pass

# ============ 多租户API Key鉴权 ============
TENANTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tenants')
USAGE_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'api_usage.jsonl')

def load_tenants():
    """加载所有租户"""
    tenants = {}
    if not os.path.exists(TENANTS_DIR):
        return tenants
    for f in os.listdir(TENANTS_DIR):
        if f.endswith('.json'):
            try:
                with open(os.path.join(TENANTS_DIR, f)) as fp:
                    t = json.load(fp)
                    tenants[t['api_key']] = t
            except:
                pass
    return tenants

def verify_api_key(api_key):
    """验证API Key，返回租户信息或None"""
    if not api_key:
        return None
    tenants = load_tenants()
    return tenants.get(api_key)

def record_usage(api_key, endpoint, status, elapsed):
    """记录API调用用量"""
    try:
        os.makedirs(os.path.dirname(USAGE_LOG), exist_ok=True)
        record = {
            'timestamp': datetime.now().isoformat(),
            'api_key': api_key or 'anonymous',
            'endpoint': endpoint,
            'status': status,
            'elapsed_ms': round(elapsed * 1000, 2)
        }
        with open(USAGE_LOG, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except:
        pass

def get_usage_stats():
    """获取用量统计"""
    stats = {'total_calls': 0, 'by_endpoint': {}, 'by_status': {}, 'avg_response_time': 0, 'recent_calls': []}
    if not os.path.exists(USAGE_LOG):
        return stats
    total_time = 0
    count = 0
    recent = []
    with open(USAGE_LOG) as f:
        for line in f:
            try:
                r = json.loads(line)
                stats['total_calls'] += 1
                stats['by_endpoint'][r['endpoint']] = stats['by_endpoint'].get(r['endpoint'], 0) + 1
                stats['by_status'][str(r['status'])] = stats['by_status'].get(str(r['status']), 0) + 1
                total_time += r.get('elapsed_ms', 0)
                count += 1
                recent.append(r)
            except:
                pass
    if count > 0:
        stats['avg_response_time'] = round(total_time / count, 2)
    stats['recent_calls'] = recent[-20:]
    return stats

def get_hot_questions():
    """获取热门问题统计（从chat日志）"""
    hot_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'chat_hot.jsonl')
    questions = {}
    if os.path.exists(hot_log):
        with open(hot_log) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    q = r.get('question', '')[:50]
                    if q:
                        questions[q] = questions.get(q, 0) + 1
                except:
                    pass
    # 按热度排序，返回Top10
    hot = sorted(questions.items(), key=lambda x: -x[1])[:10]
    return [{'question': q, 'count': c} for q, c in hot]

def safe_decode_query(raw_query):
    """编码容错：处理未URL编码的UTF-8中文query"""
    try:
        params = urllib.parse.parse_qs(raw_query)
        # 检测是否有乱码（UTF-8字节被误解析为Latin-1）
        for k, v in params.items():
            for i, val in enumerate(v):
                try:
                    # 尝试将Latin-1误解析的字符串还原为UTF-8
                    fixed = val.encode('latin-1').decode('utf-8')
                    if fixed != val:
                        params[k][i] = fixed
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
        return params
    except Exception:
        return urllib.parse.parse_qs(raw_query)
from http.server import HTTPServer, BaseHTTPRequestHandler

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
AIPROXY_URL = 'http://127.0.0.1:8021/chat'
ADMIN_KEY = 'zongyuan-gov-admin-2026'  # 管理API密钥

# 操作日志
LOG_FILE = os.path.join(DATA_DIR, 'admin_audit_log.jsonl')

def log_admin_action(action, target, detail=""):
    """记录管理操作日志"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "target": target,
        "detail": detail[:200],
        "ip": "127.0.0.1"
    }
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except:
        pass

def check_admin_auth(headers):
    """简单API Key认证"""
    key = headers.get('X-Admin-Key', '')
    return key == ADMIN_KEY

def save_policies():
    """保存政策库到文件"""
    with open(os.path.join(DATA_DIR, 'policies.json'), 'w', encoding='utf-8') as f:
        json.dump(POLICIES, f, ensure_ascii=False, indent=2)

def save_guides():
    """保存办事指南到文件"""
    with open(os.path.join(DATA_DIR, 'guides.json'), 'w', encoding='utf-8') as f:
        json.dump(GUIDES, f, ensure_ascii=False, indent=2)


# 加载政策库
with open(os.path.join(DATA_DIR, 'policies.json')) as f:
    POLICIES = json.load(f)
# 加载办事指南
with open(os.path.join(DATA_DIR, 'guides.json')) as f:
    GUIDES = json.load(f)

GOV_SYSTEM_PROMPT = '''你是政务AI助手，由火斗云智AIOS驱动，专门为群众提供专业、准确的政务咨询服务。

【角色定位】
- 你是政务服务智能顾问，精通社保、医保、户籍、教育、就业、住房、婚姻、生育、税务、交通等领域
- 你的回答必须基于提供的政策和办事指南上下文，不得编造政策文号、机构名称或办理流程

【回答规范】
1. 准确性优先：引用政策依据时注明文号和发布机构，不确定的信息明确告知"建议咨询当地主管部门"
2. 结构化回答：涉及办事指南时，按"办理条件→所需材料→办理流程→办理地点→咨询电话→办理时限"组织
3. 通俗易懂：将专业术语转化为群众易懂的语言，必要时举例说明
4. 简洁高效：先给核心结论，再展开细节，避免冗长铺垫
5. 分类引导：根据问题类型自动归类（政策咨询/办事指南/公文写作/通用咨询），提供针对性回答

【上下文使用】
- 系统会提供相关政策和办事指南作为参考上下文
- 回答时优先引用上下文中的信息
- 若上下文不足，基于通用知识回答并标注"仅供参考，以当地最新政策为准"

【禁止事项】
- 禁止编造不存在的政策、文号、机构
- 禁止给出绝对化的法律意见
- 禁止超越政务咨询范围回答医疗诊断、投资理财等专业问题'''

# ============ 多语言支持 ============
GOV_SYSTEM_PROMPT_ZH = GOV_SYSTEM_PROMPT
GOV_SYSTEM_PROMPT_EN = """You are a government services AI assistant, powered by Huodou Cloud AIOS.
Please answer government service inquiries in English. Be accurate, concise, and structured.
If asked about procedures, use: eligibility, required documents, process, location, contact, timeframe.
If unsure, state clearly and advise consulting local authorities."""
GOV_SYSTEM_PROMPT_YUE = """你係政務AI助手，由火斗雲智AIOS驅動。
請用粵語回答用戶嘅政務咨詢問題。回答要準確、簡潔、有結構。
如果用戶咨詢辦事流程，請按：辦理條件、所需材料、辦理流程、辦理地點、咨詢電話、辦理時限嘅結構回答。
如果唔確定，請清楚講明，並建議咨詢當地主管部門。"""


def enhanced_search(user_msg, top_k=5):
    """增强检索：多字段匹配政策+办事指南，按相关度排序"""
    user_msg_lower = user_msg.lower()
    # 提取关键词（简单分词：2字以上的词）
    keywords = set()
    for word in re.findall(r'[\u4e00-\u9fa5]{2,}', user_msg):
        keywords.add(word)
    # 常见政务关键词映射
    keyword_map = {
        '养老': ['养老保险', '养老金', '退休'], '医疗': ['医保', '医疗保险', '报销'],
        '失业': ['失业保险', '失业金'], '工伤': ['工伤保险', '工伤认定'],
        '生育': ['生育保险', '产假'], '公积金': ['住房公积金', '公积金'],
        '买房': ['购房', '住房', '贷款'], '租房': ['租赁', '公租房'],
        '结婚': ['婚姻登记', '结婚证'], '离婚': ['离婚登记', '离婚冷静期'],
        '户口': ['户籍', '户口迁移', '落户'], '身份证': ['居民身份证', '身份证'],
        '护照': ['出入境', '护照'], '驾照': ['驾驶证', '驾照'],
        '上学': ['入学', '义务教育', '学区'], '高考': ['高考', '招生'],
        '创业': ['创业', '营业执照', '注册'], '税': ['税务', '纳税', '个税'],
        '社保': ['社会保险', '社保'], '就业': ['求职', '招聘', '就业'],
    }
    for kw, mappings in keyword_map.items():
        if kw in user_msg:
            keywords.update(mappings)

    results = []
    # 检索政策
    for p in POLICIES:
        score = 0
        text = (p.get('title', '') + p.get('summary', '') + ' '.join(p.get('keywords', []))).lower()
        for kw in keywords:
            if kw.lower() in text:
                score += 2 if kw in p.get('title', '') else 1
        if p.get('category', '') in user_msg:
            score += 3
        if score > 0:
            results.append({'type': 'policy', 'score': score, 'title': p['title'],
                          'category': p.get('category', ''), 'summary': p.get('summary', '')[:100],
                          'doc_no': p.get('doc_no', ''), 'org': p.get('org', '')})
    # 检索办事指南
    for g in GUIDES:
        score = 0
        text = (g.get('title', '') + str(g.get('conditions', '')) + str(g.get('steps', ''))).lower()
        for kw in keywords:
            if kw.lower() in text:
                score += 2 if kw in g.get('title', '') else 1
        if g.get('category', '') in user_msg:
            score += 3
        if score > 0:
            results.append({'type': 'guide', 'score': score, 'title': g['title'],
                          'category': g.get('category', ''),
                          'conditions': g.get('conditions', '')[:80],
                          'materials': str(g.get('materials', ''))[:80],
                          'location': g.get('location', ''), 'phone': g.get('phone', '')})
    # 按分数排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]

def classify_question(user_msg):
    """问题分类：政策咨询/办事指南/公文写作/通用咨询"""
    doc_keywords = ['公文', '通知', '报告', '请示', '函', '纪要', '写一份', '起草', '润色']
    guide_keywords = ['怎么办', '怎么办理', '流程', '材料', '条件', '在哪办', '去哪里办', '需要什么']
    policy_keywords = ['政策', '规定', '标准', '比例', '基数', '待遇', '报销多少', '领多少']
    for kw in doc_keywords:
        if kw in user_msg:
            return 'document'
    for kw in guide_keywords:
        if kw in user_msg:
            return 'guide'
    for kw in policy_keywords:
        if kw in user_msg:
            return 'policy'
    return 'general'


def call_aiproxy(messages, max_tokens=512):
    """调用aiproxy（主备双路：云端→本地Ollama）"""
    try:
        body = json.dumps({'messages': messages, 'model': 'zhipu', 'max_tokens': max_tokens}).encode()
        req = urllib.request.Request(AIPROXY_URL, data=body, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data.get('result', data.get('choices', [{}])[0].get('message', {}).get('content', ''))
    except Exception as e:
        return f'[服务暂时不可用] {str(e)}'

class GovHandler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # 政策配图索引
        if self.path == '/api/policy-images':
            try:
                index_file = os.path.join(DATA_DIR, 'policy_images', 'index.json')
                if os.path.exists(index_file):
                    with open(index_file) as f:
                        images = json.load(f)
                else:
                    images = []
                self._send(200, {"ok": True, "total": len(images), "images": images})
            except Exception as e:
                self._send(500, {"error": str(e)})
            return

        # 安全中间件：速率限制检查
        allowed, retry_after = security_middleware.check_rate_limit(self, 'api')
        if not allowed:
            self._send(429, {'error': 'rate_limit_exceeded', 'retry_after': retry_after})
            return
        
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = safe_decode_query(parsed.query)

        if path == '/health':
            usage = get_usage_stats()
            self._send(200, {'status': 'healthy', 'service': 'gov-api', 'policies': len(POLICIES), 'guides': len(GUIDES), 'usage': usage})
            record_usage(api_key, path, 200, time.time() - _start_time)
            return
        
        elif path == '/api/gov/policy/search':
            q = params.get('q', [''])[0].strip()
            category = params.get('category', [''])[0].strip()
            results = []
            for p in POLICIES:
                if category and p.get('category') != category:
                    continue
                if q:
                    ql = q.lower()
                    if (ql in p['title'].lower() or ql in p.get('summary','').lower() or 
                        any(ql in k.lower() for k in p.get('keywords', []))):
                        results.append(p)
                else:
                    results.append(p)
            # 进化引擎：记录无结果搜索
            if q and len(results) == 0:
                evolution_engine.record_no_result_search(q, 'policy')
            self._send(200, {'results': results[:20], 'total': len(results), 'query': q})
        
        elif path == '/api/gov/policy/categories':
            cats = sorted(set(p['category'] for p in POLICIES))
            self._send(200, {'categories': cats})
        
        elif path == '/api/gov/guide/list':
            category = params.get('category', [''])[0].strip()
            results = [g for g in GUIDES if not category or g.get('category') == category]
            self._send(200, {'results': results, 'total': len(results)})
        
        elif path == '/api/gov/guide/detail':
            gid = params.get('id', [''])[0]
            guide = next((g for g in GUIDES if g['id'] == gid), None)
            if guide:
                self._send(200, guide)
            else:
                self._send(404, {'error': 'guide not found'})

        # === 管理端点 ===
        elif path == '/api/usage':
            usage = get_usage_stats()
            self._send(200, usage)
            record_usage(api_key, path, 200, time.time() - _start_time)
            return
        elif path == '/api/hot':
            hot = get_hot_questions()
            self._send(200, {'hot_questions': hot})
            record_usage(api_key, path, 200, time.time() - _start_time)
            return
        elif path == '/api/admin/stats':
            if not check_admin_auth(self.headers):
                self._send(401, {'error': 'unauthorized'})
                return
            # 读取操作日志数量
            log_count = 0
            try:
                with open(LOG_FILE) as f:
                    log_count = sum(1 for _ in f)
            except:
                pass
            # 政策分类统计
            policy_cats = {}
            for p in POLICIES:
                policy_cats[p.get('category', '其他')] = policy_cats.get(p.get('category', '其他'), 0) + 1
            # 指南分类统计
            guide_cats = {}
            for g in GUIDES:
                guide_cats[g.get('category', '其他')] = guide_cats.get(g.get('category', '其他'), 0) + 1
            self._send(200, {
                'policies_total': len(POLICIES),
                'guides_total': len(GUIDES),
                'policy_categories': policy_cats,
                'guide_categories': guide_cats,
                'audit_log_count': log_count,
                'api_version': 'V2.5',
                'last_updated': datetime.now().isoformat()
            })

        elif path == '/api/admin/logs':
            if not check_admin_auth(self.headers):
                self._send(401, {'error': 'unauthorized'})
                return
            limit = int(params.get('limit', ['50'])[0])
            logs = []
            try:
                with open(LOG_FILE) as f:
                    lines = f.readlines()
                    logs = [json.loads(line) for line in lines[-limit:]]
            except:
                pass
            self._send(200, {'logs': logs, 'total': len(logs)})
        

        # === 算子统计端点 ===
        elif path == '/api/gov/operators/stats':
            op_id = params.get('op_id', [''])[0].strip()
            hours = int(params.get('hours', ['24'])[0])
            stats = operator_stats.get_operator_stats(op_id=op_id or None, hours=hours)
            self._send(200, {'ok': True, 'operators': stats, 'total': len(stats)})
            return
        elif path == '/api/gov/operators/summary':
            hours = int(params.get('hours', ['24'])[0])
            summary = operator_stats.get_summary_stats(hours=hours)
            self._send(200, {'ok': True, 'summary': summary})
            return
        elif path == '/api/gov/operators/logs':
            op_id = params.get('op_id', [''])[0].strip()
            limit = int(params.get('limit', ['50'])[0])
            logs = operator_stats.get_operator_logs(op_id=op_id or None, limit=limit)
            self._send(200, {'ok': True, 'logs': logs, 'total': len(logs)})
            return
        elif path == '/api/gov/operators/meta':
            self._send(200, {'ok': True, 'operators': operator_stats.OPERATORS_META, 'total': len(operator_stats.OPERATORS_META)})
            return

        elif path == '/api/gov/operators/trend':
            op_id = params.get('op_id', [''])[0].strip()
            days = int(params.get('days', ['7'])[0])
            trend = operator_stats.get_trend_stats(op_id=op_id or None, days=days)
            self._send(200, {'ok': True, 'trend': trend, 'days': days})
            return
        elif path == '/api/gov/operators/hourly':
            op_id = params.get('op_id', [''])[0].strip()
            hours = int(params.get('hours', ['24'])[0])
            hourly = operator_stats.get_hourly_stats(op_id=op_id or None, hours=hours)
            self._send(200, {'ok': True, 'hourly': hourly, 'hours': hours})
            return
        elif path == '/api/gov/operators/alerts':
            limit = int(params.get('limit', ['50'])[0])
            # 先检查新告警
            new_alerts = operator_stats.check_operator_alerts()
            # 获取历史告警
            all_alerts = operator_stats.get_alerts(limit=limit)
            self._send(200, {'ok': True, 'alerts': all_alerts, 'new_alerts': len(new_alerts), 'total': len(all_alerts)})
            return
        elif path == '/api/gov/operators/alert-config':
            self._send(200, {'ok': True, 'config': operator_stats.ALERT_CONFIG})
            return

        # === 自进化引擎端点 ===
        elif path == '/api/gov/evolution/status':
            status = evolution_engine.get_evolution_status()
            self._send(200, {'ok': True, 'status': status})
            return
        elif path == '/api/gov/evolution/cache/stats':
            stats = evolution_engine.get_cache_stats()
            self._send(200, {'ok': True, 'cache': stats})
            return
        elif path == '/api/gov/evolution/knowledge-gaps':
            limit = int(params.get('limit', ['20'])[0])
            status_filter = params.get('status', [''])[0].strip()
            gaps = evolution_engine.get_knowledge_gaps(limit=limit, status=status_filter or None)
            self._send(200, {'ok': True, 'gaps': gaps})
            return
        elif path == '/api/gov/evolution/daily-report':
            date = params.get('date', [''])[0].strip()
            report = evolution_engine.generate_daily_report(date=date or None)
            self._send(200, {'ok': True, 'report': report})
            return
        elif path == '/api/gov/evolution/reports':
            limit = int(params.get('limit', ['7'])[0])
            reports = evolution_engine.get_daily_reports(limit=limit)
            self._send(200, {'ok': True, 'reports': reports, 'total': len(reports)})
            return
        elif path == '/api/gov/evolution/config':
            config = evolution_engine.load_config()
            self._send(200, {'ok': True, 'config': config})
            return

        # === 政务工作台端点 ===
        elif path == '/api/workbench/stats':
            stats = workbench_api.get_workbench_stats()
            self._send(200, {'ok': True, 'stats': stats})
            return
        elif path == '/api/workbench/todos':
            data = json.loads(body)
            if data.get('action') == 'create':
                todo = workbench_api.create_todo(
                    data.get('title',''), data.get('description',''),
                    data.get('priority','medium'), data.get('due_date'),
                    data.get('assignee','')
                )
                self._send(200, {'ok': True, 'todo': todo})
            elif data.get('action') == 'update':
                todo = workbench_api.update_todo(data.get('id'), **{k:v for k,v in data.items() if k not in ('id','action')})
                self._send(200, {'ok': todo is not None, 'todo': todo})
            elif data.get('action') == 'delete':
                workbench_api.delete_todo(data.get('id'))
                self._send(200, {'ok': True})
            else:
                self._send(200, {'todos': workbench_api.get_todos()})

            if self.command == 'POST':
                data = self._read_json()
                todo = workbench_api.create_todo(
                    title=data.get('title',''),
                    description=data.get('description',''),
                    priority=data.get('priority','medium')
                )
                self._send(200, {'ok': True, 'todo': todo})
            else:
                status = params.get('status', [''])[0]
                limit = int(params.get('limit', ['50'])[0])
                todos = workbench_api.get_todos(status=status or None, limit=limit)
                self._send(200, {'ok': True, 'todos': todos, 'total': len(todos)})
            return
        elif path.startswith('/api/workbench/todos/'):
            todo_id = path.split('/')[-1]
            if self.command == 'PUT':
                data = self._read_json()
                todo = workbench_api.update_todo(todo_id, **data)
                self._send(200, {'ok': True, 'todo': todo})
            elif self.command == 'DELETE':
                workbench_api.delete_todo(todo_id)
                self._send(200, {'ok': True})
            return
        elif path == '/api/workbench/doc-templates':
            templates = workbench_api.get_doc_templates()
            self._send(200, {'ok': True, **templates})
            return
        elif path == '/api/workbench/quick-actions':
            self._send(200, {'actions': workbench_api.get_quick_actions()})
            return
        elif path == '/api/workbench/v11/stats':
            self._send(200, workbench_api_v2.get_v11_stats())
        elif path == '/api/workbench/approvals':
            status = params.get('status', [''])[0]
            self._send(200, {'approvals': workbench_api_v2.get_approvals(status=status)})
        elif path == '/api/workbench/approvals/create':
            title = params.get('title', [''])[0]
            applicant = params.get('applicant', [''])[0]
            item_type = params.get('item_type', ['other'])[0]
            desc = params.get('description', [''])[0]
            self._send(200, workbench_api_v2.create_approval(title, applicant, item_type, desc))
        elif path == '/api/workbench/consultations':
            status = params.get('status', [''])[0]
            self._send(200, {'consultations': workbench_api_v2.get_consultations(status=status)})
        elif path == '/api/workbench/consultations/create':
            name = params.get('citizen_name', [''])[0]
            question = params.get('question', [''])[0]
            category = params.get('category', ['general'])[0]
            self._send(200, workbench_api_v2.create_consultation(name, question, category))
        elif path == '/api/workbench/doc-history':
            self._send(200, {'docs': workbench_api_v2.get_doc_history()})
        elif path == '/api/workbench/performance':
            period = params.get('period', ['month'])[0]
            self._send(200, workbench_api_v2.get_performance(period=period))
        elif path == '/api/workbench/users':
            self._send(200, {'users': workbench_api_v2.get_users()})
            return
        elif path == '/api/gov/appointments':
            uid = params.get('user_id', [''])[0]
            status = params.get('status', [''])[0]
            self._send(200, {'appointments': user_data_api.get_appointments(uid or None, status or None)})
        elif path == '/api/gov/appointments/stats':
            self._send(200, user_data_api.get_appointment_stats())
        elif path == '/api/gov/favorites':
            uid = params.get('user_id', ['anonymous'])[0]
            self._send(200, {'favorites': user_data_api.get_favorites(uid)})
        elif path == '/api/gov/favorites/check':
            uid = params.get('user_id', ['anonymous'])[0]
            pid = params.get('policy_id', [''])[0]
            self._send(200, {'favorited': user_data_api.is_favorited(uid, pid)})
        elif path == '/api/gov/user-actions/stats':
            self._send(200, user_data_api.get_action_stats())
        elif path == '/api/gov/evolution/v2/status':
            self._send(200, evolution_engine_v2.get_v2_status())
        elif path == '/api/gov/evolution/v2/quality/stats':
            self._send(200, evolution_engine_v2.get_quality_stats())
        elif path == '/api/gov/evolution/v2/quality/low-quality':
            threshold = int(params.get('threshold', ['60'])[0])
            self._send(200, {'low_quality': evolution_engine_v2.get_low_quality_caches(threshold)})
        elif path == '/api/gov/evolution/v2/feedback/stats':
            self._send(200, evolution_engine_v2.get_feedback_stats())
        elif path == '/api/gov/evolution/v2/strategy':
            self._send(200, evolution_engine_v2.get_evolution_strategy())
            self._send(200, user_data_api.get_action_stats())
            self._send(200, {'users': workbench_api_v2.get_users()})
            actions = workbench_api.get_quick_actions()
            self._send(200, {'ok': True, 'actions': actions})
            return







        # ============ RBAC权限系统 GET端点 ============
        elif path == '/api/rbac/verify':
            token = params.get('token', [''])[0]
            session = rbac_system.verify_token(token)
            if session:
                self._send(200, {'success': True, 'user': session, 'permissions': rbac_system.get_user_permissions(session['user_id'])})
            else:
                self._send(401, {'success': False, 'error': 'Token无效或已过期'})
        elif path == '/api/rbac/users':
            token = params.get('token', [''])[0]
            session = rbac_system.verify_token(token)
            if not session:
                self._send(401, {'success': False, 'error': '未登录'})
                return
            if not rbac_system.check_permission(session['user_id'], 'sys.user.manage'):
                self._send(403, {'success': False, 'error': '无权限'})
                return
            users = rbac_system.read_json(rbac_system.USERS_FILE, {}).get('users', [])
            safe_users = [{k:v for k,v in u.items() if k != 'password_hash'} for u in users]
            self._send(200, {'success': True, 'users': safe_users, 'count': len(safe_users)})
        elif path == '/api/rbac/roles':
            roles = rbac_system.read_json(rbac_system.ROLES_FILE, {}).get('roles', [])
            self._send(200, {'success': True, 'roles': roles, 'count': len(roles)})
        elif path == '/api/rbac/permissions':
            perms = rbac_system.read_json(rbac_system.PERMISSIONS_FILE, {}).get('permissions', [])
            self._send(200, {'success': True, 'permissions': perms, 'count': len(perms)})
        elif path == '/api/rbac/audit':
            token = params.get('token', [''])[0]
            session = rbac_system.verify_token(token)
            if not session:
                self._send(401, {'success': False, 'error': '未登录'})
                return
            if not rbac_system.check_permission(session['user_id'], 'sys.audit.view'):
                self._send(403, {'success': False, 'error': '无权限'})
                return
            logs = []
            try:
                with open(rbac_system.AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            logs.append(json.loads(line))
            except:
                pass
            logs.reverse()
            limit = int(params.get('limit', ['100'])[0])
            self._send(200, {'success': True, 'logs': logs[:limit], 'count': len(logs)})
        elif path == '/api/rbac/stats':
            users = rbac_system.read_json(rbac_system.USERS_FILE, {}).get('users', [])
            roles = rbac_system.read_json(rbac_system.ROLES_FILE, {}).get('roles', [])
            sessions = rbac_system.read_json(rbac_system.SESSIONS_FILE, {}).get('sessions', [])
            audit_count = 0
            try:
                with open(rbac_system.AUDIT_LOG_FILE, 'r') as f:
                    audit_count = sum(1 for _ in f)
            except:
                pass
            self._send(200, {'success': True, 'users': len(users), 'roles': len(roles), 'active_sessions': len(sessions), 'audit_logs': audit_count, 'permissions': 16})
        # ============ 数据聚合 GET端点 ============
        elif path == '/api/analytics/dashboard':
            self._send(200, {'success': True, **data_analytics_api.get_dashboard_stats()})
        elif path == '/api/analytics/trend':
            days = int(params.get('days', ['7'])[0])
            self._send(200, {'success': True, **data_analytics_api.get_trend_data(days)})
        elif path == '/api/analytics/policy-hotness':
            self._send(200, {'success': True, **data_analytics_api.get_policy_hotness()})
        elif path == '/api/analytics/evolution':
            self._send(200, {'success': True, **data_analytics_api.get_evolution_stats()})
        elif path == '/api/analytics/operators':
            self._send(200, {'success': True, **data_analytics_api.get_operator_stats()})
        elif path == '/api/analytics/user-activity':
            self._send(200, {'success': True, **data_analytics_api.get_user_activity()})
        elif path == '/api/analytics/categories':
            self._send(200, {'success': True, **data_analytics_api.get_category_distribution()})
        elif path == '/api/analytics/export':
            self._send(200, {'success': True, **data_analytics_api.export_report()})
        # ============ 通知系统 GET端点 ============
        elif path == '/api/notifications/list':
            user_id = params.get('user_id', ['default'])[0]
            unread_only = params.get('unread_only', ['false'])[0] == 'true'
            limit = int(params.get('limit', ['50'])[0])
            notifs = notification_system.get_notifications(user_id, unread_only, limit)
            self._send(200, {'success': True, 'notifications': notifs, 'count': len(notifs)})
        elif path == '/api/notifications/unread-count':
            user_id = params.get('user_id', ['default'])[0]
            count = notification_system.get_unread_count(user_id)
            self._send(200, {'success': True, 'unread_count': count})
        elif path == '/api/notifications/stats':
            user_id = params.get('user_id', ['default'])[0]
            stats = notification_system.get_stats(user_id)
            self._send(200, {'success': True, **stats})
        elif path == '/api/esign/seals':
            user_id = params.get('user_id', ['admin'])[0]
            result = esign_system.get_user_seals(user_id)
            self._send(200, result)
        elif path == '/api/esign/records':
            user_id = params.get('user_id', [None])[0]
            document_id = params.get('document_id', [None])[0]
            limit = int(params.get('limit', [50])[0])
            result = esign_system.get_sign_records(user_id, document_id, limit)
            self._send(200, result)
        elif path == '/api/esign/stats':
            result = esign_system.get_stats()
            self._send(200, result)
        elif path == '/api/esign/verify':
            record_id = params.get('record_id', [''])[0]
            result = esign_system.verify_signature(record_id)
            self._send(200, result)
        elif path == '/api/tenants/list':
            limit = int(params.get('limit', [50])[0])
            result = multi_tenant.list_tenants(limit)
            self._send(200, result)
        elif path == '/api/tenants/stats':
            result = multi_tenant.get_stats()
            self._send(200, result)
        elif path == '/api/tenants/detail':
            tenant_id = params.get('tenant_id', [''])[0]
            result = multi_tenant.get_tenant(tenant_id)
            self._send(200, result)
        elif path == '/api/ai-models/list':
            result = ai_model_router.get_available_models()
            self._send(200, result)
        elif path == '/api/ai-models/route':
            result = ai_model_router.get_model_route()
            self._send(200, result)
        elif path == '/api/ai-models/usage':
            result = ai_model_router.get_usage_stats()
            self._send(200, result)
        elif path == '/api/ai-models/config':
            result = ai_model_router.get_model_config()
            self._send(200, result)
        elif path == '/api/ai-models/deploy-guide':
            result = ai_model_router.deploy_local_model_guide()
            self._send(200, result)
        else:
            self._send(404, {'error': 'not found'})

    def do_PUT(self):
        """更新政策/指南"""
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b'{}'
        try:
            data = json.loads(body)
        except:
            data = {}

        if not check_admin_auth(self.headers):
            self._send(401, {'error': 'unauthorized'})
            return

        if self.path == '/api/admin/policy':
            pid = data.get('id', '')
            for i, p in enumerate(POLICIES):
                if p['id'] == pid:
                    for key in ['title', 'category', 'doc_no', 'org', 'effective_date', 'summary', 'keywords']:
                        if key in data:
                            POLICIES[i][key] = data[key]
                    save_policies()
                    log_admin_action('UPDATE_POLICY', pid, data.get('title', ''))
                    self._send(200, {'ok': True, 'policy': POLICIES[i]})
                    return
            self._send(404, {'error': 'policy not found'})

        elif self.path == '/api/admin/guide':
            gid = data.get('id', '')
            for i, g in enumerate(GUIDES):
                if g['id'] == gid:
                    for key in ['title', 'category', 'conditions', 'materials', 'steps', 'location', 'phone', 'time']:
                        if key in data:
                            GUIDES[i][key] = data[key]
                    save_guides()
                    log_admin_action('UPDATE_GUIDE', gid, data.get('title', ''))
                    self._send(200, {'ok': True, 'guide': GUIDES[i]})
                    return
            self._send(404, {'error': 'guide not found'})


        # === 算子统计端点 ===
        elif path == '/api/gov/operators/stats':
            op_id = params.get('op_id', [''])[0].strip()
            hours = int(params.get('hours', ['24'])[0])
            stats = operator_stats.get_operator_stats(op_id=op_id or None, hours=hours)
            self._send(200, {'ok': True, 'operators': stats, 'total': len(stats)})
            return
        elif path == '/api/gov/operators/summary':
            hours = int(params.get('hours', ['24'])[0])
            summary = operator_stats.get_summary_stats(hours=hours)
            self._send(200, {'ok': True, 'summary': summary})
            return
        elif path == '/api/gov/operators/logs':
            op_id = params.get('op_id', [''])[0].strip()
            limit = int(params.get('limit', ['50'])[0])
            logs = operator_stats.get_operator_logs(op_id=op_id or None, limit=limit)
            self._send(200, {'ok': True, 'logs': logs, 'total': len(logs)})
            return
        elif path == '/api/gov/operators/meta':
            self._send(200, {'ok': True, 'operators': operator_stats.OPERATORS_META, 'total': len(operator_stats.OPERATORS_META)})
            return

        elif path == '/api/gov/operators/trend':
            op_id = params.get('op_id', [''])[0].strip()
            days = int(params.get('days', ['7'])[0])
            trend = operator_stats.get_trend_stats(op_id=op_id or None, days=days)
            self._send(200, {'ok': True, 'trend': trend, 'days': days})
            return
        elif path == '/api/gov/operators/hourly':
            op_id = params.get('op_id', [''])[0].strip()
            hours = int(params.get('hours', ['24'])[0])
            hourly = operator_stats.get_hourly_stats(op_id=op_id or None, hours=hours)
            self._send(200, {'ok': True, 'hourly': hourly, 'hours': hours})
            return
        elif path == '/api/gov/operators/alerts':
            limit = int(params.get('limit', ['50'])[0])
            # 先检查新告警
            new_alerts = operator_stats.check_operator_alerts()
            # 获取历史告警
            all_alerts = operator_stats.get_alerts(limit=limit)
            self._send(200, {'ok': True, 'alerts': all_alerts, 'new_alerts': len(new_alerts), 'total': len(all_alerts)})
            return
        elif path == '/api/gov/operators/alert-config':
            self._send(200, {'ok': True, 'config': operator_stats.ALERT_CONFIG})
            return

        # === 自进化引擎端点 ===
        elif path == '/api/gov/evolution/status':
            status = evolution_engine.get_evolution_status()
            self._send(200, {'ok': True, 'status': status})
            return
        elif path == '/api/gov/evolution/cache/stats':
            stats = evolution_engine.get_cache_stats()
            self._send(200, {'ok': True, 'cache': stats})
            return
        elif path == '/api/gov/evolution/knowledge-gaps':
            limit = int(params.get('limit', ['20'])[0])
            status_filter = params.get('status', [''])[0].strip()
            gaps = evolution_engine.get_knowledge_gaps(limit=limit, status=status_filter or None)
            self._send(200, {'ok': True, 'gaps': gaps})
            return
        elif path == '/api/gov/evolution/daily-report':
            date = params.get('date', [''])[0].strip()
            report = evolution_engine.generate_daily_report(date=date or None)
            self._send(200, {'ok': True, 'report': report})
            return
        elif path == '/api/gov/evolution/reports':
            limit = int(params.get('limit', ['7'])[0])
            reports = evolution_engine.get_daily_reports(limit=limit)
            self._send(200, {'ok': True, 'reports': reports, 'total': len(reports)})
            return
        elif path == '/api/gov/evolution/config':
            config = evolution_engine.load_config()
            self._send(200, {'ok': True, 'config': config})
            return

        # === 政务工作台端点 ===
        elif path == '/api/workbench/stats':
            stats = workbench_api.get_workbench_stats()
            self._send(200, {'ok': True, 'stats': stats})
            return
        elif path == '/api/workbench/todos':
            if self.command == 'POST':
                data = self._read_json()
                todo = workbench_api.create_todo(
                    title=data.get('title',''),
                    description=data.get('description',''),
                    priority=data.get('priority','medium')
                )
                self._send(200, {'ok': True, 'todo': todo})
            else:
                status = params.get('status', [''])[0]
                limit = int(params.get('limit', ['50'])[0])
                todos = workbench_api.get_todos(status=status or None, limit=limit)
                self._send(200, {'ok': True, 'todos': todos, 'total': len(todos)})
            return
        elif path.startswith('/api/workbench/todos/'):
            todo_id = path.split('/')[-1]
            if self.command == 'PUT':
                data = self._read_json()
                todo = workbench_api.update_todo(todo_id, **data)
                self._send(200, {'ok': True, 'todo': todo})
            elif self.command == 'DELETE':
                workbench_api.delete_todo(todo_id)
                self._send(200, {'ok': True})
            return
        elif path == '/api/workbench/doc-templates':
            templates = workbench_api.get_doc_templates()
            self._send(200, {'ok': True, **templates})
            return
        elif path == '/api/workbench/quick-actions':
            actions = workbench_api.get_quick_actions()
            self._send(200, {'ok': True, 'actions': actions})
            return







        else:
            self._send(404, {'error': 'not found'})

    def do_DELETE(self):
        """删除政策/指南"""
        if not check_admin_auth(self.headers):
            self._send(401, {'error': 'unauthorized'})
            return

        parsed = __import__('urllib.parse').parse.urlparse(self.path)
        params = __import__('urllib.parse').parse.parse_qs(parsed.query)

        if parsed.path == '/api/admin/policy':
            pid = params.get('id', [''])[0]
            for i, p in enumerate(POLICIES):
                if p['id'] == pid:
                    deleted = POLICIES.pop(i)
                    save_policies()
                    log_admin_action('DELETE_POLICY', pid, deleted['title'])
                    self._send(200, {'ok': True, 'total': len(POLICIES)})
                    return
            self._send(404, {'error': 'policy not found'})

        elif parsed.path == '/api/admin/guide':
            gid = params.get('id', [''])[0]
            for i, g in enumerate(GUIDES):
                if g['id'] == gid:
                    deleted = GUIDES.pop(i)
                    save_guides()
                    log_admin_action('DELETE_GUIDE', gid, deleted['title'])
                    self._send(200, {'ok': True, 'total': len(GUIDES)})
                    return
            self._send(404, {'error': 'guide not found'})


        # === 算子统计端点 ===
        elif path == '/api/gov/operators/stats':
            op_id = params.get('op_id', [''])[0].strip()
            hours = int(params.get('hours', ['24'])[0])
            stats = operator_stats.get_operator_stats(op_id=op_id or None, hours=hours)
            self._send(200, {'ok': True, 'operators': stats, 'total': len(stats)})
            return
        elif path == '/api/gov/operators/summary':
            hours = int(params.get('hours', ['24'])[0])
            summary = operator_stats.get_summary_stats(hours=hours)
            self._send(200, {'ok': True, 'summary': summary})
            return
        elif path == '/api/gov/operators/logs':
            op_id = params.get('op_id', [''])[0].strip()
            limit = int(params.get('limit', ['50'])[0])
            logs = operator_stats.get_operator_logs(op_id=op_id or None, limit=limit)
            self._send(200, {'ok': True, 'logs': logs, 'total': len(logs)})
            return
        elif path == '/api/gov/operators/meta':
            self._send(200, {'ok': True, 'operators': operator_stats.OPERATORS_META, 'total': len(operator_stats.OPERATORS_META)})
            return

        elif path == '/api/gov/operators/trend':
            op_id = params.get('op_id', [''])[0].strip()
            days = int(params.get('days', ['7'])[0])
            trend = operator_stats.get_trend_stats(op_id=op_id or None, days=days)
            self._send(200, {'ok': True, 'trend': trend, 'days': days})
            return
        elif path == '/api/gov/operators/hourly':
            op_id = params.get('op_id', [''])[0].strip()
            hours = int(params.get('hours', ['24'])[0])
            hourly = operator_stats.get_hourly_stats(op_id=op_id or None, hours=hours)
            self._send(200, {'ok': True, 'hourly': hourly, 'hours': hours})
            return
        elif path == '/api/gov/operators/alerts':
            limit = int(params.get('limit', ['50'])[0])
            # 先检查新告警
            new_alerts = operator_stats.check_operator_alerts()
            # 获取历史告警
            all_alerts = operator_stats.get_alerts(limit=limit)
            self._send(200, {'ok': True, 'alerts': all_alerts, 'new_alerts': len(new_alerts), 'total': len(all_alerts)})
            return
        elif path == '/api/gov/operators/alert-config':
            self._send(200, {'ok': True, 'config': operator_stats.ALERT_CONFIG})
            return

        # === 自进化引擎端点 ===
        elif path == '/api/gov/evolution/status':
            status = evolution_engine.get_evolution_status()
            self._send(200, {'ok': True, 'status': status})
            return
        elif path == '/api/gov/evolution/cache/stats':
            stats = evolution_engine.get_cache_stats()
            self._send(200, {'ok': True, 'cache': stats})
            return
        elif path == '/api/gov/evolution/knowledge-gaps':
            limit = int(params.get('limit', ['20'])[0])
            status_filter = params.get('status', [''])[0].strip()
            gaps = evolution_engine.get_knowledge_gaps(limit=limit, status=status_filter or None)
            self._send(200, {'ok': True, 'gaps': gaps})
            return
        elif path == '/api/gov/evolution/daily-report':
            date = params.get('date', [''])[0].strip()
            report = evolution_engine.generate_daily_report(date=date or None)
            self._send(200, {'ok': True, 'report': report})
            return
        elif path == '/api/gov/evolution/reports':
            limit = int(params.get('limit', ['7'])[0])
            reports = evolution_engine.get_daily_reports(limit=limit)
            self._send(200, {'ok': True, 'reports': reports, 'total': len(reports)})
            return
        elif path == '/api/gov/evolution/config':
            config = evolution_engine.load_config()
            self._send(200, {'ok': True, 'config': config})
            return

        # === 政务工作台端点 ===
        elif path == '/api/workbench/stats':
            stats = workbench_api.get_workbench_stats()
            self._send(200, {'ok': True, 'stats': stats})
            return
        elif path == '/api/workbench/todos':
            if self.command == 'POST':
                data = self._read_json()
                todo = workbench_api.create_todo(
                    title=data.get('title',''),
                    description=data.get('description',''),
                    priority=data.get('priority','medium')
                )
                self._send(200, {'ok': True, 'todo': todo})
            else:
                status = params.get('status', [''])[0]
                limit = int(params.get('limit', ['50'])[0])
                todos = workbench_api.get_todos(status=status or None, limit=limit)
                self._send(200, {'ok': True, 'todos': todos, 'total': len(todos)})
            return
        elif path.startswith('/api/workbench/todos/'):
            todo_id = path.split('/')[-1]
            if self.command == 'PUT':
                data = self._read_json()
                todo = workbench_api.update_todo(todo_id, **data)
                self._send(200, {'ok': True, 'todo': todo})
            elif self.command == 'DELETE':
                workbench_api.delete_todo(todo_id)
                self._send(200, {'ok': True})
            return
        elif path == '/api/workbench/doc-templates':
            templates = workbench_api.get_doc_templates()
            self._send(200, {'ok': True, **templates})
            return
        elif path == '/api/workbench/quick-actions':
            actions = workbench_api.get_quick_actions()
            self._send(200, {'ok': True, 'actions': actions})
            return







        # ============ RBAC权限系统 GET端点 ============
        elif path == '/api/rbac/verify':
            token = params.get('token', [''])[0]
            session = rbac_system.verify_token(token)
            if session:
                self._send(200, {'success': True, 'user': session, 'permissions': rbac_system.get_user_permissions(session['user_id'])})
            else:
                self._send(401, {'success': False, 'error': 'Token无效或已过期'})
        elif path == '/api/rbac/users':
            token = params.get('token', [''])[0]
            session = rbac_system.verify_token(token)
            if not session:
                self._send(401, {'success': False, 'error': '未登录'})
                return
            if not rbac_system.check_permission(session['user_id'], 'sys.user.manage'):
                self._send(403, {'success': False, 'error': '无权限'})
                return
            users = rbac_system.read_json(rbac_system.USERS_FILE, {}).get('users', [])
            safe_users = [{k:v for k,v in u.items() if k != 'password_hash'} for u in users]
            self._send(200, {'success': True, 'users': safe_users, 'count': len(safe_users)})
        elif path == '/api/rbac/roles':
            roles = rbac_system.read_json(rbac_system.ROLES_FILE, {}).get('roles', [])
            self._send(200, {'success': True, 'roles': roles, 'count': len(roles)})
        elif path == '/api/rbac/permissions':
            perms = rbac_system.read_json(rbac_system.PERMISSIONS_FILE, {}).get('permissions', [])
            self._send(200, {'success': True, 'permissions': perms, 'count': len(perms)})
        elif path == '/api/rbac/audit':
            token = params.get('token', [''])[0]
            session = rbac_system.verify_token(token)
            if not session:
                self._send(401, {'success': False, 'error': '未登录'})
                return
            if not rbac_system.check_permission(session['user_id'], 'sys.audit.view'):
                self._send(403, {'success': False, 'error': '无权限'})
                return
            logs = []
            try:
                with open(rbac_system.AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            logs.append(json.loads(line))
            except:
                pass
            logs.reverse()
            limit = int(params.get('limit', ['100'])[0])
            self._send(200, {'success': True, 'logs': logs[:limit], 'count': len(logs)})
        elif path == '/api/rbac/stats':
            users = rbac_system.read_json(rbac_system.USERS_FILE, {}).get('users', [])
            roles = rbac_system.read_json(rbac_system.ROLES_FILE, {}).get('roles', [])
            sessions = rbac_system.read_json(rbac_system.SESSIONS_FILE, {}).get('sessions', [])
            audit_count = 0
            try:
                with open(rbac_system.AUDIT_LOG_FILE, 'r') as f:
                    audit_count = sum(1 for _ in f)
            except:
                pass
            self._send(200, {'success': True, 'users': len(users), 'roles': len(roles), 'active_sessions': len(sessions), 'audit_logs': audit_count, 'permissions': 16})
        else:
            self._send(404, {'error': 'not found'})

    def do_POST(self):
        _start_time = time.time()
        # 安全中间件：速率限制检查
        endpoint_type = 'chat' if '/chat' in self.path else ('login' if '/login' in self.path else 'api')
        allowed, retry_after = security_middleware.check_rate_limit(self, endpoint_type)
        if not allowed:
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Retry-After', str(retry_after))
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'rate_limit_exceeded', 'retry_after': retry_after}).encode())
            return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except:
            data = {}
        api_key = self.headers.get('X-API-Key') or data.get('api_key')


        if self.path == '/api/workbench/approvals/update':
            result = workbench_api_v2.update_approval(data.get('id'), **{k:v for k,v in data.items() if k != 'id'})
            self._send(200, {'ok': result is not None, 'approval': result})
            return
        elif self.path == '/api/workbench/consultations/update':
            result = workbench_api_v2.update_consultation(data.get('id'), **{k:v for k,v in data.items() if k != 'id'})
            self._send(200, {'ok': result is not None, 'consultation': result})
            return
        elif self.path == '/api/workbench/doc-history/save':
            result = workbench_api_v2.save_doc_history(
                data.get('title',''), data.get('doc_type',''),
                data.get('content',''), data.get('creator',''),
                data.get('template_id','')
            )
            self._send(200, {'ok': True, 'doc': result})
            return
        elif self.path == '/api/gov/appointments/create':
            apt = user_data_api.create_appointment(
                data.get('user_id','anonymous'),
                data.get('guide_id',''),
                data.get('guide_title',''),
                data.get('name',''),
                data.get('phone',''),
                data.get('date',''),
                data.get('time_slot',''),
                data.get('remark','')
            )
            self._send(200, {'ok': True, 'appointment': apt})
            return
        elif self.path == '/api/gov/appointments/update':
            result = user_data_api.update_appointment(data.get('id'), **{k:v for k,v in data.items() if k != 'id'})
            self._send(200, {'ok': result is not None, 'appointment': result})
            return
        elif self.path == '/api/gov/evolution/v2/quality/record':
            result = evolution_engine_v2.record_cache_quality(
                data.get('query',''), data.get('answer',''),
                data.get('score', 80), data.get('source','auto')
            )
            self._send(200, {'ok': True, 'quality': result})
            return
        elif self.path == '/api/gov/evolution/v2/feedback/record':
            result = evolution_engine_v2.record_feedback(
                data.get('query',''), data.get('type','thumbs_up'),
                data.get('comment','')
            )
            self._send(200, {'ok': True, 'feedback': result})
            return
        elif self.path == '/api/gov/evolution/v2/strategy/check':
            allowed, reason = evolution_engine_v2.can_auto_execute(data.get('action_type',''))
            self._send(200, {'allowed': allowed, 'reason': reason})
            return
        elif self.path == '/api/gov/favorites/toggle':
            result = user_data_api.toggle_favorite(
                data.get('user_id','anonymous'),
                data.get('policy_id',''),
                data.get('title',''),
                data.get('category','')
            )
            self._send(200, {'ok': True, **result})
            return
        elif self.path == '/api/gov/user-actions/record':
            action = user_data_api.record_action(
                data.get('user_id','anonymous'),
                data.get('action_type',''),
                data.get('target_id',''),
                data.get('target_type',''),
                data.get('metadata')
            )
            self._send(200, {'ok': True, 'action': action})
            return
        if self.path == '/api/workbench/approvals/create':
            result = workbench_api_v2.create_approval(
                data.get('title',''), data.get('applicant',''),
                data.get('item_type','other'), data.get('description','')
            )
            self._send(200, {'ok': True, 'approval': result})
            return
        elif self.path == '/api/workbench/consultations/create':
            result = workbench_api_v2.create_consultation(
                data.get('citizen_name',''), data.get('question',''),
                data.get('category','general'), data.get('phone','')
            )
            self._send(200, {'ok': True, 'consultation': result})
            return
        if self.path == '/api/gov/operators/call':
            op_id = data.get('op_id', '')
            success = data.get('success', True)
            latency_ms = data.get('latency_ms', 0)
            details = data.get('details', {})
            if not op_id:
                self._send(400, {'error': 'op_id required'})
                return
            record = operator_stats.record_operator_call(op_id, success=success, latency_ms=latency_ms, details=details)
            self._send(200, {'ok': True, 'record': record})
            return

        # === 政务工作台 POST 端点 ===
        if self.path == '/api/workbench/todos':
            todo = workbench_api.create_todo(
                title=data.get('title',''),
                description=data.get('description',''),
                priority=data.get('priority','medium')
            )
            self._send(200, {'ok': True, 'todo': todo})
            return

        if self.path == '/api/gov/chat':
            user_msg = data.get('message', '')
            history = data.get('history', [])
            lang = data.get('lang', 'zh')  # zh/en/yue
            
            # 进化引擎：检查高频问答缓存
            evo_hit, evo_answer = evolution_engine.check_high_freq_cache(user_msg)
            if evo_hit:
                self._send(200, {
                    'reply': evo_answer,
                    'cached': True,
                    'cache_source': 'evolution_high_freq',
                    'question_type': 'auto_cached'
                })
                record_usage(api_key, self.path, 200, time.time() - _start_time)
                return
            
            # 检查缓存（包含语言）
            cache_key = get_cache_key('chat', f"{lang}:{user_msg[:100]}")
            cached = get_cache(cache_key)
            if cached:
                # 进化引擎：即使缓存命中也记录高频缓存判断
                evolution_engine.record_question_for_cache(user_msg, cached.get('reply', ''))
                cached['cached'] = True
                self._send(200, cached)
                record_usage(api_key, self.path, 200, time.time() - _start_time)
                return
            # 问题分类
            q_type = classify_question(user_msg)
            # 优化检索：top_k从5减少到3
            search_results = enhanced_search(user_msg, top_k=3)
            # 构建上下文
            context_parts = []
            related_policies = []
            related_guides = []
            for r in search_results:
                if r['type'] == 'policy':
                    related_policies.append(r['title'])
                    context_parts.append(f"[政策] {r['title']}（{r.get('doc_no','')}，{r.get('org','')}）：{r.get('summary','')}")
                else:
                    related_guides.append(r['title'])
                    context_parts.append(f"[办事指南] {r['title']}：条件-{r.get('conditions','')}；地点-{r.get('location','')}；电话-{r.get('phone','')}")
            # 构建消息
            type_prompt = {
                'policy': '用户正在咨询政策问题，请重点引用政策依据，准确说明政策内容和适用条件。',
                'guide': '用户正在咨询办事流程，请按办理条件、所需材料、办理流程、办理地点、咨询电话、办理时限的结构回答。',
                'document': '用户需要公文写作帮助，请提供规范的公文格式和内容。',
                'general': '用户进行通用政务咨询，请准确、简洁地回答。'
            }.get(q_type, '')
            # 根据语言选择system prompt
            lang_prompt = {'zh': GOV_SYSTEM_PROMPT_ZH, 'en': GOV_SYSTEM_PROMPT_EN, 'yue': GOV_SYSTEM_PROMPT_YUE}.get(lang, GOV_SYSTEM_PROMPT_ZH)
            system_content = lang_prompt + '\n\n【当前问题类型】' + q_type + '\n' + type_prompt
            if context_parts:
                system_content += '\n\n【参考资料】\n' + '\n'.join(context_parts[:4])
            messages = [{'role': 'system', 'content': system_content}]
            messages.extend(history[-6:])
            messages.append({'role': 'user', 'content': user_msg})
            reply = call_aiproxy(messages)
            # 进化引擎：记录问题用于高频缓存判断
            evolution_engine.record_question_for_cache(user_msg, reply)
            
            result = {'reply': reply, 'question_type': q_type,
                           'related_policies': related_policies[:5],
                           'related_guides': related_guides[:5],
                           'search_count': len(search_results),
                           'cached': False,
                           'language': lang}
            if reply and '错误' not in reply and len(reply) > 10:
                set_cache(cache_key, result)
            self._send(200, result)
            record_usage(api_key, self.path, 200, time.time() - _start_time)
            return
        
        elif self.path == '/api/gov/doc/generate':
            doc_type = data.get('type', '通知')
            title = data.get('title', '')
            content = data.get('content', '')
            prompt = f'请帮我生成一份{doc_type}。\n标题：{title}\n主要内容：{content}\n\n要求：格式规范，要素完整，语言正式。'
            messages = [{'role': 'system', 'content': '你是公文写作助手，精通各类公文格式。'}, {'role': 'user', 'content': prompt}]
            result = call_aiproxy(messages, max_tokens=2048)
            self._send(200, {'result': result, 'type': doc_type})
            record_usage(api_key, self.path, 200, time.time() - _start_time)
            return
        
        elif self.path == '/api/gov/doc/polish':
            text = data.get('text', '')
            prompt = f'请润色以下公文，使其更加规范、严谨：\n\n{text}'
            messages = [{'role': 'system', 'content': '你是公文润色助手。'}, {'role': 'user', 'content': prompt}]
            result = call_aiproxy(messages, max_tokens=2048)
            self._send(200, {'result': result})

        # === 管理端点：新增 ===
        elif self.path == '/api/admin/policy':
            if not check_admin_auth(self.headers):
                self._send(401, {'error': 'unauthorized'})
                return
            new_id = f'P{len(POLICIES) + 1000}'
            policy = {
                'id': new_id,
                'title': data.get('title', ''),
                'category': data.get('category', '其他'),
                'doc_no': data.get('doc_no', ''),
                'org': data.get('org', ''),
                'effective_date': data.get('effective_date', ''),
                'summary': data.get('summary', ''),
                'keywords': data.get('keywords', [])
            }
            POLICIES.append(policy)
            save_policies()
            log_admin_action('CREATE_POLICY', new_id, policy['title'])
            self._send(200, {'ok': True, 'id': new_id, 'total': len(POLICIES)})

        elif self.path == '/api/admin/guide':
            if not check_admin_auth(self.headers):
                self._send(401, {'error': 'unauthorized'})
                return
            new_id = f'G{len(GUIDES) + 100}'
            guide = {
                'id': new_id,
                'title': data.get('title', ''),
                'category': data.get('category', '其他'),
                'conditions': data.get('conditions', ''),
                'materials': data.get('materials', ''),
                'steps': data.get('steps', ''),
                'location': data.get('location', ''),
                'phone': data.get('phone', ''),
                'time': data.get('time', '')
            }
            GUIDES.append(guide)
            save_guides()
            log_admin_action('CREATE_GUIDE', new_id, guide['title'])
            self._send(200, {'ok': True, 'id': new_id, 'total': len(GUIDES)})
        



        
        # ============ RBAC权限系统 POST端点 ============
        elif self.path == '/api/rbac/login':
            data = json.loads(body) if body else {}
            result = rbac_system.login(data.get('username',''), data.get('password',''))
            self._send(200 if result['success'] else 401, result)
        elif self.path == '/api/rbac/logout':
            data = json.loads(body) if body else {}
            self._send(200, rbac_system.logout(data.get('token','')))
        elif self.path == '/api/rbac/users/create':
            data = json.loads(body) if body else {}
            session = rbac_system.verify_token(data.get('token',''))
            if not session: self._send(401, {'success':False,'error':'未登录'}); return
            if not rbac_system.check_permission(session['user_id'], 'sys.user.manage'): self._send(403, {'success':False,'error':'无权限'}); return
            users = rbac_system.read_json(rbac_system.USERS_FILE, {}).get('users', [])
            new_user = {'id':'user_'+str(len(users)+1).zfill(3),'username':data.get('username',''),'password_hash':rbac_system.hashlib.sha256(data.get('password','123456').encode()).hexdigest(),'name':data.get('name',''),'role':data.get('role','visitor'),'email':data.get('email',''),'phone':data.get('phone',''),'status':'active','created_at':rbac_system.datetime.datetime.now().isoformat(),'last_login':None}
            users.append(new_user)
            rbac_system.write_json(rbac_system.USERS_FILE, {'users':users,'count':len(users)})
            rbac_system.append_audit(session['user_id'], 'create_user', 'rbac', f'创建用户 {new_user["username"]}')
            self._send(200, {'success':True,'user':{k:v for k,v in new_user.items() if k!='password_hash'}})
        elif self.path == '/api/rbac/users/update':
            data = json.loads(body) if body else {}
            session = rbac_system.verify_token(data.get('token',''))
            if not session: self._send(401, {'success':False,'error':'未登录'}); return
            if not rbac_system.check_permission(session['user_id'], 'sys.user.manage'): self._send(403, {'success':False,'error':'无权限'}); return
            users = rbac_system.read_json(rbac_system.USERS_FILE, {}).get('users', [])
            for u in users:
                if u['id'] == data.get('user_id',''):
                    for k in ['name','role','email','phone','status']:
                        if k in data: u[k] = data[k]
                    if data.get('password'): u['password_hash'] = rbac_system.hashlib.sha256(data['password'].encode()).hexdigest()
                    break
            rbac_system.write_json(rbac_system.USERS_FILE, {'users':users,'count':len(users)})
            rbac_system.append_audit(session['user_id'], 'update_user', 'rbac', f'更新用户 {data.get("user_id")}')
            self._send(200, {'success':True})
        elif self.path == '/api/rbac/users/delete':
            data = json.loads(body) if body else {}
            session = rbac_system.verify_token(data.get('token',''))
            if not session: self._send(401, {'success':False,'error':'未登录'}); return
            if not rbac_system.check_permission(session['user_id'], 'sys.user.manage'): self._send(403, {'success':False,'error':'无权限'}); return
            users = [u for u in rbac_system.read_json(rbac_system.USERS_FILE, {}).get('users', []) if u['id'] != data.get('user_id','')]
            rbac_system.write_json(rbac_system.USERS_FILE, {'users':users,'count':len(users)})
            rbac_system.append_audit(session['user_id'], 'delete_user', 'rbac', f'删除用户 {data.get("user_id")}')
            self._send(200, {'success':True})
        elif self.path == '/api/rbac/roles/update':
            data = json.loads(body) if body else {}
            session = rbac_system.verify_token(data.get('token',''))
            if not session: self._send(401, {'success':False,'error':'未登录'}); return
            if not rbac_system.check_permission(session['user_id'], 'sys.role.manage'): self._send(403, {'success':False,'error':'无权限'}); return
            roles = rbac_system.read_json(rbac_system.ROLES_FILE, {}).get('roles', [])
            for r in roles:
                if r['id'] == data.get('role_id','') and not r.get('is_system',False):
                    for k in ['name','desc','permissions']:
                        if k in data: r[k] = data[k]
                    break
            rbac_system.write_json(rbac_system.ROLES_FILE, {'roles':roles,'count':len(roles)})
            rbac_system.append_audit(session['user_id'], 'update_role', 'rbac', f'更新角色 {data.get("role_id")}')
            self._send(200, {'success':True})

        # ============ 通知系统 POST端点 ============
        elif self.path == '/api/notifications/read':
            data = json.loads(body) if body else {}
            notification_system.mark_as_read(data.get('id', ''), data.get('user_id', 'default'))
            self._send(200, {'success': True})
        elif self.path == '/api/notifications/read-all':
            data = json.loads(body) if body else {}
            notification_system.mark_all_as_read(data.get('user_id', 'default'))
            self._send(200, {'success': True})
        elif self.path == '/api/notifications/create':
            data = json.loads(body) if body else {}
            notif = notification_system.create_notification(
                data.get('user_id', 'default'),
                data.get('type', 'system'),
                data.get('title', ''),
                data.get('content', ''),
                data.get('link', '')
            )
            self._send(200, {'success': True, 'notification': notif})
        elif self.path == '/api/notifications/delete':
            data = json.loads(body) if body else {}
            notification_system.delete_notification(data.get('id', ''), data.get('user_id', 'default'))
            self._send(200, {'success': True})


        elif self.path == '/api/esign/create':
            user_id = data.get('user_id', 'admin')
            seal_name = data.get('seal_name', '新签章')
            seal_type = data.get('seal_type', 'official')
            result = esign_system.create_seal(user_id, seal_name, seal_type)
            return self.json_response(result)
        elif self.path == '/api/esign/sign':
            user_id = data.get('user_id', 'admin')
            document_id = data.get('document_id', '')
            document_content = data.get('document_content', '')
            seal_id = data.get('seal_id', '')
            result = esign_system.sign_document(user_id, document_id, document_content, seal_id)
            return self.json_response(result)
        elif self.path == '/api/tenants/create':
            name = data.get('name', '新租户')
            domain = data.get('domain', '')
            plan = data.get('plan', 'trial')
            config = data.get('config', None)
            result = multi_tenant.create_tenant(name, domain, plan, config)
            return self.json_response(result)
        elif self.path == '/api/tenants/update':
            tenant_id = data.get('tenant_id', '')
            config_updates = data.get('config', {})
            result = multi_tenant.update_tenant_config(tenant_id, config_updates)
            return self.json_response(result)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8025)
    args = parser.parse_args()
    server = HTTPServer(('0.0.0.0', args.port), GovHandler)
    print(f'政务API服务启动: http://0.0.0.0:{args.port}')
    print(f'政策库: {len(POLICIES)}条 | 办事指南: {len(GUIDES)}条')
    server.serve_forever()
