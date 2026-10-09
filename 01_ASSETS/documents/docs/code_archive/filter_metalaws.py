#!/usr/bin/env python3
import json

with open("/tmp/all_metalaws.json") as f:
    data = json.load(f)

metalaws = data["metalaws"]
print("总元法则相关记录:", len(metalaws))

# 筛选核心元法则
core = []
for m in metalaws:
    key = m["key"]
    if key.startswith("CLASSIFICATION."): continue
    if key.startswith("APPROVAL_PENDING"): continue
    if "observation" in key.lower() or "snapshot" in key.lower(): continue
    if key.startswith("LOCK.") and "METARULE" not in key: continue
    core.append(m)

print("核心元法则:", len(core))

# 按类型分组
groups = {}
for m in core:
    key = m["key"]
    if key.startswith("MR-"): g = "MR-系列"
    elif key.startswith("METALAW."): g = "METALAW系列"
    elif key.startswith("METARULE."): g = "METARULE系列"
    elif key.startswith("META-RULE."): g = "META-RULE系列"
    elif key.startswith("META_LAW."): g = "META_LAW系列"
    elif key.startswith("meta_law."): g = "meta_law系列"
    else: g = "其他"
    groups.setdefault(g, []).append(m)

for g, items in sorted(groups.items()):
    print("\n=== " + g + " (" + str(len(items)) + "条) ===")
    for m in sorted(items, key=lambda x: x["key"]):
        k = m["key"]
        title = k
        try:
            v = m["value"]
            if isinstance(v, str) and v.startswith("{"):
                vj = json.loads(v)
                title = vj.get("title", vj.get("name", vj.get("law_id", k)))
        except: pass
        print("  " + k)
        print("    -> " + str(title)[:90])

with open("/tmp/core_metalaws.json", "w") as f:
    json.dump({"total": len(core), "metalaws": core}, f, ensure_ascii=False, indent=2)
print("\n核心元法则已保存:", len(core), "条")
