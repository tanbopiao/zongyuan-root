#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 本地处理优先工具集
用途：图像/视频/音频/哈希等任务本地完成，零API消耗
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
CACHE_DIR = ROOT / "cache" / "api_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ============ 哈希工具（零成本） ============
def sha256_file(filepath):
    """计算文件SHA256"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_text(text):
    """计算文本SHA256"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def merkle_root(file_list):
    """计算Merkle根"""
    hashes = [sha256_file(f) for f in sorted(file_list) if os.path.isfile(f)]
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [sha256_text(hashes[i] + hashes[i+1]) for i in range(0, len(hashes), 2)]
    return hashes[0] if hashes else "empty"

# ============ 图像本地处理（替代image_edit） ============
def image_resize(input_path, output_path, width=None, height=None):
    """图像缩放（pillow，零API）"""
    from PIL import Image
    img = Image.open(input_path)
    if width and height:
        img = img.resize((width, height), Image.LANCZOS)
    elif width:
        ratio = width / img.width
        img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
    elif height:
        ratio = height / img.height
        img = img.resize((int(img.width * ratio), height), Image.LANCZOS)
    img.save(output_path)
    return output_path

def image_watermark(input_path, output_path, text="Ω₀⊂⊙∞⊂Ω", position="bottom-right"):
    """图像水印/暗印镌刻（pillow，零API）"""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(input_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # 隐秘暗印：右下角，低透明度
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if position == "bottom-right":
        x, y = img.width - tw - 10, img.height - th - 10
    else:
        x, y = 10, img.height - th - 10
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 60))
    combined = Image.alpha_composite(img, overlay)
    combined.convert("RGB").save(output_path)
    return output_path

def image_convert(input_path, output_path, fmt=None):
    """图像格式转换（pillow/imagemagick，零API）"""
    from PIL import Image
    img = Image.open(input_path)
    if fmt:
        img.save(output_path, fmt)
    else:
        img.save(output_path)
    return output_path

# ============ 视频本地处理（替代视频API） ============
def video_clip(input_path, output_path, start_sec, duration_sec):
    """视频剪辑（ffmpeg，零API）"""
    cmd = ["ffmpeg", "-y", "-ss", str(start_sec), "-i", input_path,
           "-t", str(duration_sec), "-c", "copy", output_path]
    subprocess.run(cmd, capture_output=True)
    return output_path

def video_extract_audio(input_path, output_path):
    """提取音频（ffmpeg，零API）"""
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "copy", output_path]
    subprocess.run(cmd, capture_output=True)
    return output_path

def video_thumbnail(input_path, output_path, frame_num=0):
    """提取视频帧/缩略图（ffmpeg，零API）"""
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", f"select=eq(n\\,{frame_num})",
           "-vframes", "1", output_path]
    subprocess.run(cmd, capture_output=True)
    return output_path

def video_concat(file_list, output_path):
    """视频拼接（ffmpeg，零API）"""
    list_file = "/tmp/concat_list.txt"
    with open(list_file, "w") as f:
        for fp in file_list:
            f.write(f"file '{fp}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
           "-c", "copy", output_path]
    subprocess.run(cmd, capture_output=True)
    return output_path

# ============ API缓存（减少重复调用） ============
def cache_get(key):
    """获取API缓存"""
    cache_file = CACHE_DIR / f"{sha256_text(key)}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
        return data.get("value")
    return None

def cache_set(key, value, ttl_hours=24):
    """设置API缓存"""
    cache_file = CACHE_DIR / f"{sha256_text(key)}.json"
    with open(cache_file, "w") as f:
        json.dump({"key": key, "value": value, "ttl": ttl_hours}, f, ensure_ascii=False)
    return True

# ============ 全域资产扫描（零成本） ============
def scan_all_assets():
    """扫描全量资产并计算哈希"""
    assets = []
    for fp in ROOT.rglob("*"):
        if fp.is_file() and "cache" not in str(fp):
            rel = fp.relative_to(ROOT)
            assets.append({
                "path": str(rel),
                "sha256": sha256_file(fp),
                "size": fp.stat().st_size,
                "domain": str(rel).split("/")[0]
            })
    return assets

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "scan":
            assets = scan_all_assets()
            print(json.dumps({"total": len(assets), "assets": assets}, ensure_ascii=False, indent=2))
        elif cmd == "hash":
            print(sha256_file(sys.argv[2]))
        elif cmd == "merkle":
            files = sys.argv[2:]
            print(merkle_root(files))
        else:
            print(f"Unknown command: {cmd}")
    else:
        print("ZONGYUAN-ROOT 本地处理工具集")
        print("Commands: scan, hash <file>, merkle <files...>")
