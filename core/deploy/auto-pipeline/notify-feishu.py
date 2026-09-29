#!/usr/bin/env python3
"""部署完成飞书群通知"""
import json
import subprocess

WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/oc_1c68eb3664e751e397062ff0c60ffa3e"

def notify_deploy(status, commit, files_count):
    """发送部署完成通知到飞书群"""
    color = "green" if status == "success" else "red"
    msg = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"ZONGYUAN-ROOT 自动部署 {status.upper()}"},
                "template": color
            },
            "elements": [
                {"tag": "div", "text": {"tag": "plain_text", "content": f"提交: {commit}"}},
                {"tag": "div", "text": {"tag": "plain_text", "content": f"文件数: {files_count}"}},
                {"tag": "div", "text": {"tag": "plain_text", "content": "确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω"}}
            ]
        }
    }
    subprocess.run([
        "curl", "-s", "-X", "POST", WEBHOOK,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(msg)
    ])

if __name__ == "__main__":
    notify_deploy("success", "auto-deploy-20260922", 36)
