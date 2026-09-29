#!/usr/bin/env python3
"""
全域图片视频URL归档台账生成器
整合本地资产URL + 工作空间提取URL + 飞书文件链接，去重分类，生成CSV+JSON
"""
import json
import csv
import hashlib
import os
from datetime import datetime

# === 1. 本地上传资产（有本地路径，可计算真实SHA256）===
local_assets = [
    {
        "url": "https://aka.doubaocdn.com/s/a5OcUkPk76",
        "local_path": "/home/user/.doubao/agent_mode/workspace/.sessions/38437458338949122/attachments/image.png",
        "name": "会话附件图片-38437458338949122",
        "type": "image",
        "format": "png",
        "source": "local_attachment",
        "size_bytes": 1126329,
    },
    {
        "url": "https://aka.doubaocdn.com/s/9U8TIBUvwF",
        "local_path": "/home/user/.doubao/agent_mode/workspace/zongyuan_tools/social_auto_upload/repo/videos/demo.mp4",
        "name": "社媒自动上传-demo视频",
        "type": "video",
        "format": "mp4",
        "source": "social_auto_upload_tool",
        "size_bytes": 988559,
    },
    {
        "url": "https://aka.doubaocdn.com/s/b2LtEyQog6",
        "local_path": "/home/user/.doubao/agent_mode/workspace/.sessions/1128121028098/attachments/image.png",
        "name": "会话附件图片-1128121028098",
        "type": "image",
        "format": "png",
        "source": "local_attachment",
        "size_bytes": 988116,
    },
    {
        "url": "https://aka.doubaocdn.com/s/SlVaPCUR9g",
        "local_path": "/home/user/.doubao/agent_mode/workspace/zongyuan_tools/social_auto_upload/repo/media/show/tkupload.gif",
        "name": "社媒自动上传-TikTok上传演示GIF",
        "type": "image",
        "format": "gif",
        "source": "social_auto_upload_tool",
        "size_bytes": 922235,
    },
    {
        "url": "https://aka.doubaocdn.com/s/rmjeSsuW5S",
        "local_path": "/home/user/.doubao/agent_mode/workspace/.sessions/38437335960673794/attachments/image.png",
        "name": "会话附件图片-38437335960673794",
        "type": "image",
        "format": "png",
        "source": "local_attachment",
        "size_bytes": 682892,
    },
    {
        "url": "https://aka.doubaocdn.com/s/sYf37zJRCw",
        "local_path": "/home/user/.doubao/agent_mode/workspace/.sessions/1128121028098/attachments/attachment_1788595757_0.jpg",
        "name": "会话附件图片-1788595757",
        "type": "image",
        "format": "jpg",
        "source": "local_attachment",
        "size_bytes": 517710,
    },
    {
        "url": "https://aka.doubaocdn.com/s/kh9iX55om1",
        "local_path": "/home/user/.doubao/agent_mode/workspace/zongyuan_tools/social_auto_upload/repo/media/show/pdf3.gif",
        "name": "社媒自动上传-PDF上传演示GIF",
        "type": "image",
        "format": "gif",
        "source": "social_auto_upload_tool",
        "size_bytes": 405950,
    },
    {
        "url": "https://aka.doubaocdn.com/s/8QOqCB05tI",
        "local_path": "/home/user/.doubao/agent_mode/workspace/zongyuan_tools/social_auto_upload/test_video.mp4",
        "name": "社媒自动上传-测试视频",
        "type": "video",
        "format": "mp4",
        "source": "social_auto_upload_tool",
        "size_bytes": 344794,
    },
]

# === 2. 工作空间提取的自有/高价值外部URL ===
external_assets = [
    {
        "url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png",
        "name": "ARK平台-演示图片1",
        "type": "image", "format": "png", "source": "ark_platform", "size_bytes": None,
    },
    {
        "url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/r2v_tea_pic1.jpg",
        "name": "ARK平台-图生视频茶图1",
        "type": "image", "format": "jpg", "source": "ark_platform", "size_bytes": None,
    },
    {
        "url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/r2v_tea_pic2.jpg",
        "name": "ARK平台-图生视频茶图2",
        "type": "image", "format": "jpg", "source": "ark_platform", "size_bytes": None,
    },
    {
        "url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seepro_i2v.png",
        "name": "ARK平台-SeePro图生视频",
        "type": "image", "format": "png", "source": "ark_platform", "size_bytes": None,
    },
    {
        "url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/r2v_tea_video1.mp4",
        "name": "ARK平台-图生视频茶视频1",
        "type": "video", "format": "mp4", "source": "ark_platform", "size_bytes": None,
    },
    {
        "url": "https://www.huodouai.com/assets/og-cover.jpg",
        "name": "火斗云智官网-OG封面图",
        "type": "image", "format": "jpg", "source": "huodouai_official", "size_bytes": None,
    },
]

# === 3. 飞书文件链接 ===
feishu_assets = [
    {"url": "https://feishu.cn/file/E8j3bkMJwocgzsxUPsfcJxyZnnd", "name": "飞书文件-E8j3bkM", "type": "file", "format": "feishu", "source": "feishu_drive", "size_bytes": None},
    {"url": "https://feishu.cn/file/EU8lb78q7oChnOxYHpUcZQekngh", "name": "飞书文件-EU8lb78", "type": "file", "format": "feishu", "source": "feishu_drive", "size_bytes": None},
    {"url": "https://feishu.cn/file/GkTZbdxd3oBC5ExHthacc3zJnCe", "name": "飞书文件-GkTZbdx", "type": "file", "format": "feishu", "source": "feishu_drive", "size_bytes": None},
    {"url": "https://feishu.cn/file/I1QPbseAuoGicrxzP0Lc1OivnwC", "name": "飞书文件-I1QPbse", "type": "file", "format": "feishu", "source": "feishu_drive", "size_bytes": None},
    {"url": "https://feishu.cn/file/RqvCbMWPbou2BIxSylpcddwLnhb", "name": "飞书文件-RqvCbMW", "type": "file", "format": "feishu", "source": "feishu_drive", "size_bytes": None},
    {"url": "https://feishu.cn/file/XaMLbaPp8oIoFMxEyqjcjd27ncf", "name": "飞书文件-XaMLbaP", "type": "file", "format": "feishu", "source": "feishu_drive", "size_bytes": None},
]

# 合并所有资产
all_assets = local_assets + external_assets + feishu_assets

# 计算本地资产的真实SHA256
for asset in all_assets:
    if asset.get("local_path") and os.path.exists(asset["local_path"]):
        with open(asset["local_path"], "rb") as f:
            asset["sha256"] = hashlib.sha256(f.read()).hexdigest()
    else:
        # 对URL计算内容指纹（URL哈希作为标识）
        asset["sha256"] = hashlib.sha256(asset["url"].encode()).hexdigest()
    # URL去重指纹
    asset["url_hash"] = hashlib.md5(asset["url"].encode()).hexdigest()[:12]

# 去重（按URL）
seen_urls = set()
unique_assets = []
for asset in all_assets:
    if asset["url"] not in seen_urls:
        seen_urls.add(asset["url"])
        unique_assets.append(asset)

# 分配资产ID和元类
META_CLASS_MAP = {
    "local_attachment": "M5",
    "social_auto_upload_tool": "M5",
    "ark_platform": "M5",
    "huodouai_official": "M6",
    "feishu_drive": "M6",
}

for i, asset in enumerate(unique_assets, 1):
    asset["asset_id"] = f"KD-MEDIA-{i:04d}"
    asset["meta_class"] = META_CLASS_MAP.get(asset["source"], "M5")
    asset["did"] = "DID-BR-000002"
    asset["trace_mark"] = "Ω₀⊂⊙∞⊂Ω"
    asset["archived_at"] = datetime.now().isoformat()
    asset["lock_level"] = 3

# 统计
stats = {
    "total": len(unique_assets),
    "by_type": {},
    "by_source": {},
    "by_meta_class": {},
    "by_format": {},
    "total_size_bytes": sum(a["size_bytes"] for a in unique_assets if a["size_bytes"]),
    "local_count": len([a for a in unique_assets if a.get("local_path")]),
    "external_count": len([a for a in unique_assets if not a.get("local_path") and a["source"] != "feishu_drive"]),
    "feishu_count": len([a for a in unique_assets if a["source"] == "feishu_drive"]),
}

for asset in unique_assets:
    stats["by_type"][asset["type"]] = stats["by_type"].get(asset["type"], 0) + 1
    stats["by_source"][asset["source"]] = stats["by_source"].get(asset["source"], 0) + 1
    stats["by_meta_class"][asset["meta_class"]] = stats["by_meta_class"].get(asset["meta_class"], 0) + 1
    stats["by_format"][asset["format"]] = stats["by_format"].get(asset["format"], 0) + 1

# 输出目录
output_dir = "/home/user/Doubao/chats/38442240612888322"
os.makedirs(output_dir, exist_ok=True)

# 写JSON
json_path = os.path.join(output_dir, "media_url_archive.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump({"stats": stats, "assets": unique_assets}, f, ensure_ascii=False, indent=2)

# 写CSV
csv_path = os.path.join(output_dir, "media_url_archive.csv")
fieldnames = ["asset_id", "name", "type", "format", "url", "source", "meta_class",
              "sha256", "url_hash", "size_bytes", "local_path", "lock_level", "did", "archived_at"]
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for asset in unique_assets:
        row = {k: asset.get(k, "") for k in fieldnames}
        writer.writerow(row)

print(f"=== 全域图片视频URL归档台账生成完成 ===")
print(f"总资产数: {stats['total']}")
print(f"按类型: {json.dumps(stats['by_type'], ensure_ascii=False)}")
print(f"按来源: {json.dumps(stats['by_source'], ensure_ascii=False)}")
print(f"按元类: {json.dumps(stats['by_meta_class'], ensure_ascii=False)}")
print(f"按格式: {json.dumps(stats['by_format'], ensure_ascii=False)}")
print(f"已知总大小: {stats['total_size_bytes']} bytes ({stats['total_size_bytes']/1024/1024:.2f} MB)")
print(f"本地资产: {stats['local_count']}, 外部URL: {stats['external_count']}, 飞书文件: {stats['feishu_count']}")
print(f"JSON: {json_path}")
print(f"CSV: {csv_path}")
