#!/usr/bin/env python3
"""自动蒸馏：每天从轨迹/经验提炼高价值z单元"""
import json, glob, os, time

sfmp_dir = "/root/zongyuan-yuanji/var/sfmp"
os.makedirs(sfmp_dir, exist_ok=True)

def propose_z(z_id, label, content, confidence, tag="distilled"):
    z = {
        "z_id": z_id, "label": label, "content": content,
        "confidence_U": confidence, "tag": tag,
        "status": "pending_multi_tenant_verify", "votes": {},
        "proposed_at": int(time.time()), "tenant": "auto_distill",
        "trust_evidence": "每日自动蒸馏提炼"
    }
    fn = sfmp_dir + "/z-" + z_id + ".json"
    if os.path.exists(fn): return False
    json.dump(z, open(fn, "w"), ensure_ascii=False)
    return True

# 从轨迹提炼成功模式
traj_files = sorted(glob.glob("/root/zongyuan-yuanji/var/trajectories/*.json"))[-50:]
patterns = {}
for f in traj_files:
    try:
        d = json.load(open(f))
        if d.get("result") == "ok":
            action = d.get("action", d.get("cmd", "unknown"))
            patterns[action] = patterns.get(action, 0) + 1
    except: pass

new_count = 0
for action, count in sorted(patterns.items(), key=lambda x: -x[1])[:10]:
    safe = action.replace("/","-").replace(" ","-")[:30]
    zid = "Z-PATTERN-" + safe
    label = "高频操作: " + action
    content = "操作 " + action + " 在最近50条轨迹中出现" + str(count) + "次且全部成功"
    if propose_z(zid, label, content, 0.7):
        new_count += 1

# 从元法则提炼
meta_files = glob.glob("/root/zongyuan-yuanji/var/truth-cache/meta-rules/*.json")
for f in meta_files[:10]:
    try:
        d = json.load(open(f))
        law_id = d.get("law_id", "")
        name = d.get("name", "")
        if law_id and name:
            zid = "Z-LAW-" + law_id
            content = "元法则 " + law_id + ": " + name
            if propose_z(zid, name, content, 0.85, tag="meta_law"):
                new_count += 1
    except: pass

print("蒸馏完成: 扫描" + str(len(traj_files)) + "轨迹 → 新增" + str(new_count) + "个z单元")
