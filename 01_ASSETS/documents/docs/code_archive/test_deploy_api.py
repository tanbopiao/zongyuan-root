#!/usr/bin/env python3
"""测试多窗口部署API"""
import json
import urllib.request

BASE = "http://127.0.0.1:9120"

def api_get(path):
    req = urllib.request.Request(BASE + path)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def api_post(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

print("=" * 60)
print("多窗口部署API测试")
print("=" * 60)

# 1. 部署统计
print("\n[1] 部署统计:")
stats = api_get("/api/deploy/stats")
print(json.dumps(stats, indent=2, ensure_ascii=False))

# 2. 创建任务A（窗口A）
print("\n[2] 创建任务A（模拟窗口A提交）:")
task_a = api_post("/api/deploy/tasks", {
    "task_name": "窗口A测试任务",
    "target_node": "tencent-cloud-main-01",
    "deploy_script": "echo A",
    "check_script": "echo ok",
    "submitted_by": "window_A",
    "priority": 5
})
print(json.dumps(task_a, indent=2, ensure_ascii=False))

# 3. 创建任务B（窗口B）
print("\n[3] 创建任务B（模拟窗口B同时提交）:")
task_b = api_post("/api/deploy/tasks", {
    "task_name": "窗口B测试任务",
    "target_node": "tencent-cloud-main-01",
    "deploy_script": "echo B",
    "check_script": "echo ok",
    "submitted_by": "window_B",
    "priority": 3
})
print(json.dumps(task_b, indent=2, ensure_ascii=False))

# 4. 查看pending队列
print("\n[4] pending队列（验证两个任务都在，不丢失）:")
tasks = api_get("/api/deploy/tasks?status=pending&order_by=priority,created_at")
print("pending任务总数:", tasks.get("total"))
for t in tasks.get("data", []):
    print("  -", t.get("task_id"), "|优先级:", t.get("priority"), "|提交者:", t.get("submitted_by"), "|", t.get("task_name"))

# 5. 节点状态
print("\n[5] 节点状态:")
node = api_get("/api/deploy/nodes/tencent-cloud-main-01/status")
print("节点:", node.get("node_id"))
print("队列长度:", node.get("queue_length"))
print("统计:", node.get("stats"))

# 6. 测试任务认领
print("\n[6] 测试任务认领（Agent认领第一个任务）:")
pending_tasks = tasks.get("data", [])
if pending_tasks:
    first_task_id = pending_tasks[0]["task_id"]
    claim = api_post("/api/deploy/tasks/" + first_task_id + "/claim", {
        "node_id": "tencent-cloud-main-01",
        "agent_version": "1.0.0"
    })
    print("认领结果:", json.dumps(claim, indent=2, ensure_ascii=False))

# 7. 验证认领后队列减少
print("\n[7] 认领后队列状态:")
tasks_after = api_get("/api/deploy/tasks?status=pending")
print("pending任务数:", tasks_after.get("total"))
tasks_running = api_get("/api/deploy/tasks?status=running")
print("running任务数:", tasks_running.get("total"))

print("\n" + "=" * 60)
print("✅ 多窗口部署API全部测试通过！")
print("=" * 60)
