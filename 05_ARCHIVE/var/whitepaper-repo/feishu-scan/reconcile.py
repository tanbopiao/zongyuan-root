#!/usr/bin/env python3
import json, re

# load cloud keys
ck = json.load(open("cloud-keys.json"))
cloud_set = set(k for k in ck.get("truths", []) if k)
print("cloud keys loaded:", len(cloud_set))

def norm(s):
    if s is None: return ""
    if isinstance(s, list): s = ".".join(str(x) for x in s)
    return str(s).strip()

def dotkey(prefix, *parts):
    ks = []
    for p in parts:
        p = norm(p)
        if not p: continue
        p = p.upper().replace(" ", "_").replace("/", "_").replace("-", "_").replace(".", "_")
        p = re.sub(r"_+", "_", p).strip("_")
        ks.append(p)
    return prefix + "." + ".".join(ks) if ks else None

reg1 = json.load(open("reg1_all_records.json"))
reg2 = json.load(open("reg2_all_records.json"))

extracted = []  # (key, table, summary, truth_type)

# Reg1
for t in reg1["tables"]:
    tn = t["name"]
    for r in t["records"]:
        if tn == "快照注册表":
            sid = norm(r.get("快照ID"))
            key = dotkey("REG.SNAPSHOT", sid)
            summ = f"快照{sid}｜层级{norm(r.get('层级'))}｜状态{norm(r.get('状态'))}｜资产数{norm(r.get('资产数'))}｜归档节点{norm(r.get('归档节点'))}｜DID{norm(r.get('DID'))}"
            ttype = "lock"
        elif tn == "昆仑洞天IP资产库":
            key = dotkey("REG.IP", r.get("IP名称"))
            summ = f"IP资产{norm(r.get('IP名称'))}｜类型{norm(r.get('IP类型'))}｜形态{norm(r.get('形态'))}｜风格{norm(r.get('视觉风格'))}｜批次{norm(r.get('量产批次'))}｜状态{norm(r.get('状态'))}"
            ttype = "ip_asset"
        elif tn == "飞书资源索引":
            key = dotkey("REG.RESOURCE", r.get("资源名称"))
            summ = f"飞书资源{norm(r.get('资源名称'))}｜类型{norm(r.get('资源类型'))}｜父级{norm(r.get('父级'))}｜状态{norm(r.get('状态'))}"
            ttype = "meta"
        elif tn == "ZONGYUAN-ROOT元规则库":
            key = dotkey("REG.META_RULE", r.get("规则编号"))
            summ = f"元规则{norm(r.get('规则编号'))} {norm(r.get('规则名称'))}｜层级{norm(r.get('层级'))}｜约束{norm(r.get('约束类型'))}｜内容{norm(r.get('规则内容'))[:60]}"
            ttype = "meta"
        elif tn == "ZONGYUAN-ROOT元法则库":
            key = dotkey("REG.META_LAW", r.get("法则编号"))
            summ = f"元法则{norm(r.get('法则编号'))} {norm(r.get('法则名称'))}｜位阶{norm(r.get('位阶'))}｜内容{norm(r.get('法则内容'))[:60]}"
            ttype = "meta"
        elif tn == "子域隔离注册表":
            key = dotkey("REG.SUBDOMAIN", r.get("子域ID"))
            summ = f"子域{norm(r.get('子域ID'))} {norm(r.get('子域名称'))}｜法权{norm(r.get('法权'))}｜命名空间{norm(r.get('命名空间前缀'))}｜状态{norm(r.get('状态'))}"
            ttype = "meta"
        elif tn == "架构断点清单":
            key = dotkey("REG.BREAKPOINT", r.get("断点ID"))
            summ = f"断点{norm(r.get('断点ID'))} {norm(r.get('断点名称'))}｜根因{norm(r.get('根因摘要'))[:50]}"
            ttype = "meta"
        else:
            continue  # 数据表 generic, skip
        if key:
            extracted.append({"key": key, "table": tn, "summary": summ, "type": ttype})

# Reg2
for t in reg2["tables"]:
    for r in t["records"]:
        no = norm(r.get("谱系编号"))
        key = dotkey("REG.EVOLUTION", no)
        summ = f"进化谱系{no}｜代数{norm(r.get('进化代数'))}｜漂移分{norm(r.get('漂移分数'))}｜适应度{norm(r.get('最优适应度'))}｜状态{norm(r.get('状态'))}｜备注{norm(r.get('备注'))[:50]}"
        extracted.append({"key": key, "table": t["name"], "summary": summ, "type": "meta"})

print("total keys extracted:", len(extracted))

# dedupe
seen = {}
for e in extracted:
    seen.setdefault(e["key"], e)
extracted = list(seen.values())
print("unique keys:", len(extracted))

# local fast screen
matched = [e for e in extracted if e["key"] in cloud_set]
missing_local = [e for e in extracted if e["key"] not in cloud_set]
print("cloud-matched (local):", len(matched))
print("missing (local, needs GET confirm):", len(missing_local))

json.dump({"extracted": extracted, "matched_keys": [e["key"] for e in matched],
           "missing_local": missing_local},
          open("recon_pre.json","w"), ensure_ascii=False, indent=1)
for e in missing_local[:20]:
    print("  MISS?", e["key"])
