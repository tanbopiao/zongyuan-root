#!/usr/bin/env python3
"""
政务中台数据聚合与可视化API V1.0
提供政务大数据统计、趋势分析、分类分布等数据
"""
import json
import os
import datetime
from collections import Counter, defaultdict

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data'

def read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

def get_dashboard_stats():
    """获取仪表盘核心指标"""
    consultations = read_json(os.path.join(DATA_DIR, 'consultations.json'), [])
    appointments = read_json(os.path.join(DATA_DIR, 'appointments.json'), [])
    doc_history = read_json(os.path.join(DATA_DIR, 'doc_history.json'), [])
    user_actions = read_json(os.path.join(DATA_DIR, 'user_actions.json'), [])
    approvals = read_json(os.path.join(DATA_DIR, 'approvals.json'), [])
    policies = read_json(os.path.join(DATA_DIR, 'policies.json'), [])
    guides = read_json(os.path.join(DATA_DIR, 'guides.json'), [])

    # 今日数据
    today = datetime.date.today().isoformat()
    today_consult = sum(1 for c in consultations if today in str(c.get('created_at', '')))
    today_appt = sum(1 for a in appointments if today in str(a.get('created_at', '')))
    today_doc = sum(1 for d in doc_history if today in str(d.get('created_at', '')))

    # 预约状态分布
    appt_status = Counter(a.get('status', 'pending') for a in appointments)

    # 咨询分类分布
    consult_cats = Counter(c.get('category', '其他') for c in consultations)

    return {
        'overview': {
            'total_consultations': len(consultations),
            'today_consultations': today_consult,
            'total_appointments': len(appointments),
            'today_appointments': today_appt,
            'total_documents': len(doc_history),
            'today_documents': today_doc,
            'total_policies': len(policies),
            'total_guides': len(guides),
            'total_approvals': len(approvals),
            'total_user_actions': len(user_actions),
            'pending_approvals': sum(1 for a in approvals if a.get('status') == 'pending'),
        },
        'appointment_status': dict(appt_status),
        'consultation_categories': dict(consult_cats.most_common(10)),
    }

def get_trend_data(days=7):
    """获取趋势数据（最近N天）"""
    consultations = read_json(os.path.join(DATA_DIR, 'consultations.json'), [])
    appointments = read_json(os.path.join(DATA_DIR, 'appointments.json'), [])
    doc_history = read_json(os.path.join(DATA_DIR, 'doc_history.json'), [])
    user_actions = read_json(os.path.join(DATA_DIR, 'user_actions.json'), [])

    today = datetime.date.today()
    dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(days-1, -1, -1)]

    def count_by_date(items, date_field='created_at'):
        counts = defaultdict(int)
        for item in items:
            dt = str(item.get(date_field, ''))[:10]
            if dt in dates:
                counts[dt] += 1
        return [counts.get(d, 0) for d in dates]

    return {
        'dates': dates,
        'consultations': count_by_date(consultations),
        'appointments': count_by_date(appointments),
        'documents': count_by_date(doc_history),
        'user_actions': count_by_date(user_actions, 'timestamp'),
    }

def get_policy_hotness():
    """政策热度排行"""
    policies = read_json(os.path.join(DATA_DIR, 'policies.json'), [])
    user_actions = read_json(os.path.join(DATA_DIR, 'user_actions.json'), [])

    # 统计政策浏览/收藏
    policy_views = Counter()
    policy_favs = Counter()
    for action in user_actions:
        if action.get('action_type') == 'policy_view':
            policy_views[action.get('target_id', '')] += 1
        elif action.get('action_type') == 'policy_favorite':
            policy_favs[action.get('target_id', '')] += 1

    # 合并政策信息
    hot_list = []
    for p in policies[:20]:
        pid = p.get('id', '')
        views = policy_views.get(pid, 0)
        favs = policy_favs.get(pid, 0)
        hot_list.append({
            'id': pid,
            'title': p.get('title', ''),
            'category': p.get('category', ''),
            'views': views,
            'favorites': favs,
            'hot_score': views * 2 + favs * 5,
        })
    hot_list.sort(key=lambda x: x['hot_score'], reverse=True)
    return {'top_policies': hot_list[:10], 'total': len(hot_list)}

def get_evolution_stats():
    """自进化效果统计"""
    evolution_data = read_json(os.path.join(DATA_DIR, 'evolution_cache.json'), {'cache': {}, 'knowledge_gaps': []})
    cache = evolution_data.get('cache', {})
    gaps = evolution_data.get('knowledge_gaps', [])

    # 缓存命中率（模拟：缓存条目数/总查询数）
    total_queries = sum(v.get('count', 0) for v in cache.values())
    cached_queries = sum(v.get('count', 0) for v in cache.values() if v.get('count', 0) >= 5)
    hit_rate = round(cached_queries / max(total_queries, 1) * 100, 1)

    return {
        'cache_entries': len(cache),
        'total_cached_queries': total_queries,
        'cache_hit_rate': hit_rate,
        'knowledge_gaps': len(gaps),
        'top_gaps': sorted(gaps, key=lambda x: x.get('count', 0), reverse=True)[:5],
        'auto_optimizations': len(cache),
    }

def get_operator_stats():
    """算子调用统计"""
    operator_logs = read_json(os.path.join(DATA_DIR, 'operator_logs.json'), [])
    if isinstance(operator_logs, dict):
        operator_logs = operator_logs.get('logs', [])

    op_counts = Counter(log.get('operator_id', 'unknown') for log in operator_logs)
    op_success = Counter(log.get('operator_id', 'unknown') for log in operator_logs if log.get('success'))

    stats = []
    for op_id, count in op_counts.most_common(17):
        success = op_success.get(op_id, 0)
        stats.append({
            'operator_id': op_id,
            'calls': count,
            'success': success,
            'success_rate': round(success / max(count, 1) * 100, 1),
        })

    return {
        'total_calls': len(operator_logs),
        'total_operators': len(op_counts),
        'top_operators': stats[:10],
        'overall_success_rate': round(sum(op_success.values()) / max(len(operator_logs), 1) * 100, 1),
    }

def get_user_activity():
    """用户活跃度统计"""
    user_actions = read_json(os.path.join(DATA_DIR, 'user_actions.json'), [])

    # 按动作类型统计
    action_types = Counter(a.get('action_type', 'unknown') for a in user_actions)

    # 按小时分布
    hour_dist = defaultdict(int)
    for a in user_actions:
        ts = str(a.get('timestamp', ''))
        if 'T' in ts:
            hour = ts.split('T')[1][:2]
            hour_dist[hour] += 1

    return {
        'total_actions': len(user_actions),
        'action_types': dict(action_types.most_common(10)),
        'hour_distribution': {h: hour_dist.get(f'{h:02d}', 0) for h in range(24)},
        'active_users': len(set(a.get('user_id', '') for a in user_actions)),
    }

def get_category_distribution():
    """政策/指南分类分布"""
    policies = read_json(os.path.join(DATA_DIR, 'policies.json'), [])
    guides = read_json(os.path.join(DATA_DIR, 'guides.json'), [])

    policy_cats = Counter(p.get('category', '其他') for p in policies)
    guide_cats = Counter(g.get('category', '其他') for g in guides)

    return {
        'policy_categories': dict(policy_cats.most_common()),
        'guide_categories': dict(guide_cats.most_common()),
    }

def export_report(format='json'):
    """导出数据报告"""
    data = {
        'generated_at': datetime.datetime.now().isoformat(),
        'dashboard': get_dashboard_stats(),
        'trend': get_trend_data(7),
        'policy_hotness': get_policy_hotness(),
        'evolution': get_evolution_stats(),
        'operators': get_operator_stats(),
        'user_activity': get_user_activity(),
    }
    return data

if __name__ == '__main__':
    print('=== 政务大数据看板 ===')
    stats = get_dashboard_stats()
    print(json.dumps(stats['overview'], ensure_ascii=False, indent=2))
    print('\n=== 7日趋势 ===')
    trend = get_trend_data(7)
    print('日期:', trend['dates'])
    print('咨询:', trend['consultations'])
    print('预约:', trend['appointments'])
