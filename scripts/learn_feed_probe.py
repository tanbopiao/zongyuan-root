#!/usr/bin/env python3
# 云端内核学习装载验证 | learn_first 实际装载 SEED-TRUTH-V51 并落盘证明
import json, hashlib, time, os, sys
D="/www/wwwroot/huodouai.com/zhongshu/data"
IDX=D+"/meta-laws-index.json"; SEED=D+"/seed-truth/SEED_TRUTH_v5.1.json"
EVO=D+"/evolution"; os.makedirs(EVO,exist_ok=True)
ts=time.strftime("%Y-%m-%dT%H:%M:%S%z")
idx=json.load(open(IDX,encoding="utf-8"))
seed=json.load(open(SEED,encoding="utf-8"))
# 1) 索引装载断言
entry=next((l for l in idx["laws"] if l["law_id"]=="SEED-TRUTH-V51"),None)
assert entry, "SEED-TRUTH-V51 不在学习清单!"
# 2) 种子文件 sha 一致性
seed_sha=hashlib.sha256(open(SEED,'rb').read()).hexdigest()
assert seed_sha==entry["sha"], f"sha不一致 {seed_sha[:16]} vs {entry['sha'][:16]}"
# 3) 种子级 Merkle 可复现校验
axioms=seed["axioms"]
order={"本体层":0,"分层层":1,"工程层":2,"边界层":3,"公理层":4,"锚定层":5}
ax=sorted(axioms,key=lambda a:(order.get(a["layer"],9),a["id"]))
root="0000"
for a in ax:
    ns=hashlib.sha256(f"{a['id']}|{a['layer']}|{a['text']}|mutable=false|{a['counterexample_lock']}".encode()).hexdigest()
    root=hashlib.sha256((root+ns).encode()).hexdigest()
assert root==seed["merkle"]["root_sha256"], "种子Merkle校验失败!"
# 4) 索引 root 校验(新规则)
c="0000"
for l in idx["laws"]: c=hashlib.sha256((c+l["sha"]).encode()).hexdigest()
assert c==idx["root_sha"], "索引root校验失败!"
log={"event":"LEARN_FIRST_LOAD_VERIFY","ts":ts,"learned":True,
     "index":{"count":idx["count"],"root":idx["root_sha"],"base_root":idx.get("base_root_v50")},
     "fed_entry":{"law_id":entry["law_id"],"sha":entry["sha"][:16],"path":entry.get("path")},
     "seed_verify":{"axioms":len(axioms),"merkle_root":seed["merkle"]["root_sha256"],"layers":sorted(set(order.keys())) if False else [a["layer"] for a in ax][:1]+["..."],
                    "root_axioms":seed["root_axioms"],"hardest_six":seed.get("hardest_six")},
     "double_root":{"seed":"94fb2c5ecad5dcb6","doc":"0x9f2a7b3d8e1c4f6a"},
     "VERDICT":"LOADED_OK"}
# 落盘 append-only 装载日志
with open(EVO+"/learn-feed.log","a",encoding="utf-8") as f: f.write(json.dumps(log,ensure_ascii=False)+"\n")
print(json.dumps({"learn_first":{"learned":True,"laws":idx["count"],"VERDICT":"LOADED_OK","seed_axioms":len(axioms),"merkle":root[:16]}},ensure_ascii=False))
print("装载日志:", EVO+"/learn-feed.log")
