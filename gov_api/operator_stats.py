#!/usr/bin/env python3
"""
政务中台算子调用统计模块
记录17个算子的调用情况，提供统计查询和健康度计算
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict

# 算子调用日志文件
OPERATOR_CALLS_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'operator_calls.jsonl')

# 17个算子元数据
OPERATORS_META = {
    "GOV-OP-001": {"name": "API通信算子", "layer": "infra", "layer_name": "基础设施层", "desc": "统一API请求封装，支持超时重试、错误处理、请求审计"},
    "GOV-OP-002": {"name": "用户状态算子", "layer": "infra", "layer_name": "基础设施层", "desc": "用户登录态管理、权限校验、会话保持、本地存储"},
    "GOV-OP-003": {"name": "弹窗模态算子", "layer": "infra", "layer_name": "基础设施层", "desc": "统一弹窗组件，支持确认框、详情页、表单弹窗"},
    "GOV-OP-004": {"name": "加载状态算子", "layer": "infra", "layer_name": "基础设施层", "desc": "全局加载指示器、骨架屏、进度条、异步状态管理"},
    "GOV-OP-005": {"name": "审计日志算子", "layer": "infra", "layer_name": "基础设施层", "desc": "全链路操作审计、行为追踪、合规日志、不可篡改记录"},
    "GOV-OP-006": {"name": "智能问答算子", "layer": "core", "layer_name": "核心功能层", "desc": "政务AI对话引擎，支持多轮对话、上下文理解、真值核验"},
    "GOV-OP-007": {"name": "政策查询算子", "layer": "core", "layer_name": "核心功能层", "desc": "政策法规检索、分类筛选、全文搜索、政策详情"},
    "GOV-OP-008": {"name": "公文助手算子", "layer": "core", "layer_name": "核心功能层", "desc": "公文生成、模板套用、格式校验、合规审查、导出"},
    "GOV-OP-009": {"name": "办事指南算子", "layer": "core", "layer_name": "核心功能层", "desc": "办事流程查询、材料清单、在线预约、进度跟踪"},
    "GOV-OP-010": {"name": "合规审查算子", "layer": "compliance", "layer_name": "合规治理层", "desc": "敏感词过滤、涉密拦截、违规识别、用语规范校验"},
    "GOV-OP-011": {"name": "政策真值核验算子", "layer": "compliance", "layer_name": "合规治理层", "desc": "AI答复置信度评估、真值溯源、高风险自动转人工"},
    "GOV-OP-015": {"name": "人工复核工单算子", "layer": "compliance", "layer_name": "合规治理层", "desc": "高风险内容复核工单创建、流转、审批、归档"},
    "GOV-OP-012": {"name": "会话超时回收算子", "layer": "business", "layer_name": "业务闭环层", "desc": "会话超时检测、自动登出、敏感信息清除、预警提醒"},
    "GOV-OP-016": {"name": "政策版本生命周期算子", "layer": "business", "layer_name": "业务闭环层", "desc": "政策生效/过期/废止状态管理、版本追踪、变更提醒"},
    "GOV-OP-013": {"name": "批量导出算子", "layer": "ops", "layer_name": "运营完善层", "desc": "政策库/公文/报表多格式导出（PDF/Word/Excel/CSV）"},
    "GOV-OP-014": {"name": "消息通知算子", "layer": "ops", "layer_name": "运营完善层", "desc": "系统公告、站内消息、未读计数、静默时段、通知中心"},
    "GOV-OP-017": {"name": "运营统计算子", "layer": "ops", "layer_name": "运营完善层", "desc": "PV/UV统计、功能使用排行、用户行为分析、报表生成"},
}


def ensure_log_file():
    """确保日志文件存在"""
    os.makedirs(os.path.dirname(OPERATOR_CALLS_LOG), exist_ok=True)
    if not os.path.exists(OPERATOR_CALLS_LOG):
        with open(OPERATOR_CALLS_LOG, 'w', encoding='utf-8') as f:
            pass


def record_operator_call(op_id, success=True, latency_ms=0, details=None):
    """记录算子调用
    
    Args:
        op_id: 算子ID (如 GOV-OP-001)
        success: 是否成功
        latency_ms: 延迟毫秒数
        details: 额外详情
    """
    ensure_log_file()
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "op_id": op_id,
        "op_name": OPERATORS_META.get(op_id, {}).get("name", "未知"),
        "success": success,
        "latency_ms": latency_ms,
        "details": details or {}
    }
    with open(OPERATOR_CALLS_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    return record


def get_all_calls(limit=100):
    """获取最近的算子调用记录"""
    ensure_log_file()
    calls = []
    with open(OPERATOR_CALLS_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    calls.append(json.loads(line))
                except:
                    pass
    return calls[-limit:]


def get_operator_stats(op_id=None, hours=24):
    """获取算子统计数据
    
    Args:
        op_id: 算子ID，None表示全部
        hours: 统计时间范围（小时）
    
    Returns:
        统计数据字典
    """
    ensure_log_file()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    
    # 按算子分组统计
    stats = defaultdict(lambda: {
        "total_calls": 0,
        "success_calls": 0,
        "failed_calls": 0,
        "total_latency": 0,
        "latencies": []
    })
    
    with open(OPERATOR_CALLS_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("timestamp", "") < cutoff:
                    continue
                if op_id and record.get("op_id") != op_id:
                    continue
                
                oid = record.get("op_id", "unknown")
                stats[oid]["total_calls"] += 1
                if record.get("success", True):
                    stats[oid]["success_calls"] += 1
                else:
                    stats[oid]["failed_calls"] += 1
                latency = record.get("latency_ms", 0)
                stats[oid]["total_latency"] += latency
                stats[oid]["latencies"].append(latency)
            except:
                pass
    
    # 计算成功率和平均延迟
    result = {}
    for oid, s in stats.items():
        success_rate = (s["success_calls"] / s["total_calls"] * 100) if s["total_calls"] > 0 else 100
        avg_latency = (s["total_latency"] / s["total_calls"]) if s["total_calls"] > 0 else 0
        result[oid] = {
            "op_id": oid,
            "op_name": OPERATORS_META.get(oid, {}).get("name", "未知"),
            "layer": OPERATORS_META.get(oid, {}).get("layer", "unknown"),
            "layer_name": OPERATORS_META.get(oid, {}).get("layer_name", "未知"),
            "desc": OPERATORS_META.get(oid, {}).get("desc", ""),
            "total_calls": s["total_calls"],
            "success_calls": s["success_calls"],
            "failed_calls": s["failed_calls"],
            "success_rate": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "health_score": round(success_rate * 0.7 + (100 - min(avg_latency/50, 100)) * 0.3, 2),
            "status": "active" if success_rate >= 95 else ("warning" if success_rate >= 80 else "error")
        }
    
    # 补充没有调用记录的算子
    for oid, meta in OPERATORS_META.items():
        if oid not in result:
            result[oid] = {
                "op_id": oid,
                "op_name": meta["name"],
                "layer": meta["layer"],
                "layer_name": meta["layer_name"],
                "desc": meta["desc"],
                "total_calls": 0,
                "success_calls": 0,
                "failed_calls": 0,
                "success_rate": 100,
                "avg_latency_ms": 0,
                "health_score": 100,
                "status": "active"
            }
    
    return result


def get_summary_stats(hours=24):
    """获取汇总统计"""
    stats = get_operator_stats(hours=hours)
    total_calls = sum(s["total_calls"] for s in stats.values())
    total_success = sum(s["success_calls"] for s in stats.values())
    avg_success_rate = (total_success / total_calls * 100) if total_calls > 0 else 100
    active_count = sum(1 for s in stats.values() if s["status"] == "active")
    warning_count = sum(1 for s in stats.values() if s["status"] == "warning")
    error_count = sum(1 for s in stats.values() if s["status"] == "error")
    
    # 按层级统计
    layer_stats = defaultdict(lambda: {"count": 0, "calls": 0})
    for s in stats.values():
        layer_stats[s["layer"]]["count"] += 1
        layer_stats[s["layer"]]["calls"] += s["total_calls"]
    
    return {
        "total_operators": len(OPERATORS_META),
        "active_operators": active_count,
        "warning_operators": warning_count,
        "error_operators": error_count,
        "total_calls": total_calls,
        "avg_success_rate": round(avg_success_rate, 2),
        "time_range_hours": hours,
        "layer_distribution": dict(layer_stats),
        "generated_at": datetime.utcnow().isoformat()
    }


def get_operator_logs(op_id=None, limit=50):
    """获取算子调用日志"""
    calls = get_all_calls(limit=200)
    if op_id:
        calls = [c for c in calls if c.get("op_id") == op_id]
    return calls[-limit:]


if __name__ == "__main__":
    # 测试
    print("=== 算子统计模块测试 ===")
    print(f"算子总数: {len(OPERATORS_META)}")
    print(f"日志文件: {OPERATOR_CALLS_LOG}")
    
    # 记录测试调用
    record_operator_call("GOV-OP-006", success=True, latency_ms=1200, details={"query": "测试"})
    
    # 获取统计
    stats = get_operator_stats()
    print(f"\n最近24小时统计:")
    for oid, s in sorted(stats.items()):
        if s["total_calls"] > 0:
            print(f"  {oid}: {s['total_calls']}次调用, 成功率{s['success_rate']}%, 平均延迟{s['avg_latency_ms']}ms")
    
    summary = get_summary_stats()
    print(f"\n汇总: {summary['total_calls']}次调用, 平均成功率{summary['avg_success_rate']}%")


# ============ 趋势查询功能 ============

def get_trend_stats(op_id=None, days=7):
    """按天统计算子调用趋势
    
    Args:
        op_id: 算子ID，None表示全部
        days: 统计天数
    
    Returns:
        按天分组的统计数据
    """
    ensure_log_file()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    # 按天分组
    daily_stats = defaultdict(lambda: {
        "total_calls": 0,
        "success_calls": 0,
        "failed_calls": 0,
        "total_latency": 0
    })
    
    with open(OPERATOR_CALLS_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("timestamp", "") < cutoff:
                    continue
                if op_id and record.get("op_id") != op_id:
                    continue
                
                day = record.get("timestamp", "")[:10]  # YYYY-MM-DD
                daily_stats[day]["total_calls"] += 1
                if record.get("success", True):
                    daily_stats[day]["success_calls"] += 1
                else:
                    daily_stats[day]["failed_calls"] += 1
                daily_stats[day]["total_latency"] += record.get("latency_ms", 0)
            except:
                pass
    
    # 转换为列表并计算成功率
    result = []
    for day in sorted(daily_stats.keys()):
        s = daily_stats[day]
        success_rate = (s["success_calls"] / s["total_calls"] * 100) if s["total_calls"] > 0 else 100
        avg_latency = (s["total_latency"] / s["total_calls"]) if s["total_calls"] > 0 else 0
        result.append({
            "date": day,
            "total_calls": s["total_calls"],
            "success_calls": s["success_calls"],
            "failed_calls": s["failed_calls"],
            "success_rate": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency, 2)
        })
    
    # 补充没有数据的日期
    if days <= 31:
        all_days = []
        for i in range(days-1, -1, -1):
            d = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            all_days.append(d)
        existing_days = {r["date"] for r in result}
        for d in all_days:
            if d not in existing_days:
                result.append({
                    "date": d,
                    "total_calls": 0,
                    "success_calls": 0,
                    "failed_calls": 0,
                    "success_rate": 100,
                    "avg_latency_ms": 0
                })
        result.sort(key=lambda x: x["date"])
    
    return result


def get_hourly_stats(op_id=None, hours=24):
    """按小时统计算子调用趋势
    
    Args:
        op_id: 算子ID，None表示全部
        hours: 统计小时数
    
    Returns:
        按小时分组的统计数据
    """
    ensure_log_file()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    
    hourly_stats = defaultdict(lambda: {
        "total_calls": 0,
        "success_calls": 0,
        "total_latency": 0
    })
    
    with open(OPERATOR_CALLS_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("timestamp", "") < cutoff:
                    continue
                if op_id and record.get("op_id") != op_id:
                    continue
                
                hour = record.get("timestamp", "")[:13]  # YYYY-MM-DDTHH
                hourly_stats[hour]["total_calls"] += 1
                if record.get("success", True):
                    hourly_stats[hour]["success_calls"] += 1
                hourly_stats[hour]["total_latency"] += record.get("latency_ms", 0)
            except:
                pass
    
    result = []
    for hour in sorted(hourly_stats.keys()):
        s = hourly_stats[hour]
        success_rate = (s["success_calls"] / s["total_calls"] * 100) if s["total_calls"] > 0 else 100
        avg_latency = (s["total_latency"] / s["total_calls"]) if s["total_calls"] > 0 else 0
        result.append({
            "hour": hour,
            "total_calls": s["total_calls"],
            "success_rate": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency, 2)
        })
    
    return result


# ============ 健康度告警功能 ============

ALERT_CONFIG = {
    "success_rate_warning": 95,    # 成功率低于95%警告
    "success_rate_error": 80,      # 成功率低于80%错误
    "latency_warning_ms": 3000,    # 延迟高于3秒警告
    "latency_error_ms": 5000,      # 延迟高于5秒错误
    "min_calls_for_alert": 5,     # 最少调用次数才触发告警
    "consecutive_failures": 3     # 连续失败次数触发告警
}

ALERTS_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'operator_alerts.jsonl')


def check_operator_alerts():
    """检查所有算子的健康度，生成告警
    
    Returns:
        告警列表
    """
    stats = get_operator_stats(hours=1)  # 最近1小时
    alerts = []
    
    for op_id, s in stats.items():
        if s["total_calls"] < ALERT_CONFIG["min_calls_for_alert"]:
            continue
        
        # 成功率告警
        if s["success_rate"] < ALERT_CONFIG["success_rate_error"]:
            alerts.append({
                "level": "error",
                "op_id": op_id,
                "op_name": s["op_name"],
                "type": "success_rate",
                "message": f"{s['op_name']}成功率过低: {s['success_rate']}%",
                "value": s["success_rate"],
                "threshold": ALERT_CONFIG["success_rate_error"],
                "timestamp": datetime.utcnow().isoformat()
            })
        elif s["success_rate"] < ALERT_CONFIG["success_rate_warning"]:
            alerts.append({
                "level": "warning",
                "op_id": op_id,
                "op_name": s["op_name"],
                "type": "success_rate",
                "message": f"{s['op_name']}成功率下降: {s['success_rate']}%",
                "value": s["success_rate"],
                "threshold": ALERT_CONFIG["success_rate_warning"],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # 延迟告警
        if s["avg_latency_ms"] > ALERT_CONFIG["latency_error_ms"]:
            alerts.append({
                "level": "error",
                "op_id": op_id,
                "op_name": s["op_name"],
                "type": "latency",
                "message": f"{s['op_name']}延迟过高: {s['avg_latency_ms']}ms",
                "value": s["avg_latency_ms"],
                "threshold": ALERT_CONFIG["latency_error_ms"],
                "timestamp": datetime.utcnow().isoformat()
            })
        elif s["avg_latency_ms"] > ALERT_CONFIG["latency_warning_ms"]:
            alerts.append({
                "level": "warning",
                "op_id": op_id,
                "op_name": s["op_name"],
                "type": "latency",
                "message": f"{s['op_name']}延迟升高: {s['avg_latency_ms']}ms",
                "value": s["avg_latency_ms"],
                "threshold": ALERT_CONFIG["latency_warning_ms"],
                "timestamp": datetime.utcnow().isoformat()
            })
    
    # 保存告警
    if alerts:
        os.makedirs(os.path.dirname(ALERTS_LOG), exist_ok=True)
        with open(ALERTS_LOG, 'a', encoding='utf-8') as f:
            for alert in alerts:
                f.write(json.dumps(alert, ensure_ascii=False) + '\n')
    
    return alerts


def get_alerts(limit=50):
    """获取历史告警记录"""
    if not os.path.exists(ALERTS_LOG):
        return []
    alerts = []
    with open(ALERTS_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    alerts.append(json.loads(line))
                except:
                    pass
    return alerts[-limit:]
