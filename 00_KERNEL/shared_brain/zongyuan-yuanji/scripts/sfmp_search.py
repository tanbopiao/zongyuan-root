#!/usr/bin/env python3
"""SFMP相似度检索：给z单元加向量，支持语义搜索"""
import json, glob, hashlib, math, os

def text_to_vec(text, dim=128):
    """简单hash-based向量（不依赖GPU/外部模型）"""
    vec = [0.0] * dim
    words = text.lower().split()
    for w in words:
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    # L2归一化
    norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v/norm for v in vec]

def cosine(a, b):
    return sum(x*y for x,y in zip(a,b))

# 给所有z单元补embedding
sfmp_dir = "/root/zongyuan-yuanji/var/sfmp"
files = glob.glob(sfmp_dir + "/z-*.json")
updated = 0
for f in files:
    d = json.load(open(f))
    if "embedding" not in d:
        text = d.get("assertion","") + " " + d.get("z_id","")
        d["embedding"] = text_to_vec(text)
        json.dump(d, open(f,"w"), ensure_ascii=False)
        updated += 1

print(f"已给{updated}/{len(files)}个z单元补embedding")

# 冲突检测：两两对比admitted的z单元
admitted = []
for f in files:
    d = json.load(open(f))
    if d.get("status") == "admitted" and "embedding" in d:
        admitted.append(d)

conflicts = []
for i in range(len(admitted)):
    for j in range(i+1, len(admitted)):
        sim = cosine(admitted[i]["embedding"], admitted[j]["embedding"])
        if sim > 0.8:
            conflicts.append({
                "a": admitted[i]["z_id"],
                "b": admitted[j]["z_id"],
                "similarity": round(sim, 3)
            })

print(f"冲突检测: {len(conflicts)}对高相似z单元")
for c in conflicts:
    print(f"  {c[a]} <-> {c[b]} = {c[similarity]}")
