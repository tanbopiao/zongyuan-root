#!/usr/bin/env python3
import json, subprocess, os

def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"ok": False, "_err": p.stderr[-200:]}

def extract_base(base_token, tables, out_prefix):
    out = {"base_token": base_token, "tables": []}
    for tid, tname in tables:
        # field list: id->name
        ff = json.load(open(f"reg1_fields/{tid}.json"))
        fs = ff.get("data", {}).get("fields", ff.get("data", {}).get("items", []))
        id2name = {f["id"]: f["name"] for f in fs}
        rows = []
        offset = 0
        while True:
            d = run(["lark-cli","base","+record-list","--base-token",base_token,"--table-id",tid,
                     "--as","user","--format","json","--limit","200","--offset",str(offset)])
            data = d.get("data", {})
            fid_list = data.get("field_id_list", [])
            names = [id2name.get(fid, fid) for fid in fid_list]
            batch = data.get("data", [])
            for r in batch:
                rows.append({names[i]: (r[i] if i < len(r) else None) for i in range(len(names))})
            if not data.get("has_more") or not batch:
                break
            offset += len(batch)
        out["tables"].append({"table_id": tid, "name": tname, "fields": names, "record_count": len(rows), "records": rows})
        print(f"  {tname}: {len(rows)} records")
    return out

print("=== Reg1 全域快照注册表 ===")
reg1 = extract_base("WBQNbr4tca2neIs23X8coL4jnch", [
    ("tblCAOoZWlXJaES2","快照注册表"),
    ("tblupyiEi8wxJJzv","昆仑洞天IP资产库"),
    ("tblzSekdjIBEtSKY","飞书资源索引"),
    ("tblwjUrcuuHg3LP9","ZONGYUAN-ROOT元规则库"),
    ("tblzUfFmQ3uZ9fUl","ZONGYUAN-ROOT元法则库"),
    ("tbl6JcYtRJx21aBs","子域隔离注册表"),
    ("tblj6UtrvvNYbLpi","架构断点清单"),
    ("tblOx2talJkurh5m","数据表"),
], "reg1")

print("=== Reg2 进化抗漂移谱系注册表 ===")
reg2 = extract_base("IKIdb7KLDapblXsvVDIcs8FLnLa", [
    ("tbl6bt6EuQrgkj6b","进化谱系记录"),
], "reg2")

json.dump(reg1, open("reg1_all_records.json","w"), ensure_ascii=False, indent=1)
json.dump(reg2, open("reg2_all_records.json","w"), ensure_ascii=False, indent=1)
print("saved both")
