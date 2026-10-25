#!/usr/bin/env python3
"""
self_learn.py 自动学习引擎
每天从日志提炼经验，优化自治脚本
"""
import json, os, time, requests

ROOT = "/home/user/ZONGYUAN-ROOT"
LEARN_LOG = f"{ROOT}/.self_learn.json"

# 加载历史学习记录
if os.path.exists(LEARN_LOG):
    with open(LEARN_LOG) as f:
        state = json.load(f)
else:
    state = {"learned_rules": [], "total_learns": 0}

# 扫描日志找异常
lessons = []
for logfile in ["/tmp/heartbeat.log", "/tmp/recycle.log", "/tmp/claim.log"]:
    if os.path.exists(logfile):
        with open(logfile) as f:
            for line in f:
                if "失败" in line or "告警" in line or "错误" in line:
                    lessons.append({"time": time.ctime(), "log": line.strip()})

# 提炼经验
if lessons:
    new_rules = [f"避免: {l['log'][:100]}" for l in lessons[:5]]
    state["learned_rules"].extend(new_rules)
    state["total_learns"] += len(new_rules)

# 上报
requests.post("https://www.huodouai.com/api/report/truth",
    json={"truth_value": f"自动学习 新经验:{len(lessons)}条 累计:{state['total_learns']}条",
          "truth_type": "meta_law"})

# 保存
with open(LEARN_LOG, "w") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print(f"学习完成，累计{state['total_learns']}条经验")
