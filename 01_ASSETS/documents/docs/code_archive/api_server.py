"""
本源智能普惠教育体系 API 服务 V1.1
RESTful API 服务层，将六大引擎能力暴露为HTTP接口
"""
import os
import sys
import json
import time
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS

# 项目路径（api_server.py在src/下，项目根目录是上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.settings import SYSTEM_NAME, SYSTEM_VERSION, DID, ANCHOR, ROOT_HASH, DATA_DIR
from src.main import AutoEduSystem
from src.autonomy_orchestrator import EternalAutonomyOrchestrator

# 创建Flask应用
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 全局系统实例
_system = None
_autonomy = None
_start_time = datetime.now()
_request_count = 0


def get_system():
    """获取或初始化系统实例（单例）"""
    global _system, _autonomy
    if _system is None:
        print("[API] 正在初始化本源智能普惠教育系统...")
        _system = AutoEduSystem()
        _system.initialize_demo_data()
        _system.deploy()
        # 初始化永恒自治调度器并绑定系统
        _autonomy = EternalAutonomyOrchestrator()
        _autonomy.bind_system(_system)
        print("[API] 系统初始化完成，状态：running，永恒自治调度器已就绪")
    return _system


def get_autonomy():
    """获取自治调度器实例"""
    get_system()  # 确保已初始化
    return _autonomy


def api_response(code=0, message="success", data=None, **kwargs):
    """统一API响应格式"""
    resp = {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        "request_id": str(uuid.uuid4())[:8]
    }
    resp.update(kwargs)
    return jsonify(resp)


def require_system(f):
    """装饰器：确保系统已初始化"""
    @wraps(f)
    def decorated(*args, **kwargs):
        global _request_count
        _request_count += 1
        try:
            sys_obj = get_system()
            return f(sys_obj, *args, **kwargs)
        except Exception as e:
            return api_response(code=50001, message=f"系统内部错误: {str(e)}", data=None), 500
    return decorated


# ============================================================
# 一、系统状态接口
# ============================================================

@app.route('/api/v1/system/status', methods=['GET'])
@require_system
def system_status(sys_obj):
    """获取系统状态"""
    status = sys_obj.get_system_status()
    status['api_request_count'] = _request_count
    status['api_uptime'] = str(datetime.now() - _start_time)
    return api_response(data=status)


@app.route('/api/v1/system/health', methods=['GET'])
def health_check():
    """健康检查"""
    return api_response(data={
        "status": "healthy",
        "service": "auto-edu-api",
        "version": SYSTEM_VERSION,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/v1/system/evolve', methods=['POST'])
@require_system
def trigger_evolve(sys_obj):
    """触发自治演化周期"""
    body = request.get_json(silent=True) or {}
    cycles = body.get('cycles', 1)
    results = []
    for _ in range(min(cycles, 5)):
        results.append(sys_obj.evolution.run_full_evolution_cycle())
    return api_response(data={"cycles_run": len(results), "results": results})


# ============================================================
# 二、知识图谱接口
# ============================================================

@app.route('/api/v1/knowledge/stats', methods=['GET'])
@require_system
def knowledge_stats(sys_obj):
    """获取图谱统计"""
    return api_response(data=sys_obj.kg.get_graph_stats())


@app.route('/api/v1/knowledge/domains', methods=['GET'])
@require_system
def knowledge_domains(sys_obj):
    """获取所有知识域及其实体数"""
    stats = sys_obj.kg.get_graph_stats()
    return api_response(data=stats["domain_distribution"])


@app.route('/api/v1/knowledge/domains/<domain>', methods=['GET'])
@require_system
def knowledge_by_domain(sys_obj, domain):
    """按域获取知识点"""
    stage = request.args.get('stage')
    entities = sys_obj.kg.get_knowledge_by_domain(domain)
    if stage:
        entities = [e for e in entities if stage in e.get('stages', [])]
    return api_response(data={
        "domain": domain,
        "count": len(entities),
        "entities": entities
    })


@app.route('/api/v1/knowledge/stages/<stage>', methods=['GET'])
@require_system
def knowledge_by_stage(sys_obj, stage):
    """按学段获取知识点"""
    entities = sys_obj.kg.get_knowledge_by_stage(stage)
    return api_response(data={
        "stage": stage,
        "count": len(entities),
        "entities": entities
    })


@app.route('/api/v1/knowledge/entities/<entity_id>', methods=['GET'])
@require_system
def knowledge_entity_detail(sys_obj, entity_id):
    """获取知识点详情"""
    entity = sys_obj.kg.entities.get(entity_id)
    if not entity:
        return api_response(code=40401, message="知识点不存在", data=None), 404
    prereqs = sys_obj.kg.get_prerequisites(entity_id)
    return api_response(data={
        "entity": entity,
        "prerequisites": prereqs
    })


@app.route('/api/v1/knowledge/search', methods=['GET'])
@require_system
def knowledge_search(sys_obj):
    """搜索知识点"""
    q = request.args.get('q', '').strip()
    if not q:
        return api_response(code=40001, message="搜索关键词不能为空", data=None), 400
    results = []
    for eid, ent in sys_obj.kg.entities.items():
        if q.lower() in ent['name'].lower() or q.lower() in ent.get('domain', '').lower():
            results.append(ent)
    return api_response(data={"query": q, "count": len(results), "results": results[:20]})


@app.route('/api/v1/knowledge/update', methods=['POST'])
@require_system
def knowledge_update(sys_obj):
    """触发知识图谱更新"""
    body = request.get_json(silent=True) or {}
    new_knowledge = body.get('new_knowledge')
    updated = sys_obj.kg.auto_update(new_knowledge)
    new_relations = sys_obj.kg.link_prediction()
    return api_response(data={
        "updated_entities": updated,
        "new_relations": new_relations,
        "total_entities": len(sys_obj.kg.entities),
        "total_relations": len(sys_obj.kg.relations)
    })


# ============================================================
# 三、内容生产接口
# ============================================================

@app.route('/api/v1/content/textbook', methods=['POST'])
@require_system
def generate_textbook(sys_obj):
    """生成教材章节"""
    body = request.get_json(silent=True) or {}
    entity_id = body.get('entity_id')
    stage = body.get('stage', '初中')
    if not entity_id or entity_id not in sys_obj.kg.entities:
        return api_response(code=40001, message="entity_id无效或不存在", data=None), 400
    entity = sys_obj.kg.entities[entity_id]
    chapter = sys_obj.content.generate_textbook_chapter(entity, stage)
    return api_response(data=chapter)


@app.route('/api/v1/content/lesson-plan', methods=['POST'])
@require_system
def generate_lesson_plan(sys_obj):
    """生成教案"""
    body = request.get_json(silent=True) or {}
    chapter_id = body.get('chapter_id')
    duration = body.get('duration_minutes', 45)
    # 从已生成教材中查找
    chapter = None
    for ch in sys_obj.content.generated_content['textbooks']:
        if ch['chapter_id'] == chapter_id:
            chapter = ch
            break
    if not chapter:
        # 如果找不到，用第一个教材生成
        if sys_obj.content.generated_content['textbooks']:
            chapter = sys_obj.content.generated_content['textbooks'][0]
        else:
            return api_response(code=40401, message="未找到教材章节，请先生成教材", data=None), 404
    lp = sys_obj.content.generate_lesson_plan(chapter, duration)
    return api_response(data=lp)


@app.route('/api/v1/content/exercises', methods=['POST'])
@require_system
def generate_exercises(sys_obj):
    """生成习题"""
    body = request.get_json(silent=True) or {}
    entity_id = body.get('entity_id')
    stage = body.get('stage', '初中')
    count = min(body.get('count', 5), 20)
    if not entity_id or entity_id not in sys_obj.kg.entities:
        return api_response(code=40001, message="entity_id无效或不存在", data=None), 400
    entity = sys_obj.kg.entities[entity_id]
    exercises = sys_obj.content.generate_exercises(entity, stage, count)
    return api_response(data={"count": len(exercises), "exercises": exercises})


@app.route('/api/v1/content/training', methods=['POST'])
@require_system
def generate_training(sys_obj):
    """生成实训模板（中职）"""
    body = request.get_json(silent=True) or {}
    entity_id = body.get('entity_id')
    if not entity_id or entity_id not in sys_obj.kg.entities:
        return api_response(code=40001, message="entity_id无效或不存在", data=None), 400
    entity = sys_obj.kg.entities[entity_id]
    training = sys_obj.content.generate_training_template(entity, '中职')
    return api_response(data=training)


@app.route('/api/v1/content/batch', methods=['POST'])
@require_system
def batch_generate(sys_obj):
    """批量生成教学内容"""
    body = request.get_json(silent=True) or {}
    stage = body.get('stage', '初中')
    domains = body.get('domains', ['AI基础理论', 'AI伦理安全'])
    max_chapters = min(body.get('max_chapters', 6), 20)
    results = sys_obj.content.batch_generate(stage=stage, domains=domains, max_chapters=max_chapters)
    return api_response(data={
        "stage": stage,
        "chapters": len(results['chapters']),
        "lesson_plans": len(results['lesson_plans']),
        "exercises": len(results['exercises']),
        "training": len(results.get('training', [])),
        "results": results
    })


@app.route('/api/v1/content/stats', methods=['GET'])
@require_system
def content_stats(sys_obj):
    """获取内容生产统计"""
    return api_response(data=sys_obj.content.get_stats())


# ============================================================
# 四、自适应学习接口
# ============================================================

@app.route('/api/v1/learners', methods=['POST'])
@require_system
def create_learner(sys_obj):
    """创建学习者"""
    body = request.get_json(silent=True) or {}
    name = body.get('name', '匿名学习者')
    stage = body.get('stage', '初中')
    grade = body.get('grade', '初一')
    learner = sys_obj.adaptive.create_learner(name, stage, grade)
    return api_response(data=learner.to_dict())


@app.route('/api/v1/learners/<learner_id>', methods=['GET'])
@require_system
def get_learner(sys_obj, learner_id):
    """获取学习者画像"""
    learner = sys_obj.adaptive.learners.get(learner_id)
    if not learner:
        return api_response(code=40401, message="学习者不存在", data=None), 404
    return api_response(data=learner.to_dict())


@app.route('/api/v1/learners/<learner_id>/placement-test', methods=['POST'])
@require_system
def placement_test(sys_obj, learner_id):
    """生成入学测评"""
    if learner_id not in sys_obj.adaptive.learners:
        return api_response(code=40401, message="学习者不存在", data=None), 404
    body = request.get_json(silent=True) or {}
    num = min(body.get('num_questions', 10), 30)
    test = sys_obj.adaptive.generate_placement_test(learner_id, num)
    return api_response(data=test)


@app.route('/api/v1/learners/<learner_id>/test-result', methods=['POST'])
@require_system
def submit_test_result(sys_obj, learner_id):
    """提交测评结果"""
    if learner_id not in sys_obj.adaptive.learners:
        return api_response(code=40401, message="学习者不存在", data=None), 404
    body = request.get_json(silent=True) or {}
    test_id = body.get('test_id')
    answers = body.get('answers', [])
    result = sys_obj.adaptive.submit_test_result(learner_id, test_id, answers)
    return api_response(data=result)


@app.route('/api/v1/learners/<learner_id>/learning-path', methods=['GET'])
@require_system
def learning_path(sys_obj, learner_id):
    """生成个性化学习路径"""
    if learner_id not in sys_obj.adaptive.learners:
        return api_response(code=40401, message="学习者不存在", data=None), 404
    path = sys_obj.adaptive.generate_learning_path(learner_id)
    return api_response(data={"count": len(path), "path": path})


@app.route('/api/v1/learners/<learner_id>/recommendations', methods=['GET'])
@require_system
def recommendations(sys_obj, learner_id):
    """推荐学习内容"""
    if learner_id not in sys_obj.adaptive.learners:
        return api_response(code=40401, message="学习者不存在", data=None), 404
    recs = sys_obj.adaptive.recommend_content(learner_id, sys_obj.content)
    return api_response(data={"count": len(recs), "recommendations": recs})


@app.route('/api/v1/learners/<learner_id>/activity', methods=['POST'])
@require_system
def record_activity(sys_obj, learner_id):
    """记录学习活动"""
    if learner_id not in sys_obj.adaptive.learners:
        return api_response(code=40401, message="学习者不存在", data=None), 404
    body = request.get_json(silent=True) or {}
    kp_id = body.get('kp_id')
    activity_type = body.get('activity_type', '视频学习')
    duration = body.get('duration_minutes', 20)
    score = body.get('score')
    if not kp_id:
        return api_response(code=40001, message="kp_id不能为空", data=None), 400
    result = sys_obj.adaptive.record_learning_activity(learner_id, kp_id, activity_type, duration, score)
    return api_response(data={"success": result})


@app.route('/api/v1/learners/<learner_id>/report', methods=['GET'])
@require_system
def learner_report(sys_obj, learner_id):
    """生成学习报告"""
    if learner_id not in sys_obj.adaptive.learners:
        return api_response(code=40401, message="学习者不存在", data=None), 404
    report = sys_obj.adaptive.generate_learning_report(learner_id)
    return api_response(data=report)


@app.route('/api/v1/learners/stats', methods=['GET'])
@require_system
def learner_stats(sys_obj):
    """获取学习者群体统计"""
    return api_response(data=sys_obj.adaptive.get_class_stats())


# ============================================================
# 五、师资培育接口
# ============================================================

@app.route('/api/v1/teachers', methods=['POST'])
@require_system
def create_teacher(sys_obj):
    """创建教师"""
    body = request.get_json(silent=True) or {}
    name = body.get('name', '匿名教师')
    subject = body.get('subject', '信息科技')
    school_type = body.get('school_type', '城区')
    teacher = sys_obj.teachers.create_teacher(name, subject, school_type)
    return api_response(data=teacher.to_dict())


@app.route('/api/v1/teachers/<teacher_id>', methods=['GET'])
@require_system
def get_teacher(sys_obj, teacher_id):
    """获取教师画像"""
    teacher = sys_obj.teachers.teachers.get(teacher_id)
    if not teacher:
        return api_response(code=40401, message="教师不存在", data=None), 404
    return api_response(data=teacher.to_dict())


@app.route('/api/v1/teachers/<teacher_id>/training-path', methods=['GET'])
@require_system
def teacher_training_path(sys_obj, teacher_id):
    """生成培训路径"""
    if teacher_id not in sys_obj.teachers.teachers:
        return api_response(code=40401, message="教师不存在", data=None), 404
    path = sys_obj.teachers.generate_training_path(teacher_id)
    return api_response(data=path)


@app.route('/api/v1/teachers/<teacher_id>/complete-training', methods=['POST'])
@require_system
def complete_training(sys_obj, teacher_id):
    """完成培训课程"""
    if teacher_id not in sys_obj.teachers.teachers:
        return api_response(code=40401, message="教师不存在", data=None), 404
    body = request.get_json(silent=True) or {}
    course = body.get('course')
    score = body.get('score', 80)
    if not course:
        return api_response(code=40001, message="course不能为空", data=None), 400
    record = sys_obj.teachers.complete_training(teacher_id, course, score)
    return api_response(data=record)


@app.route('/api/v1/teachers/stats', methods=['GET'])
@require_system
def teacher_stats(sys_obj):
    """获取教师培训统计"""
    return api_response(data=sys_obj.teachers.get_training_stats())


# ============================================================
# 六、评估反馈接口
# ============================================================

@app.route('/api/v1/evaluation/learning-effect', methods=['POST'])
@require_system
def eval_learning_effect(sys_obj):
    """学习效果评估"""
    body = request.get_json(silent=True) or {}
    learner_ids = body.get('learner_ids')
    result = sys_obj.evaluation.evaluate_learning_effect(learner_ids)
    return api_response(data=result)


@app.route('/api/v1/evaluation/content-quality', methods=['POST'])
@require_system
def eval_content_quality(sys_obj):
    """内容质量评估"""
    body = request.get_json(silent=True) or {}
    content_items = body.get('content_items')
    result = sys_obj.evaluation.evaluate_content_quality(content_items)
    return api_response(data={"count": len(result), "results": result})


@app.route('/api/v1/evaluation/system-operation', methods=['POST'])
@require_system
def eval_system_operation(sys_obj):
    """体系运行评估"""
    result = sys_obj.evaluation.evaluate_system_operation()
    return api_response(data=result)


@app.route('/api/v1/evaluation/improvement-plan', methods=['POST'])
@require_system
def improvement_plan(sys_obj):
    """生成改进方案"""
    plans = sys_obj.evaluation.generate_improvement_plan()
    return api_response(data={"count": len(plans), "plans": plans})


@app.route('/api/v1/evaluation/summary', methods=['GET'])
@require_system
def eval_summary(sys_obj):
    """获取评估总览"""
    return api_response(data=sys_obj.evaluation.get_evaluation_summary())


# ============================================================
# 七、演化引擎接口
# ============================================================

@app.route('/api/v1/evolution/status', methods=['GET'])
@require_system
def evolution_status(sys_obj):
    """获取演化状态"""
    return api_response(data=sys_obj.evolution.get_evolution_status())


@app.route('/api/v1/evolution/full-cycle', methods=['POST'])
@require_system
def evolution_full_cycle(sys_obj):
    """运行完整演化周期"""
    result = sys_obj.evolution.run_full_evolution_cycle()
    return api_response(data=result)


@app.route('/api/v1/evolution/<mechanism>', methods=['POST'])
@require_system
def evolution_single(sys_obj, mechanism):
    """触发单机制演化"""
    mechanism_map = {
        'knowledge_update': 'evolve_knowledge_update',
        'course_iteration': 'evolve_course_iteration',
        'question_bank': 'evolve_question_bank_expansion',
        'method_optimization': 'evolve_method_optimization',
        'resource_balancing': 'evolve_resource_balancing',
        'risk_control': 'evolve_risk_control',
        'system_upgrade': 'evolve_system_upgrade'
    }
    method = mechanism_map.get(mechanism)
    if not method:
        return api_response(code=40001, message=f"未知演化机制: {mechanism}，可用: {list(mechanism_map.keys())}", data=None), 400
    result = getattr(sys_obj.evolution, method)()
    return api_response(data=result)


# ============================================================
# 八、归档确权接口
# ============================================================

@app.route('/api/v1/archive/root', methods=['GET'])
@require_system
def archive_root_list(sys_obj):
    """获取ROOT根库归档列表"""
    archive_path = os.path.join(DATA_DIR, 'root_archive.json')
    if os.path.exists(archive_path):
        with open(archive_path, 'r', encoding='utf-8') as f:
            archives = json.load(f)
        return api_response(data={
            "total": len(archives),
            "types": list(set(a.get('asset_type', 'unknown') for a in archives)),
            "recent": archives[-10:]
        })
    return api_response(data={"total": 0, "types": [], "recent": []})


@app.route('/api/v1/archive/export', methods=['GET'])
@require_system
def archive_export(sys_obj):
    """导出全量数据清单"""
    data_files = {}
    for fname in os.listdir(DATA_DIR):
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.isfile(fpath):
            data_files[fname] = {
                "size_bytes": os.path.getsize(fpath),
                "modified": datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()
            }
    return api_response(data={
        "system": SYSTEM_NAME,
        "version": SYSTEM_VERSION,
        "did": DID,
        "data_files": data_files
    })


# ============================================================
# 九、知识图谱扩展接口
# ============================================================

@app.route('/api/v1/kg/entity/<entity_id>', methods=['GET', 'PUT', 'DELETE'])
@require_system
def kg_entity_detail(sys_obj, entity_id):
    """知识图谱实体详情/更新/删除"""
    if request.method == 'GET':
        entity = sys_obj.kg.get_entity_by_id(entity_id)
        if not entity:
            return api_response(code=404, message="实体不存在"), 404
        relations = sys_obj.kg.get_relations_for_entity(entity_id)
        return api_response(data={"entity": entity, "relations": relations})
    elif request.method == 'PUT':
        body = request.get_json(silent=True) or {}
        result = sys_obj.kg.update_entity(entity_id, **body)
        return api_response(data={"updated": result})
    else:
        result = sys_obj.kg.delete_entity(entity_id)
        return api_response(data={"deleted": result})

@app.route('/api/v1/kg/search', methods=['GET'])
@require_system
def kg_search(sys_obj):
    """知识图谱实体搜索"""
    keyword = request.args.get('keyword', '')
    domain = request.args.get('domain')
    stage = request.args.get('stage')
    limit = int(request.args.get('limit', 20))
    results = sys_obj.kg.search_entities(keyword, domain, stage, limit)
    return api_response(data={"count": len(results), "results": results})

@app.route('/api/v1/kg/domains', methods=['GET'])
@require_system
def kg_domains(sys_obj):
    """获取知识域列表"""
    return api_response(data=sys_obj.kg.get_domains())

@app.route('/api/v1/kg/export', methods=['GET'])
@require_system
def kg_export(sys_obj):
    """导出图谱（可视化格式）"""
    return api_response(data=sys_obj.kg.export_graph())

@app.route('/api/v1/kg/stage-stats', methods=['GET'])
@require_system
def kg_stage_stats(sys_obj):
    """按学段统计实体数"""
    return api_response(data=sys_obj.kg.get_entity_count_by_stage())


# ============================================================
# 十、内容引擎扩展接口
# ============================================================

@app.route('/api/v1/content/<content_id>', methods=['GET', 'PUT', 'DELETE'])
@require_system
def content_detail(sys_obj, content_id):
    """内容详情/更新/删除"""
    if request.method == 'GET':
        found = sys_obj.content.get_content_by_id(content_id)
        if not found:
            return api_response(code=404, message="内容不存在"), 404
        return api_response(data=found)
    elif request.method == 'PUT':
        body = request.get_json(silent=True) or {}
        result = sys_obj.content.update_content(content_id, **body)
        return api_response(data={"updated": result})
    else:
        result = sys_obj.content.delete_content(content_id)
        return api_response(data={"deleted": result})

@app.route('/api/v1/content/search', methods=['GET'])
@require_system
def content_search(sys_obj):
    """内容搜索"""
    keyword = request.args.get('keyword', '')
    content_type = request.args.get('type')
    limit = int(request.args.get('limit', 20))
    results = sys_obj.content.search_content(keyword, content_type, limit)
    return api_response(data={"count": len(results), "results": results})

@app.route('/api/v1/content/by-stage/<stage>', methods=['GET'])
@require_system
def content_by_stage(sys_obj, stage):
    """按学段查询内容"""
    return api_response(data=sys_obj.content.get_content_by_stage(stage))

@app.route('/api/v1/content/<content_id>/review', methods=['POST'])
@require_system
def content_review(sys_obj, content_id):
    """内容审核"""
    body = request.get_json(silent=True) or {}
    result = sys_obj.content.review_content(
        content_id,
        reviewer=body.get('reviewer', 'admin'),
        approved=body.get('approved', True),
        comment=body.get('comment', '')
    )
    return api_response(data={"reviewed": result})

@app.route('/api/v1/content/pending-reviews', methods=['GET'])
@require_system
def content_pending_reviews(sys_obj):
    """获取待审核内容"""
    pending = sys_obj.content.get_pending_reviews()
    return api_response(data={"count": len(pending), "items": pending})

@app.route('/api/v1/content/<content_id>/quality', methods=['GET'])
@require_system
def content_quality(sys_obj, content_id):
    """内容质量评分"""
    score = sys_obj.content.rate_content_quality(content_id)
    return api_response(data={"content_id": content_id, "quality_score": score})

@app.route('/api/v1/content/stats-detail', methods=['GET'])
@require_system
def content_stats_detail(sys_obj):
    """详细内容统计"""
    return api_response(data=sys_obj.content.get_content_stats_detail())


# ============================================================
# 十一、自适应学习扩展接口
# ============================================================

@app.route('/api/v1/learning/learner/<learner_id>', methods=['GET', 'PUT', 'DELETE'])
@require_system
def learner_detail(sys_obj, learner_id):
    """学习者详情/更新/删除"""
    if request.method == 'GET':
        learner = sys_obj.adaptive.get_learner_by_id(learner_id)
        if not learner:
            return api_response(code=404, message="学习者不存在"), 404
        return api_response(data=learner)
    elif request.method == 'PUT':
        body = request.get_json(silent=True) or {}
        result = sys_obj.adaptive.update_learner(learner_id, **body)
        return api_response(data={"updated": result})
    else:
        result = sys_obj.adaptive.delete_learner(learner_id)
        return api_response(data={"deleted": result})

@app.route('/api/v1/learning/learner/<learner_id>/history', methods=['GET'])
@require_system
def learner_history(sys_obj, learner_id):
    """学习者学习历史"""
    limit = int(request.args.get('limit', 50))
    history = sys_obj.adaptive.get_learning_history(learner_id, limit)
    return api_response(data={"count": len(history), "history": history})

@app.route('/api/v1/learning/learner/<learner_id>/mastery', methods=['GET'])
@require_system
def learner_mastery(sys_obj, learner_id):
    """学习者掌握度概览"""
    overview = sys_obj.adaptive.get_learner_mastery_overview(learner_id)
    if not overview:
        return api_response(code=404, message="学习者不存在"), 404
    return api_response(data=overview)

@app.route('/api/v1/learning/learner/<learner_id>/weak-practice', methods=['GET'])
@require_system
def learner_weak_practice(sys_obj, learner_id):
    """薄弱点专项练习"""
    count = int(request.args.get('count', 5))
    practices = sys_obj.adaptive.generate_weak_point_practice(learner_id, count)
    return api_response(data={"count": len(practices), "practices": practices})

@app.route('/api/v1/learning/ranking', methods=['GET'])
@require_system
def learning_ranking(sys_obj):
    """学习者排名"""
    by = request.args.get('by', 'avg_mastery')
    limit = int(request.args.get('limit', 10))
    ranking = sys_obj.adaptive.get_learners_ranking(by, limit)
    return api_response(data={"count": len(ranking), "ranking": ranking})

@app.route('/api/v1/learning/by-stage/<stage>', methods=['GET'])
@require_system
def learners_by_stage(sys_obj, stage):
    """按学段查询学习者"""
    return api_response(data=sys_obj.adaptive.get_learners_by_stage(stage))


# ============================================================
# 十二、师资培育扩展接口
# ============================================================

@app.route('/api/v1/teacher/<teacher_id>', methods=['GET', 'PUT', 'DELETE'])
@require_system
def teacher_detail(sys_obj, teacher_id):
    """教师详情/更新/删除"""
    if request.method == 'GET':
        teacher = sys_obj.teachers.get_teacher_by_id(teacher_id)
        if not teacher:
            return api_response(code=404, message="教师不存在"), 404
        return api_response(data=teacher)
    elif request.method == 'PUT':
        body = request.get_json(silent=True) or {}
        result = sys_obj.teachers.update_teacher(teacher_id, **body)
        return api_response(data={"updated": result})
    else:
        result = sys_obj.teachers.delete_teacher(teacher_id)
        return api_response(data={"deleted": result})

@app.route('/api/v1/teacher/courses', methods=['GET', 'POST'])
@require_system
def teacher_courses(sys_obj):
    """培训课程库查询/添加"""
    if request.method == 'GET':
        return api_response(data=sys_obj.teachers.get_training_courses())
    else:
        body = request.get_json(silent=True) or {}
        course = sys_obj.teachers.add_training_course(
            name=body.get('name', ''),
            level=body.get('level', '入门级'),
            subject=body.get('subject', ''),
            duration_hours=body.get('duration_hours', 4),
            description=body.get('description', '')
        )
        return api_response(data=course)

@app.route('/api/v1/teacher/research-groups', methods=['GET'])
@require_system
def teacher_research_groups(sys_obj):
    """教研小组列表"""
    return api_response(data=sys_obj.teachers.get_research_groups())

@app.route('/api/v1/teacher/cases', methods=['GET'])
@require_system
def teacher_cases(sys_obj):
    """教学案例库"""
    teacher_id = request.args.get('teacher_id')
    subject = request.args.get('subject')
    limit = int(request.args.get('limit', 20))
    cases = sys_obj.teachers.get_teaching_cases(teacher_id, subject, limit)
    return api_response(data={"count": len(cases), "cases": cases})

@app.route('/api/v1/teacher/<teacher_id>/skill-report', methods=['GET'])
@require_system
def teacher_skill_report(sys_obj, teacher_id):
    """教师能力评估报告"""
    report = sys_obj.teachers.get_teacher_skill_report(teacher_id)
    if not report:
        return api_response(code=404, message="教师不存在"), 404
    return api_response(data=report)

@app.route('/api/v1/teacher/ranking', methods=['GET'])
@require_system
def teacher_ranking(sys_obj):
    """教师排名"""
    by = request.args.get('by', 'avg_skill_score')
    limit = int(request.args.get('limit', 10))
    ranking = sys_obj.teachers.get_teachers_ranking(by, limit)
    return api_response(data={"count": len(ranking), "ranking": ranking})

@app.route('/api/v1/teacher/training-records', methods=['GET'])
@require_system
def teacher_training_records(sys_obj):
    """培训记录"""
    teacher_id = request.args.get('teacher_id')
    limit = int(request.args.get('limit', 50))
    records = sys_obj.teachers.get_training_records(teacher_id, limit)
    return api_response(data={"count": len(records), "records": records})


# ============================================================
# 十三、评估反馈扩展接口
# ============================================================

@app.route('/api/v1/evaluation/history', methods=['GET'])
@require_system
def evaluation_history(sys_obj):
    """评估历史"""
    eval_type = request.args.get('type')
    limit = int(request.args.get('limit', 20))
    return api_response(data=sys_obj.evaluation.get_evaluation_history(eval_type, limit))

@app.route('/api/v1/evaluation/alerts', methods=['GET'])
@require_system
def evaluation_alerts(sys_obj):
    """质量告警列表"""
    status = request.args.get('status')
    limit = int(request.args.get('limit', 20))
    alerts = sys_obj.evaluation.get_quality_alerts(status, limit)
    return api_response(data={"count": len(alerts), "alerts": alerts})

@app.route('/api/v1/evaluation/alerts/<alert_id>/acknowledge', methods=['POST'])
@require_system
def evaluation_acknowledge_alert(sys_obj, alert_id):
    """确认/处理质量告警"""
    body = request.get_json(silent=True) or {}
    result = sys_obj.evaluation.acknowledge_alert(
        alert_id,
        handler=body.get('handler', 'admin'),
        note=body.get('note', '')
    )
    return api_response(data={"acknowledged": result})

@app.route('/api/v1/evaluation/trend', methods=['GET'])
@require_system
def evaluation_trend(sys_obj):
    """评估趋势"""
    eval_type = request.args.get('type', 'learning')
    periods = int(request.args.get('periods', 5))
    return api_response(data=sys_obj.evaluation.get_evaluation_trend(eval_type, periods))

@app.route('/api/v1/evaluation/report', methods=['POST'])
@require_system
def evaluation_report(sys_obj):
    """生成综合评估报告"""
    return api_response(data=sys_obj.evaluation.generate_evaluation_report())

@app.route('/api/v1/evaluation/improvements', methods=['GET'])
@require_system
def evaluation_improvements(sys_obj):
    """改进任务列表"""
    status = request.args.get('status')
    limit = int(request.args.get('limit', 20))
    tasks = sys_obj.evaluation.get_improvement_tasks(status, limit)
    return api_response(data={"count": len(tasks), "tasks": tasks})

@app.route('/api/v1/evaluation/improvements/<task_id>', methods=['PUT'])
@require_system
def evaluation_update_improvement(sys_obj, task_id):
    """更新改进任务状态"""
    body = request.get_json(silent=True) or {}
    result = sys_obj.evaluation.update_improvement_task(
        task_id,
        status=body.get('status', '处理中'),
        note=body.get('note', '')
    )
    return api_response(data={"updated": result})


# ============================================================
# 十四、演化引擎扩展接口
# ============================================================

@app.route('/api/v1/evolution/history', methods=['GET'])
@require_system
def evolution_history(sys_obj):
    """演化历史"""
    limit = int(request.args.get('limit', 20))
    return api_response(data=sys_obj.evolution.get_evolution_history(limit))

@app.route('/api/v1/evolution/mechanism/<mechanism_name>', methods=['GET'])
@require_system
def evolution_mechanism_detail(sys_obj, mechanism_name):
    """单机制演化详情"""
    return api_response(data=sys_obj.evolution.get_mechanism_detail(mechanism_name))

@app.route('/api/v1/evolution/mechanism-stats', methods=['GET'])
@require_system
def evolution_mechanism_stats(sys_obj):
    """各机制执行统计"""
    return api_response(data=sys_obj.evolution.get_mechanism_stats())

@app.route('/api/v1/evolution/effect', methods=['GET'])
@require_system
def evolution_effect(sys_obj):
    """演化效果评估"""
    return api_response(data=sys_obj.evolution.get_evolution_effect())

@app.route('/api/v1/evolution/run-mechanism', methods=['POST'])
@require_system
def evolution_run_mechanism(sys_obj):
    """运行单个演化机制"""
    body = request.get_json(silent=True) or {}
    mechanism = body.get('mechanism', '')
    return api_response(data=sys_obj.evolution.run_single_mechanism(mechanism))


# ============================================================
# 十五、系统扩展接口
# ============================================================

@app.route('/api/v1/system/export', methods=['POST'])
@require_system
def system_export(sys_obj):
    """全量数据导出"""
    filepath = sys_obj.export_all_data()
    return api_response(data={"exported": True, "filepath": filepath})

@app.route('/api/v1/system/health-check', methods=['GET'])
@require_system
def system_health_check(sys_obj):
    """模块健康检查"""
    return api_response(data=sys_obj.module_health_check())

@app.route('/api/v1/system/module/<module_name>', methods=['GET'])
@require_system
def system_module_status(sys_obj, module_name):
    """单个模块状态"""
    return api_response(data=sys_obj.get_module_status(module_name))


# ============================================================
# 十六、视频教学内容生产通道接口（对接短剧流水线）
# ============================================================

@app.route('/api/v1/video/produce', methods=['POST'])
@require_system
def video_produce(sys_obj):
    """生产教学视频内容（完整6步流水线）"""
    body = request.get_json(silent=True) or {}
    entity_id = body.get('entity_id', '')
    stage = body.get('stage', '初中')
    duration_minutes = int(body.get('duration_minutes', 3))
    if not entity_id:
        return api_response(code=400, message="entity_id必填"), 400
    result = sys_obj.produce_teaching_video(entity_id, stage, duration_minutes)
    return api_response(data=result)

@app.route('/api/v1/video/batch-produce', methods=['POST'])
@require_system
def video_batch_produce(sys_obj):
    """批量生产教学视频"""
    body = request.get_json(silent=True) or {}
    entity_ids = body.get('entity_ids', [])
    stage = body.get('stage', '初中')
    duration_minutes = int(body.get('duration_minutes', 3))
    if not entity_ids:
        return api_response(code=400, message="entity_ids必填"), 400
    result = sys_obj.batch_produce_teaching_videos(entity_ids, stage, duration_minutes)
    return api_response(data=result)

@app.route('/api/v1/video/status', methods=['GET'])
@require_system
def video_status(sys_obj):
    """获取视频流水线状态"""
    return api_response(data=sys_obj.get_video_pipeline_status())

@app.route('/api/v1/video/history', methods=['GET'])
@require_system
def video_history(sys_obj):
    """获取视频生产历史"""
    limit = int(request.args.get('limit', 10))
    return api_response(data={"runs": sys_obj.video_pipeline.get_run_history(limit)})

@app.route('/api/v1/video/assets', methods=['GET'])
@require_system
def video_assets(sys_obj):
    """获取视频资产列表"""
    asset_type = request.args.get('type')
    if asset_type:
        assets = sys_obj.video_pipeline.asset_manager.get_assets_by_type(asset_type)
    else:
        assets = sys_obj.video_pipeline.asset_manager.assets
    return api_response(data={"count": len(assets), "assets": assets})

@app.route('/api/v1/video/assets/<asset_id>', methods=['GET'])
@require_system
def video_asset_detail(sys_obj, asset_id):
    """获取视频资产详情"""
    asset = sys_obj.video_pipeline.asset_manager.get_asset(asset_id)
    if not asset:
        return api_response(code=404, message="资产不存在"), 404
    content = sys_obj.video_pipeline.asset_manager.get_asset_content(asset_id)
    return api_response(data={"asset": asset, "content": content})

@app.route('/api/v1/video/assets/<asset_id>/verify', methods=['POST'])
@require_system
def video_asset_verify(sys_obj, asset_id):
    """验证视频资产完整性"""
    result = sys_obj.video_pipeline.asset_manager.verify_asset_integrity(asset_id)
    return api_response(data=result)

@app.route('/api/v1/video/manifest', methods=['GET'])
@require_system
def video_manifest(sys_obj):
    """导出视频资产清单（台账）"""
    manifest = sys_obj.video_pipeline.asset_manager.export_asset_manifest()
    return api_response(data=manifest)


# ============================================================
# 十六B、端到端视频成片生产接口（知识点→最终mp4）
# ============================================================

@app.route('/api/v1/video/e2e/produce', methods=['POST'])
@require_system
def video_e2e_produce(sys_obj):
    """端到端生产最终教学视频成片（11步完整流水线）"""
    body = request.get_json(silent=True) or {}
    entity_id = body.get('entity_id', '')
    stage = body.get('stage', '初中')
    duration_minutes = int(body.get('duration_minutes', 2))
    generate_keyframes = body.get('generate_keyframes', True)
    generate_video = body.get('generate_video', True)
    generate_audio = body.get('generate_audio', True)
    burn_subtitles = body.get('burn_subtitles', True)
    use_drama_pipeline = body.get('use_drama_pipeline', False)
    if not entity_id:
        return api_response(code=400, message="entity_id必填"), 400
    result = sys_obj.produce_final_video(
        entity_id, stage, duration_minutes,
        generate_keyframes, generate_video,
        generate_audio, burn_subtitles, use_drama_pipeline
    )
    return api_response(data=result)

@app.route('/api/v1/video/e2e/batch-produce', methods=['POST'])
@require_system
def video_e2e_batch_produce(sys_obj):
    """批量端到端生产最终教学视频"""
    body = request.get_json(silent=True) or {}
    entity_ids = body.get('entity_ids', [])
    stage = body.get('stage', '初中')
    duration_minutes = int(body.get('duration_minutes', 2))
    if not entity_ids:
        return api_response(code=400, message="entity_ids必填"), 400
    result = sys_obj.batch_produce_final_videos(entity_ids, stage, duration_minutes)
    return api_response(data=result)

@app.route('/api/v1/video/e2e/status', methods=['GET'])
@require_system
def video_e2e_status(sys_obj):
    """获取端到端生产状态"""
    return api_response(data=sys_obj.get_e2e_production_status())

@app.route('/api/v1/video/e2e/history', methods=['GET'])
@require_system
def video_e2e_history(sys_obj):
    """获取端到端生产历史"""
    limit = int(request.args.get('limit', 10))
    history = sys_obj.e2e_producer.production_runs[-limit:][::-1]
    return api_response(data={"runs": history, "total": len(sys_obj.e2e_producer.production_runs)})


# ============================================================
# 十七、永恒自治模式接口
# ============================================================

@app.route('/api/v1/autonomy/status', methods=['GET'])
@require_system
def autonomy_status(sys_obj):
    """获取永恒自治模式运行状态"""
    auto = get_autonomy()
    return api_response(data=auto.get_status())


@app.route('/api/v1/autonomy/start', methods=['POST'])
@require_system
def autonomy_start(sys_obj):
    """启动永恒自治循环"""
    auto = get_autonomy()
    body = request.get_json(silent=True) or {}
    if 'poll_interval_seconds' in body:
        auto.config.poll_interval_seconds = max(10, int(body['poll_interval_seconds']))
    result = auto.start()
    return api_response(data={
        "started": result,
        "poll_interval_seconds": auto.config.poll_interval_seconds,
        "message": "永恒自治循环已启动" if result else "自治循环已在运行中"
    })


@app.route('/api/v1/autonomy/pause', methods=['POST'])
@require_system
def autonomy_pause(sys_obj):
    """暂停永恒自治循环"""
    auto = get_autonomy()
    result = auto.pause()
    return api_response(data={"paused": result, "message": "永恒自治循环已暂停"})


@app.route('/api/v1/autonomy/resume', methods=['POST'])
@require_system
def autonomy_resume(sys_obj):
    """恢复永恒自治循环"""
    auto = get_autonomy()
    result = auto.resume()
    return api_response(data={
        "resumed": result,
        "message": "永恒自治循环已恢复" if result else "恢复失败，可能处于熔断状态"
    })


@app.route('/api/v1/autonomy/run-cycle', methods=['POST'])
@require_system
def autonomy_run_cycle(sys_obj):
    """手动触发一轮自治循环"""
    auto = get_autonomy()
    result = auto.run_one_cycle()
    return api_response(data=result)


@app.route('/api/v1/autonomy/logs', methods=['GET'])
@require_system
def autonomy_logs(sys_obj):
    """查询自治审计日志"""
    auto = get_autonomy()
    limit = min(int(request.args.get('limit', 50)), 500)
    logs = auto.get_audit_logs(limit)
    return api_response(data={"count": len(logs), "logs": logs})


@app.route('/api/v1/autonomy/risk-report', methods=['GET'])
@require_system
def autonomy_risk_report(sys_obj):
    """获取自治风险评估报告"""
    auto = get_autonomy()
    return api_response(data=auto.get_risk_report())


@app.route('/api/v1/autonomy/reset-circuit', methods=['POST'])
@require_system
def autonomy_reset_circuit(sys_obj):
    """重置熔断"""
    auto = get_autonomy()
    result = auto.reset_circuit_breaker()
    return api_response(data={"reset": result, "message": "熔断已重置"})


@app.route('/api/v1/autonomy/manual-tasks', methods=['GET'])
@require_system
def autonomy_manual_tasks(sys_obj):
    """获取待人工审核任务列表"""
    auto = get_autonomy()
    tasks = [t.to_dict() for t in auto.manual_review_queue]
    return api_response(data={"count": len(tasks), "tasks": tasks})


@app.route('/api/v1/autonomy/manual-tasks/<task_id>/approve', methods=['POST'])
@require_system
def autonomy_approve_task(sys_obj, task_id):
    """人工审核通过任务"""
    auto = get_autonomy()
    result = auto.approve_manual_task(task_id)
    return api_response(data={
        "approved": result,
        "message": "任务已通过，加入执行队列" if result else "任务未找到"
    })


@app.route('/api/v1/autonomy/manual-tasks/<task_id>/reject', methods=['POST'])
@require_system
def autonomy_reject_task(sys_obj, task_id):
    """人工审核拒绝任务"""
    auto = get_autonomy()
    body = request.get_json(silent=True) or {}
    reason = body.get('reason', '')
    result = auto.reject_manual_task(task_id, reason)
    return api_response(data={
        "rejected": result,
        "message": "任务已拒绝" if result else "任务未找到"
    })


@app.route('/api/v1/autonomy/config', methods=['GET', 'POST'])
@require_system
def autonomy_config(sys_obj):
    """获取或更新自治配置"""
    auto = get_autonomy()
    if request.method == 'GET':
        return api_response(data=auto.config.to_dict())
    else:
        body = request.get_json(silent=True) or {}
        auto.config.update(body)
        return api_response(data={"updated": True, "config": auto.config.to_dict()})


# ============================================================
# 错误处理
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return api_response(code=40401, message="接口不存在", data=None), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return api_response(code=40501, message="请求方法不允许", data=None), 405


@app.errorhandler(500)
def internal_error(e):
    return api_response(code=50001, message=f"服务器内部错误: {str(e)}", data=None), 500


# ============================================================
# 启动入口
# ============================================================

def create_app():
    """应用工厂"""
    return app


if __name__ == '__main__':
    print("=" * 60)
    print(f"{SYSTEM_NAME} API 服务 {SYSTEM_VERSION}")
    print(f"确权: {DID} | 锚定: {ANCHOR}")
    print(f"根哈希: {ROOT_HASH}")
    print("=" * 60)
    print("正在初始化系统...")
    get_system()
    print("系统初始化完成，启动API服务...")
    print("API文档: GET /api/v1/system/status")
    print("健康检查: GET /api/v1/system/health")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
