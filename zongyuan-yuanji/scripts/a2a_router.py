#!/usr/bin/env python3
"""A2A调度路由：根据任务类型选择最合适节点"""
import json, requests, urllib3
urllib3.disable_warnings()

HUB = "https://127.0.0.1:18080/v1/a2a"

def discover(capability=None):
    """发现可用节点"""
    try:
        r = requests.post(HUB+"/discover", json={"capability":capability}, verify=False, timeout=5)
        return r.json().get("nodes", [])
    except:
        return []

def route(task_type, query):
    """根据任务类型路由"""
    nodes = discover(task_type)
    if not nodes:
        # 降级到通用chat节点
        nodes = discover("chat")
    
    if not nodes:
        return {"error": "无可用节点"}
    
    # 选第一个可用节点
    target = nodes[0]
    return {
        "node": target["name"],
        "node_id": target["id"],
        "endpoint": target["endpoint"],
        "action": "route",
        "query": query[:100]
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: a2a_router.py <capability>")
        print("  例: a2a_router.py chat")
        print("      a2a_router.py embedding")
        print("      a2a_router.py image")
        nodes = discover()
        print(f"可用节点: {len(nodes)}")
        for n in nodes:
            print(f"  {n['name']} [{','.join(n.get('capabilities',[]))}]")
    else:
        cap = sys.argv[1]
        nodes = discover(cap)
        print(f"能力 [{cap}] 可用节点: {len(nodes)}")
        for n in nodes:
            print(f"  → {n['name']} ({n['endpoint']})")
