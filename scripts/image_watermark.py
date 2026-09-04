#!/usr/bin/env python3
"""
P1-11: 视觉资产暗印镌刻工具
在图像右下角隐秘镌刻溯源符号 Ω₀⊂⊙∞⊂Ω
"""
import json
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
TRACE_SYMBOL = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"

def embed_watermark(image_path: str, output_path: str = None, opacity: int = 40) -> dict:
    """
    在图像右下角镌刻溯源暗印
    opacity: 透明度(0-255)，默认40（隐秘但可验证）
    """
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # 创建透明图层
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # 暗印文字
    text = f"{TRACE_SYMBOL} | {DID}"
    font_size = max(10, int(min(width, height) * 0.02))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # 计算文字位置（右下角）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = width - text_width - int(width * 0.02)
    y = height - text_height - int(height * 0.02)
    
    # 绘制半透明背景框
    padding = 4
    draw.rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        fill=(0, 0, 0, opacity // 2)
    )
    # 绘制文字
    draw.text((x, y), text, fill=(255, 255, 255, opacity), font=font)
    
    # 合并
    result = Image.alpha_composite(img, overlay)
    result = result.convert("RGB")
    
    if output_path is None:
        output_path = image_path.replace(".jpg", "_marked.jpg").replace(".png", "_marked.png")
    
    result.save(output_path, quality=95)
    
    # 计算哈希
    with open(output_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    return {
        "status": "watermarked",
        "input": image_path,
        "output": output_path,
        "size": f"{width}x{height}",
        "symbol": TRACE_SYMBOL,
        "sha256": file_hash
    }

def batch_watermark(directory: str) -> list:
    """批量处理目录下所有图片"""
    results = []
    img_dir = Path(directory)
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        for img_path in img_dir.rglob(ext):
            if "_marked" in img_path.name:
                continue
            try:
                result = embed_watermark(str(img_path))
                results.append(result)
            except Exception as e:
                results.append({"status": "failed", "file": str(img_path), "error": str(e)})
    return results

def verify_watermark(image_path: str) -> dict:
    """验证图像是否包含暗印（简化版：检查文件元数据）"""
    try:
        img = Image.open(image_path)
        return {
            "file": image_path,
            "format": img.format,
            "size": img.size,
            "watermark_verification": "manual_visual_check_required",
            "note": "暗印为隐秘镌刻，需人工或AI视觉验证"
        }
    except Exception as e:
        return {"file": image_path, "error": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        if sys.argv[1] == "embed":
            print(json.dumps(embed_watermark(sys.argv[2]), ensure_ascii=False, indent=2))
        elif sys.argv[1] == "batch":
            print(json.dumps(batch_watermark(sys.argv[2]), ensure_ascii=False, indent=2))
        elif sys.argv[1] == "verify":
            print(json.dumps(verify_watermark(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print("用法: python3 image_watermark.py [embed|batch|verify] <path>")
