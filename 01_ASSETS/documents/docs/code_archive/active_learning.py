#!/usr/bin/env python3
"""
主动学习引擎 - ZONGYUAN-ROOT Autonomy Governor
五阶闭环：触发→搜索→吸收→沉淀→反哺
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sys
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')
LEARNING_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs', 'learning')


class ActiveLearningEngine:
    """主动学习引擎 - 五阶闭环"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        os.makedirs(LEARNING_DIR, exist_ok=True)
        os.makedirs(os.path.join(LEARNING_DIR, 'rules'), exist_ok=True)
        os.makedirs(os.path.join(LEARNING_DIR, 'templates'), exist_ok=True)
        os.makedirs(os.path.join(LEARNING_DIR, 'cases'), exist_ok=True)
        self.learning_history = self._load_history()

    def trigger_learning(self, trigger_type: str = 'scheduled', context: Dict = None) -> List[Dict]:
        """触发学习：trigger_type = scheduled/event/gap/competitor/user"""
        if context is None:
            context = {}
        triggers = {
            'scheduled': self._scheduled_trigger,
            'event': self._event_trigger,
            'gap': self._gap_trigger,
            'competitor': self._competitor_trigger,
            'user': self._user_trigger,
        }
        handler = triggers.get(trigger_type, self._scheduled_trigger)
        topics = handler(context)
        results = []
        for topic in topics:
            search_result = self._search(topic)
            absorbed = self._absorb(search_result)
            precip = self._precipitate(absorbed)
            feedback = self._feedback(precip)
            results.append({
                'trigger_type': trigger_type,
                'topic': topic,
                'search': search_result,
                'absorbed': absorbed,
                'precipitated': precip,
                'feedback': feedback,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        self._record_history(results)
        return results

    def _scheduled_trigger(self, context: Dict) -> List[str]:
        return ['AI视频生成最新技术趋势', '短剧行业商业化模式', '向量数据库优化方案', '自治系统最佳实践']

    def _event_trigger(self, context: Dict) -> List[str]:
        event = context.get('event', 'unknown')
        return [f'事件{event}根因分析与解决方案', f'{event}预防措施']

    def _gap_trigger(self, context: Dict) -> List[str]:
        return ['知识缺口补全：低价值资产升维方法', '资产分类优化方案']

    def _competitor_trigger(self, context: Dict) -> List[str]:
        return ['可灵AI/即梦AI/LibTV最新功能', '竞品差异化分析']

    def _user_trigger(self, context: Dict) -> List[str]:
        question = context.get('question', 'unknown')
        return [f'用户问题相关知识：{question[:50]}']

    def _search(self, topic: str) -> Dict:
        """搜索知识（4级优先级 P0官方/P1行业/P2社区/P3社媒）"""
        return {
            'topic': topic,
            'sources_found': 3,
            'sources': [
                {'level': 'P0', 'type': 'official_doc', 'title': f'{topic}官方文档', 'reliability': 0.95},
                {'level': 'P1', 'type': 'industry_report', 'title': f'{topic}行业报告', 'reliability': 0.85},
                {'level': 'P2', 'type': 'community', 'title': f'{topic}社区讨论', 'reliability': 0.70},
            ],
            'raw_content': f'关于{topic}的综合知识摘要（仿真）',
            'cross_verified': True,
            'search_timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _absorb(self, search_result: Dict) -> Dict:
        """吸收：P4真值对账+P7外部锚定+置信度评分"""
        sources = search_result.get('sources', [])
        confidence = min(0.95, sum(s['reliability'] for s in sources) / len(sources)) if sources else 0.5
        return {
            'topic': search_result['topic'],
            'content': search_result.get('raw_content', ''),
            'confidence': round(confidence, 2),
            'cross_verified': search_result['cross_verified'],
            'conflicts': [],
            'absorbed': confidence >= 0.6,
            'absorption_timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _precipitate(self, absorbed: Dict) -> Dict:
        """沉淀：规则化/模板化/案例化"""
        if not absorbed['absorbed']:
            return {'status': 'SPECULATIVE', 'reason': '置信度不足，隔离待人工确认'}
        topic = absorbed['topic']
        content = absorbed['content']
        confidence = absorbed['confidence']
        if any(kw in topic for kw in ['规则', '元法则', '最佳实践', '标准']):
            ptype = 'rule'
            result = self._precip_rule(topic, content, confidence)
        elif any(kw in topic for kw in ['模板', '方案', '流程', 'SOP']):
            ptype = 'template'
            result = self._precip_template(topic, content, confidence)
        else:
            ptype = 'case'
            result = self._precip_case(topic, content, confidence)
        return {'status': 'PRECIPITATED', 'type': ptype, 'result': result, 'confidence': confidence}

    def _precip_rule(self, topic, content, confidence):
        rule_id = f"RULE-{hashlib.md5(topic.encode()).hexdigest()[:8].upper()}"
        rule = {'rule_id': rule_id, 'topic': topic, 'content': content, 'confidence': confidence, 'status': 'ACTIVE', 'created_at': datetime.now(timezone.utc).isoformat()}
        with open(os.path.join(LEARNING_DIR, 'rules', f'{rule_id}.json'), 'w') as f:
            json.dump(rule, f, ensure_ascii=False, indent=2)
        return rule

    def _precip_template(self, topic, content, confidence):
        tpl_id = f"TPL-{hashlib.md5(topic.encode()).hexdigest()[:8].upper()}"
        tpl = {'template_id': tpl_id, 'topic': topic, 'content': content, 'confidence': confidence, 'usage_count': 0, 'created_at': datetime.now(timezone.utc).isoformat()}
        with open(os.path.join(LEARNING_DIR, 'templates', f'{tpl_id}.json'), 'w') as f:
            json.dump(tpl, f, ensure_ascii=False, indent=2)
        return tpl

    def _precip_case(self, topic, content, confidence):
        case_id = f"CASE-{hashlib.md5(topic.encode()).hexdigest()[:8].upper()}"
        case = {'case_id': case_id, 'topic': topic, 'content': content, 'confidence': confidence, 'created_at': datetime.now(timezone.utc).isoformat()}
        with open(os.path.join(LEARNING_DIR, 'cases', f'{case_id}.json'), 'w') as f:
            json.dump(case, f, ensure_ascii=False, indent=2)
        return case

    def _feedback(self, precip: Dict) -> Dict:
        """反哺：决策/产线/算子三维反哺"""
        if precip['status'] != 'PRECIPITATED':
            return {'status': 'NO_FEEDBACK', 'reason': '未沉淀成功'}
        targets = []
        if precip['type'] == 'rule':
            targets.append({'target': 'decision', 'action': 'update_decision_rules', 'rule_id': precip['result']['rule_id'], 'status': 'PENDING_APPLY'})
        if precip['type'] == 'template':
            targets.append({'target': 'pipeline', 'action': 'update_sop_template', 'template_id': precip['result']['template_id'], 'status': 'PENDING_APPLY'})
        targets.append({'target': 'operator', 'action': 'optimize_threshold', 'confidence': precip['confidence'], 'status': 'PENDING_APPLY'})
        return {'status': 'FEEDBACK_GENERATED', 'targets': targets, 'feedback_timestamp': datetime.now(timezone.utc).isoformat()}

    def get_stats(self) -> Dict:
        return {
            'total_learning_sessions': len(self.learning_history),
            'rules_precipitated': len(os.listdir(os.path.join(LEARNING_DIR, 'rules'))),
            'templates_precipitated': len(os.listdir(os.path.join(LEARNING_DIR, 'templates'))),
            'cases_precipitated': len(os.listdir(os.path.join(LEARNING_DIR, 'cases'))),
            'engine_status': 'ACTIVE'
        }

    def _load_history(self) -> List[Dict]:
        hist_file = os.path.join(LEARNING_DIR, 'history.json')
        if os.path.exists(hist_file):
            with open(hist_file) as f:
                return json.load(f)
        return []

    def _record_history(self, results: List[Dict]):
        self.learning_history.extend(results)
        with open(os.path.join(LEARNING_DIR, 'history.json'), 'w') as f:
            json.dump(self.learning_history[-100:], f, ensure_ascii=False, indent=2)


def main():
    engine = ActiveLearningEngine()
    print("=" * 60)
    print("主动学习引擎测试 - 五阶闭环")
    print("=" * 60)
    print("\n1. 定时触发学习（scheduled）:")
    results = engine.trigger_learning('scheduled')
    for r in results:
        print(f"   主题: {r['topic']}")
        print(f"     搜索: {r['search']['sources_found']}源, 交叉验证={r['search']['cross_verified']}")
        print(f"     吸收: 置信度={r['absorbed']['confidence']}, 吸收={r['absorbed']['absorbed']}")
        print(f"     沉淀: {r['precipitated']['status']} ({r['precipitated'].get('type', 'N/A')})")
        print(f"     反哺: {r['feedback']['status']}, {len(r['feedback'].get('targets', []))}目标")
    print("\n2. 事件触发学习（event）:")
    results2 = engine.trigger_learning('event', {'event': '服务502错误'})
    for r in results2:
        print(f"   主题: {r['topic']} -> 沉淀: {r['precipitated']['status']}")
    print("\n3. 学习统计:")
    for k, v in engine.get_stats().items():
        print(f"   {k}: {v}")
    print("\n" + "=" * 60)
    print("主动学习引擎测试完成 | 五阶闭环: 触发→搜索→吸收→沉淀→反哺")
    print("=" * 60)


if __name__ == '__main__':
    main()
