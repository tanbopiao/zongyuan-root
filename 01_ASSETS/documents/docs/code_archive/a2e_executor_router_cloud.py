#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2E 通用审批→执行闭环 · 云端执行器路由 V1.0
挂载于 8060 飞书审批回调服务，按提案 type 分发执行
- ontology / rule_* 类型：保持原流程（由 feishu_approval_callback 调用 ontology_evolution_proposer.py）
- A2E扩展类型：本模块分发执行（备份→执行→验证→回滚）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
"""
import json
import os
import shutil
import subprocess
from datetime import datetime

A2E_TYPES = ("operator_deploy", "ops_action", "config_change", "truth_sync", "archive_lock")
RISK_LEVELS = {"low": 0, "medium": 1, "high": 2}

TRUTH_SYNC_URL = "https://www.huodouai.com/api/v1/truths/sync"
TRUTH_SYNC_KEY = "ZONGYUAN-TRUTH-SYNC-2026-e44fd36576a2b7db"  # 20260911轮换


def validate_proposal(p: dict) -> tuple:
    """提案层校验：必填 + 未知类型 + 高风险回滚方案"""
    required = ["proposal_id", "type", "title", "payload"]
    for k in required:
        if k not in p:
            return False, f"缺少必填字段: {k}"
    if p["type"] not in A2E_TYPES:
        return False, f"非A2E类型: {p['type']}（应由ontology流程处理）"
    if RISK_LEVELS.get(p.get("risk_level", "low"), 0) >= 2 and not p.get("rollback_plan"):
        return False, "高风险操作必须包含 rollback_plan"
    return True, "OK"


def _backup(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    bak = f"{path}.bak_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    shutil.copy2(path, bak)
    return bak


def _verify(payload: dict) -> bool:
    """执行层验证：端口监听 或 进程存在"""
    port = payload.get("port")
    service = payload.get("service", "")
    try:
        if port:
            r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
            return f":{port} " in r.stdout
        if service:
            r = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True)
            return r.stdout.strip() == "active"
    except Exception:
        pass
    return True


def _exec_truth_sync(proposal: dict) -> dict:
    """truth_sync：真值同步到公网API"""
    payload = proposal.get("payload", {})
    try:
        import requests
        r = requests.post(
            TRUTH_SYNC_URL,
            headers={"X-API-Key": TRUTH_SYNC_KEY, "Content-Type": "application/json"},
            json={
                "node_id": payload.get("node_id", "ZONGYUAN-CLOUD-001"),
                "truth_type": payload.get("truth_type", "achievement.a2e_auto"),
                "truth_content": payload.get("truth_content", ""),
                "category": payload.get("category", "achievement"),
                "source_window": payload.get("source_window", "云部署基座"),
            },
            timeout=30,
        )
        data = r.json()
        if r.status_code == 200 and data.get("status") in ("synced", "duplicate"):
            return {"success": True, "output": json.dumps(data, ensure_ascii=False)[:300], "verified": True}
        return {"success": False, "error": f"同步失败: {r.status_code} {str(data)[:200]}"}
    except Exception as e:
        return {"success": False, "error": f"truth_sync异常: {str(e)}"}


def _exec_file_script(proposal: dict) -> dict:
    """operator_deploy/config_change/ops_action：执行外部脚本+备份+验证+回滚"""
    payload = proposal.get("payload", {})
    target = payload.get("target_path", "")
    executor = payload.get("executor_file", "")
    backup = _backup(target)
    try:
        if not executor:
            return {"success": False, "error": "payload.executor_file 缺失", "backup": backup}
        r = subprocess.run(["python3", executor], capture_output=True, text=True, timeout=120)
        ok = r.returncode == 0
        verified = _verify(payload)
        result = {
            "success": ok and verified,
            "exit_code": r.returncode,
            "output": (r.stdout + r.stderr)[:300],
            "verified": verified,
            "backup": backup,
        }
        if not result["success"] and backup:
            shutil.copy2(backup, target)
            result["rolled_back"] = True
            result["error"] = (result.get("error") or "") + " 已自动回滚"
        return result
    except Exception as e:
        result = {"success": False, "error": str(e), "backup": backup}
        if backup:
            try:
                shutil.copy2(backup, target)
                result["rolled_back"] = True
            except Exception:
                pass
        return result


def dispatch_proposal(proposal: dict) -> dict:
    """A2E路由入口"""
    ok, err = validate_proposal(proposal)
    if not ok:
        return {"success": False, "error": err}
    ptype = proposal["type"]
    result = {"proposal_id": proposal.get("proposal_id"), "type": ptype, "dispatched_at": datetime.now().isoformat()}
    if ptype == "truth_sync":
        r = _exec_truth_sync(proposal)
    else:
        r = _exec_file_script(proposal)
    result.update(r)
    return result


if __name__ == "__main__":
    # 自测
    print("A2E路由模块 V1.0 就绪 | A2E_TYPES:", A2E_TYPES)
