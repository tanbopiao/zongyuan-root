"""
火斗云智企业一体化系统 - 智能派单引擎
五维加权评分：位置30% + 技能25% + 负载20% + 绩效15% + 资质10%
"""
import math
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models import Worker, WorkOrder

def haversine(lat1, lon1, lat2, lon2):
    """Haversine球面距离计算(km)"""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def calc_location_score(distance_km, lambda_decay=0.1):
    """位置分：指数衰减，0km=100分，50km≈0.7分"""
    return max(0, min(100, math.exp(-lambda_decay * distance_km) * 100))

def calc_skill_score(worker_skills, required_skills, worker_level):
    """技能分：匹配率 × 等级系数"""
    if not required_skills:
        return 80.0
    matched = sum(1 for s in required_skills if s in (worker_skills or []))
    match_rate = matched / len(required_skills)
    level_coeff = {"初级": 0.8, "中级": 0.9, "高级": 1.0, "专家": 1.1}.get(worker_level, 0.9)
    return match_rate * 100 * level_coeff

def calc_load_score(current_load, max_load=5):
    """负载分：1 - 当前负载/最大负载"""
    if max_load <= 0:
        return 50.0
    return max(0, min(100, (1 - current_load / max_load) * 100))

def calc_performance_score(performance_score, good_rate=90):
    """绩效分：绩效分×0.6 + 好评率×0.4"""
    return (performance_score or 80) * 0.6 + (good_rate or 90) * 0.4

def calc_certification_score(worker_certs, work_type):
    """资质分：特殊工程持证=100，无资质=0，普通工程默认80"""
    special_types = {"安防监控": ["安防资质", "高空作业证"], "弱电工程": ["电工证"]}
    if work_type in special_types:
        required = special_types[work_type]
        if any(c in (worker_certs or []) for c in required):
            return 100.0
        return 0.0
    return 80.0

def dispatch_order(db: Session, order_id: int, top_n: int = 3) -> List[Dict[str, Any]]:
    """智能派单：五维加权评分推荐TopN师傅"""
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        return []

    workers = db.query(Worker).filter(Worker.status.in_(["空闲", "施工中"])).all()
    if not workers:
        return []

    required_skills = order.skill_required or []
    order_lat = order.latitude or 22.5431
    order_lon = order.longitude or 114.0579

    recommendations = []
    for worker in workers:
        # 智能过滤
        if worker.current_order_count >= worker.max_load:
            continue
        if required_skills and not any(s in (worker.skills or []) for s in required_skills):
            continue

        # 距离计算
        w_lat = worker.latitude or 22.5431
        w_lon = worker.longitude or 114.0579
        distance = haversine(order_lat, order_lon, w_lat, w_lon)

        # 五维评分
        s_location = calc_location_score(distance)
        s_skill = calc_skill_score(worker.skills, required_skills, worker.level)
        s_load = calc_load_score(worker.current_order_count, worker.max_load)
        s_perf = calc_performance_score(worker.performance_score, worker.good_rate)
        s_cert = calc_certification_score(worker.certifications, order.work_type)

        # 加权总分
        total = s_location * 0.30 + s_skill * 0.25 + s_load * 0.20 + s_perf * 0.15 + s_cert * 0.10

        match_rate = sum(1 for s in required_skills if s in (worker.skills or [])) / len(required_skills) if required_skills else 1.0

        recommendations.append({
            "worker_id": worker.id,
            "worker_name": worker.name,
            "worker_level": worker.level,
            "distance_km": round(distance, 2),
            "match_rate": round(match_rate, 2),
            "current_load": f"{worker.current_order_count}/{worker.max_load}",
            "total_score": round(total, 2),
            "scores": {
                "location": round(s_location, 1),
                "skill": round(s_skill, 1),
                "load": round(s_load, 1),
                "performance": round(s_perf, 1),
                "certification": round(s_cert, 1),
            }
        })

    recommendations.sort(key=lambda x: x["total_score"], reverse=True)
    return recommendations[:top_n]
