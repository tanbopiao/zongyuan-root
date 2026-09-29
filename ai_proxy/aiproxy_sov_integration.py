#!/usr/bin/env python3
"""
aiproxy 国家主权根集成中间件（修复版）
AI Proxy Sovereignty Root Integration Middleware

修复：使用国家主权根API正确的请求格式（ComplianceCheckRequest）
确权: DID-BR-000002 | 锚点: Ω₀⊂⊙∞⊂Ω | 根: ZONGYUAN-ROOT V1.7
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
SOV_API_KEY = os.environ.get("SOV_API_KEY", "761828c27706eecca9660f7bbd46e03a5926ef2ab85ddaa4f21ad8a1ede2e942")
SOV_TIMEOUT = 3  # 3秒超时，避免阻塞AI调用
SOV_ENABLED = True  # 总开关

# 按模型配置校验策略
MODEL_COMPLIANCE_POLICY = {
    "doubao": {"check_content": True, "block_on_violation": False, "log_only": True},
    "hunyuan": {"check_content": True, "block_on_violation": False, "log_only": True},
    "kimi": {"check_content": True, "block_on_violation": False, "log_only": True},
    "aliyun": {"check_content": True, "block_on_violation": False, "log_only": True},
    "zhipu": {"check_content": True, "block_on_violation": False, "log_only": True},
    "agnes": {"check_content": True, "block_on_violation": False, "log_only": True},
    "siliconflow": {"check_content": True, "block_on_violation": False, "log_only": True},
    "ollama-local": {"check_content": False, "block_on_violation": False, "log_only": True},
    "ollama-win": {"check_content": False, "block_on_violation": False, "log_only": True},
    "default": {"check_content": True, "block_on_violation": False, "log_only": True},
}

# 日志
LOG_DIR = "/opt/ZONGYUAN-ROOT/ai_proxy/logs"
os.makedirs(LOG_DIR, exist_ok=True)
AUDIT_LOG = os.path.join(LOG_DIR, "sov_aiproxy_audit.log")

def _log_audit(model_key, action, result, level="info"):
    """记录审计日志"""
    try:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_key,
            "action": action,
            "result": result,
            "level": level,
            "did": "DID-BR-000002"
        }
        with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except:
        pass

def _generate_operation_id():
    """生成操作ID"""
    return f"aiproxy-{int(time.time()*1000)}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"

def _sov_request(endpoint, payload, timeout=SOV_TIMEOUT):
    """调用国家主权根API"""
    if not SOV_ENABLED:
        return {"fallback": True, "reason": "sov_disabled"}
    try:
        url = f"{SOV_API_URL}{endpoint}"
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': SOV_API_KEY
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_detail = ""
        try:
            error_detail = e.read().decode()[:200]
        except:
            pass
        return {"fallback": True, "reason": f"http_error_{e.code}", "detail": error_detail}
    except Exception as e:
        return {"fallback": True, "reason": str(e)[:100]}

def check_ai_output_compliance(model_key, content, messages=None):
    """
    校验AI输出内容合规性（修复版：使用正确的API格式）
    
    Args:
        model_key: 模型标识
        content: AI生成的内容
        messages: 原始请求消息（可选）
    
    Returns:
        dict: 合规校验结果
    """
    if not SOV_ENABLED:
        return {"passed": True, "fallback": True, "reason": "sov_disabled", "blocked": False}
    
    # 获取模型策略
    policy = MODEL_COMPLIANCE_POLICY.get(model_key, MODEL_COMPLIANCE_POLICY["default"])
    
    if not policy.get("check_content", True):
        return {"passed": True, "fallback": False, "reason": "policy_skip", "blocked": False}
    
    # 构造正确的API请求格式（ComplianceCheckRequest）
    operation_id = _generate_operation_id()
    content_summary = content[:500] if content else ""
    
    payload = {
        "operation_id": operation_id,
        "operation_type": "data_modification",  # AI内容生成属于数据修改
        "operator_id": f"aiproxy-{model_key}",
        "operator_role": "ai_model",
        "target_resource": "ai_output_content",
        "resource_type": "text",
        "data_sensitivity": "normal",
        "contains_personal_info": False,
        "cross_border": False,
        "automated_decision": True,
        "external_dependency": True,
        "metadata": {
            "pipeline": "aiproxy",
            "model": model_key,
            "content_length": len(content) if content else 0,
            "content_summary": content_summary,
            "has_messages": messages is not None,
            "integration_version": "2.0-fixed"
        }
    }
    
    result = _sov_request("/api/v1/compliance/check", payload)
    
    if result.get("fallback"):
        _log_audit(model_key, "compliance_check",
                   {"passed": True, "fallback": True, "reason": result.get("reason"),
                    "detail": result.get("detail", "")}, "info")
        return {"passed": True, "fallback": True, "reason": result.get("reason"),
                "detail": result.get("detail", ""), "blocked": False}
    
    # 解析正确的API响应格式
    success = result.get("success", False)
    overall_compliance = result.get("overall_compliance", "unknown")
    overall_risk = result.get("overall_risk", "unknown")
    total_checks = result.get("total_checks", 0)
    passed_checks = result.get("passed_checks", 0)
    failed_checks = result.get("failed_checks", 0)
    action_recommendation = result.get("action_recommendation", "allow")
    review_required = result.get("review_required", False)
    results = result.get("results", [])
    report_hash = result.get("report_hash", "")
    
    # 判断是否通过
    passed = success and (failed_checks == 0 or action_recommendation == "allow")
    
    # 判断合规等级
    if overall_compliance == "fully_compliant":
        level = "info"
    elif overall_compliance == "conditional_compliant":
        level = "warning"
    elif overall_compliance == "non_compliant":
        level = "warning"
    elif overall_compliance == "critical_violation":
        level = "critical"
    else:
        level = "info"
    
    # 是否阻断（根据策略）
    blocked = False
    if not passed and policy.get("block_on_violation", False):
        blocked = True
    elif not passed and overall_compliance == "critical_violation" and not policy.get("log_only", True):
        blocked = True
    
    audit_hash = report_hash or hashlib.sha256(
        f"{operation_id}{passed}{level}{time.time()}".encode()
    ).hexdigest()[:16]
    
    _log_audit(model_key, "compliance_check",
               {"passed": passed, "level": level, "overall_compliance": overall_compliance,
                "overall_risk": overall_risk, "total_checks": total_checks,
                "passed_checks": passed_checks, "failed_checks": failed_checks,
                "action_recommendation": action_recommendation, "review_required": review_required,
                "blocked": blocked, "audit_hash": audit_hash, "operation_id": operation_id},
               level if level in ["warning", "critical"] else "info")
    
    return {
        "passed": passed,
        "fallback": False,
        "level": level,
        "overall_compliance": overall_compliance,
        "overall_risk": overall_risk,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "action_recommendation": action_recommendation,
        "review_required": review_required,
        "issues": [r for r in results if not r.get("passed", True)],
        "blocked": blocked,
        "audit_hash": audit_hash,
        "operation_id": operation_id,
        "report_hash": report_hash
    }

def get_integration_stats():
    """获取集成统计信息"""
    try:
        if os.path.exists(AUDIT_LOG):
            with open(AUDIT_LOG, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            total = len(lines)
            passed = sum(1 for l in lines if '"passed": true' in l)
            blocked = sum(1 for l in lines if '"blocked": true' in l)
            fallback = sum(1 for l in lines if '"fallback": true' in l)
            warnings = sum(1 for l in lines if '"level": "warning"' in l)
            critical = sum(1 for l in lines if '"level": "critical"' in l)
            return {
                "total_checks": total,
                "passed": passed,
                "blocked": blocked,
                "fallback": fallback,
                "warnings": warnings,
                "critical": critical,
                "sov_enabled": SOV_ENABLED,
                "sov_url": SOV_API_URL
            }
    except:
        pass
    return {"total_checks": 0, "sov_enabled": SOV_ENABLED}
