#!/usr/bin/env python3
"""V2.7.0: 全链路端到端生产测试（计时）"""
import urllib.request, json, time

BASE = "http://127.0.0.1:8021"

def call_api(path, data):
    req = urllib.request.Request(BASE + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        elapsed = (time.time() - start) * 1000
        return {"success": True, "time_ms": round(elapsed, 1), "data": result}
    except Exception as e:
        return {"success": False, "time_ms": 0, "error": str(e)[:100]}

print("全链路端到端生产测试")
print("=" * 50)

# 阶段1: 剧本生成
print("\n阶段1: 剧本生成")
r1 = call_api("/generate/script", {"prompt": "昆仑洞天神女传说", "template": "taiyin"})
print("  结果: %s, 耗时: %.1fms" % ("成功" if r1["success"] else "失败", r1["time_ms"]))

# 阶段2: 分镜生成
print("阶段2: 分镜生成")
r2 = call_api("/generate/storyboard", {"script": "测试剧本"})
print("  结果: %s, 耗时: %.1fms" % ("成功" if r2["success"] else "失败", r2["time_ms"]))

# 阶段3: 关键帧生成（异步，只提交任务）
print("阶段3: 关键帧生成（提交任务）")
r3 = call_api("/generate/keyframe", {"prompt": "纯乌黑长发东方神女，青黑长裙，9:16竖屏", "ratio": "9:16"})
print("  结果: %s, 耗时: %.1fms" % ("成功" if r3["success"] else "失败/不支持", r3["time_ms"]))

# 阶段4: 作品库查询
print("阶段4: 作品库查询")
r4 = call_api("/drama/works/list", {"device_id": "e2e_test", "page": 1, "page_size": 5})
print("  结果: %s, 耗时: %.1fms" % ("成功" if r4["success"] else "失败", r4["time_ms"]))

# 阶段5: 热门推荐
print("阶段5: 热门推荐")
r5 = call_api("/drama/works/trending", {})
print("  结果: %s, 耗时: %.1fms, 作品数: %d" % ("成功" if r5["success"] else "失败", r5["time_ms"], len(r5.get("data", {}).get("trending", []))))

# 阶段6: 评分提交
print("阶段6: 评分提交")
r6 = call_api("/drama/works/rate", {"id": 1, "device_id": "e2e_test", "rating": 5})
print("  结果: %s, 耗时: %.1fms" % ("成功" if r6["success"] else "失败", r6["time_ms"]))

# 阶段7: 优化检查
print("阶段7: 优化检查")
r7 = call_api("/optimization/check", {})
print("  结果: %s, 耗时: %.1fms" % ("成功" if r7["success"] else "失败", r7["time_ms"]))

# 汇总
total_time = sum(r["time_ms"] for r in [r1, r2, r3, r4, r5, r6, r7])
success_count = sum(1 for r in [r1, r2, r3, r4, r5, r6, r7] if r["success"])
print("\n" + "=" * 50)
print("全链路测试汇总: %d/7成功, 总耗时%.1fms" % (success_count, total_time))
print("稳态判定: %s" % ("PASS" if success_count >= 5 else "FAIL"))
