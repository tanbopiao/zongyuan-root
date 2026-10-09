#!/usr/bin/env python3
"""V2.6.0: 政务窗口完整业务流程接入Operator Hub"""
import sys, json, time
sys.path.insert(0, "/home/user/ZONGYUAN-ROOT/ai_proxy/operators")
from operator_hub import operator_hub

def government_production_pipeline(topic):
    """政务内容生产完整流水线"""
    print("政务生产流水线启动: %s" % topic)
    results = {}
    
    # 步骤1: 政务文案生成
    print("  步骤1: 生成政务文案...")
    r1 = operator_hub.call(
        window_id="window-government-ai",
        group="text",
        operator="generate_script",
        params={"prompt": topic}
    )
    results["script"] = "成功" if r1.get("success") else "失败"
    if r1.get("success"):
        results["script_preview"] = r1.get("script", "")[:100]
    
    # 步骤2: 文案优化
    print("  步骤2: 优化文案...")
    r2 = operator_hub.call(
        window_id="window-government-ai",
        group="text",
        operator="optimize_prompt",
        params={"prompt": topic}
    )
    results["optimize"] = "成功" if r2.get("success") else "跳过"
    
    # 步骤3: 旁白提取
    print("  步骤3: 提取旁白...")
    r3 = operator_hub.call(
        window_id="window-government-ai",
        group="text",
        operator="extract_narration",
        params={"script": r1.get("script", "") if r1.get("success") else topic}
    )
    results["narration"] = "成功" if r3.get("success") else "跳过"
    
    # 步骤4: 保存任务
    print("  步骤4: 保存生产任务...")
    r4 = operator_hub.call(
        window_id="window-government-ai",
        group="storage",
        operator="persist_task",
        params={"task_type": "government_production", "topic": topic, "status": "completed"}
    )
    results["persist"] = "成功" if r4.get("success") else "跳过"
    
    # 统计
    stats = operator_hub.get_stats()
    results["hub_calls"] = stats.get("total_calls", 0)
    results["windows"] = stats.get("registered_windows", 0)
    
    print("政务生产流水线完成:")
    for k, v in results.items():
        print("  %s: %s" % (k, v))
    return results

if __name__ == "__main__":
    government_production_pipeline("政务公开宣传")
