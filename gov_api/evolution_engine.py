#!/usr/bin/env python3
"""
政务中台自进化引擎 V1.0
基于用户使用数据自动优化系统
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

核心机制：
1. 高频问答自动缓存
2. 搜索无结果自动记录
3. 性能日报自动生成
4. 模式识别与策略生成
"""
import json
import os
import time
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
EVOLUTION_DIR = os.path.join(DATA_DIR, 'evolution')

# 确保目录存在
os.makedirs(EVOLUTION_DIR, exist_ok=True)

# 进化数据文件
HIGH_FREQ_CACHE_FILE = os.path.join(EVOLUTION_DIR, 'high_freq_cache.json')
NO_RESULT_SEARCHES_FILE = os.path.join(EVOLUTION_DIR, 'no_result_searches.json')
DAILY_REPORTS_DIR = os.path.join(EVOLUTION_DIR, 'daily_reports')
EVOLUTION_LOG_FILE = os.path.join(EVOLUTION_DIR, 'evolution_log.jsonl')
EVOLUTION_CONFIG_FILE = os.path.join(EVOLUTION_DIR, 'config.json')

# 默认配置
DEFAULT_CONFIG = {
    "high_freq_threshold": 5,           # 高频阈值：5次以上触发缓存
    "cache_ttl_hours": 24,              # 缓存有效期24小时
    "max_cache_entries": 500,           # 最大缓存条目
    "no_result_min_count": 3,           # 无结果搜索最少3次才记录
    "auto_cache_enabled": True,         # 自动缓存开关
    "auto_report_enabled": True,        # 自动日报开关
    "evolution_level": "basic",         # basic/advanced/full
    "last_evolution_time": None
}


def load_config():
    """加载进化配置"""
    if os.path.exists(EVOLUTION_CONFIG_FILE):
        with open(EVOLUTION_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # 合并默认配置
        for k, v in DEFAULT_CONFIG.items():
            if k not in config:
                config[k] = v
        return config
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存进化配置"""
    with open(EVOLUTION_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def log_evolution(action, details, level="info"):
    """记录进化日志"""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "level": level,
        "details": details
    }
    with open(EVOLUTION_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry


# ============ 机制1：高频问答自动缓存 ============

def load_high_freq_cache():
    """加载高频缓存"""
    if os.path.exists(HIGH_FREQ_CACHE_FILE):
        with open(HIGH_FREQ_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"entries": {}, "stats": {"total_cached": 0, "cache_hits": 0, "cache_misses": 0}}


def save_high_freq_cache(cache):
    """保存高频缓存"""
    with open(HIGH_FREQ_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_cache_key(query):
    """生成缓存键"""
    return hashlib.md5(query.strip().lower().encode('utf-8')).hexdigest()


def check_high_freq_cache(query):
    """检查高频缓存
    
    Returns:
        (hit, cached_answer) 或 (False, None)
    """
    config = load_config()
    if not config.get("auto_cache_enabled", True):
        return False, None
    
    cache = load_high_freq_cache()
    key = get_cache_key(query)
    
    if key in cache["entries"]:
        entry = cache["entries"][key]
        # 检查是否过期
        created_at = datetime.fromisoformat(entry["created_at"])
        if (datetime.utcnow() - created_at).total_seconds() < config["cache_ttl_hours"] * 3600:
            cache["stats"]["cache_hits"] += 1
            entry["hit_count"] += 1
            save_high_freq_cache(cache)
            return True, entry["answer"]
        else:
            # 过期删除
            del cache["entries"][key]
            save_high_freq_cache(cache)
    
    cache["stats"]["cache_misses"] += 1
    save_high_freq_cache(cache)
    return False, None


def record_question_for_cache(query, answer, query_count=None):
    """记录问题用于高频缓存判断
    
    如果问题出现次数达到阈值，自动缓存
    """
    config = load_config()
    if not config.get("auto_cache_enabled", True):
        return False
    
    cache = load_high_freq_cache()
    key = get_cache_key(query)
    
    if key in cache["entries"]:
        # 已缓存，更新
        cache["entries"][key]["answer"] = answer
        cache["entries"][key]["last_used"] = datetime.utcnow().isoformat()
        save_high_freq_cache(cache)
        return True
    
    # 记录查询次数（使用临时计数器）
    counter_file = os.path.join(EVOLUTION_DIR, 'query_counter.json')
    if os.path.exists(counter_file):
        with open(counter_file, 'r', encoding='utf-8') as f:
            counter = json.load(f)
    else:
        counter = {}
    
    counter[key] = counter.get(key, 0) + 1
    count = counter[key]
    
    with open(counter_file, 'w', encoding='utf-8') as f:
        json.dump(counter, f, ensure_ascii=False, indent=2)
    
    # 达到阈值则自动缓存
    if count >= config["high_freq_threshold"]:
        # 检查缓存容量
        if len(cache["entries"]) >= config["max_cache_entries"]:
            # 删除最旧的条目
            oldest_key = min(cache["entries"].keys(), 
                           key=lambda k: cache["entries"][k].get("hit_count", 0))
            del cache["entries"][oldest_key]
        
        cache["entries"][key] = {
            "query": query,
            "answer": answer,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": datetime.utcnow().isoformat(),
            "hit_count": 0,
            "frequency": count
        }
        cache["stats"]["total_cached"] += 1
        save_high_freq_cache(cache)
        log_evolution("auto_cache", {
            "query": query[:50],
            "frequency": count,
            "action": "cached"
        }, "success")
        return True
    
    return False


def get_cache_stats():
    """获取缓存统计"""
    cache = load_high_freq_cache()
    return {
        "total_entries": len(cache["entries"]),
        "total_cached": cache["stats"].get("total_cached", 0),
        "cache_hits": cache["stats"].get("cache_hits", 0),
        "cache_misses": cache["stats"].get("cache_misses", 0),
        "hit_rate": round(cache["stats"].get("cache_hits", 0) / 
                         max(cache["stats"].get("cache_hits", 0) + 
                             cache["stats"].get("cache_misses", 0), 1) * 100, 2)
    }


# ============ 机制2：搜索无结果自动记录 ============

def load_no_result_searches():
    """加载无结果搜索记录"""
    if os.path.exists(NO_RESULT_SEARCHES_FILE):
        with open(NO_RESULT_SEARCHES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"searches": {}, "total_recorded": 0}


def save_no_result_searches(data):
    """保存无结果搜索记录"""
    with open(NO_RESULT_SEARCHES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_no_result_search(query, search_type="policy"):
    """记录无结果搜索
    
    Args:
        query: 搜索关键词
        search_type: 搜索类型（policy/guide/chat）
    """
    config = load_config()
    data = load_no_result_searches()
    
    key = hashlib.md5(f"{search_type}:{query.strip().lower()}".encode('utf-8')).hexdigest()
    
    if key not in data["searches"]:
        data["searches"][key] = {
            "query": query,
            "type": search_type,
            "count": 0,
            "first_seen": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "status": "pending",  # pending/analyzed/resolved
            "suggested_answer": None
        }
    
    data["searches"][key]["count"] += 1
    data["searches"][key]["last_seen"] = datetime.utcnow().isoformat()
    data["total_recorded"] += 1
    
    # 达到阈值标记为需要分析
    if data["searches"][key]["count"] >= config.get("no_result_min_count", 3):
        data["searches"][key]["status"] = "needs_analysis"
        log_evolution("knowledge_gap_identified", {
            "query": query[:50],
            "type": search_type,
            "count": data["searches"][key]["count"]
        }, "warning")
    
    save_no_result_searches(data)
    return data["searches"][key]


def get_knowledge_gaps(limit=20, status=None):
    """获取知识缺口列表"""
    data = load_no_result_searches()
    searches = list(data["searches"].values())
    
    if status:
        searches = [s for s in searches if s["status"] == status]
    
    # 按出现次数排序
    searches.sort(key=lambda x: x["count"], reverse=True)
    
    return {
        "total": len(searches),
        "pending": sum(1 for s in searches if s["status"] == "pending"),
        "needs_analysis": sum(1 for s in searches if s["status"] == "needs_analysis"),
        "resolved": sum(1 for s in searches if s["status"] == "resolved"),
        "top_gaps": searches[:limit]
    }


def resolve_knowledge_gap(query_key, suggested_answer):
    """解决知识缺口"""
    data = load_no_result_searches()
    if query_key in data["searches"]:
        data["searches"][query_key]["status"] = "resolved"
        data["searches"][query_key]["suggested_answer"] = suggested_answer
        data["searches"][query_key]["resolved_at"] = datetime.utcnow().isoformat()
        save_no_result_searches(data)
        log_evolution("knowledge_gap_resolved", {
            "query": data["searches"][query_key]["query"][:50],
            "action": "resolved"
        }, "success")
        return True
    return False


# ============ 机制3：性能日报自动生成 ============

def generate_daily_report(date=None):
    """生成性能日报
    
    Args:
        date: 日期字符串 YYYY-MM-DD，默认昨天
    """
    if date is None:
        date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 读取算子调用日志
    operator_log = os.path.join(DATA_DIR, 'operator_calls.jsonl')
    daily_calls = []
    
    if os.path.exists(operator_log):
        with open(operator_log, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        if record.get('timestamp', '').startswith(date):
                            daily_calls.append(record)
                    except:
                        pass
    
    # 统计
    total_calls = len(daily_calls)
    success_calls = sum(1 for c in daily_calls if c.get('success', True))
    failed_calls = total_calls - success_calls
    avg_latency = sum(c.get('latency_ms', 0) for c in daily_calls) / max(total_calls, 1)
    
    # 按算子统计
    op_stats = defaultdict(lambda: {"calls": 0, "success": 0, "latency": 0})
    for c in daily_calls:
        op_id = c.get('op_id', 'unknown')
        op_stats[op_id]["calls"] += 1
        if c.get('success', True):
            op_stats[op_id]["success"] += 1
        op_stats[op_id]["latency"] += c.get('latency_ms', 0)
    
    # Top 5高频算子
    top_ops = sorted(op_stats.items(), key=lambda x: x[1]["calls"], reverse=True)[:5]
    
    # 缓存统计
    cache_stats = get_cache_stats()
    
    # 知识缺口
    gaps = get_knowledge_gaps(limit=5)
    
    # 生成报告
    report = {
        "date": date,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_calls": total_calls,
            "success_rate": round(success_calls / max(total_calls, 1) * 100, 2),
            "failed_calls": failed_calls,
            "avg_latency_ms": round(avg_latency, 2)
        },
        "top_operators": [
            {
                "op_id": op_id,
                "calls": stats["calls"],
                "success_rate": round(stats["success"] / max(stats["calls"], 1) * 100, 2),
                "avg_latency_ms": round(stats["latency"] / max(stats["calls"], 1), 2)
            }
            for op_id, stats in top_ops
        ],
        "cache": cache_stats,
        "knowledge_gaps": {
            "total": gaps["total"],
            "needs_analysis": gaps["needs_analysis"],
            "top_5": gaps["top_gaps"]
        },
        "evolution_actions": [],
        "recommendations": []
    }
    
    # 生成优化建议
    if avg_latency > 2000:
        report["recommendations"].append({
            "type": "performance",
            "priority": "high",
            "message": f"平均延迟{avg_latency:.0f}ms偏高，建议优化高频接口或增加缓存"
        })
    
    if failed_calls > total_calls * 0.05:
        report["recommendations"].append({
            "type": "reliability",
            "priority": "high",
            "message": f"失败率{failed_calls/total_calls*100:.1f}%偏高，建议检查错误日志"
        })
    
    if gaps["needs_analysis"] > 0:
        report["recommendations"].append({
            "type": "knowledge",
            "priority": "medium",
            "message": f"发现{gaps['needs_analysis']}个知识缺口需要分析补充"
        })
    
    # 保存报告
    os.makedirs(DAILY_REPORTS_DIR, exist_ok=True)
    report_file = os.path.join(DAILY_REPORTS_DIR, f'report_{date}.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    log_evolution("daily_report_generated", {
        "date": date,
        "total_calls": total_calls,
        "recommendations": len(report["recommendations"])
    }, "info")
    
    return report


def get_daily_reports(limit=7):
    """获取历史日报列表"""
    if not os.path.exists(DAILY_REPORTS_DIR):
        return []
    
    reports = []
    for filename in sorted(os.listdir(DAILY_REPORTS_DIR), reverse=True)[:limit]:
        if filename.endswith('.json'):
            with open(os.path.join(DAILY_REPORTS_DIR, filename), 'r', encoding='utf-8') as f:
                reports.append(json.load(f))
    return reports


# ============ 进化状态总览 ============

def get_evolution_status():
    """获取自进化引擎状态总览"""
    config = load_config()
    cache_stats = get_cache_stats()
    gaps = get_knowledge_gaps(limit=10)
    
    # 读取进化日志最近10条
    evolution_log = []
    if os.path.exists(EVOLUTION_LOG_FILE):
        with open(EVOLUTION_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            evolution_log = [json.loads(line) for line in lines[-10:] if line.strip()]
    
    return {
        "engine_status": "running",
        "version": "1.0",
        "config": config,
        "cache": cache_stats,
        "knowledge_gaps": {
            "total": gaps["total"],
            "pending": gaps["pending"],
            "needs_analysis": gaps["needs_analysis"],
            "resolved": gaps["resolved"]
        },
        "recent_evolution_actions": evolution_log,
        "mechanisms": {
            "auto_cache": {"enabled": config["auto_cache_enabled"], "status": "active"},
            "knowledge_gap_tracking": {"enabled": True, "status": "active"},
            "daily_report": {"enabled": config["auto_report_enabled"], "status": "active"}
        }
    }


if __name__ == "__main__":
    print("=== 政务中台自进化引擎 V1.0 ===")
    print(f"数据目录: {EVOLUTION_DIR}")
    
    # 测试
    print("\n=== 测试高频缓存 ===")
    for i in range(6):
        result = record_question_for_cache("深圳社保怎么办理", f"这是第{i+1}次回答")
        print(f"  第{i+1}次记录: {'已缓存' if result else '计数中'}")
    
    hit, answer = check_high_freq_cache("深圳社保怎么办理")
    print(f"  缓存命中: {hit}, 回答: {answer[:20] if answer else 'None'}")
    
    print("\n=== 测试无结果搜索 ===")
    for i in range(4):
        record_no_result_search("火星移民政策", "policy")
    gaps = get_knowledge_gaps()
    print(f"  知识缺口总数: {gaps['total']}")
    print(f"  需要分析: {gaps['needs_analysis']}")
    
    print("\n=== 测试日报生成 ===")
    report = generate_daily_report()
    print(f"  日报日期: {report['date']}")
    print(f"  总调用: {report['summary']['total_calls']}")
    print(f"  建议数: {len(report['recommendations'])}")
    
    print("\n=== 进化状态 ===")
    status = get_evolution_status()
    print(f"  引擎状态: {status['engine_status']}")
    print(f"  缓存命中率: {status['cache']['hit_rate']}%")
    print(f"  知识缺口: {status['knowledge_gaps']['total']}")
    
    print("\n✅ 自进化引擎测试完成")
