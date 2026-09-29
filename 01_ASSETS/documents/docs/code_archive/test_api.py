"""
API服务集成测试
验证API服务各接口功能正确性
"""
import os
import sys
import json
import time
import unittest
import urllib.request
import urllib.error
import urllib.parse

BASE_URL = "http://127.0.0.1:5000/api/v1"


def _encode_path(path):
    """对URL路径中的中文进行编码，保留query参数格式"""
    if '?' in path:
        path_part, query_part = path.split('?', 1)
        encoded_path = '/'.join(urllib.parse.quote(p, safe='') for p in path_part.split('/'))
        # 编码query参数值
        params = urllib.parse.parse_qs(query_part)
        encoded_query = urllib.parse.urlencode({k: v[0] for k, v in params.items()})
        return f"{encoded_path}?{encoded_query}"
    return '/'.join(urllib.parse.quote(p, safe='') for p in path.split('/'))


def api_get(path):
    """GET请求"""
    try:
        req = urllib.request.Request(f"{BASE_URL}{_encode_path(path)}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"code": -1, "message": str(e), "data": None}


def api_post(path, data=None):
    """POST请求"""
    try:
        body = json.dumps(data or {}).encode('utf-8')
        req = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"code": -1, "message": str(e), "data": None}


class TestAPIService(unittest.TestCase):
    """API服务测试"""

    @classmethod
    def setUpClass(cls):
        """等待API服务就绪"""
        print("等待API服务就绪...")
        for i in range(10):
            result = api_get('/system/health')
            if result.get('code') == 0:
                print("API服务已就绪")
                return
            time.sleep(2)
        raise RuntimeError("API服务未就绪，请先启动 api_server.py")

    def test_01_health_check(self):
        """健康检查"""
        result = api_get('/system/health')
        self.assertEqual(result['code'], 0)
        self.assertEqual(result['data']['status'], 'healthy')
        self.assertIn('version', result['data'])

    def test_02_system_status(self):
        """系统状态"""
        result = api_get('/system/status')
        self.assertEqual(result['code'], 0)
        data = result['data']
        self.assertEqual(data['status'], 'running')
        self.assertIn('modules', data)
        self.assertIn('knowledge_graph', data['modules'])
        self.assertIn('content_engine', data['modules'])
        self.assertIn('adaptive_learning', data['modules'])
        self.assertIn('teacher_training', data['modules'])
        self.assertIn('evolution', data['modules'])

    def test_03_knowledge_stats(self):
        """知识图谱统计"""
        result = api_get('/knowledge/stats')
        self.assertEqual(result['code'], 0)
        data = result['data']
        self.assertGreater(data['total_entities'], 0)
        self.assertGreater(data['total_relations'], 0)
        self.assertEqual(len(data['domain_distribution']), 10)

    def test_04_knowledge_domains(self):
        """知识域列表"""
        result = api_get('/knowledge/domains')
        self.assertEqual(result['code'], 0)
        self.assertEqual(len(result['data']), 10)

    def test_05_knowledge_by_domain(self):
        """按域查询知识点"""
        result = api_get('/knowledge/domains/AI基础理论')
        self.assertEqual(result['code'], 0)
        self.assertGreater(result['data']['count'], 0)
        self.assertEqual(result['data']['domain'], 'AI基础理论')

    def test_06_knowledge_by_stage(self):
        """按学段查询知识点"""
        result = api_get('/knowledge/stages/初中')
        self.assertEqual(result['code'], 0)
        self.assertGreater(result['data']['count'], 0)

    def test_07_knowledge_search(self):
        """搜索知识点"""
        result = api_get('/knowledge/search?q=人工智能')
        self.assertEqual(result['code'], 0)
        self.assertGreater(result['data']['count'], 0)

    def test_08_content_stats(self):
        """内容生产统计"""
        result = api_get('/content/stats')
        self.assertEqual(result['code'], 0)
        self.assertIn('textbooks', result['data'])
        self.assertIn('exercises', result['data'])

    def test_09_generate_textbook(self):
        """生成教材章节"""
        # 先获取一个知识点ID
        kg_result = api_get('/knowledge/domains/AI伦理安全')
        entity_id = kg_result['data']['entities'][0]['id']
        # 生成教材
        result = api_post('/content/textbook', {
            "entity_id": entity_id,
            "stage": "初中"
        })
        self.assertEqual(result['code'], 0)
        self.assertIn('chapter_id', result['data'])
        self.assertIn('sections', result['data'])
        self.assertEqual(len(result['data']['sections']), 5)

    def test_10_generate_exercises(self):
        """生成习题"""
        kg_result = api_get('/knowledge/domains/数据科学')
        entity_id = kg_result['data']['entities'][0]['id']
        result = api_post('/content/exercises', {
            "entity_id": entity_id,
            "stage": "高中",
            "count": 3
        })
        self.assertEqual(result['code'], 0)
        self.assertEqual(result['data']['count'], 3)

    def test_11_batch_generate(self):
        """批量生成内容"""
        result = api_post('/content/batch', {
            "stage": "中职",
            "domains": ["硬件机器人"],
            "max_chapters": 2
        })
        self.assertEqual(result['code'], 0)
        self.assertGreater(result['data']['chapters'], 0)

    def test_12_create_learner(self):
        """创建学习者"""
        result = api_post('/learners', {
            "name": "API测试学生",
            "stage": "高中",
            "grade": "高二"
        })
        self.assertEqual(result['code'], 0)
        self.assertIn('learner_id', result['data'])
        self.assertEqual(result['data']['stage'], '高中')

    def test_13_learner_stats(self):
        """学习者统计"""
        result = api_get('/learners/stats')
        self.assertEqual(result['code'], 0)
        self.assertGreater(result['data']['total_learners'], 0)

    def test_14_create_teacher(self):
        """创建教师"""
        result = api_post('/teachers', {
            "name": "API测试老师",
            "subject": "数学",
            "school_type": "乡村"
        })
        self.assertEqual(result['code'], 0)
        self.assertIn('teacher_id', result['data'])

    def test_15_teacher_stats(self):
        """教师统计"""
        result = api_get('/teachers/stats')
        self.assertEqual(result['code'], 0)
        self.assertGreater(result['data']['total_teachers'], 0)

    def test_16_evaluation_learning(self):
        """学习效果评估"""
        result = api_post('/evaluation/learning-effect')
        self.assertEqual(result['code'], 0)
        self.assertIn('avg_mastery', result['data'])

    def test_17_evaluation_system(self):
        """体系运行评估"""
        result = api_post('/evaluation/system-operation')
        self.assertEqual(result['code'], 0)
        self.assertIn('balanced_index', result['data'])

    def test_18_evolution_status(self):
        """演化状态"""
        result = api_get('/evolution/status')
        self.assertEqual(result['code'], 0)
        self.assertIn('total_cycles', result['data'])
        self.assertEqual(len(result['data']['axioms_active']), 7)

    def test_19_evolution_single_mechanism(self):
        """单机制演化"""
        result = api_post('/evolution/knowledge_update')
        self.assertEqual(result['code'], 0)
        self.assertIn('updated_entities', result['data'])

    def test_20_evolution_full_cycle(self):
        """完整演化周期"""
        result = api_post('/evolution/full-cycle')
        self.assertEqual(result['code'], 0)
        self.assertIn('cycle', result['data'])
        self.assertIn('knowledge_update', result['data'])
        self.assertIn('course_iteration', result['data'])
        self.assertIn('question_bank', result['data'])
        self.assertIn('method_optimization', result['data'])
        self.assertIn('resource_balancing', result['data'])
        self.assertIn('risk_control', result['data'])
        self.assertIn('system_upgrade', result['data'])

    def test_21_archive_root(self):
        """ROOT根库归档"""
        result = api_get('/archive/root')
        self.assertEqual(result['code'], 0)
        self.assertIn('total', result['data'])

    def test_22_archive_export(self):
        """全量数据导出"""
        result = api_get('/archive/export')
        self.assertEqual(result['code'], 0)
        self.assertIn('data_files', result['data'])

    def test_23_invalid_entity(self):
        """无效知识点ID测试"""
        result = api_post('/content/textbook', {
            "entity_id": "INVALID_ID",
            "stage": "初中"
        })
        self.assertNotEqual(result['code'], 0)

    def test_24_invalid_evolution_mechanism(self):
        """无效演化机制测试"""
        result = api_post('/evolution/invalid_mechanism')
        self.assertNotEqual(result['code'], 0)

    def test_25_response_format(self):
        """响应格式统一校验"""
        result = api_get('/system/health')
        self.assertIn('code', result)
        self.assertIn('message', result)
        self.assertIn('data', result)
        self.assertIn('timestamp', result)
        self.assertIn('request_id', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
