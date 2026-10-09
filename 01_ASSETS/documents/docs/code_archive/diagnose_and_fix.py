#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断并修复JSON解析问题"""

import sys
sys.path.insert(0, "/opt/ZONGYUAN-ROOT/scripts")

import importlib.util
import json
import re
import os

spec = importlib.util.spec_from_file_location("orchestrator", "/opt/ZONGYUAN-ROOT/scripts/drama_auto_orchestrator.py")
orchestrator = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(orchestrator)
except SystemExit:
    pass

# 直接调用AI，查看原始输出
print("【1】调用AI生成剧本，查看原始输出")
script_prompt = """你是昆仑洞天短剧编剧。请为第1集《测试》生成剧本大纲。
要求：
1. 3个场景
2. 每个场景包含：场景编号、地点、时间、出场角色、简要情节
3. 只输出JSON格式，不要其他文字

格式：
{"synopsis":"概要","scenes":[
  {"scene_no":1,"location":"地点","time":"时间","characters":["角色1"],"plot":"情节"}
]}"""

result = orchestrator.call_ai(script_prompt, max_tokens=600)
print("原始输出前500字符:")
print(repr(result[:500]))
print()

# 尝试各种修复方式
print("【2】尝试各种JSON修复方式")

# 方式1: 替换中文引号
fixed = result.replace("```json", "").replace("```", "").strip()
fixed = fixed.replace("\u201c", '"').replace("\u201d", '"')
fixed = fixed.replace("\u2018", "'").replace("\u2019", "'")

try:
    data = json.loads(fixed)
    print("  ✅ 方式1成功（中文引号替换）")
    print("  synopsis:", data.get("synopsis", "")[:50])
    print("  scenes:", len(data.get("scenes", [])))
except Exception as e:
    print(f"  ❌ 方式1失败: {e}")
    
    # 方式2: 使用正则提取JSON
    print("  尝试方式2: 正则提取JSON...")
    match = re.search(r'\{.*\}', fixed, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            print("  ✅ 方式2成功（正则提取）")
        except Exception as e2:
            print(f"  ❌ 方式2失败: {e2}")
            print("  JSON片段:")
            print(match.group()[:300])

# 修复编排器中的JSON解析
print()
print("【3】修复编排器中的JSON解析")

target = "/opt/ZONGYUAN-ROOT/scripts/drama_auto_orchestrator.py"
os.system(f"chattr -i {target} 2>/dev/null")

with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 替换JSON解析部分，使用更健壮的方式
old_parse = '''    try:
        # 清理可能的markdown代码块
        script_result = script_result.replace("```json", "").replace("```", "").strip()
        # 修复中文引号导致的JSON解析失败
        script_result = script_result.replace("\\u201c", "\\"").replace("\\u201d", "\\"")
        script_result = script_result.replace("\\u2018", "'").replace("\\u2019", "'")
        script_data = json.loads(script_result)
    except Exception as e:
        return {"error": f"剧本JSON解析失败: {e}", "raw": script_result[:300]}'''

new_parse = '''    try:
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

if old_parse in content:
    content = content.replace(old_parse, new_parse)
    print("  ✅ JSON解析已修复（正则提取+中文引号替换）")
else:
    print("  ⚠️ 未找到精确匹配，使用sed直接替换")
    # 简单替换：在json.loads之前添加正则提取
    content = content.replace(
        'script_data = json.loads(script_result)',
        'import re as _re; _m = _re.search(r"\\{.*\\}", script_result, _re.DOTALL); script_data = json.loads(_m.group() if _m else script_result)'
    )
    print("  ✅ 已添加正则提取")

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(target, doraise=True)
    print("  ✅ Python语法验证通过")
except Exception as e:
    print(f"  ❌ 语法错误: {e}")

# 重新锁定
os.system(f"chattr +i {target} 2>/dev/null")

# 重启服务
os.system("systemctl restart zongyuan-drama-orchestrator 2>&1")
import time
time.sleep(2)
status = os.popen("systemctl is-active zongyuan-drama-orchestrator 2>/dev/null").read().strip()
print(f"  服务状态: {status}")

print()
print("✅ 修复完成！")
