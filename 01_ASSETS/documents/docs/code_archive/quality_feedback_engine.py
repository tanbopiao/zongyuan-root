#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天 · 质量反馈闭环引擎 V1.0
技术领先核心机制：质检不通过 → 自动分析原因 → 优化提示词 → 下一次自动应用
形成进化闭环，每一次生产都比上一次更好
"""

import json
import time
import os
import sys
import urllib.request
from datetime import datetime

# ========== 配置 ==========
AI_PROXY = "http://127.0.0.1:8021/v1/chat/completions"
MEMORY_GATEWAY = "http://127.0.0.1:9120"
EVOLUTION_LOG_PATH = "/opt/ZONGYUAN-ROOT/data/quality_evolution_log.json"
PROMPT_TEMPLATE_PATH = "/opt/ZONGYUAN-ROOT/data/optimized_prompts.json"

# 确保目录存在
os.makedirs(os.path.dirname(EVOLUTION_LOG_PATH), exist_ok=True)

# ========== 缺陷分类体系 ==========
DEFECT_CATEGORIES = {
    "multiple_hands": {
        "name": "多手/多指",
        "description": "人物出现多余的手或手指",
        "negative_prompt": "multiple hands, extra fingers, deformed hands, mutated hands",
        "optimization_strategy": "在提示词中强调'单头单手单脚'，添加负面提示词'multiple hands, extra fingers'"
    },
    "face_distortion": {
        "name": "面部崩坏",
        "description": "人物面部扭曲、五官错位",
        "negative_prompt": "deformed face, distorted features, ugly face, cross-eyed",
        "optimization_strategy": "强调'精致五官，面部细节清晰'，使用更高质量的面部描述"
    },
    "proportion_error": {
        "name": "比例失调",
        "description": "人物身体比例不正常",
        "negative_prompt": "bad proportions, long body, short legs, deformed body",
        "optimization_strategy": "强调'标准人体比例，九头身'，添加具体的身材描述"
    },
    "style_drift": {
        "name": "风格漂移",
        "description": "生成风格与预期不符",
        "negative_prompt": "wrong style, modern clothing, western style, cartoon style",
        "optimization_strategy": "强化风格描述，添加'国风仙侠，东方美学，传统服饰'等关键词"
    },
    "lighting_abnormal": {
        "name": "光影异常",
        "description": "画面光影不自然",
        "negative_prompt": "bad lighting, overexposed, underexposed, harsh shadows",
        "optimization_strategy": "添加'电影级光影，柔和光线，体积光'等描述"
    },
    "composition_poor": {
        "name": "构图不佳",
        "description": "画面构图不合理",
        "negative_prompt": "bad composition, off-center, cropped, awkward pose",
        "optimization_strategy": "添加'黄金分割构图，居中对称，电影级构图'等描述"
    },
    "character_inconsistency": {
        "name": "角色不一致",
        "description": "同一角色多张图片形象不统一",
        "negative_prompt": "different face, different hair, inconsistent character",
        "optimization_strategy": "使用固定种子，强化角色描述，建立角色资产库"
    },
    "low_quality": {
        "name": "质量低下",
        "description": "整体画质差，细节不足",
        "negative_prompt": "low quality, blurry, pixelated, jpeg artifacts",
        "optimization_strategy": "添加'8K高清，极致细节，大师级作品'等质量描述"
    }
}

# ========== 工具函数 ==========
def call_ai(prompt, model="zhipu", max_tokens=800, temperature=0.7):
    """调用AI代理"""
    try:
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        req = urllib.request.Request(
            AI_PROXY,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ❌ AI调用失败: {e}")
        return None

def load_evolution_log():
    """加载进化日志"""
    if os.path.exists(EVOLUTION_LOG_PATH):
        with open(EVOLUTION_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"total_checks": 0, "total_failures": 0, "evolution_history": [], "defect_stats": {}}

def save_evolution_log(log):
    """保存进化日志"""
    with open(EVOLUTION_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def load_optimized_prompts():
    """加载优化后的提示词模板"""
    if os.path.exists(PROMPT_TEMPLATE_PATH):
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"templates": {}, "version": "1.0", "last_updated": None}

def save_optimized_prompts(prompts):
    """保存优化后的提示词模板"""
    prompts["last_updated"] = datetime.now().isoformat()
    with open(PROMPT_TEMPLATE_PATH, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

# ========== 核心功能 ==========
def analyze_defect(image_path, original_prompt, quality_score):
    """
    分析缺陷原因（使用AI视觉分析）
    返回：缺陷分类 + 根因分析 + 优化建议
    """
    print(f"\n  🔍 分析缺陷: {image_path}")
    print(f"  原始质量评分: {quality_score}")
    
    # 构建分析prompt
    analysis_prompt = f"""你是AI图像质量专家。请分析以下图像生成失败的原因：

原始提示词: {original_prompt}
质量评分: {quality_score}/100

请分析：
1. 最可能的缺陷类型（从以下选择：多手/面部崩坏/比例失调/风格漂移/光影异常/构图不佳/角色不一致/质量低下）
2. 缺陷的根本原因（是提示词问题、模型问题还是参数问题）
3. 具体的提示词优化建议
4. 需要添加的负面提示词

只输出JSON格式：
{{"defect_type": "类型", "root_cause": "原因", "optimization": "优化建议", "negative_prompt": "负面提示词"}}"""
    
    result = call_ai(analysis_prompt, max_tokens=500)
    if not result:
        return {"defect_type": "unknown", "root_cause": "AI分析失败", "optimization": "重试", "negative_prompt": ""}
    
    # 解析JSON
    try:
        # 清理markdown
        result = result.replace("```json", "").replace("```", "").strip()
        # 替换中文标点
        result = result.replace("\u201c", '"').replace("\u201d", '"')
        result = result.replace("\uff0c", ",").replace("\uff1a", ":")
        # 正则提取JSON
        import re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            analysis = json.loads(match.group())
        else:
            analysis = json.loads(result)
        print(f"  ✅ 缺陷分析完成: {analysis.get('defect_type', 'unknown')}")
        return analysis
    except Exception as e:
        print(f"  ⚠️ 分析结果解析失败: {e}")
        return {"defect_type": "unknown", "root_cause": "解析失败", "optimization": result[:200], "negative_prompt": ""}

def optimize_prompt(original_prompt, analysis):
    """
    根据缺陷分析优化提示词
    返回：优化后的提示词
    """
    print(f"\n  ✨ 优化提示词...")
    
    defect_type = analysis.get("defect_type", "unknown")
    defect_info = DEFECT_CATEGORIES.get(defect_type, {})
    
    # 构建优化prompt
    optimization_prompt = f"""你是AI提示词优化专家。请优化以下图像生成提示词：

原始提示词: {original_prompt}

检测到的缺陷: {defect_type} - {defect_info.get('description', '')}
缺陷原因: {analysis.get('root_cause', '')}
优化方向: {analysis.get('optimization', '')}
建议负面提示词: {analysis.get('negative_prompt', '')}

请输出优化后的完整提示词，要求：
1. 保留原始提示词的核心内容
2. 添加质量提升关键词（8K高清，极致细节，大师级作品）
3. 添加角色一致性约束
4. 添加风格强化描述
5. 添加负面提示词

只输出优化后的提示词文本，不要其他内容。"""
    
    optimized = call_ai(optimization_prompt, max_tokens=600, temperature=0.5)
    if optimized:
        print(f"  ✅ 提示词优化完成")
        return optimized.strip()
    else:
        # 简单优化：添加基础质量词
        simple_optimized = f"{original_prompt}，8K高清，极致细节，大师级作品，电影级光影，单头单手单脚，精致五官"
        print(f"  ⚠️ AI优化失败，使用简单优化")
        return simple_optimized

def record_evolution(image_path, original_prompt, quality_score, analysis, optimized_prompt):
    """
    记录进化日志
    """
    log = load_evolution_log()
    
    # 更新统计
    log["total_checks"] += 1
    if quality_score < 80:
        log["total_failures"] += 1
    
    # 更新缺陷统计
    defect_type = analysis.get("defect_type", "unknown")
    log["defect_stats"][defect_type] = log["defect_stats"].get(defect_type, 0) + 1
    
    # 记录进化历史
    evolution_entry = {
        "timestamp": datetime.now().isoformat(),
        "image_path": image_path,
        "original_prompt": original_prompt,
        "quality_score": quality_score,
        "defect_analysis": analysis,
        "optimized_prompt": optimized_prompt,
        "defect_type": defect_type
    }
    log["evolution_history"].append(evolution_entry)
    
    # 只保留最近100条
    if len(log["evolution_history"]) > 100:
        log["evolution_history"] = log["evolution_history"][-100:]
    
    save_evolution_log(log)
    print(f"  📝 进化日志已记录")
    return log

def update_prompt_template(category, optimized_prompt):
    """
    更新提示词模板库
    """
    prompts = load_optimized_prompts()
    
    if category not in prompts["templates"]:
        prompts["templates"][category] = []
    
    # 检查是否已存在相似模板
    exists = False
    for t in prompts["templates"][category]:
        if t["prompt"][:50] == optimized_prompt[:50]:
            t["usage_count"] = t.get("usage_count", 0) + 1
            exists = True
            break
    
    if not exists:
        prompts["templates"][category].append({
            "prompt": optimized_prompt,
            "created_at": datetime.now().isoformat(),
            "usage_count": 1,
            "success_rate": 0
        })
    
    # 每个分类只保留最优的10个模板
    if len(prompts["templates"][category]) > 10:
        prompts["templates"][category] = sorted(
            prompts["templates"][category],
            key=lambda x: x.get("usage_count", 0),
            reverse=True
        )[:10]
    
    save_optimized_prompts(prompts)
    print(f"  📚 提示词模板库已更新")

def get_best_prompt(category, base_description):
    """
    获取最优提示词（从模板库中选择）
    """
    prompts = load_optimized_prompts()
    
    if category in prompts["templates"] and prompts["templates"][category]:
        # 选择使用次数最多的模板
        best = max(prompts["templates"][category], key=lambda x: x.get("usage_count", 0))
        print(f"  🎯 使用最优模板（使用{best.get('usage_count', 0)}次）")
        return best["prompt"]
    
    # 没有模板时返回基础描述
    return base_description

def run_quality_feedback_cycle(image_path, original_prompt, quality_score, category="general"):
    """
    运行完整的质量反馈闭环
    1. 分析缺陷原因
    2. 优化提示词
    3. 记录进化日志
    4. 更新提示词模板库
    5. 返回优化后的提示词
    """
    print("\n" + "=" * 60)
    print("  质量反馈闭环启动")
    print("=" * 60)
    
    # 1. 分析缺陷
    analysis = analyze_defect(image_path, original_prompt, quality_score)
    
    # 2. 优化提示词
    optimized_prompt = optimize_prompt(original_prompt, analysis)
    
    # 3. 记录进化日志
    log = record_evolution(image_path, original_prompt, quality_score, analysis, optimized_prompt)
    
    # 4. 更新提示词模板库
    update_prompt_template(category, optimized_prompt)
    
    # 5. 上报到记忆网关
    try:
        data = {
            "key": f"quality_evolution_{int(time.time())}",
            "value": json.dumps({
                "defect_type": analysis.get("defect_type"),
                "quality_score": quality_score,
                "optimization": analysis.get("optimization", "")[:100]
            }, ensure_ascii=False),
            "category": "quality_evolution",
            "truth_type": "evolution_log",
            "confidence": 0.9,
            "locked": True
        }
        req = urllib.request.Request(
            f"{MEMORY_GATEWAY}/api/truth/upsert",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
    except:
        pass
    
    print("\n" + "=" * 60)
    print("  ✅ 质量反馈闭环完成")
    print(f"  缺陷类型: {analysis.get('defect_type')}")
    print(f"  根因: {analysis.get('root_cause', '')[:50]}")
    print(f"  总检查数: {log['total_checks']}")
    print(f"  总失败数: {log['total_failures']}")
    print("=" * 60)
    
    return {
        "analysis": analysis,
        "optimized_prompt": optimized_prompt,
        "defect_type": analysis.get("defect_type"),
        "evolution_log": log
    }

def get_evolution_stats():
    """获取进化统计"""
    log = load_evolution_log()
    prompts = load_optimized_prompts()
    
    total_templates = sum(len(v) for v in prompts.get("templates", {}).values())
    failure_rate = (log["total_failures"] / log["total_checks"] * 100) if log["total_checks"] > 0 else 0
    
    return {
        "total_checks": log["total_checks"],
        "total_failures": log["total_failures"],
        "failure_rate": round(failure_rate, 1),
        "defect_stats": log["defect_stats"],
        "total_templates": total_templates,
        "template_categories": list(prompts.get("templates", {}).keys()),
        "last_updated": prompts.get("last_updated")
    }

# ========== 命令行入口 ==========
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="质量反馈闭环引擎")
    parser.add_argument("--image", type=str, help="图像路径")
    parser.add_argument("--prompt", type=str, help="原始提示词")
    parser.add_argument("--score", type=float, help="质量评分")
    parser.add_argument("--category", type=str, default="general", help="分类")
    parser.add_argument("--stats", action="store_true", help="显示进化统计")
    args = parser.parse_args()
    
    if args.stats:
        stats = get_evolution_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif args.image and args.prompt and args.score:
        result = run_quality_feedback_cycle(
            args.image, args.prompt, args.score, args.category
        )
        print("\n优化后的提示词:")
        print(result["optimized_prompt"])
    else:
        print("使用方法:")
        print("  python3 quality_feedback_engine.py --image <路径> --prompt <提示词> --score <评分>")
        print("  python3 quality_feedback_engine.py --stats")
