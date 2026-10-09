#!/usr/bin/env python3
"""
国家主权根 · 政务AI中台集成中间件
提供合规校验、权力监测、决策审计等功能的客户端封装
带fallback机制：国家主权根不可用时自动降级，不影响政务AI中台正常运行
"""
import os
import json
import time
import hashlib
import urllib.request
import urllib.error
from datetime import datetime

# 配置
SOV_API_URL = os.environ.get("SOV_API_URL", "http://127.0.0.1:8031")
SOV_API_KEY = os.environ.get("SOV_API_KEY", "")
SOV_TIMEOUT = 3  # 超时3秒，不阻塞主流程
SOV_ENABLED = True  # 总开关
SOV_FALLBACK_MODE = "fail_open"  # fail_open: 不可用时放行; fail_closed: 不可用时阻断

# 统计
_stats = {
    "total_calls": 0,
    "success_calls": 0,
    "failed_calls": 0,
    "fallback_calls": 0,
    "last_error": None,
    "last_error_time": None
}

def _sov_request(method, path, data=None):
    """统一请求方法，带超时和异常处理"""
    global _stats
    _stats["total_calls"] += 1

    if not SOV_ENABLED or not SOV_API_KEY:
        _stats["fallback_calls"] += 1
        return None  # 未启用，返回None表示跳过

    url = f"{SOV_API_URL}{path}"
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': SOV_API_KEY
        }
        if method == 'GET':
            req = urllib.request.Request(url, headers=headers)
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode() if data else None,
                headers=headers,
                method=method
            )
        with urllib.request.urlopen(req, timeout=SOV_TIMEOUT) as resp:
            result = json.loads(resp.read().decode())
            _stats["success_calls"] += 1
            return result
    except Exception as e:
        _stats["failed_calls"] += 1
        _stats["last_error"] = str(e)
        _stats["last_error_time"] = datetime.now().isoformat()
        return None  # 调用失败，返回None表示跳过

def check_content_compliance(content, content_type="ai_generated", risk_level="low"):
    """
    内容合规校验 - 在AI生成内容返回前调用
    参数:
        content: 生成的内容文本
        content_type: 内容类型 (ai_generated/document/chat/other)
        risk_level: 风险等级 (low/medium/high/critical)
    返回:
        dict: {passed: bool, level: str, score: float, suggestions: list, blocked: bool}
        None: 国家主权根不可用（根据fallback模式决定是否放行）
    """
    data = {
        "operation": "content_generation",
        "data_type": "public" if risk_level == "low" else "sensitive",
        "content_summary": content[:500] if content else "",
        "content_type": content_type,
        "risk_level": risk_level,
        "content_length": len(content) if content else 0,
        "content_hash": hashlib.sha256(content.encode() if content else b"").hexdigest()[:16],
        "timestamp": datetime.now().isoformat()
    }
    result = _sov_request('POST', '/api/v1/compliance/check', data)

    if result is None:
        # 国家主权根不可用
        if SOV_FALLBACK_MODE == "fail_closed":
            return {"passed": False, "level": "error", "score": 0,
                    "suggestions": ["国家主权根服务不可用，fail_closed模式阻断"],
                    "blocked": True, "fallback": True}
        return {"passed": True, "level": "unknown", "score": -1,
                "suggestions": ["国家主权根服务不可用，fail_open模式放行"],
                "blocked": False, "fallback": True}

    # 解析结果
    compliance = result.get('compliance', {})
    level = compliance.get('overall_level', 'pass')
    score = compliance.get('overall_score', 100)
    rules = compliance.get('rules', [])
    suggestions = [r.get('message', '') for r in rules if r.get('level') in ['warning', 'fail']]

    # 判断是否阻断
    blocked = level in ['fail', 'critical'] or score < 30

    return {
        "passed": not blocked,
        "level": level,
        "score": score,
        "suggestions": suggestions,
        "blocked": blocked,
        "fallback": False,
        "rules_checked": len(rules)
    }

def check_config_change_power(config_key, old_value, new_value, operator="system"):
    """
    配置变更权力前置检测 - 在配置变更前调用
    返回:
        dict: {allowed: bool, level: str, reason: str, audit_hash: str}
        None: 跳过（国家主权根不可用时默认放行）
    """
    data = {
        "config_key": config_key,
        "old_value": str(old_value)[:200],
        "new_value": str(new_value)[:200],
        "operator": operator,
        "change_type": "config_update",
        "timestamp": datetime.now().isoformat()
    }
    result = _sov_request('POST', '/api/v1/config/change', data)

    if result is None:
        return {"allowed": True, "level": "unknown", "reason": "国家主权根不可用，默认放行",
                "audit_hash": hashlib.sha256(f"{config_key}:{datetime.now()}".encode()).hexdigest()[:16],
                "fallback": True}

    # 解析结果
    power = result.get('power_check', {})
    allowed = power.get('allowed', True)
    level = power.get('level', 'normal')
    reason = power.get('reason', '')

    return {
        "allowed": allowed,
        "level": level,
        "reason": reason,
        "audit_hash": result.get('audit_hash', ''),
        "fallback": False
    }

def check_high_risk_decision(decision_type, decision_content, decision_maker="admin"):
    """
    高权限决策执行流程 - 在删除/重置等高风险操作前调用
    完整流程: 合规前置校验 → 权力集中度检测 → 审计哈希生成
    返回:
        dict: {allowed: bool, level: str, reason: str, audit_hash: str, compliance_result: dict}
        None: 跳过
    """
    data = {
        "decision_type": decision_type,
        "decision_content": decision_content[:500],
        "decision_maker": decision_maker,
        "impact_scope": "global" if decision_type in ['delete_all', 'reset_system', 'config_global'] else "local",
        "timestamp": datetime.now().isoformat()
    }
    result = _sov_request('POST', '/api/v1/decision/execute', data)

    if result is None:
        return {"allowed": True, "level": "unknown", "reason": "国家主权根不可用，默认放行",
                "audit_hash": hashlib.sha256(f"{decision_type}:{datetime.now()}".encode()).hexdigest()[:16],
                "fallback": True}

    # 解析结果
    decision = result.get('decision', {})
    allowed = decision.get('allowed', True)
    level = decision.get('level', 'normal')
    reason = decision.get('reason', '')

    return {
        "allowed": allowed,
        "level": level,
        "reason": reason,
        "audit_hash": result.get('audit_hash', ''),
        "compliance_result": decision.get('compliance', {}),
        "fallback": False
    }

def get_stats():
    """获取集成统计信息"""
    return _stats.copy()

def reset_stats():
    """重置统计"""
    global _stats
    _stats = {
        "total_calls": 0,
        "success_calls": 0,
        "failed_calls": 0,
        "fallback_calls": 0,
        "last_error": None,
        "last_error_time": None
    }
