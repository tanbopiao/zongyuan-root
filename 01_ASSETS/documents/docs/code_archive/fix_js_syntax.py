import re

with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 用正则表达式删除孤立的函数体代码
# 匹配 renderGallery 函数后面跟着的孤立代码块
pattern = r"(function renderGallery\(filter\) \{\s+currentFilter = filter;\s+applyFilters\(\);\s+\})\s+const grid = document\.getElementById\([\"']gallery-grid[\"']\);.*?\n\}"
match = re.search(pattern, content, flags=re.DOTALL)
if match:
    print(f"找到孤立代码块，长度: {len(match.group(0))} 字符")
    content = re.sub(pattern, r"\1", content, flags=re.DOTALL)
    print("已删除孤立的函数体代码")
else:
    print("未找到匹配的代码块，尝试其他模式...")
    # 尝试更宽松的匹配
    pattern2 = r"(applyFilters\(\);\s+\})\s+const grid = document\.getElementById"
    match2 = re.search(pattern2, content)
    if match2:
        print("找到第二个模式匹配")
        # 找到从这里开始到下一个function之前的多余}
        start = match2.start() + len(match2.group(1))
        # 找到下一个function
        next_func = content.find("function ", start)
        if next_func > 0:
            # 删除中间的孤立代码，但保留一个}
            # 找到最后一个}
            block = content[start:next_func]
            # 这个block应该以}开头（renderGallery的闭括号），然后是孤立代码，最后又是}
            # 我们只保留第一个}
            first_brace = block.find("}")
            if first_brace >= 0:
                new_block = block[:first_brace+1] + "\n\n"
                content = content[:start] + new_block + content[next_func:]
                print("已用第二种方式删除孤立代码")

with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print(f"文件大小: {len(content)} 字符")

# 验证语法
scripts = re.findall(r"<script[^>]*>(.*?)</script>", content, re.DOTALL)
if scripts:
    with open("/tmp/gallery_js_fixed.js", "w", encoding="utf-8") as f:
        f.write(scripts[0])
    print(f"JavaScript代码: {len(scripts[0])} 字符")
