#!/usr/bin/env python3
"""
作品质量批量筛选脚本
- 扫描官网展示位置的所有图片
- 使用glm-4v-flash进行多维度质量评估
- 低质量作品（多手/面部崩坏/模糊/漂移）自动归档
- 生成质量白名单和黑名单
"""
import os
import json
import time
import hashlib
import requests
from datetime import datetime
from pathlib import Path

# 配置
ZHIPU_API_KEY = "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
MODEL = "glm-4v-flash"

# 官网展示位置（优先级排序）
DISPLAY_PATHS = [
    "/www/wwwroot/huodouai.com/drama/keyframes/ep01",
    "/www/wwwroot/huodouai.com/drama/gallery/keyframes",
    "/www/wwwroot/huodouai.com/aios/assets/kunlun/keyframes",
    "/www/wwwroot/huodouai.com/aios/assets/kunlun/characters",
]

# 低质量归档目录
ARCHIVE_DIR = "/www/wwwroot/huodouai.com/drama/_archive_low_quality/images"

# 质量报告目录
REPORT_DIR = "/www/wwwroot/huodouai.com/drama/_quality_reports"

# 质量阈值
QUALITY_THRESHOLD = 80  # 综合评分≥80分为高质量
SEVERE_ISSUES = ["multiple_hands", "face_distortion", "extra_fingers", "missing_limbs"]

def get_image_hash(image_path):
    """计算图片SHA256哈希"""
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def encode_image_to_base64(image_path):
    """将图片编码为base64"""
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def check_image_quality(image_path):
    """使用glm-4v-flash检查图片质量"""
    try:
        image_b64 = encode_image_to_base64(image_path)
        
        prompt = """请对这张AI生成的图片进行严格的质量评估，特别关注以下问题：
1. 多手/多手指/多余肢体（multiple hands/fingers/limbs）
2. 面部崩坏/五官扭曲（face distortion）
3. 图像模糊/低分辨率（blurry/low resolution）
4. 角色形象漂移（character drift）
5. 构图问题/内容不合理（composition issues）
6. 文字乱码/水印（text artifacts/watermarks）

请以JSON格式返回评估结果：
{
  "overall_score": 0-100,
  "has_multiple_hands": true/false,
  "hand_count": "正常/2只/3只/更多",
  "has_face_distortion": true/false,
  "is_blurry": true/false,
  "has_character_drift": true/false,
  "has_severe_issues": true/false,
  "issues": ["问题1", "问题2"],
  "severity": "none/low/medium/high/critical",
  "pass": true/false,
  "quality_level": "excellent/good/acceptable/poor/unusable"
}

只返回JSON，不要其他文字。"""

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }

        headers = {
            "Authorization": f"Bearer {ZHIPU_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{ZHIPU_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            # 解析JSON
            try:
                # 清理可能的markdown标记
                content = content.replace("```json", "").replace("```", "").strip()
                quality_result = json.loads(content)
                return quality_result
            except json.JSONDecodeError:
                return {"overall_score": 50, "pass": False, "issues": ["解析失败"], "severity": "medium"}
        else:
            return {"overall_score": 50, "pass": False, "issues": [f"API错误: {response.status_code}"], "severity": "medium"}

    except Exception as e:
        return {"overall_score": 50, "pass": False, "issues": [f"异常: {str(e)}"], "severity": "medium"}

def scan_images():
    """扫描所有展示位置的图片"""
    images = []
    for display_path in DISPLAY_PATHS:
        if os.path.exists(display_path):
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                for img_path in Path(display_path).rglob(ext):
                    images.append(str(img_path))
    return list(set(images))  # 去重

def archive_low_quality(image_path, reason):
    """归档低质量图片"""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    filename = os.path.basename(image_path)
    archive_path = os.path.join(ARCHIVE_DIR, filename)
    
    # 如果目标已存在，添加时间戳
    if os.path.exists(archive_path):
        name, ext = os.path.splitext(filename)
        archive_path = os.path.join(ARCHIVE_DIR, f"{name}_{int(time.time())}{ext}")
    
    # 移动文件
    os.rename(image_path, archive_path)
    return archive_path

def main():
    print("=" * 60)
    print("  作品质量批量筛选启动")
    print("=" * 60)
    print(f"时间: {datetime.now().isoformat()}")
    print(f"质量阈值: {QUALITY_THRESHOLD}分")
    print(f"严重问题: {SEVERE_ISSUES}")
    print()

    # 1. 扫描图片
    print("【1/4】扫描展示位置图片...")
    images = scan_images()
    print(f"  发现 {len(images)} 张图片")
    print()

    # 2. 批量质量检查
    print("【2/4】批量质量检查...")
    results = []
    passed = []
    failed = []
    
    for i, image_path in enumerate(images):
        filename = os.path.basename(image_path)
        print(f"  [{i+1}/{len(images)}] 检查: {filename[:50]}...", end=" ")
        
        # 跳过webp（只检查jpg/png，webp作为副本）
        if image_path.endswith(".webp"):
            print("跳过(webp副本)")
            continue
        
        quality = check_image_quality(image_path)
        quality["filepath"] = image_path
        quality["filename"] = filename
        quality["file_hash"] = get_image_hash(image_path)
        quality["check_time"] = datetime.now().isoformat()
        
        results.append(quality)
        
        if quality.get("pass", False) and quality.get("overall_score", 0) >= QUALITY_THRESHOLD and not quality.get("has_severe_issues", False):
            passed.append(quality)
            print(f"✅ 通过 ({quality.get('overall_score')}分)")
        else:
            failed.append(quality)
            print(f"❌ 未通过 ({quality.get('overall_score')}分) - {quality.get('issues', [])[:2]}")
        
        # 避免API限流
        time.sleep(0.5)
    
    print()
    print(f"  检查完成: 通过 {len(passed)} 张, 未通过 {len(failed)} 张")
    print()

    # 3. 归档低质量图片
    print("【3/4】归档低质量图片...")
    archived = []
    for item in failed:
        try:
            archive_path = archive_low_quality(item["filepath"], item.get("issues", []))
            item["archived_to"] = archive_path
            archived.append(item)
            print(f"  📦 已归档: {item['filename'][:40]} -> {os.path.basename(archive_path)}")
        except Exception as e:
            print(f"  ⚠️ 归档失败: {item['filename'][:40]} - {e}")
    print()

    # 4. 生成质量报告
    print("【4/4】生成质量报告...")
    os.makedirs(REPORT_DIR, exist_ok=True)
    report = {
        "report_time": datetime.now().isoformat(),
        "model": MODEL,
        "quality_threshold": QUALITY_THRESHOLD,
        "total_scanned": len(images),
        "total_checked": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "archived": len(archived),
        "pass_rate": f"{len(passed)/max(len(results),1)*100:.1f}%",
        "avg_score": sum(r.get("overall_score", 0) for r in results) / max(len(results), 1),
        "whitelist": [
            {"filename": r["filename"], "score": r["overall_score"], "hash": r["file_hash"]}
            for r in passed
        ],
        "blacklist": [
            {"filename": r["filename"], "score": r["overall_score"], "issues": r.get("issues", []), "archived_to": r.get("archived_to", "")}
            for r in archived
        ],
        "all_results": results
    }

    report_file = os.path.join(REPORT_DIR, f"quality_screening_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"  报告已保存: {report_file}")
    print()

    # 输出总结
    print("=" * 60)
    print("  质量筛选完成总结")
    print("=" * 60)
    print(f"  扫描图片: {len(images)} 张")
    print(f"  实际检查: {len(results)} 张")
    print(f"  通过: {len(passed)} 张 ✅")
    print(f"  未通过: {len(failed)} 张 ❌")
    print(f"  已归档: {len(archived)} 张 📦")
    print(f"  通过率: {report['pass_rate']}")
    print(f"  平均分: {report['avg_score']:.1f}")
    print()
    print(f"  质量白名单: {len(passed)} 张高质量作品")
    print(f"  低质量归档: {ARCHIVE_DIR}")
    print(f"  质量报告: {report_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
