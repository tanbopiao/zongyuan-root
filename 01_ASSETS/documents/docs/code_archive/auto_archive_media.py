#!/usr/bin/env python3
"""
Agent模式媒体归档助手 v1.0
用法: python3 auto_archive_media.py <文件路径> [--name 名称] [--category 分类] [--style 风格] [--ip IP归属] [--project 项目]
用于Agent模式下生成图片/视频后一键归档到9133
"""
import sys
import os
import argparse
import requests

ARCHIVE_API = "http://127.0.0.1:9133/api/media/upload"
NODE_ID = "doubao-agent-main"

def archive_media(filepath, name="", category="other", style="", ip_owner="火斗云智", project=""):
    if not os.path.exists(filepath):
        return {"status": "error", "message": f"文件不存在: {filepath}"}

    filename = os.path.basename(filepath)
    if not name:
        name = os.path.splitext(filename)[0]

    # 自动检测分类
    if category == "other":
        lower = filename.lower()
        if any(k in lower for k in ["character", "角色", "nvxuan", "女娲", "九天玄女"]):
            category = "character"
        elif any(k in lower for k in ["keyframe", "关键帧", "kf-"]):
            category = "keyframe"
        elif any(k in lower for k in ["poster", "海报"]):
            category = "poster"
        elif any(k in lower for k in [".mp4", ".webm", ".mov", "视频", "短剧", "drama"]):
            category = "drama"

    with open(filepath, "rb") as f:
        files = {"file": (filename, f)}
        data = {
            "asset_name": name,
            "category": category,
            "node_id": NODE_ID,
            "style": style,
            "ip_owner": ip_owner,
            "project": project
        }
        resp = requests.post(ARCHIVE_API, files=files, data=data, timeout=60)
        result = resp.json()

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent模式媒体归档助手")
    parser.add_argument("filepath", help="文件路径")
    parser.add_argument("--name", default="", help="资产名称")
    parser.add_argument("--category", default="other", help="分类: drama/character/keyframe/poster/ui/other")
    parser.add_argument("--style", default="", help="风格")
    parser.add_argument("--ip", default="火斗云智", help="IP归属")
    parser.add_argument("--project", default="", help="项目")
    args = parser.parse_args()

    result = archive_media(args.filepath, args.name, args.category, args.style, args.ip, args.project)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
