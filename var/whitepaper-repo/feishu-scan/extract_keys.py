#!/usr/bin/env python3
import json, re, os

BASE="/opt/ZONGYUAN-ROOT/ZONGYUAN-ROOT/feishu-scan"
shard=json.load(open(f"{BASE}/shard_3.json"))
cloud=set(json.load(open(f"{BASE}/cloud-keys.json"))["truths"])

def strip_ext(name):
    return re.sub(r"\.(md|json|txt|zip|tar\.gz|bat|pub|docx)$","",name,flags=re.I)

def norm(s):
    # unify separators to dots, collapse
    s=re.sub(r"[\s\-_—‑‑]+",".",s)
    s=re.sub(r"\.+",".",s).strip(".")
    return s

candidates=[]   # (key, item_name, parent)
per_item={}

for it in shard:
    name=it["name"]; typ=it["type"]; parent=it.get("parent","") or "(root)"
    raw=strip_ext(name)
    keys=set()

    # explicit编号 patterns embedded in filename
    # LOCK-... / GLOBAL-LOCK-... / SNAP-...-锁档凭证 / 全域锁档凭证-SNAP-...
    up=raw.upper()
    if "SNAP-" in up or up.startswith("全域锁档凭证") or "锁档凭证" in name:
        m=re.findall(r"SNAP[-‑]([A-Z0-9][A-Z0-9\-_.]+)", up)
        for mm in m:
            keys.add("LOCK.CREDENTIAL.SNAP."+norm(mm))
    if "LOCK" in up and not keys:
        # generic LOCK.* extraction
        m=re.findall(r"(LOCK[A-Z0-9\-_.]*)", up)
        for mm in m:
            keys.add(norm(mm))
    if up.startswith("META-RULES"):
        keys.add(norm(up))
    if up.startswith("KUNLUN"):
        keys.add(norm(up))
    if up.startswith("XUANNIAO"):
        keys.add(norm(up))
    if up.startswith("ANCHOR"):
        keys.add(norm(up))
    if up.startswith("ASSET-REPORT"):
        keys.add(norm(up))
    if up.startswith("ARCHIVE-"):
        keys.add(norm(up))
    if up.startswith("AUTOKERN-PROTO"):
        keys.add(norm(up))
    # version lock files V9.7-LOCK / LOCK-V9.7 / GLOBAL-LOCK-V6.9 / CLOUD-V6.8 etc
    vm=re.match(r"^(?:GLOBAL-LOCK-|LOCK-)?V(\d+(?:\.\d+)+)-LOCK$", up)
    if vm:
        keys.add("LOCK.V"+vm.group(1))
    if re.match(r"^LOCK-V\d", up):
        keys.add(norm(up))
    if re.match(r"^(CLOUD|SECURITY|SYNC)-V\d", up):
        keys.add(norm(up))
    # lock-report files
    if "LOCK-REPORT" in up:
        keys.add(norm(up.replace("-LOCK-REPORT","")))

    # non-text / folder / docx / bitable / shortcut -> asset meta key
    if typ in ("folder","shortcut","bitable") or name.lower().endswith((".zip",".tar.gz",".bat",".pub")):
        keys.add("asset:"+parent+":"+strip_ext(name))
    elif typ=="docx":
        keys.add("asset:docx:"+strip_ext(name))

    keys={k for k in keys if k and len(k)<200}
    per_item[name]=sorted(keys)
    for k in keys:
        candidates.append((k,name,parent))

# dedup candidate keys
allkeys=sorted(set(c[0] for c in candidates))
matched=[k for k in allkeys if k in cloud]
missing_local=[k for k in allkeys if k not in cloud]

print("items",len(shard))
print("candidate keys (uniq)",len(allkeys))
print("local cloud matched",len(matched))
print("local missing candidates",len(missing_local))
print("--- sample missing ---")
for k in missing_local[:60]:
    print(" ",k)

json.dump({"allkeys":allkeys,"matched":matched,"missing_local":missing_local,"per_item":per_item},
          open(f"{BASE}/shard_3_keys.json","w"),ensure_ascii=False,indent=1)
