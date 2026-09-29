#!/usr/bin/env python3
"""全面质检所有未覆盖的图片"""

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

QUALITY_PROMPT = """检测这张AI生成图片，重点检查：
1. 多个手/多余手臂/多余手指（正常人类只有2只手臂，每只手5根手指）
2. 手指数量不对（多于5根或少于5根）
3. 手臂数量不对（多于2只）
4. 肢体扭曲/关节异常
5. 面部崩坏/五官不对称
6. 衣物穿模/纹理错误

输出JSON：
{"overall_score":0-100,"has_multiple_hands":true/false,"hand_count":"数量","has_issues":true/false,"issues":["问题"],"severity":"none/low/medium/high/critical","pass":true/false}
发现多个手/多余手臂直接不通过，severity=critical。"""

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def check_image(path):
    img = encode_image(path)
    try:
        r = requests.post(
            f"{ZHIPU_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": QUALITY_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
                ]}],
                "max_tokens": 1024,
                "temperature": 0.1
            },
            timeout=45
        )
        result = r.json()
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            js = content.find("{")
            je = content.rfind("}") + 1
            if js >= 0 and je > js:
                return json.loads(content[js:je])
        return {"overall_score": 0, "pass": False, "issues": ["解析失败"]}
    except Exception as e:
        return {"overall_score": 0, "pass": False, "issues": [str(e)]}

def main():
    check_dirs = [
        "/www/wwwroot/drama.huodouai.com/images/2026-09-13",
        "/www/wwwroot/drama.huodouai.com/images/2026-09-14",
    ]
    
    cold_storage = "/www/wwwroot/drama.huodouai.com/images/_archive_low_quality"
    os.makedirs(cold_storage, exist_ok=True)
    
    all_images = []
    for d in check_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    all_images.append(os.path.join(d, f))
    
    print(f"发现 {len(all_images)} 张待质检图片")
    print("=" * 70)
    
    results = []
    passed = 0
    failed = 0
    multi_hand = 0
    
    for i, path in enumerate(all_images):
        name = os.path.basename(path)
        print(f"\n[{i+1}/{len(all_images)}] {name}")
        
        result = check_image(path)
        result["path"] = path
        result["name"] = name
        results.append(result)
        
        score = result.get("overall_score", 0)
        has_multi = result.get("has_multiple_hands", False)
        hands = result.get("hand_count", "?")
        status = "PASS" if result.get("pass") else "FAIL"
        issues = result.get("issues", [])
        
        print(f"  评分:{score} 多手:{has_multi}({hands}) {status}")
        if issues:
            print(f"  问题:{issues}")
        
        if has_multi:
            multi_hand += 1
        
        if result.get("pass"):
            passed += 1
        else:
            failed += 1
            try:
                dest = os.path.join(cold_storage, name)
                shutil.move(path, dest)
                print(f"  -> 移入冷库")
            except Exception as e:
                print(f"  -> 移入失败: {e}")
        
        time.sleep(1)
    
    print("\n" + "=" * 70)
    total = len(all_images)
    pass_pct = passed * 100 // total if total else 0
    print(f"【质检完成】总数:{total} 通过:{passed}({pass_pct}%) 不通过:{failed} 多手:{multi_hand}张")
    print(f"冷库: {cold_storage}")
    
    report = {
        "time": datetime.now().isoformat(),
        "total": total,
        "passed": passed,
        "failed": failed,
        "multi_hand": multi_hand,
        "results": results
    }
    report_dir = "/www/wwwroot/huodouai.com/drama/_quality_reports"
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, "full_check.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告: {report_dir}/full_check.json")

if __name__ == "__main__":
    main()
