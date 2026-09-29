#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复编排器JSON解析问题"""

import os

target = "/opt/ZONGYUAN-ROOT/scripts/drama_auto_orchestrator.py"

# 解锁
os.system(f"chattr -i {target} 2>/dev/null")

with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 查找并替换JSON解析部分
old = '''    try:
        # 清理可能的markdown代码块
        script_result = script_result.replace("```json", "").replace("```", "").strip()
        script_data = json.loads(script_result)
    except:
        return {"error": "剧本JSON解析失败", "raw": script_result[:200]}'''

new = '''    try:
        # 清理可能的markdown代码块
        script_result = script_result.replace("```json", "").replace("```", "").strip()
        # 修复中文引号导致的JSON解析失败
        script_result = script_result.replace("\\u201c", "\\"").replace("\\u201d", "\\"")
        script_result = script_result.replace("\\u2018", "'").replace("\\u2019", "'")
        script_data = json.loads(script_result)
    except Exception as e:
        return {"error": f"剧本JSON解析失败: {e}", "raw": script_result[:300]}'''

if old in content:
    content = content.replace(old, new)
    print("✅ JSON解析已修复（中文引号替换）")
else:
    print("⚠️ 未找到精确匹配，尝试模糊匹配...")
    # 查找包含"剧本JSON解析失败"的行
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "剧本JSON解析失败" in line:
            print(f"  找到问题行: 第{i+1}行")
            # 在json.loads之前插入中文引号替换
            for j in range(i, max(0, i-10), -1):
                if "json.loads(script_result)" in lines[j]:
                    print(f"  找到json.loads行: 第{j+1}行")
                    indent = " " * 8
                    lines.insert(j, f'{indent}script_result = script_result.replace("\\u201c", "\\"").replace("\\u201d", "\\"")')
                    lines.insert(j+1, f'{indent}script_result = script_result.replace("\\u2018", "'"'"'").replace("\\u2019", "'"'"'")')
                    print("  ✅ 已插入中文引号替换")
                    break
            break
    content = "\n".join(lines)

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(target, doraise=True)
    print("✅ Python语法验证通过")
except Exception as e:
    print(f"❌ 语法错误: {e}")

# 重新锁定
os.system(f"chattr +i {target} 2>/dev/null")

# 重启服务
os.system("systemctl restart zongyuan-drama-orchestrator 2>&1")
import time
time.sleep(2)
status = os.popen("systemctl is-active zongyuan-drama-orchestrator 2>/dev/null").read().strip()
print(f"服务状态: {status}")

print("\n✅ 修复完成！")
