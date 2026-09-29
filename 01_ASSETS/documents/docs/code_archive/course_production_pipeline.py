#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI普惠教育课程全自动化生产流水线
ZONGYUAN-ROOT 元极恒一自治体系
DID: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os, json, hashlib, urllib.request
from datetime import datetime

# 配置
EDUCATION_DIR = "/home/user/Doubao/education_courses"
GATEWAY_URL = "https://www.huodouai.com/api/report/truth"
GATEWAY_TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
SOURCE_NODE = "NODE-DEV-DOUBAO-WORK-001"

def generate_course_outline(course_id, course_name, description, category, price):
    """生成单门课程大纲"""
    # 3章12节标准模板
    chapters = []
    
    # 第1章：基础认知
    chapters.append({
        "chapter": "第1章：基础认知",
        "sections": [
            "1.1 核心概念与定义",
            "1.2 发展历程与现状",
            "1.3 适用场景与价值",
        ]
    })
    
    # 第2章：核心技能
    chapters.append({
        "chapter": "第2章：核心技能",
        "sections": [
            "2.1 基础操作与工具介绍",
            "2.2 核心方法与技巧",
            "2.3 实战案例演示",
        ]
    })
    
    # 第3章：进阶应用
    chapters.append({
        "chapter": "第3章：进阶应用",
        "sections": [
            "3.1 高级技巧与最佳实践",
            "3.2 常见问题与解决方案",
            "3.3 项目实战练习",
            "3.4 学习路径规划",
        ]
    })
    
    # 学习目标
    learning_objectives = [
        f"理解{course_name}的核心概念和基本原理",
        f"掌握{course_name}的核心技能和使用方法",
        f"能够独立完成{course_name}相关的实战任务",
    ]
    
    return {
        "course_id": course_id,
        "course_name": course_name,
        "description": description,
        "category": category,
        "price": price,
        "duration": "约30分钟",
        "chapters": chapters,
        "learning_objectives": learning_objectives,
        "target_audience": "零基础学员",
    }

def save_course(course):
    """保存课程文件并计算哈希"""
    filename = f"{course['course_id']}_{course['course_name'].replace(' ', '_')}.md"
    filepath = os.path.join(EDUCATION_DIR, filename)
    
    # 生成Markdown内容
    content = f"""# {course['course_name']}

> **类别**：{course['category']}  
> **时长**：{course['duration']}  
> **价格**：{course['price']}  

## 课程简介

{course['description']}

## 学习目标

"""
    for obj in course['learning_objectives']:
        content += f"- {obj}\n"
    
    content += "\n## 课程大纲\n\n"
    for ch in course['chapters']:
        content += f"### {ch['chapter']}\n\n"
        for sec in ch['sections']:
            content += f"- {sec}\n"
        content += "\n"
    
    content += """## 适合人群

"""
    content += f"{course['target_audience']}\n\n"
    content += "---\n"
    content += "Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 火斗云智AIOS\n"
    
    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 计算SHA256
    file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    return {
        "filepath": filepath,
        "filename": filename,
        "hash": file_hash,
        "size": len(content),
    }

def report_to_gateway(truth_key, truth_value, truth_type="data"):
    """上报记忆网关"""
    payload = {
        "truth_key": truth_key,
        "truth_value": truth_value,
        "source_node": SOURCE_NODE,
        "confidence": 0.9,
        "truth_type": truth_type,
    }
    
    try:
        req = urllib.request.Request(
            GATEWAY_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "X-Capture-Token": GATEWAY_TOKEN,
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('truth_count', 0)
    except Exception as e:
        print(f"    ⚠️ 上报失败：{e}")
        return 0

def run_pipeline(courses_to_produce=None):
    """运行生产流水线"""
    os.makedirs(EDUCATION_DIR, exist_ok=True)
    
    # 课程体系
    curriculum = {...}  # 从外部传入
    
    produced = []
    skipped = []
    
    for section_name, section in curriculum.items():
        for course in section['courses']:
            # 跳过已存在的
            filename = f"{course['id']}_{course['name'].replace(' ', '_')}.md"
            filepath = os.path.join(EDUCATION_DIR, filename)
            
            if os.path.exists(filepath):
                skipped.append(course['id'])
                continue
            
            # 生成课程
            course_data = generate_course_outline(
                course['id'],
                course['name'],
                course['desc'],
                section['name'],
                "免费" if section['name'] != "体系核心课（¥199）" else "¥199"
            )
            
            # 保存
            result = save_course(course_data)
            produced.append({
                "id": course['id'],
                "name": course['name'],
                "hash": result['hash'],
                "path": result['filepath'],
            })
            
            # 上报
            truth_key = f"EDUCATION.COURSE.{course['id']}.COMPLETE"
            truth_value = f"AI普惠教育课程完成：{course['name']}。{section['name']}，{course['desc']}。"
            truth_count = report_to_gateway(truth_key, truth_value)
    
    return {
        "produced": produced,
        "skipped": skipped,
        "total_produced": len(produced),
        "total_skipped": len(skipped),
    }

if __name__ == "__main__":
    print("=" * 60)
    print("AI普惠教育课程全自动化生产流水线")
    print("Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    print("=" * 60)
    
    result = run_pipeline()
    
    print(f"\n✅ 生产完成：{result['total_produced']}门")
    print(f"⏭️  跳过已存在：{result['total_skipped']}门")
    print()
    
    for p in result['produced']:
        print(f"  ✅ {p['id']}: {p['name']}")
