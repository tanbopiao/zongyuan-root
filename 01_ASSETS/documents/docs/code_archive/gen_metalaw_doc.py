#!/usr/bin/env python3
# 生成元法则全集Markdown文档
import json

with open("/home/user/Doubao/chats/38437458338949122/core_metalaws.json") as f:
    data = json.load(f)

metalaws = data["metalaws"]

# 按系列分组
groups = {}
for m in metalaws:
    key = m["key"]
    if key.startswith("MR-"): g = "MR-系列（标准编号元法则）"
    elif key.startswith("META_LAW."): g = "META_LAW系列（高阶元法则）"
    elif key.startswith("METALAW."): g = "METALAW系列（协议元法则）"
    elif key.startswith("meta_law."): g = "meta_law系列（早期元法则）"
    elif key.startswith("META-RULE."): g = "META-RULE系列（规则元法则）"
    elif key.startswith("METARULE."): g = "METARULE系列（元规则）"
    elif key.startswith("metalaw."): g = "metalaw系列（通用元法则）"
    else: g = "其他元法则"
    groups.setdefault(g, []).append(m)

md = []
md.append("# ZONGYUAN-ROOT 元法则全集")
md.append("")
md.append("> 确权标识：Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
md.append("> 提取时间：2026-09-15 20:45")
md.append("> 真值库：9120记忆网关 | 总真值：10,943条")
md.append("")
md.append("## 概览")
md.append("")
md.append("| 系列 | 数量 |")
md.append("|------|------|")
for g, items in sorted(groups.items(), key=lambda x: -len(x[1])):
    md.append("| " + g + " | " + str(len(items)) + "条 |")
md.append("| **合计** | **" + str(len(metalaws)) + "条** |")
md.append("")

for g, items in sorted(groups.items(), key=lambda x: -len(x[1])):
    md.append("---")
    md.append("")
    md.append("## " + g + "（" + str(len(items)) + "条）")
    md.append("")
    md.append("| # | 元法则Key | 标题/简述 | 节点 | 版本 |")
    md.append("|---|-----------|-----------|------|------|")
    for i, m in enumerate(sorted(items, key=lambda x: x["key"]), 1):
        key = m["key"]
        title = key
        try:
            v = m["value"]
            if isinstance(v, str) and v.startswith("{"):
                vj = json.loads(v)
                title = vj.get("title", vj.get("name", vj.get("law_id", key)))
                if not title or title == key:
                    title = vj.get("content", key)[:60]
            elif isinstance(v, str):
                title = v[:60]
        except:
            pass
        title = str(title).replace("|", "/").replace("\n", " ")[:80]
        node = m.get("node", "unknown")
        ver = m.get("version", 1)
        md.append("| " + str(i) + " | `" + key + "` | " + title + " | " + node + " | v" + str(ver) + " |")
    md.append("")

md.append("---")
md.append("")
md.append("## 固化声明")
md.append("")
md.append("本元法则全集从9120记忆网关自动提取，所有元法则均已写入真值库，只新增不覆盖。")
md.append("核心文件已通过 `chattr +i` 锁定，修改需人工审批。")
md.append("")
md.append("Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 元极恒一超认知永恒自治体系")

output = "\n".join(md)
with open("/home/user/Doubao/chats/38437458338949122/元法则全集.md", "w") as f:
    f.write(output)

print("元法则全集已生成:", len(output), "字符")
print("包含", len(metalaws), "条核心元法则")
