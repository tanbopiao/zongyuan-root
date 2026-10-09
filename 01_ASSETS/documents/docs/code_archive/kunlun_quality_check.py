#!/usr/bin/env python3
"""昆仑洞天元规则二次质检 - 加入角色一致性、构图美学、剧情表达等维度"""

import requests
import base64
import json
import os
import time
from datetime import datetime

# 智谱API配置
ZHIPU_API_KEY = "1dfafcccce4e483287fe39bcdea7691c.78z9iYwdDTRiquIk"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
MODEL = "glm-4v-flash"

# 昆仑洞天元规则质检提示词
KUNLUN_QUALITY_PROMPT = """你是昆仑洞天东方神话AI作品质检专家。请严格按照昆仑洞天五级评分制对这张图片进行质检。

## 昆仑洞天质检标准（五级评分制）

### 1. 画面质量（权重30%）
- 分辨率≥1080P、无噪点、无崩坏、无模糊
- 画面清晰，细节丰富，无明显压缩痕迹

### 2. 角色一致性（权重25%）
- 面部特征稳定、服装风格统一、不串脸
- 九天玄女：银甲红缨，战争形态，剑法无双
- 太阴月神：月白玄黑，修真形态，清冷出尘
- 西王母：昆仑之主，雍容华贵
- 红裙九尾狐：红裙，妖媚，九尾特征
- 角色形象必须符合上述设定，不得出现服装/发型/气质混乱

### 3. 构图美学（权重20%）
- 构图合理、光影自然、色彩协调、有氛围感
- 东方神话美学风格，黑金/暗金/国风色调
- 主体突出，背景有层次，有电影级画面感

### 4. 剧情表达（权重15%）
- 画面有故事感、角色动作自然、场景有意义
- 能看出角色在做什么，有叙事性
- 动作姿态符合角色身份和场景

### 5. 技术完整（权重10%）
- 无AI artifacts：多余手指/扭曲肢体/文字乱码/面部崩坏
- 手部正常（2只手，每只5根手指）
- 肢体比例正常，关节无异常
- 无穿模、无漂浮、无透视错误

## 角色设定参考
- 九天玄女：银甲红缨，战争女神，剑法无双，战场上最锋利的尖刀
- 太阴月神：月白玄黑，清冷出尘，修真形态
- 西王母：昆仑之主，雍容华贵
- 红裙九尾狐：红裙妖媚，九尾特征，与玄女立场对立

## 输出格式（严格JSON，不要其他内容）
{
  "overall_score": 0-100整数（综合评分）,
  "dimensions": {
    "image_quality": {"score": 0-100, "comment": "简短评价"},
    "character_consistency": {"score": 0-100, "comment": "角色是否符合设定，是否串脸"},
    "composition_aesthetics": {"score": 0-100, "comment": "构图光影色彩氛围"},
    "story_expression": {"score": 0-100, "comment": "是否有故事感叙事性"},
    "technical_completeness": {"score": 0-100, "comment": "有无AI artifacts"}
  },
  "character_detected": "检测到的角色名称（九天玄女/太阴月神/西王母/红裙九尾狐/其他/无）",
  "has_issues": true或false,
  "issues": ["具体问题列表"],
  "severity": "none/low/medium/high/critical",
  "pass": true或false,
  "kunlun_style_match": 0-100（昆仑洞天东方神话风格匹配度）
}

## 通过标准
- 综合评分≥70分
- 无单项评分<50分
- 无high/critical级别问题
- 角色一致性≥60分（不得严重串脸）
- 技术完整性≥60分（不得有明显AI artifacts）
"""

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def check_image_kunlun_quality(image_path, image_name):
    """昆仑洞天元规则质检单张图片"""
    image_base64 = encode_image(image_path)
    
    try:
        response = requests.post(
            f"{ZHIPU_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {ZHIPU_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": KUNLUN_QUALITY_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            },
            timeout=45
        )
        
        result = response.json()
        
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            # 提取JSON
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        
        return {"overall_score": 0, "has_issues": True, "issues": ["API解析失败"], "severity": "high", "pass": False}
        
    except Exception as e:
        return {"overall_score": 0, "has_issues": True, "issues": [f"请求失败: {str(e)}"], "severity": "high", "pass": False}

def main():
    # 待质检图片列表
    images_to_check = []
    
    # EP01关键帧（12张）
    ep01_dir = "/www/wwwroot/huodouai.com/drama/keyframes/ep01"
    if os.path.exists(ep01_dir):
        for f in sorted(os.listdir(ep01_dir)):
            if f.endswith(('.jpg', '.jpeg', '.png')):
                images_to_check.append({
                    "path": os.path.join(ep01_dir, f),
                    "category": "EP01剧情关键帧",
                    "name": f
                })
    
    # 角色关键帧（8张PNG）
    char_dir = "/www/wwwroot/huodouai.com/drama/gallery/keyframes"
    if os.path.exists(char_dir):
        for f in sorted(os.listdir(char_dir)):
            if f.endswith('.png') and 'keyframe' in f:
                images_to_check.append({
                    "path": os.path.join(char_dir, f),
                    "category": "角色设定关键帧",
                    "name": f
                })
    
    print(f"昆仑洞天元规则二次质检: {len(images_to_check)} 张")
    print("=" * 80)
    
    # 批量质检
    results = []
    passed = 0
    failed = 0
    total_score = 0
    
    for i, img_info in enumerate(images_to_check):
        print(f"\n[{i+1}/{len(images_to_check)}] 质检: {img_info['name']}")
        print(f"  类别: {img_info['category']}")
        
        result = check_image_kunlun_quality(img_info['path'], img_info['name'])
        result['image_info'] = img_info
        results.append(result)
        
        overall = result.get('overall_score', 0)
        total_score += overall
        status = "✅ 通过" if result.get('pass') else "❌ 不通过"
        char_detected = result.get('character_detected', '未知')
        style_match = result.get('kunlun_style_match', 0)
        
        print(f"  综合评分: {overall}")
        print(f"  检测角色: {char_detected}")
        print(f"  昆仑风格匹配: {style_match}")
        print(f"  状态: {status}")
        
        if result.get('has_issues'):
            print(f"  问题: {result.get('issues')}")
            print(f"  严重程度: {result.get('severity')}")
        
        # 打印各维度评分
        dims = result.get('dimensions', {})
        if dims:
            print(f"  各维度: 画面{dims.get('image_quality',{}).get('score','?')} | 角色{dims.get('character_consistency',{}).get('score','?')} | 构图{dims.get('composition_aesthetics',{}).get('score','?')} | 剧情{dims.get('story_expression',{}).get('score','?')} | 技术{dims.get('technical_completeness',{}).get('score','?')}")
        
        if result.get('pass'):
            passed += 1
        else:
            failed += 1
        
        # 避免限流
        time.sleep(1.5)
    
    # 生成报告
    avg_score = total_score // len(images_to_check) if images_to_check else 0
    
    print("\n" + "=" * 80)
    print("【昆仑洞天元规则二次质检报告】")
    print("=" * 80)
    print(f"  总图片数: {len(images_to_check)}")
    print(f"  通过: {passed} ({passed*100//len(images_to_check)}%)")
    print(f"  不通过: {failed} ({failed*100//len(images_to_check)}%)")
    print(f"  平均综合评分: {avg_score}")
    print()
    
    # 不通过的图片列表
    if failed > 0:
        print("【不通过的图片】")
        for r in results:
            if not r.get('pass'):
                info = r['image_info']
                print(f"  ❌ {info['name']} - 综合分:{r.get('overall_score')} - 问题:{r.get('issues')}")
        print()
    
    # 各维度平均分
    print("【各维度平均评分】")
    dim_names = {
        'image_quality': '画面质量',
        'character_consistency': '角色一致性',
        'composition_aesthetics': '构图美学',
        'story_expression': '剧情表达',
        'technical_completeness': '技术完整'
    }
    for dim_key, dim_name in dim_names.items():
        scores = [r.get('dimensions', {}).get(dim_key, {}).get('score', 0) for r in results if r.get('dimensions')]
        if scores:
            avg = sum(scores) // len(scores)
            print(f"  {dim_name}: {avg}分")
    print()
    
    # 角色检测统计
    print("【角色检测统计】")
    char_counts = {}
    for r in results:
        char = r.get('character_detected', '未知')
        char_counts[char] = char_counts.get(char, 0) + 1
    for char, count in char_counts.items():
        print(f"  {char}: {count}张")
    print()
    
    # 保存报告
    report = {
        "check_time": datetime.now().isoformat(),
        "model": MODEL,
        "check_type": "昆仑洞天元规则二次质检",
        "total": len(images_to_check),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed*100//len(images_to_check)}%",
        "avg_score": avg_score,
        "results": [
            {
                "name": r['image_info']['name'],
                "path": r['image_info']['path'],
                "category": r['image_info']['category'],
                "overall_score": r.get('overall_score'),
                "character_detected": r.get('character_detected'),
                "kunlun_style_match": r.get('kunlun_style_match'),
                "dimensions": r.get('dimensions'),
                "has_issues": r.get('has_issues'),
                "issues": r.get('issues'),
                "severity": r.get('severity'),
                "pass": r.get('pass')
            }
            for r in results
        ]
    }
    
    report_path = "/www/wwwroot/huodouai.com/drama/kunlun_quality_check_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"昆仑洞天元规则质检报告已保存: {report_path}")
    
    return report

if __name__ == "__main__":
    main()
