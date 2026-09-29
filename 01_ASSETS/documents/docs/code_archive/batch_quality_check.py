#!/usr/bin/env python3
"""批量质检关键帧图片 - 使用智谱GLM-4V-Flash"""

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

# 质检提示词
QUALITY_PROMPT = """你是AI图片质量检测专家。请严格检测这张图片是否存在以下AI artifacts问题：

1. 多个手/多余手指（正常人类只有2只手，每只手5根手指）
2. 肢体扭曲/关节异常/手臂或腿数量不对
3. 面部崩坏/五官不对称/眼睛异常
4. 衣物穿模/纹理错误/服饰异常
5. 背景不合理/透视错误/物体漂浮
6. 文字乱码/水印异常
7. 整体画面模糊/噪点过多/分辨率低

请严格按以下JSON格式输出（只输出JSON，不要其他内容）：
{
  "quality_score": 0-100整数,
  "has_issues": true或false,
  "issues": ["具体问题1", "具体问题2"],
  "issue_locations": ["问题在图片中的位置"],
  "severity": "none/low/medium/high/critical",
  "pass": true或false
}

判定标准：
- 90-100分：优秀，无明显问题
- 70-89分：良好，轻微问题可接受
- 50-69分：一般，有明显问题
- 0-49分：差，严重问题
- pass=true的条件：quality_score>=70 且 severity不是high/critical
"""

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def check_image_quality(image_path):
    """检测单张图片质量"""
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
                            {"type": "text", "text": QUALITY_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }
                ],
                "max_tokens": 800,
                "temperature": 0.1
            },
            timeout=30
        )
        
        result = response.json()
        
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            # 提取JSON
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        
        return {"quality_score": 0, "has_issues": True, "issues": ["API解析失败"], "severity": "high", "pass": False}
        
    except Exception as e:
        return {"quality_score": 0, "has_issues": True, "issues": [f"请求失败: {str(e)}"], "severity": "high", "pass": False}

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
    
    print(f"待质检图片: {len(images_to_check)} 张")
    print("=" * 80)
    
    # 批量质检
    results = []
    passed = 0
    failed = 0
    
    for i, img_info in enumerate(images_to_check):
        print(f"\n[{i+1}/{len(images_to_check)}] 质检: {img_info['name']}")
        print(f"  类别: {img_info['category']}")
        print(f"  大小: {os.path.getsize(img_info['path']) / 1024:.1f}KB")
        
        result = check_image_quality(img_info['path'])
        result['image_info'] = img_info
        results.append(result)
        
        status = "✅ 通过" if result.get('pass') else "❌ 不通过"
        print(f"  质量分: {result.get('quality_score')}")
        print(f"  状态: {status}")
        if result.get('has_issues'):
            print(f"  问题: {result.get('issues')}")
            print(f"  严重程度: {result.get('severity')}")
        
        if result.get('pass'):
            passed += 1
        else:
            failed += 1
        
        # 避免限流，每张间隔1秒
        time.sleep(1)
    
    # 生成报告
    print("\n" + "=" * 80)
    print("【质检报告汇总】")
    print("=" * 80)
    print(f"  总图片数: {len(images_to_check)}")
    print(f"  通过: {passed} ({passed*100//len(images_to_check)}%)")
    print(f"  不通过: {failed} ({failed*100//len(images_to_check)}%)")
    print()
    
    # 不通过的图片列表
    if failed > 0:
        print("【不通过的图片】")
        for r in results:
            if not r.get('pass'):
                info = r['image_info']
                print(f"  ❌ {info['name']} - 质量分:{r.get('quality_score')} - 问题:{r.get('issues')}")
        print()
    
    # 保存报告
    report = {
        "check_time": datetime.now().isoformat(),
        "model": MODEL,
        "total": len(images_to_check),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed*100//len(images_to_check)}%",
        "results": [
            {
                "name": r['image_info']['name'],
                "path": r['image_info']['path'],
                "category": r['image_info']['category'],
                "quality_score": r.get('quality_score'),
                "has_issues": r.get('has_issues'),
                "issues": r.get('issues'),
                "severity": r.get('severity'),
                "pass": r.get('pass')
            }
            for r in results
        ]
    }
    
    report_path = "/www/wwwroot/huodouai.com/drama/quality_check_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"质检报告已保存: {report_path}")
    
    return report

if __name__ == "__main__":
    main()
