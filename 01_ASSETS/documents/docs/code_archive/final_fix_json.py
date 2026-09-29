#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终修复：中文标点符号替换"""

import os
import re

target = "/opt/ZONGYUAN-ROOT/scripts/drama_auto_orchestrator.py"

# 解锁
os.system(f"chattr -i {target} 2>/dev/null")

with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 查找JSON解析部分并替换
old_parse = '''    try:
        # 清理可能的markdown代码块
        script_result = script_result.replace("```json", "").replace("```", "").strip()
        # 修复中文引号导致的JSON解析失败
        script_result = script_result.replace("\\u201c", "\\"").replace("\\u201d", "\\"")
        script_result = script_result.replace("\\u2018", "'").replace("\\u2019", "'")
        # 使用正则提取JSON（更健壮）
        import re as _re
        json_match = _re.search(r"\\{.*\\}", script_result, _re.DOTALL)
        if json_match:
            script_data = json.loads(json_match.group())
        else:
            script_data = json.loads(script_result)
    except Exception as e:
        return {"error": f"剧本JSON解析失败: {e}", "raw": script_result[:300]}'''

new_parse = '''    try:
        # 清理可能的markdown代码块
        script_result = script_result.replace("```json", "").replace("```", "").strip()
        # 修复中文标点符号导致的JSON解析失败
        script_result = script_result.replace("\\u201c", "\\"").replace("\\u201d", "\\"")
        script_result = script_result.replace("\\u2018", "'").replace("\\u2019", "'")
        script_result = script_result.replace("\\uff0c", ",").replace("\\uff1a", ":")
        script_result = script_result.replace("\\uff1b", ";").replace("\\uff08", "(").replace("\\uff09", ")")
        script_result = script_result.replace("\\u3001", ",").replace("\\u3002", ".")
        # 使用正则提取JSON（更健壮）
        import re as _re
        json_match = _re.search(r"\\{.*\\}", script_result, _re.DOTALL)
        if json_match:
            script_data = json.loads(json_match.group())
        else:
            script_data = json.loads(script_result)
    except Exception as e:
        return {"error": f"剧本JSON解析失败: {e}", "raw": script_result[:300]}'''

if old_parse in content:
    content = content.replace(old_parse, new_parse)
    print("✅ JSON解析已修复（中文标点符号替换）")
else:
    print("⚠️ 未找到精确匹配，使用简单替换")
    # 简单替换：在json.loads之前添加中文标点替换
    content = content.replace(
        'script_result = script_result.replace("\\u2018", "\'").replace("\\u2019", "\'")',
        'script_result = script_result.replace("\\u2018", "\'").replace("\\u2019", "\'")\n        script_result = script_result.replace("\\uff0c", ",").replace("\\uff1a", ":").replace("\\u3001", ",")'
    )
    print("✅ 已添加中文标点符号替换")

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

print()
print("✅ 最终修复完成！")
