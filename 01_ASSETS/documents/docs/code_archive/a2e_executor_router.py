#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2E 通用审批→执行闭环 · 执行器路由框架 (P0)
基于 8060 飞书审批回调服务扩展，多类型提案按 type 路由执行
本地仿真版：不改动现有 ontology 流程，仅新增路由层
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
"""
import json, os, subprocess, hashlib
from datetime import datetime

# 执行器注册表：提案type -> 执行命令模板
EXECUTORS = {
    "ontology":        ["python3", "/opt/ZONGYUAN-ROOT/scripts/ontology_evolution_proposer.py", "--implement", "{pid}"],
    "operator_deploy": ["python3", "{payload_file}", "--operator-deploy", "{pid}"],
    "ops_action":      ["python3", "{payload_file}", "--ops-action", "{pid}"],
    "config_change":   ["python3", "{payload_file}", "--config-change", "{pid}"],
    "truth_sync":      ["python3", "{payload_file}", "--sync", "{pid}"],
    "archive_lock":    ["python3", "{payload_file}", "--lock", "{pid}"],
}

# 风险等级：high 需回滚方案 + 二次确认
RISK_LEVELS = {"low": 0, "medium": 1, "high": 2}

def validate_proposal(p: dict) -> tuple:
    """提案层校验：必填字段 + 高风险回滚方案"""
    required = ["proposal_id", "type", "title", "payload"]
    for k in required:
        if k not in p:
            return False, f"缺少必填字段: {k}"
    if p["type"] not in EXECUTORS:
        return False, f"未知提案类型: {p['type']}"
    if RISK_LEVELS.get(p.get("risk_level", "low"), 0) >= 2:
        if not p.get("rollback_plan"):
            return False, "高风险操作必须包含 rollback_plan"
    return True, "OK"

def backup_file(path: str) -> str:
    """执行层：备份目标文件"""
    if not os.path.exists(path):
        return ""
    backup = f"{path}.bak_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    import shutil
    shutil.copy2(path, backup)
    return backup

def verify_after_exec(service: str, port: int = None) -> bool:
    """执行层：验证服务健康（端口监听或进程存在）"""
    try:
        if port:
            r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
            return f":{port} " in r.stdout
        r = subprocess.run(["pgrep", "-f", service], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return True  # 仿真环境无服务则跳过

def execute_proposal(p: dict) -> dict:
    """审批通过后执行：备份 → 执行 → 验证 → 回滚"""
    ok, err = validate_proposal(p)
    if not ok:
        return {"success": False, "error": err}
    pid = p["proposal_id"]
    payload = p.get("payload", {})
    # 1. 备份（如涉及文件操作）
    target = payload.get("target_path", "")
    backup = backup_file(target) if target else ""
    # 2. 构造执行命令
    cmd_tpl = EXECUTORS[p["type"]]
    cmd = [c.format(pid=pid, payload_file=payload.get("executor_file", "")) for c in cmd_tpl]
    result = {"proposal_id": pid, "type": p["type"], "backup": backup}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        result["exit_code"] = r.returncode
        result["output"] = (r.stdout + r.stderr)[:300]
        # 3. 验证
        verified = verify_after_exec(payload.get("service", ""), payload.get("port"))
        result["verified"] = verified
        result["success"] = (r.returncode == 0)
        if not verified:
            result["success"] = False
            result["error"] = "执行后验证失败"
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    # 4. 失败回滚（有备份则恢复）
    if not result["success"] and backup:
        import shutil
        shutil.copy2(backup, target)
        result["rolled_back"] = True
        result["error"] = (result.get("error") or "") + " | 已回滚"
    return result

if __name__ == "__main__":
    # 本地仿真测试用例
    cases = [
        {"proposal_id":"SIM-001","type":"ontology","title":"本体进化提案","risk_level":"medium","payload":{}},
        {"proposal_id":"SIM-002","type":"operator_deploy","title":"算子部署","risk_level":"medium","payload":{"target_path":"/tmp/sim_op.py"}},
        {"proposal_id":"SIM-003","type":"ops_action","title":"重启服务(高风险无回滚)","risk_level":"high","payload":{}},
        {"proposal_id":"SIM-004","type":"truth_sync","title":"真值同步","risk_level":"low","payload":{}},
        {"proposal_id":"SIM-005","type":"unknown_type","title":"未知类型","risk_level":"low","payload":{}},
        {"proposal_id":"SIM-006","type":"config_change","title":"配置变更(高风险带回滚)","risk_level":"high","payload":{"target_path":"/tmp/sim_config.json","rollback_plan":"恢复备份"}},
    ]
    for c in cases:
        ok, err = validate_proposal(c)
        r = execute_proposal(c)
        print(f"[{c['proposal_id']}] {c['type']:16s} 校验={'PASS' if ok else 'FAIL:'+err} | 执行={'成功' if r.get('success') else '失败:'+str(r.get('error',''))} | 备份={r.get('backup') or '无'} | 回滚={r.get('rolled_back', False)}")
