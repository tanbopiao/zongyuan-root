#!/usr/bin/env python3
"""
政务中台模型路由优化引擎
- 智能调度：根据任务类型选择最优模型
- 负载均衡：多模型轮询/权重分配
- 降级策略：免费优先，付费需人工审核
- 健康检查：模型可用性监控
"""
import json
import os
import time
from datetime import datetime
from collections import defaultdict

STATS_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data/model_stats'
os.makedirs(STATS_DIR, exist_ok=True)

# 模型矩阵（免费优先）
MODEL_MATRIX = {
    'free': [
        {'id': 'zhipu-glm-4-flash', 'name': '智谱GLM-4-Flash', 'provider': 'zhipu', 'type': 'chat', 'status': 'active', 'weight': 30, 'max_tokens': 4096},
        {'id': 'agnes-2.5-flash', 'name': 'Agnes 2.5-Flash', 'provider': 'agnes', 'type': 'chat', 'status': 'active', 'weight': 25, 'max_tokens': 4096},
        {'id': 'qwen2.5-7b', 'name': 'Qwen2.5-7B', 'provider': 'siliconflow', 'type': 'chat', 'status': 'active', 'weight': 20, 'max_tokens': 8192},
        {'id': 'ollama-local', 'name': 'Ollama本地模型(qwen2.5:0.5b)', 'provider': 'local', 'type': 'chat', 'status': 'active', 'weight': 5, 'max_tokens': 2048, 'endpoint': 'http://127.0.0.1:11434/api/generate', 'model_name': 'qwen2.5:0.5b'},
    ],
    'quota': [
        {'id': 'qwen-turbo', 'name': '通义千问Turbo', 'provider': 'aliyun', 'type': 'chat', 'status': 'active', 'weight': 15, 'max_tokens': 8192, 'quota_limit': 1000000},
        {'id': 'kimi-k2.6', 'name': 'Kimi K2.6', 'provider': 'moonshot', 'type': 'chat', 'status': 'active', 'weight': 10, 'max_tokens': 32768, 'quota_limit': 500000},
        {'id': 'hunyuan', 'name': '混元', 'provider': 'tencent', 'type': 'chat', 'status': 'active', 'weight': 5, 'max_tokens': 8192, 'quota_limit': 500000},
    ],
    'premium': [
        {'id': 'doubao-seed-1-6', 'name': '豆包Seed-1.6', 'provider': 'doubao', 'type': 'chat', 'status': 'standby', 'weight': 0, 'max_tokens': 32768, 'require_approval': True},
        {'id': 'doubao-reasoning', 'name': '豆包推理', 'provider': 'doubao', 'type': 'reasoning', 'status': 'standby', 'weight': 0, 'max_tokens': 65536, 'require_approval': True},
    ]
}

# 任务类型到模型的映射
TASK_MODEL_MAPPING = {
    'chat': {'preferred': ['zhipu-glm-4-flash', 'agnes-2.5-flash', 'qwen2.5-7b'], 'fallback': ['qwen-turbo', 'kimi-k2.6', 'ollama-local']},
    'policy_query': {'preferred': ['zhipu-glm-4-flash', 'qwen2.5-7b'], 'fallback': ['qwen-turbo']},
    'doc_generation': {'preferred': ['agnes-2.5-flash', 'zhipu-glm-4-flash'], 'fallback': ['qwen-turbo', 'hunyuan', 'ollama-local']},
    'doc_polish': {'preferred': ['zhipu-glm-4-flash', 'agnes-2.5-flash'], 'fallback': ['qwen-turbo']},
    'compliance_check': {'preferred': ['qwen2.5-7b', 'zhipu-glm-4-flash'], 'fallback': ['kimi-k2.6']},
    'summarization': {'preferred': ['agnes-2.5-flash', 'zhipu-glm-4-flash'], 'fallback': ['qwen-turbo']},
    'translation': {'preferred': ['zhipu-glm-4-flash', 'qwen2.5-7b'], 'fallback': ['qwen-turbo']},
    'reasoning': {'preferred': ['qwen2.5-7b', 'kimi-k2.6'], 'fallback': ['qwen-turbo'], 'premium': ['doubao-reasoning']},
    'long_context': {'preferred': ['kimi-k2.6', 'qwen-turbo'], 'fallback': ['zhipu-glm-4-flash']},
}

class ModelRouter:
    def __init__(self):
        self.call_stats = defaultdict(int)
        self.error_stats = defaultdict(int)
        self.last_health_check = {}
        self.load_stats()
    
    def load_stats(self):
        """加载统计数据"""
        stats_file = os.path.join(STATS_DIR, 'router_stats.json')
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.call_stats = defaultdict(int, data.get('call_stats', {}))
                    self.error_stats = defaultdict(int, data.get('error_stats', {}))
            except:
                pass
    
    def save_stats(self):
        """保存统计数据"""
        stats_file = os.path.join(STATS_DIR, 'router_stats.json')
        data = {
            'call_stats': dict(self.call_stats),
            'error_stats': dict(self.error_stats),
            'updated_at': datetime.now().isoformat()
        }
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def select_model(self, task_type='chat', prefer_free=True, require_approval=False):
        """智能选择模型"""
        mapping = TASK_MODEL_MAPPING.get(task_type, TASK_MODEL_MAPPING['chat'])
        
        # 优先免费模型
        if prefer_free:
            candidates = mapping.get('preferred', [])
            for model_id in candidates:
                model = self._get_model(model_id)
                if model and model['status'] == 'active':
                    # 检查错误率
                    error_rate = self._get_error_rate(model_id)
                    if error_rate < 0.2:  # 错误率低于20%
                        self.call_stats[model_id] += 1
                        self.save_stats()
                        return {
                            'selected': model,
                            'strategy': 'free_preferred',
                            'reason': f'免费模型，任务类型{task_type}最优匹配'
                        }
        
        # 降级到配额模型
        fallback = mapping.get('fallback', [])
        for model_id in fallback:
            model = self._get_model(model_id)
            if model and model['status'] == 'active':
                error_rate = self._get_error_rate(model_id)
                if error_rate < 0.3:
                    self.call_stats[model_id] += 1
                    self.save_stats()
                    return {
                        'selected': model,
                        'strategy': 'quota_fallback',
                        'reason': f'免费模型不可用，降级到配额模型'
                    }
        
        # 最后兜底
        all_models = [m for models in MODEL_MATRIX.values() for m in models if m['status'] == 'active']
        if all_models:
            model = all_models[0]
            self.call_stats[model['id']] += 1
            self.save_stats()
            return {
                'selected': model,
                'strategy': 'last_resort',
                'reason': '最后兜底模型'
            }
        
        return {'selected': None, 'strategy': 'none', 'reason': '无可用模型'}
    
    def _get_model(self, model_id):
        """获取模型信息"""
        for models in MODEL_MATRIX.values():
            for model in models:
                if model['id'] == model_id:
                    return model
        return None
    
    def _get_error_rate(self, model_id):
        """计算错误率"""
        total = self.call_stats.get(model_id, 0)
        errors = self.error_stats.get(model_id, 0)
        if total == 0:
            return 0
        return errors / total
    
    def report_error(self, model_id):
        """报告模型错误"""
        self.error_stats[model_id] += 1
        self.save_stats()
    
    def health_check(self):
        """模型健康检查"""
        results = []
        for tier, models in MODEL_MATRIX.items():
            for model in models:
                error_rate = self._get_error_rate(model['id'])
                status = 'healthy' if error_rate < 0.2 else ('degraded' if error_rate < 0.5 else 'unhealthy')
                results.append({
                    'model_id': model['id'],
                    'name': model['name'],
                    'tier': tier,
                    'status': model['status'],
                    'health': status,
                    'error_rate': round(error_rate, 4),
                    'total_calls': self.call_stats.get(model['id'], 0),
                    'total_errors': self.error_stats.get(model['id'], 0)
                })
        return results
    
    def get_stats(self):
        """获取路由统计"""
        total_calls = sum(self.call_stats.values())
        total_errors = sum(self.error_stats.values())
        return {
            'total_calls': total_calls,
            'total_errors': total_errors,
            'overall_error_rate': round(total_errors / total_calls, 4) if total_calls > 0 else 0,
            'model_distribution': dict(self.call_stats),
            'health_check': self.health_check(),
            'strategy': '免费优先，付费需人工审核，自动降级'
        }
    
    def get_available_models(self, tier=None):
        """获取可用模型列表"""
        if tier:
            models = MODEL_MATRIX.get(tier, [])
        else:
            models = [m for models in MODEL_MATRIX.values() for m in models]
        return [m for m in models if m['status'] == 'active']

model_router = ModelRouter()

if __name__ == '__main__':
    print('=== 模型路由测试 ===')
    result = model_router.select_model('chat')
    print(f'选择模型: {result["selected"]["name"] if result["selected"] else "无"}')
    print(f'策略: {result["strategy"]}')
    print()
    stats = model_router.get_stats()
    print(f'总调用: {stats["total_calls"]}')
    print(f'可用模型: {len(model_router.get_available_models())}个')
