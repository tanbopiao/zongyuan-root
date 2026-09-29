#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看原始JSON并使用更健壮的解析"""

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
3. 只输出JSON格式，不要其他文字，不要markdown代码块

格式：
{"synopsis":"概要","scenes":[{"scene_no":1,"location":"地点","time":"时间","characters":["角色1"],"plot":"情节"}]}"""

result = orchestrator.call_ai(script_prompt, max_tokens=600)
print("原始输出:")
print(result)
print()
print("原始输出repr:")
print(repr(result))
print()

# 尝试各种修复方式
print("【2】尝试各种JSON修复方式")

# 清理markdown
fixed = result.replace("```json", "").replace("```", "").strip()
# 替换中文引号
fixed = fixed.replace("\u201c", '"').replace("\u201d", '"')
fixed = fixed.replace("\u2018", "'").replace("\u2019", "'")

print("清理后:")
print(fixed[:500])
print()

# 方式1: 直接解析
try:
    data = json.loads(fixed)
    print("  ✅ 方式1成功（直接解析）")
except Exception as e:
    print(f"  ❌ 方式1失败: {e}")
    
    # 方式2: 正则提取JSON
    print("  尝试方式2: 正则提取JSON...")
    match = re.search(r'\{.*\}', fixed, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            print("  ✅ 方式2成功（正则提取）")
        except Exception as e2:
            print(f"  ❌ 方式2失败: {e2}")
            
            # 方式3: 修复未转义的引号
            print("  尝试方式3: 修复未转义的引号...")
            json_str = match.group()
            # 找到问题位置
            print(f"  问题位置 char 148: {repr(json_str[140:160])}")
            
            # 简单修复：将characters数组中的引号替换
            # 这是一个常见问题：角色名称中包含引号
            fixed3 = re.sub(r'"characters":\s*\[(.*?)\]', 
                          lambda m: '"characters":[' + re.sub(r'(?<!\\)"([^",\[\]]+?)"', r'"\1"', m.group(1)) + ']',
                          json_str, flags=re.DOTALL)
            try:
                data = json.loads(fixed3)
                print("  ✅ 方式3成功")
            except Exception as e3:
                print(f"  ❌ 方式3失败: {e3}")

# 最终方案：修改prompt，要求AI返回更简单的格式
print()
print("【3】最终方案：修改prompt，使用更简单的格式")

simple_prompt = """你是昆仑洞天短剧编剧。请为第1集《测试》生成剧本。
要求：
1. 3个场景
2. 每个场景一行，格式：场景编号|地点|时间|角色1,角色2|情节
3. 第一行是概要
4. 不要输出JSON，不要输出markdown，只输出纯文本

示例：
昆仑洞天发生了神秘事件
1|昆仑入口|清晨|测试官A,参与者1|测试官宣布测试开始
2|洞天内部|中午|参与者1,神秘人|遇到神秘人
3|试炼场|傍晚|所有人|最终试炼"""

result2 = orchestrator.call_ai(simple_prompt, max_tokens=400)
print("简单格式输出:")
print(result2)
print()

# 解析简单格式
lines = result2.strip().split("\n")
if len(lines) >= 2:
    synopsis = lines[0].strip()
    scenes = []
    for line in lines[1:]:
        parts = line.split("|")
        if len(parts) >= 5:
            scenes.append({
                "scene_no": int(parts[0].strip()),
                "location": parts[1].strip(),
                "time": parts[2].strip(),
                "characters": [c.strip() for c in parts[3].split(",")],
                "plot": parts[4].strip()
            })
    print(f"  ✅ 简单格式解析成功！")
    print(f"  概要: {synopsis[:50]}")
    print(f"  场景数: {len(scenes)}")
    for s in scenes:
        print(f"    场景{s['scene_no']}: {s['location']} - {s['plot'][:30]}")

print()
print("✅ 诊断完成！建议使用简单文本格式替代JSON，更稳定可靠。")
