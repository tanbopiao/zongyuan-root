#!/usr/bin/env python3
"""昆仑洞天元规则二次质检 v2 - 修正max_tokens"""

import requests
import base64
import json
import os
import time
from datetime import datetime

ZHIPU_API_KEY = "1dfafcccce4e483287fe39bcdea7691c.78z9iYwdDTRiquIk"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
MODEL = "glm-4v-flash"

PROMPT = """质检这张昆仑洞天东方神话AI作品。输出JSON：
{"overall_score":0-100,"image_quality":0-100,"character_consistency":0-100,"composition_aesthetics":0-100,"story_expression":0-100,"technical_completeness":0-100,"character_detected":"角色名","has_issues":true/false,"issues":["问题"],"pass":true/false}
维度：画面质量/角色一致(玄女银甲红缨/月神月白玄黑)/构图美学/剧情表达/技术完整(无多手扭曲)。只输出JSON。"""

def check_image(path):
    with open(path, "rb") as f:
        img = base64.b64encode(f.read()).decode("utf-8")
    try:
        r = requests.post(
            f"{ZHIPU_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": PROMPT},
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
    images = []
    ep01 = "/www/wwwroot/huodouai.com/drama/keyframes/ep01"
    for f in sorted(os.listdir(ep01)):
        if f.endswith((".jpg", ".png")):
            images.append((os.path.join(ep01, f), f, "EP01剧情"))
    char_dir = "/www/wwwroot/huodouai.com/drama/gallery/keyframes"
    for f in sorted(os.listdir(char_dir)):
        if f.endswith(".png") and "keyframe" in f:
            images.append((os.path.join(char_dir, f), f, "角色设定"))

    print(f"昆仑洞天元规则二次质检: {len(images)}张")
    print("=" * 70)

    results = []
    passed = 0
    for i, (path, name, cat) in enumerate(images):
        r = check_image(path)
        r["name"] = name
        r["category"] = cat
        results.append(r)
        score = r.get("overall_score", 0)
        status = "✅" if r.get("pass") else "❌"
        char = r.get("character_detected", "?")
        issues = r.get("issues", [])
        issue_str = ", ".join(issues) if issues else ""
        print(f"[{i+1}/{len(images)}] {status} {score}分 | {char} | {name}")
        if issue_str:
            print(f"     问题: {issue_str}")
        if r.get("pass"):
            passed += 1
        time.sleep(1)

    print()
    print("=" * 70)
    print("【昆仑洞天元规则二次质检报告】")
    print(f"  总数: {len(images)} | 通过: {passed} ({passed*100//len(images)}%) | 不通过: {len(images)-passed}")
    avg = sum(r.get("overall_score", 0) for r in results) // len(results)
    print(f"  平均综合评分: {avg}分")
    print()

    dims = [("image_quality", "画面"), ("character_consistency", "角色"),
            ("composition_aesthetics", "构图"), ("story_expression", "剧情"),
            ("technical_completeness", "技术")]
    print("【各维度平均评分】")
    for key, name in dims:
        scores = [r.get(key, 0) for r in results if r.get(key)]
        if scores:
            print(f"  {name}: {sum(scores)//len(scores)}分")
    print()

    print("【角色检测统计】")
    char_counts = {}
    for r in results:
        c = r.get("character_detected", "未知")
        char_counts[c] = char_counts.get(c, 0) + 1
    for c, n in char_counts.items():
        print(f"  {c}: {n}张")
    print()

    if len(images) - passed > 0:
        print("【不通过的图片】")
        for r in results:
            if not r.get("pass"):
                issues = r.get("issues", [])
                print(f"  ❌ {r['name']} - {r.get('overall_score')}分 - {issues}")
        print()

    report = {
        "check_time": datetime.now().isoformat(),
        "model": MODEL,
        "check_type": "昆仑洞天元规则二次质检",
        "total": len(images),
        "passed": passed,
        "failed": len(images) - passed,
        "avg_score": avg,
        "results": results
    }
    report_path = "/www/wwwroot/huodouai.com/drama/kunlun_quality_check_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告已保存: {report_path}")

if __name__ == "__main__":
    main()
