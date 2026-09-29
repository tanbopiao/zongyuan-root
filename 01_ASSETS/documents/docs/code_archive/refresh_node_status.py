#!/usr/bin/env python3
"""
节点 online_status 自动刷新脚本
ZONGYUAN-ROOT 自治体系 · AUTO-TOKEN-03 配套工具
用途：修正节点 online_status 字段（心跳正常但状态未刷新的问题）
"""
import requests
import json
import time
from datetime import datetime

GATEWAY_BASE = "https://www.huodouai.com/api/report"
HEARTBEAT_TIMEOUT_SEC = 300  # 5分钟无心跳视为离线
CONFIDENCE = 0.95

def get_nodes():
    """获取节点列表"""
    try:
        r = requests.get(f"{GATEWAY_BASE}/nodes", timeout=15)
        return r.json()
    except Exception as e:
        print(f"[ERROR] 获取节点列表失败: {e}")
        return None

def get_status():
    """获取网关状态"""
    try:
        r = requests.get(f"{GATEWAY_BASE}/status", timeout=15)
        return r.json()
    except Exception as e:
        print(f"[ERROR] 获取网关状态失败: {e}")
        return None

def report_truth(truth_key, truth_value):
    """上报修正真值"""
    payload = {
        "truth_key": truth_key,
        "truth_value": json.dumps(truth_value, ensure_ascii=False),
        "source_node": "NODE-DEV-DOUBAO-WORK-001",
        "confidence": CONFIDENCE,
        "truth_type": "maintenance"
    }
    try:
        r = requests.post(f"{GATEWAY_BASE}/truth", json=payload, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[ERROR] 真值上报失败: {e}")
        return None

def refresh_node_status():
    """主逻辑：检查并刷新节点状态"""
    print(f"=== 节点状态刷新 {datetime.now().isoformat()} ===")
    
    nodes_data = get_nodes()
    if not nodes_data or "nodes" not in nodes_data:
        print("[FAIL] 无法获取节点数据")
        return False
    
    status_data = get_status()
    now_ts = time.time()
    corrections = []
    
    for node_id, node_info in nodes_data["nodes"].items():
        last_hb = node_info.get("last_heartbeat", 0)
        current_status = node_info.get("online_status", "unknown")
        time_diff = now_ts - last_hb if last_hb > 0 else 999999
        
        # 判断应该的状态
        expected = "online" if time_diff < HEARTBEAT_TIMEOUT_SEC else "offline"
        
        if current_status != expected:
            print(f"  [修正] {node_id}: {current_status} → {expected} (心跳{time_diff:.0f}s前)")
            corrections.append({
                "node_id": node_id,
                "old_status": current_status,
                "new_status": expected,
                "last_heartbeat_ago_sec": round(time_diff, 1)
            })
        else:
            print(f"  [正常] {node_id}: {current_status} (心跳{time_diff:.0f}s前)")
    
    # 上报修正真值
    if corrections:
        result = report_truth(
            "NODE.STATUS.REFRESH",
            {
                "timestamp": datetime.now().isoformat(),
                "corrections": corrections,
                "total_nodes": len(nodes_data["nodes"]),
                "corrected_count": len(corrections)
            }
        )
        print(f"[上报] 修正真值已上报: {result}")
    else:
        print("[OK] 所有节点状态正常，无需修正")
    
    # 输出汇总
    print(f"\n汇总: {len(nodes_data['nodes'])}节点, {len(corrections)}个需要修正")
    return True

if __name__ == "__main__":
    refresh_node_status()
