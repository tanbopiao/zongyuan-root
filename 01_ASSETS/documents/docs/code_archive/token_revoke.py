#!/usr/bin/env python3
"""
Token 吊销脚本
ZONGYUAN-ROOT 自治体系 · AUTO-TOKEN-03 熔断工具
支持：单节点吊销 + 全局批量熔断吊销
"""
import requests
import json
import sys
import hashlib
from datetime import datetime

GATEWAY_BASE = "https://www.huodouai.com/api"
MAIN_TOKEN = "${MAIN_CAPTURE_TOKEN}"  # 从环境变量注入
CONFIDENCE = 0.99

# 5节点基线（与内核锁档一致）
NODE_BASELINE = {
    "NODE-001": {"name": "作品库节点", "level": "L1"},
    "NODE-002": {"name": "3D沙盘节点", "level": "L0"},
    "NODE-003": {"name": "算子Worker", "level": "L2"},
    "NODE-004": {"name": "记忆网关节点", "level": "L1"},
    "NODE-005": {"name": "监控面板节点", "level": "L0"},
}

def report_truth(truth_key, truth_value, truth_type="risk"):
    """上报真值"""
    payload = {
        "truth_key": truth_key,
        "truth_value": json.dumps(truth_value, ensure_ascii=False),
        "source_node": "MAIN-HUB",
        "confidence": CONFIDENCE,
        "truth_type": truth_type
    }
    try:
        r = requests.post(f"{GATEWAY_BASE}/report/truth", json=payload, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[ERROR] 真值上报失败: {e}")
        return None

def revoke_single(node_did, reason="manual_revoke"):
    """
    吊销单个节点子Token
    生产模式：调用 DELETE /api/token/revoke
    仿真模式：仅记录真值
    """
    if node_did not in NODE_BASELINE:
        print(f"[ERROR] 未知节点: {node_did}")
        return False
    
    node_info = NODE_BASELINE[node_did]
    print(f"\n=== 吊销节点 {node_did} ({node_info['name']}) ===")
    print(f"  原因: {reason}")
    
    # 生产模式端点（待开放后启用）
    # headers = {"X-Capture-Token": MAIN_TOKEN}
    # resp = requests.delete(f"{GATEWAY_BASE}/token/revoke", json={"node_did": node_did}, headers=headers)
    
    # 仿真/预激活模式：直接记录真值
    record = {
        "node_did": node_did,
        "node_name": node_info["name"],
        "permission_level": node_info["level"],
        "revoked_at": datetime.now().isoformat(),
        "reason": reason,
        "revoked_by": "MAIN-HUB",
        "status": "REVOKED"
    }
    
    result = report_truth(f"TOKEN.REVOKE.{node_did}", record, truth_type="risk")
    if result:
        print(f"  [成功] 吊销真值已上报: {result.get('action', 'unknown')}")
    else:
        print(f"  [失败] 真值上报失败")
    return True

def revoke_all(reason="global_fuse"):
    """
    全局批量熔断吊销
    一键吊销所有节点子Token
    """
    print(f"\n{'='*50}")
    print(f"⚠️  全局熔断吊销 — 即将吊销全部5个节点Token")
    print(f"   原因: {reason}")
    print(f"{'='*50}")
    
    confirm = input("确认执行全局熔断？输入 YES 继续: ")
    if confirm != "YES":
        print("[取消] 未确认，全局熔断已取消")
        return False
    
    revoked = []
    for node_did in NODE_BASELINE:
        success = revoke_single(node_did, reason=reason)
        if success:
            revoked.append(node_did)
    
    # 批量熔断汇总真值
    summary = {
        "triggered_at": datetime.now().isoformat(),
        "reason": reason,
        "total_revoked": len(revoked),
        "revoked_nodes": revoked,
        "triggered_by": "MAIN-HUB",
        "action": "GLOBAL_FUSE"
    }
    
    result = report_truth("TOKEN.GLOBAL.FUSE", summary, truth_type="risk")
    print(f"\n=== 全局熔断完成 ===")
    print(f"  吊销节点数: {len(revoked)}/5")
    print(f"  汇总真值: {result}")
    return True

def list_nodes():
    """列出所有节点及权限"""
    print("\n=== 5同源节点列表 ===")
    for did, info in NODE_BASELINE.items():
        print(f"  {did:12s} | {info['level']:3s} | {info['name']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 token_revoke.py list              # 列出所有节点")
        print("  python3 token_revoke.py revoke <NODE-DID> # 吊销单节点")
        print("  python3 token_revoke.py fuse               # 全局熔断")
        print()
        print("示例:")
        print("  python3 token_revoke.py revoke NODE-002")
        print("  python3 token_revoke.py fuse")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        list_nodes()
    elif cmd == "revoke" and len(sys.argv) >= 3:
        revoke_single(sys.argv[2])
    elif cmd == "fuse":
        revoke_all()
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
