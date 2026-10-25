#!/usr/bin/env python3
"""自学习 执行态：从历史执行记录提取经验"""
import json, os
LOG = "core/runtime/.learn_log.json"

def record(task, score, lessons):
    data = json.load(open(LOG)) if os.path.exists(LOG) else []
    data.append({'task':task,'score':score,'lessons':lessons})
    json.dump(data, open(LOG,'w'), ensure_ascii=False)

def best_practice():
    if not os.path.exists(LOG): return "暂无经验"
    data = json.load(open(LOG))
    good = [d for d in data if d['score']>=80]
    if not good: return "暂无达标经验"
    return f"{len(good)}条达标经验，最新: {good[-1]['lessons']}"

if __name__ == "__main__":
    record("adaptive_shard", 91, "小任务不拆效率高")
    record("quality_gate", 88, "先查缺项再查内容")
    print(f"  经验库: {best_practice()}")
