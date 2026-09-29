#!/usr/bin/env python3
"""紧急质检：对新生成的kunlun-archive图片进行质检"""

import requests
import base64
import json
import os
import time
import shutil
from datetime import datetime

ZHIPU_API_KEY = "1dfafcccce4e483287fe39bcdea7691c.78z9iYwdDTRiquIk"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
MODEL = "glm-4v-flash"

# 加强版质检提示词，重点检测多手问题
QUALITY_PROMPT = """你是专业的AI图片质量检测专家。请严格检测这张图片，重点检查以下问题：

【重点检测 - AI artifacts】
1. 多个手/多余手臂/多余手指（正常人类只有2只手臂，每只手5根手指）
2. 手指数量不对（多于5根或少于5根）
3. 手臂数量不对（多于2只）
4. 肢体扭曲/关节异常/手臂或腿变形
5. 面部崩坏/五官不对称/眼睛异常
6. 衣物穿模/纹理错误/服饰异常

【其他检测】
7. 画面质量（清晰度/噪点/模糊）
8. 构图美学（光影/色彩/氛围）
9. 角色一致性（九天玄女银甲红缨/太阴月神月白玄黑）

请严格按以下JSON格式输出（只输出JSON，不要其他内容）：
{
  "overall_score": 0-100,
  "has_multiple_hands": true或false,
  "hand_count": "检测到的手/手臂数量",
  "has_issues": true或false,
  "issues": ["具体问题列表"],
  "severity": "none/low/medium/high/critical",
  "pass": true或false
}

判定标准：
- 发现多个手/多余手臂 → 直接不通过，severity=critical
- 手指数量不对 → 直接不通过，severity=high
- 肢体扭曲/面部崩坏 → 不通过，severity=high
- 综合评分<70 → 不通过
"""

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def check_image(image_path):
    image_base64 = encode_image(image_path)
    try:
        response = requests.post(
            f"{ZHIPU_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": QUALITY_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]}],
                "max_tokens": 1024,
                "temperature": 0.1
            },
            timeout=45
        )
        result = response.json()
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        return {"overall_score": 0, "pass": False, "issues": ["API解析失败"]}
    except Exception as e:
        return {"overall_score": 0, "pass": False, "issues": [str(e)]}

def main():
    # 待质检目录
    check_dirs = [
        "/www/wwwroot/drama.huodouai.com/images/kunlun-archive-20260914",
        "/www/wwwroot/drama.huodouai.com/images/kunlun-archive-20260913",
    ]
    
    # 冷库目录
    cold_storage = "/www/wwwroot/drama.huodouai.com/images/_archive_low_quality"
    os.makedirs(cold_storage, exist_ok=True)
    
    # 收集所有图片
    all_images = []
    for check_dir in check_dirs:
        if os.path.exists(check_dir):
            for f in os.listdir(check_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    all_images.append(os.path.join(check_dir, f))
    
    print(f"紧急质检：发现 {len(all_images)} 张新生成图片")
    print("=" * 70)
    
    results = []
    passed = 0
    failed = 0
    multi_hand_count = 0
    
    for i, filepath in enumerate(all_images):
        filename = os.path.basename(filepath)
        print(f"\n[{i+1}/{len(all_images)}] 质检: {filename}")
        
        result = check_image(filepath)
        result["filepath"] = filepath
        result["filename"] = filename
        results.append(result)
        
        score = result.get("overall_score", 0)
        has_multi_hands = result.get("has_multiple_hands", False)
        hand_count = result.get("hand_count", "未知")
        status = "✅" if result.get("pass") else "❌"
        
        print(f"  评分: {score} | 多手: {has_multi_hands} ({hand_count}) | {status}")
        
        if result.get("issues"):
            print(f"  问题: {result.get('issues')}")
        
        if has_multi_hands:
            multi_hand_count += 1
        
        if result.get("pass"):
            passed += 1
        else:
            failed += 1
            # 移入冷库
            try:
                dest = os.path.join(cold_storage, filename)
                shutil.move(filepath, dest)
                print(f"  → 已移入冷库: {dest}")
            except Exception as e:
                print(f"  → 移入冷库失败: {e}")
        
        time.sleep(1)
    
    print("\n" + "=" * 70)
    print("【紧急质检报告】")
    print(f"  总数: {len(all_images)}")
    print(f"  通过: {passed} ({passed*100//len(all_images) if all_images else 0}%)")
    print(f"  不通过: {failed} ({failed*100//len(all_images) if all_images else 0}%)")
    print(f"  多手问题: {multi_hand_count} 张")
    print(f"  冷库目录: {cold_storage}")
    
    # 保存报告
    report = {
        "check_time": datetime.now().isoformat(),
        "check_type": "紧急质检 - 新生成图片",
        "total": len(all_images),
        "passed": passed,
        "failed": failed,
        "multi_hand_count": multi_hand_count,
        "cold_storage": cold_storage,
        "results": results
    }
    
    report_path = "/www/wwwroot/huodouai.com/drama/_quality_reports/emergency_check.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存: {report_path}")

if __name__ == "__main__":
    main()
