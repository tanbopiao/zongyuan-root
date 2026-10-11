#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能：魔搭数据湖活性处理引擎（数据湖 vs 冷存储：活性扫描/索引/质检）
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
用法：python3 kunlun_lake_living.py [--repo zongyuanroot/zongyuan-root-achievements]
输出：_lake_active_index.json（活性索引）+ 质检报告
"""
import json, sys, os, urllib.request, urllib.parse, collections, datetime

REPO = "zongyuanroot/zongyuan-root-achievements"
if "--repo" in sys.argv:
    REPO = sys.argv[sys.argv.index("--repo") + 1]

def tree_api(repo):
    url = f"https://www.modelscope.cn/api/v1/datasets/{repo}/repo/tree?Recursive=true&Revision=master"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def main():
    d = tree_api(REPO)
    files = [f for f in d["Data"]["Files"] if f.get("Type") == "blob"]
    dirs = [f for f in d["Data"]["Files"] if f.get("Type") == "tree"]
    cat, ext = collections.Counter(), collections.Counter()
    for f in files:
        e = f["Name"].rsplit(".", 1)[-1].lower() if "." in f["Name"] else "(none)"
        ext[e] += 1
        p = f["Path"]
        cat["data_lake" if p.startswith("data_lake") else ("顶层" if "/" not in p else "数据区")] += 1
    sha = collections.Counter(f["Sha256"] for f in files if f["Sha256"])
    dup = {k: v for k, v in sha.items() if v > 1}
    index = {
        "schema": "数据湖活性索引 V1.0", "repo": REPO,
        "scan_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dirs": len(dirs), "files": len(files),
        "total_size": sum(f.get("Size", 0) for f in files),
        "categories": dict(cat), "extensions": dict(ext.most_common(15)),
        "quality": {
            "unique_sha": len(sha), "dup_sha_groups": len(dup),
            "lone_top_files": sum(1 for f in files if "/" not in f["Path"]),
        },
        "assets": [{"name": f["Name"], "path": f["Path"], "size": f.get("Size", 0),
                    "sha256": f.get("Sha256", "")[:12]} for f in files],
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_lake_active_index.json")
    json.dump(index, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"✅ 活性索引: 目录{len(dirs)}/文件{len(files)}/{(index['total_size']/1048576):.1f}MB")
    print(f"   分类:{dict(cat)} | 扩展:{dict(ext.most_common(8))}")
    print(f"   质检: 唯一sha{len(sha)} 重复组{len(dup)} 顶层散落{index['quality']['lone_top_files']}")
    print(f"   输出: {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
