#!/usr/bin/env python3
"""
自进化引擎V2.0扩展模块
- 答案质量控制（缓存答案质量评分）
- 缓存定期刷新机制（TTL过期自动重新生成）
- 进化策略自动执行范围界定
- 用户满意度反馈循环
"""
import json, os, datetime, hashlib

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data'
QUALITY_FILE = os.path.join(DATA_DIR, 'cache_quality.json')
FEEDBACK_FILE = os.path.join(DATA_DIR, 'user_feedback.json')
STRATEGY_FILE = os.path.join(DATA_DIR, 'evolution_strategy.json')

def _load(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def _save(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============ 答案质量控制 ============
def record_cache_quality(query, answer, quality_score, source='auto'):
    """记录缓存答案的质量评分"""
    data = _load(QUALITY_FILE, {})
    key = hashlib.md5(query.encode()).hexdigest()[:12]
    if key not in data:
        data[key] = {'query': query, 'scores': [], 'avg_score': 0, 'refresh_count': 0, 'last_refresh': None}
    data[key]['scores'].append({
        'score': quality_score,
        'source': source,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    # 只保留最近10次评分
    data[key]['scores'] = data[key]['scores'][-10:]
    data[key]['avg_score'] = sum(s['score'] for s in data[key]['scores']) / len(data[key]['scores'])
    data[key]['last_evaluated'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _save(QUALITY_FILE, data)
    return data[key]

def get_low_quality_caches(threshold=60):
    """获取低质量缓存（需要刷新）"""
    data = _load(QUALITY_FILE, {})
    low_quality = []
    for key, item in data.items():
        if item.get('avg_score', 100) < threshold:
            low_quality.append({
                'key': key,
                'query': item.get('query', ''),
                'avg_score': item.get('avg_score', 0),
                'refresh_count': item.get('refresh_count', 0)
            })
    return sorted(low_quality, key=lambda x: x['avg_score'])

def mark_cache_refreshed(query):
    """标记缓存已刷新"""
    data = _load(QUALITY_FILE, {})
    key = hashlib.md5(query.encode()).hexdigest()[:12]
    if key in data:
        data[key]['refresh_count'] = data[key].get('refresh_count', 0) + 1
        data[key]['last_refresh'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _save(QUALITY_FILE, data)
    return data.get(key)

def get_quality_stats():
    """获取质量控制统计"""
    data = _load(QUALITY_FILE, {})
    if not data:
        return {'total_caches': 0, 'avg_quality': 0, 'low_quality': 0, 'refreshed': 0}
    scores = [item.get('avg_score', 0) for item in data.values()]
    return {
        'total_caches': len(data),
        'avg_quality': round(sum(scores) / len(scores), 1),
        'low_quality': sum(1 for s in scores if s < 60),
        'medium_quality': sum(1 for s in scores if 60 <= s < 80),
        'high_quality': sum(1 for s in scores if s >= 80),
        'total_refreshes': sum(item.get('refresh_count', 0) for item in data.values())
    }

# ============ 用户满意度反馈 ============
def record_feedback(query, feedback_type, comment=''):
    """记录用户反馈（thumbs_up/thumbs_down）"""
    data = _load(FEEDBACK_FILE, [])
    feedback = {
        'id': 'FB-' + hashlib.md5(query + datetime.datetime.now().isoformat()).hexdigest()[:8].upper(),
        'query': query,
        'type': feedback_type,  # thumbs_up / thumbs_down
        'comment': comment,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    data.append(feedback)
    # 只保留最近1000条
    if len(data) > 1000:
        data = data[-1000:]
    _save(FEEDBACK_FILE, data)
    # 如果是差评，自动降低该缓存的质量评分
    if feedback_type == 'thumbs_down':
        record_cache_quality(query, '', 30, source='user_feedback')
    return feedback

def get_feedback_stats():
    """获取反馈统计"""
    data = _load(FEEDBACK_FILE, [])
    thumbs_up = sum(1 for f in data if f.get('type') == 'thumbs_up')
    thumbs_down = sum(1 for f in data if f.get('type') == 'thumbs_down')
    total = len(data)
    satisfaction = round(thumbs_up / total * 100, 1) if total > 0 else 0
    return {
        'total_feedback': total,
        'thumbs_up': thumbs_up,
        'thumbs_down': thumbs_down,
        'satisfaction_rate': satisfaction
    }

# ============ 进化策略自动执行范围界定 ============
DEFAULT_STRATEGY = {
    'version': '2.0',
    'auto_execute_allowed': [
        'high_freq_cache',           # 高频问答自动缓存
        'no_result_search_tracking', # 无结果搜索自动记录
        'daily_report_generation',   # 每日报告自动生成
        'cache_quality_evaluation',  # 缓存质量自动评估
        'low_quality_cache_refresh', # 低质量缓存自动刷新标记
    ],
    'manual_review_required': [
        'knowledge_gap_resolution',  # 知识缺口补充（需人工确认答案）
        'policy_content_update',     # 政策内容更新（需人工审核）
        'guide_content_update',      # 办事指南更新（需人工审核）
        'model_parameter_change',    # 模型参数变更（需人工确认）
        'api_endpoint_change',       # API端点变更（需人工确认）
    ],
    'paid_actions_blocked': [
        'paid_model_calls',          # 付费模型调用（一律禁止）
        'paid_api_calls',            # 付费API调用（一律禁止）
    ],
    'free_models_allowed': [
        'zhipu_glm_4_flash',
        'agnes_2_5_flash',
        'siliconflow_qwen2_5_7b',
        'ollama_local',
    ],
    'quality_threshold': {
        'cache_refresh': 60,         # 低于60分自动标记刷新
        'auto_cache': 80,            # 高于80分才自动缓存
        'warning': 40,               # 低于40分告警
    },
    'last_updated': datetime.datetime.now(datetime.timezone.utc).isoformat()
}

def get_evolution_strategy():
    """获取进化策略配置"""
    data = _load(STRATEGY_FILE, None)
    if data is None:
        _save(STRATEGY_FILE, DEFAULT_STRATEGY)
        return DEFAULT_STRATEGY
    return data

def can_auto_execute(action_type):
    """检查某操作是否可以自动执行"""
    strategy = get_evolution_strategy()
    if action_type in strategy.get('paid_actions_blocked', []):
        return False, '付费操作已被元法则禁止'
    if action_type in strategy.get('auto_execute_allowed', []):
        return True, '自动执行允许'
    if action_type in strategy.get('manual_review_required', []):
        return False, '需要人工审核'
    return False, '未在策略中定义，默认需要人工审核'

def update_evolution_strategy(key, value):
    """更新进化策略配置"""
    strategy = get_evolution_strategy()
    strategy[key] = value
    strategy['last_updated'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _save(STRATEGY_FILE, strategy)
    return strategy

# ============ V2.0综合状态 ============
def get_v2_status():
    """获取V2.0扩展模块综合状态"""
    return {
        'version': '2.0',
        'quality_control': get_quality_stats(),
        'user_feedback': get_feedback_stats(),
        'strategy': {
            'auto_execute_count': len(get_evolution_strategy().get('auto_execute_allowed', [])),
            'manual_review_count': len(get_evolution_strategy().get('manual_review_required', [])),
            'paid_blocked_count': len(get_evolution_strategy().get('paid_actions_blocked', [])),
        }
    }

print('✅ evolution_engine_v2.py 模块创建完成')
print('   - 答案质量控制: record/get_low_quality/mark_refreshed/stats')
print('   - 用户满意度反馈: record/stats')
print('   - 策略范围界定: get_strategy/can_auto_execute/update')
print('   - 综合状态: get_v2_status')
