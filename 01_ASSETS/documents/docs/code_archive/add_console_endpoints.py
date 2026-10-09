#!/usr/bin/env python3
"""为统一控制台API添加历史数据和告警端点"""
import sys

api_file = "/opt/ZONGYUAN-ROOT/ai-native-ops/unified_console_api.py"

with open(api_file, "r") as f:
    content = f.read()

# 添加导入
if "console_enhancer" not in content:
    content = content.replace(
        "import uvicorn",
        "import uvicorn\nimport sys\nsys.path.insert(0, \"/opt/ZONGYUAN-ROOT/ai-native-ops\")\nimport console_enhancer"
    )

# 新端点代码
endpoints_code = '''
@app.get("/api/console/history")
async def get_history(hours: int = 24):
    data = console_enhancer.get_history(hours)
    return {
        "hours": hours,
        "points": len(data),
        "data": data,
        "timestamps": [d["timestamp"] for d in data],
        "cpu": [d.get("cpu_percent", 0) for d in data],
        "memory": [d.get("memory_percent", 0) for d in data],
        "disk": [d.get("disk_percent", 0) for d in data],
        "truth_count": [d.get("truth_count", 0) for d in data],
        "kg_nodes": [d.get("kg_nodes", 0) for d in data],
    }

@app.get("/api/console/alerts")
async def get_alerts(limit: int = 20):
    alerts = console_enhancer.get_alerts(limit)
    critical = len([a for a in alerts if a.get("level") == "critical"])
    warning = len([a for a in alerts if a.get("level") == "warning"])
    unack = len([a for a in alerts if not a.get("acknowledged")])
    return {"total": len(alerts), "critical": critical, "warning": warning, "unacknowledged": unack, "alerts": alerts}

@app.post("/api/console/collect")
async def trigger_collection():
    result = console_enhancer.run_collection()
    return result

'''

# 在if __name__之前插入
content = content.replace(
    'if __name__ == "__main__":',
    endpoints_code + 'if __name__ == "__main__":'
)

with open(api_file, "w") as f:
    f.write(content)

print("端点添加成功")
print("新增端点：")
print("  GET /api/console/history")
print("  GET /api/console/alerts")
print("  POST /api/console/collect")
