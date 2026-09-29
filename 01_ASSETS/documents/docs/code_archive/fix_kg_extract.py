#!/usr/bin/env python3
"""修复知识图谱extract端点：将抽取结果合并到全局graph并持久化"""
import re

api_file = "/opt/ZONGYUAN-ROOT/ai-native-ops/kg_api.py"

with open(api_file, "r") as f:
    content = f.read()

# 查找全局graph变量名
match = re.search(r"^(\w+)\s*=\s*KnowledgeGraph\(\)", content, re.MULTILINE)
if match:
    global_graph_var = match.group(1)
    print("找到全局graph变量:", global_graph_var)
else:
    match = re.search(r"^(\w+)\s*=\s*KnowledgeGraph", content, re.MULTILINE)
    if match:
        global_graph_var = match.group(1)
        print("找到全局graph变量(模式2):", global_graph_var)
    else:
        global_graph_var = "graph"
        print("未找到全局graph变量，使用默认: graph")

# 修复后的extract端点代码
new_extract = '''@app.post("/api/v1/kg/extract")
def kg_extract(req: ExtractRequest):
    """抽取实体关系并合并到全局知识图谱，持久化保存"""
    g = KnowledgeGraph()
    g.parse_text(req.text)
    # 合并到全局graph
    for entity, data in g.nodes.items():
        if entity not in ''' + global_graph_var + '''.nodes:
            ''' + global_graph_var + '''.nodes[entity] = {"type": data.get("type", "unknown"), "count": 0}
        ''' + global_graph_var + '''.nodes[entity]["count"] += data.get("count", 1)
    for (a, b), data in g.edges.items():
        key = tuple(sorted([a, b]))
        if key not in ''' + global_graph_var + '''.edges:
            ''' + global_graph_var + '''.edges[key] = {"rel": data.get("rel", "co_occur"), "weight": 0}
        ''' + global_graph_var + '''.edges[key]["weight"] += data.get("weight", 1)
    # 持久化保存
    ''' + global_graph_var + '''.save()
    return {"status": "ok", "entities": list(g.nodes.keys()),
            "edges": [f"{a}-{v['rel']}->{b}" for (a, b), v in g.edges.items()],
            "total_nodes": len(''' + global_graph_var + '''.nodes),
            "total_edges": len(''' + global_graph_var + '''.edges)}

'''

# 使用正则匹配并替换extract端点
pattern = r"@app\.post\(\"/api/v1/kg/extract\"\)\s*def kg_extract\(req: ExtractRequest\):.*?(?=\n@app\.)"
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + new_extract + content[match.end():]
    print("成功替换extract端点")
else:
    print("无法匹配extract端点，请手动检查")
    # 打印附近内容帮助调试
    idx = content.find("/api/v1/kg/extract")
    if idx >= 0:
        print("找到extract位置，附近内容:")
        print(content[idx-50:idx+500])
    exit(1)

with open(api_file, "w") as f:
    f.write(content)

print("修复完成！")
print("全局graph变量:", global_graph_var)
