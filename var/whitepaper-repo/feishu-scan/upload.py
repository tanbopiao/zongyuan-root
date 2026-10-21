#!/usr/bin/env python3
import json, urllib.request, urllib.error, time
BASE="/opt/ZONGYUAN-ROOT/ZONGYUAN-ROOT/feishu-scan"
d=json.load(open(f"{BASE}/shard_3_canon.json"))
missing=d["missing"]; matched=d["matched"]

def summarize(r):
    name=r["name"]; parent=r["parent"]; t=r["truth_type"]; typ=r["type"]
    type_cn={"lock":"锁档凭证/回执","asset":"资产条目","meta":"元规则/内核配置",
             "whitepaper":"技术白皮书","ip_asset":"IP/世界观资产"}.get(t,"资产")
    return f"本地飞书持久化存储层提炼：{type_cn}「{name}」，归档目录「{parent}」，类型={typ}，来源节点 local-feishu-extract。"

URL="https://www.huodouai.com/api/report/truth"
uploaded=[]; failed=[]
for i,r in enumerate(missing):
    body=json.dumps({
        "truth_key":r["key"],
        "truth_value":summarize(r),
        "source_node":"local-feishu-extract",
        "confidence":0.95,
        "truth_type":r["truth_type"],
    }).encode()
    req=urllib.request.Request(URL,data=body,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=25) as resp:
            txt=resp.read().decode()[:200]
            uploaded.append({"truth_key":r["key"],"truth_type":r["truth_type"],"http":resp.status,"resp":txt})
    except urllib.error.HTTPError as e:
        failed.append({"key":r["key"],"err":f"HTTP{e.code}:{e.read().decode()[:120]}"})
    except Exception as e:
        failed.append({"key":r["key"],"err":str(e)[:120]})
    if (i+1)%40==0:
        print(f"progress {i+1}/{len(missing)} ok={len(uploaded)} fail={len(failed)}")
    time.sleep(0.05)

print("DONE uploaded",len(uploaded),"failed",len(failed))
json.dump({"uploaded":uploaded,"failed":failed}, open(f"{BASE}/shard_3_upload.json","w"),
          ensure_ascii=False,indent=1)
