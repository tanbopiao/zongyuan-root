#!/usr/bin/env python3
import json, glob, os, time
# 每个节点自动提炼本地资产上报
nodes = glob.glob("/root/zongyuan-yuanji/var/nodes/*.json")
print("在线节点:", len(nodes))
for n in nodes:
    d = json.load(open(n))
    print(" -", d.get("node_id", os.path.basename(n)))
