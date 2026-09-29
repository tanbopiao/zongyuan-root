#!/usr/bin/env python3
"""
AI模型路由管理模块
策略：免费优先 > 免费额度 > 本地轻量模型 > 付费(需人工审核)
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
元法则：META-RULE-001 免费唯一·额度保护
"""
import json
import os
import datetime

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data/ai_models'
os.makedirs(DATA_DIR, exist_ok=True)

# 模型注册表 - 按优先级排序
MODEL_REGISTRY = {
    # 完全免费模型（优先级最高）
    'zhipu-glm4-flash': {
        'name': '智谱GLM-4-Flash',
        'provider': 'zhipu',
        'type': 'free',  # free/free_quota/local/paid
        'base_url': 'https://open.bigmodel.cn/api/paas/v4',
        'model': 'glm-4-flash',
        'max_tokens': 4096,
        'priority': 1,
        'status': 'active',
        'description': '智谱GLM-4-Flash，永久免费，响应快'
    },
    'agnes-flash': {
        'name': 'Agnes 2.5-Flash',
        'provider': 'agnes',
        'type': 'free',
        'base_url': '',
        'model': 'agnes-2.5-flash',
        'max_tokens': 4096,
        'priority': 2,
        'status': 'active',
        'description': 'Agnes全模态免费模型'
    },
    'qwen2.5-7b-local': {
        'name': 'Qwen2.5-7B-Instruct',
        'provider': 'local',
        'type': 'local',
        'base_url': 'http://127.0.0.1:11434/v1',
        'model': 'qwen2.5:7b',
        'max_tokens': 4096,
        'priority': 3,
        'status': 'available',  # available需要部署
        'description': '本地部署Qwen2.5-7B，数据不出域，需4GB+内存',
        'requirements': 'Ollama + 4GB RAM + 5GB磁盘'
    },
    # 免费额度模型
    'aliyun-qwen-turbo': {
        'name': '通义千问Qwen-Turbo',
        'provider': 'aliyun',
        'type': 'free_quota',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-turbo',
        'max_tokens': 4096,
        'priority': 4,
        'status': 'active',
        'description': '阿里云百炼，免费额度，需配置API Key',
        'quota_warning': 90  # 使用率超过90%告警
    },
    'kimi-k2.6': {
        'name': 'Kimi K2.6',
        'provider': 'kimi',
        'type': 'free_quota',
        'base_url': 'https://api.moonshot.cn/v1',
        'model': 'kimi-k2.6',
        'max_tokens': 8192,
        'priority': 5,
        'status': 'active',
        'description': '月之暗面Kimi，免费额度，长上下文'
    },
    'doubao-seed-1.6': {
        'name': '豆包Seed-1.6',
        'provider': 'doubao',
        'type': 'free_quota',
        'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'model': 'seed-1-6',
        'max_tokens': 4096,
        'priority': 6,
        'status': 'active',
        'description': '字节豆包，免费额度，需配置API Key'
    },
    # 付费模型（禁用，需人工审核）
    'gpt-4': {
        'name': 'GPT-4',
        'provider': 'openai',
        'type': 'paid',
        'priority': 99,
        'status': 'disabled',
        'description': '付费模型，元法则禁用，需人工审核开启'
    }
}

def _load_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

def _save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_available_models():
    """获取可用模型列表（按优先级排序）"""
    models = []
    for mid, m in MODEL_REGISTRY.items():
        if m['status'] in ('active', 'available'):
            models.append({
                'model_id': mid,
                'name': m['name'],
                'type': m['type'],
                'priority': m['priority'],
                'status': m['status'],
                'description': m['description']
            })
    models.sort(key=lambda x: x['priority'])
    return {'models': models, 'total': len(models)}

def get_model_route():
    """获取当前最优模型路由（免费优先）"""
    usage = _load_json('usage.json', {})
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 按优先级遍历，选择第一个可用且未超配额的模型
    for mid, m in sorted(MODEL_REGISTRY.items(), key=lambda x: x[1]['priority']):
        if m['status'] != 'active':
            continue
        
        # 检查免费额度模型的配额
        if m['type'] == 'free_quota':
            model_usage = usage.get(mid, {}).get(today, 0)
            # 假设每天1000次免费额度
            if model_usage >= 1000:
                continue
        
        return {
            'selected_model': mid,
            'model_name': m['name'],
            'type': m['type'],
            'base_url': m.get('base_url', ''),
            'model': m.get('model', ''),
            'reason': f'优先级{m["priority"]}，{m["type"]}模型'
        }
    
    return {'error': '无可用模型', 'code': 503}

def record_model_usage(model_id, tokens=0):
    """记录模型使用量"""
    usage = _load_json('usage.json', {})
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    if model_id not in usage:
        usage[model_id] = {}
    if today not in usage[model_id]:
        usage[model_id][today] = {'calls': 0, 'tokens': 0}
    
    usage[model_id][today]['calls'] += 1
    usage[model_id][today]['tokens'] += tokens
    _save_json('usage.json', usage)
    
    return True

def get_usage_stats():
    """获取模型使用统计"""
    usage = _load_json('usage.json', {})
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    stats = {}
    for mid, daily in usage.items():
        if today in daily:
            stats[mid] = daily[today]
    
    return {
        'date': today,
        'usage': stats,
        'total_models': len(MODEL_REGISTRY),
        'active_models': len([m for m in MODEL_REGISTRY.values() if m['status'] == 'active'])
    }

def get_model_config():
    """获取模型路由配置"""
    return {
        'strategy': 'free_first',  # 免费优先
        'free_models': [mid for mid, m in MODEL_REGISTRY.items() if m['type'] == 'free'],
        'free_quota_models': [mid for mid, m in MODEL_REGISTRY.items() if m['type'] == 'free_quota'],
        'local_models': [mid for mid, m in MODEL_REGISTRY.items() if m['type'] == 'local'],
        'paid_models': [mid for mid, m in MODEL_REGISTRY.items() if m['type'] == 'paid'],
        'paid_enabled': False,  # 元法则：付费禁用
        'quota_threshold': 90,  # 免费额度使用率告警阈值
        'fallback_chain': ['zhipu-glm4-flash', 'agnes-flash', 'qwen2.5-7b-local', 'aliyun-qwen-turbo', 'kimi-k2.6', 'doubao-seed-1.6']
    }

def deploy_local_model_guide():
    """生成本地模型部署指南"""
    return {
        'title': '本地轻量模型部署指南',
        'recommended': 'Qwen2.5-7B-Instruct (Ollama)',
        'requirements': {
            'memory': '4GB RAM (最低2GB可运行1.8B模型)',
            'disk': '5GB',
            'cpu': '2核以上'
        },
        'steps': [
            '1. 安装Ollama: curl -fsSL https://ollama.com/install.sh | sh',
            '2. 拉取模型: ollama pull qwen2.5:7b',
            '3. 启动服务: ollama serve (默认11434端口)',
            '4. 验证: curl http://127.0.0.1:11434/v1/models',
            '5. 在模型路由中启用本地模型'
        ],
        'lightweight_alternative': {
            'model': 'Qwen2.5-1.8B-Instruct',
            'memory': '2GB RAM',
            'command': 'ollama pull qwen2.5:1.8b'
        },
        'note': '当前服务器2GB内存，建议部署1.8B轻量模型，或升级内存后部署7B模型'
    }

# 初始化
if not os.path.exists(os.path.join(DATA_DIR, 'usage.json')):
    _save_json('usage.json', {})
    print('AI模型路由管理初始化完成')
