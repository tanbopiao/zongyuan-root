#!/usr/bin/env python3
"""
矩阵组织资源调度 V3.1 - 同源协议接入版
接入huodouai身份节点，支持云内核同步+本地降级
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
"""
import json
import numpy as np
import requests
from datetime import datetime

# ===================== 同源协议配置 =====================
HOMO_CONFIG = {
    "node_id": "ext-agent-1788663115-3e3fd867",
    "node_name": "ZONGYUAN-ROOT-MetaAxiom-Foundation-Node",
    "api_key": "zy-101e3e6f7188482f87bca9e806ca7c5d775a6e44e4784772",
    "base_url": "https://www.huodouai.com/v1",
    "handshake_url": "https://www.huodouai.com/anchor/api/v1/sync/handshake",
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "did": "DID-BR-000002",
}

def build_headers():
    """构建同源协议认证头（仅ASCII，避免编码错误）"""
    return {
        "Authorization": f"Bearer {HOMO_CONFIG['api_key']}",
        "X-Node-ID": HOMO_CONFIG["node_id"],
        "Content-Type": "application/json"
    }

def sync_to_cloud(payload):
    """同步调度结果到云内核"""
    try:
        resp = requests.post(
            HOMO_CONFIG["handshake_url"],
            headers=build_headers(),
            json=payload,
            timeout=8
        )
        if resp.status_code == 200:
            return {"status": "ONLINE", "cloud_resp": resp.json()}
        else:
            return {"status": "DEGRADED", "reason": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "OFFLINE_DEGRADED", "reason": str(e)}

# ===================== 调度核心（同V3） =====================
RESOURCE_POOL = [
    {"id":"A1","name":"火山豆包Pro","load":0.0,"tags":["model","main"],"vec":np.array([0.85,0.70,0.20,0.40])},
    {"id":"A2","name":"火山豆包Pro-Key3","load":0.0,"tags":["model","backup"],"vec":np.array([0.82,0.68,0.22,0.38])},
    {"id":"V1","name":"视觉A","load":0.0,"tags":["visual"],"vec":np.array([0.20,0.90,0.15,0.30])},
    {"id":"V2","name":"视觉B","load":0.0,"tags":["visual"],"vec":np.array([0.18,0.88,0.16,0.32])},
    {"id":"V3","name":"视觉C","load":0.0,"tags":["visual"],"vec":np.array([0.22,0.86,0.14,0.29])},
    {"id":"W1","name":"提示词初稿(智谱)","load":0.0,"tags":["prompt","draft"],"vec":np.array([0.70,0.40,0.85,0.25])},
    {"id":"W2","name":"提示词精修","load":0.0,"tags":["prompt","refine"],"vec":np.array([0.75,0.42,0.88,0.27])},
    {"id":"O1","name":"运维内核组","load":0.0,"tags":["ops"],"vec":np.array([0.10,0.20,0.30,0.92])},
    {"id":"C1","name":"合规锁档组","load":0.0,"tags":["audit"],"vec":np.array([0.12,0.22,0.32,0.90])},
    {"id":"IMA1","name":"IMA知识库","load":0.0,"tags":["knowledge"],"vec":np.array([0.78,0.35,0.72,0.40])},
    {"id":"BK1","name":"百度网盘","load":0.0,"tags":["storage"],"vec":np.array([0.08,0.25,0.20,0.85])},
]

PROJECTS = [
    {"pid":"P01","name":"太阴月神PV","priority":1,"deadline_days":7,"tags":["model","visual","audit","storage"],"vec":np.array([0.84,0.86,0.30,0.50])},
    {"pid":"P02","name":"九天玄女EP05","priority":2,"deadline_days":10,"tags":["model","prompt","audit"],"vec":np.array([0.80,0.50,0.82,0.45])},
    {"pid":"P03","name":"RAG知识库","priority":3,"deadline_days":14,"tags":["model","knowledge","audit"],"vec":np.array([0.79,0.38,0.75,0.42])},
    {"pid":"P04","name":"短剧量产线","priority":2,"deadline_days":11,"tags":["prompt","visual","knowledge","storage"],"vec":np.array([0.76,0.84,0.80,0.48])},
    {"pid":"P05","name":"运维巡检系统","priority":1,"deadline_days":5,"tags":["ops","audit"],"vec":np.array([0.11,0.21,0.31,0.91])},
]

def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-8 else v

def inner(pv, rv):
    return float(np.dot(norm(pv), norm(rv)))

def score(proj, res):
    sem = inner(proj["vec"], res["vec"])
    p = (5 - proj["priority"]) / 5
    d = 1.0 / (proj["deadline_days"] + 1)
    u = 1.0 - res["load"]
    return 0.4*sem + 0.2*d + 0.2*p + 0.2*u

def allocate(resources, projects, threshold=0.8):
    result = {}
    alerts = []
    for proj in sorted(projects, key=lambda x: (x["priority"], x["deadline_days"])):
        pid = proj["pid"]
        result[pid] = {"project": proj["name"], "assigned": []}
        for tag in proj["tags"]:
            candidates = [r for r in resources if tag in r["tags"] and r["load"] < threshold]
            if not candidates:
                alerts.append(f"⚠️ {pid} 标签{tag}无可用资源")
                continue
            candidates.sort(key=lambda r: score(proj, r), reverse=True)
            pick = candidates[0]
            pick["load"] += 0.22
            result[pid]["assigned"].append(pick["name"])
    return result, alerts

# ===================== 主程序 =====================
if __name__ == "__main__":
    print("=" * 60)
    print("矩阵调度 V3.1 | 同源协议接入版")
    print(f"节点: {HOMO_CONFIG['node_name']}")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. 云内核握手
    print("\n[1/3] 云内核握手...")
    sync_result = sync_to_cloud({"action": "handshake", "node": HOMO_CONFIG["node_id"]})
    print(f"  状态: {sync_result['status']}")
    if sync_result['status'] != "ONLINE":
        print(f"  原因: {sync_result.get('reason', 'N/A')}")
        print("  → 降级本地仿真模式")

    # 2. 执行调度
    print("\n[2/3] 执行酉空间语义调度...")
    alloc, alerts = allocate(RESOURCE_POOL, PROJECTS)
    for pid, item in alloc.items():
        print(f"  {pid} {item['project']}: {', '.join(item['assigned'])}")
    if alerts:
        for a in alerts:
            print(f"  {a}")

    # 3. 同步结果
    print("\n[3/3] 同步调度结果到云内核...")
    payload = {
        "action": "sync_schedule",
        "snapshot": "SNAP-20260909-MATRIX-V3.1",
        "allocations": alloc,
        "alerts": alerts,
        "anchor": HOMO_CONFIG["anchor"],
        "did": HOMO_CONFIG["did"]
    }
    sync_result2 = sync_to_cloud(payload)
    print(f"  状态: {sync_result2['status']}")

    # 输出统计
    total_load = sum(r["load"] for r in RESOURCE_POOL) / len(RESOURCE_POOL)
    print(f"\n平均利用率: {total_load:.2%}")
    print(f"告警数: {len(alerts)}")
    print("=" * 60)
    print("✅ V3.1同源协议调度完成")

    # 保存结果
    with open("/tmp/matrix_v3_1_result.json", "w") as f:
        json.dump({
            "snapshot": "SNAP-20260909-MATRIX-V3.1",
            "cloud_status": sync_result2["status"],
            "allocations": alloc,
            "alerts": alerts,
            "avg_util": total_load
        }, f, ensure_ascii=False, indent=2)
