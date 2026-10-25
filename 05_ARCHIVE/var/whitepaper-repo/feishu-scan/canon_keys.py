#!/usr/bin/env python3
import json, re
BASE="/opt/ZONGYUAN-ROOT/ZONGYUAN-ROOT/feishu-scan"
shard=json.load(open(f"{BASE}/shard_3.json"))
cloud=set(json.load(open(f"{BASE}/cloud-keys.json"))["truths"])

def stem(name):
    s=re.sub(r"\.tar\.gz$","",name,flags=re.I)
    s=re.sub(r"\.(md|json|txt|zip|bat|pub)$","",s,flags=re.I)
    s=re.sub(r"（公钥备份）","",s)
    return s.strip()

def classify(name, typ):
    u=name.upper()
    if typ=="bitable": return "asset"
    if typ in ("folder","shortcut"): return "asset"
    if name.lower().endswith((".zip",".tar.gz",".bat",".pub")): return "asset"
    if typ=="docx":
        if any(w in name for w in ["白皮书","世界观","山海经","昆仑","同源协议","元法则","真值","世界观元法则"]):
            return "ip_asset"
        return "asset"
    if "白皮书" in name or "WHITEPAPER" in u: return "whitepaper"
    if "LOCK" in u or "lock" in name or "锁档" in name or "CREDENTIAL" in u or "HARDEN" in u:
        return "lock"
    if "META" in u or "KERNEL" in u or "CONSTITUTION" in u or "ARCH" in u or "PROTO" in u or "SOP" in u or "规则" in name or "宪法" in name:
        return "meta"
    if any(w in name for w in ["昆仑","玄鸟","山海经","短剧","EP0","KF-","KD-"]) or "XUANNIAO" in u or "KUNLUN" in u:
        return "ip_asset"
    return "meta"

def make_key(it):
    name=it["name"]; typ=it["type"]; parent=it.get("parent","") or "(root)"
    # non-text & generic -> asset: meta key
    if typ in ("folder","shortcut","bitable") or name.lower().endswith((".zip",".tar.gz",".bat",".pub")):
        return f"asset:{parent}:{stem(name)}", "asset"
    s=stem(name).upper()
    s=re.sub(r"-LOCK-REPORT$","",s)
    s=re.sub(r"_+$","",s)
    # docx that are documents -> asset:docx:key
    if typ=="docx":
        return f"asset:docx:{stem(name)}", classify(name,typ)
    return s, classify(name,typ)

rows=[]
for it in shard:
    k,t=make_key(it)
    rows.append({"name":it["name"],"type":it["type"],"parent":it.get("parent","") or "(root)",
                 "token":it["token"],"key":k,"truth_type":t})

# dedup by key (keep first)
seen={}; uniq=[]
for r in rows:
    if r["key"] not in seen:
        seen[r["key"]]=r; uniq.append(r)

matched=[r for r in uniq if r["key"] in cloud]
missing=[r for r in uniq if r["key"] not in cloud]
print("items",len(shard),"unique keys",len(uniq),"matched",len(matched),"missing",len(missing))
json.dump({"matched":matched,"missing":missing}, open(f"{BASE}/shard_3_canon.json","w"),
          ensure_ascii=False,indent=1)
print("sample missing keys:")
for r in missing[:25]: print("  ",r["truth_type"],r["key"])
