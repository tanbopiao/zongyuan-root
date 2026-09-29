#!/usr/bin/env python3
"""
ZONGYUAN-ROOT AI端媒体归档任务推送器
支持两种模式：
1. HTTP模式：直接访问服务器API（需网络可达）
2. SSH模式：通过SSH隧道在服务器端执行curl（默认，最安全）

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, sys, subprocess
from datetime import datetime

# 服务器配置
SERVER_IP = "123.207.202.158"
SSH_KEY = "~/.ssh/id_ed25519"
API_KEY = "ZONGYUAN-MEDIA-ARCHIVE-2026-9f3a7c1e"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

def push_media_archive_task(project, episode, media_items, task_id=None, mode="ssh"):
    """
    推送媒体归档任务到服务器
    
    Args:
        project: 项目名称（如 kunlun）
        episode: 集数/编号（如 ep01）
        media_items: 媒体列表，每项包含 id/type/filename/url
        task_id: 可选任务ID
        mode: "ssh"（默认）或 "http"
    """
    task = {
        "task_id": task_id or f"AUTO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "project": project,
        "episode": episode,
        "media_items": media_items,
        "source": "ai-producer",
        "did": DID,
        "trace": TRACE
    }
    
    task_json = json.dumps(task, ensure_ascii=False)
    
    if mode == "ssh":
        # SSH模式：在服务器端执行curl
        cmd = [
            "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=15",
            f"root@{SERVER_IP}",
            f"curl -s -X POST http://127.0.0.1:9400/api/media-archive/task "
            f"-H 'X-API-Key: {API_KEY}' "
            f"-H 'Content-Type: application/json' "
            f"-d '{task_json}'"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                resp = json.loads(result.stdout)
                print("✅ 任务推送成功（SSH模式）")
                print(f"   任务ID: {resp.get('task_id')}")
                print(f"   媒体数: {resp.get('media_count')}")
                print(f"   消息: {resp.get('message')}")
                return resp
            else:
                print(f"❌ SSH执行失败: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ 推送失败: {e}")
            return None
    else:
        # HTTP模式
        try:
            import requests
            resp = requests.post(
                f"http://{SERVER_IP}/media-archive/api/media-archive/task",
                headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
                json=task, timeout=10
            )
            result = resp.json()
            print("✅ 任务推送成功（HTTP模式）")
            return result
        except Exception as e:
            print(f"❌ HTTP推送失败: {e}")
            return None

def check_server_health(mode="ssh"):
    """检查服务器任务接收API健康状态"""
    if mode == "ssh":
        cmd = [
            "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=15",
            f"root@{SERVER_IP}",
            "curl -s http://127.0.0.1:9400/health"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return json.loads(result.stdout)
        except Exception as e:
            return {"error": str(e)}
    else:
        try:
            import requests
            resp = requests.get(f"http://{SERVER_IP}/media-archive/health", timeout=5)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        print("服务器状态:", check_server_health())
    else:
        print("用法:")
        print("  python3 media_archive_push.py health  # 检查服务器状态")
        print("")
        print("在AI产线中调用:")
        print("  from media_archive_push import push_media_archive_task")
        print("  push_media_archive_task('kunlun', 'ep02', [")
        print("    {'id':'S02-001','type':'image','filename':'xxx.jpg','url':'https://...'},")
        print("    {'id':'S02-001','type':'video','filename':'xxx.mp4','url':'https://...'}")
        print("  ])")
