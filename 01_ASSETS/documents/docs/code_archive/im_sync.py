#!/usr/bin/env python3
"""
飞书IM消息同步通道 (im_sync.py)
ZONGYUAN-ROOT 元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

通过飞书IM消息实现轻量级同步：
- 心跳保活：定期发送心跳消息
- 状态通知：内核状态变更/告警/事件通知
- 指令下发：通过IM消息下发指令到本地
- 多窗口共享：多窗口通过群消息共享状态

用法：
  python3 im_sync.py --send "消息内容" [--chat-id <群ID>]
  python3 im_sync.py --heartbeat
  python3 im_sync.py --notify --level info --title "标题" --content "内容"
  python3 im_sync.py --listen [--chat-id <群ID>]
"""
import json
import subprocess
import argparse
import hashlib
from datetime import datetime

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
DEFAULT_CHAT_ID = "oc_feishu_sync_channel"  # 需配置实际群ID


def run_lark_cli(args, timeout=30):
    """执行lark-cli命令并返回解析后的JSON"""
    cmd = ["lark-cli"] + args + ["--as", "user", "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    output = result.stdout
    lines = output.strip().split('\n')
    json_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('{'):
            json_start = i
            break
    try:
        return json.loads('\n'.join(lines[json_start:]))
    except json.JSONDecodeError:
        return {"ok": False, "error": "JSON parse failed", "raw": output}


def send_message(content, chat_id=None):
    """发送消息到指定群聊"""
    target = chat_id or DEFAULT_CHAT_ID
    print(f"[IM-SYNC] 发送消息到 {target}")
    print(f"  内容: {content[:80]}...")

    result = run_lark_cli([
        "im", "+send-message",
        "--chat-id", target,
        "--content", content,
        "--msg-type", "text"
    ])

    if result.get("ok"):
        msg_id = result.get("data", {}).get("message_id", "unknown")
        print(f"  ✓ 发送成功，message_id: {msg_id}")
        return True, msg_id
    else:
        print(f"  ✗ 发送失败: {result.get('error', 'unknown')}")
        return False, None


def send_heartbeat():
    """发送心跳消息"""
    ts = datetime.now().isoformat()
    heartbeat = {
        "type": "HEARTBEAT",
        "timestamp": ts,
        "did": DID,
        "trace_mark": TRACE_MARK,
        "status": "ALIVE",
        "kernel_version": "ZONGYUAN-ROOT-SNAP-20260912-V3.1",
        "channel": "IM_SYNC"
    }
    content = f"[心跳] {ts} | 内核V3.1 | 状态: ALIVE | {TRACE_MARK}"
    return send_message(content)


def send_notification(level, title, content):
    """发送通知消息"""
    level_icons = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "success": "✅",
        "critical": "🚨"
    }
    icon = level_icons.get(level, "📢")
    ts = datetime.now().isoformat()
    msg = f"{icon} [{level.upper()}] {title}\n时间: {ts}\n内容: {content}\n确权: {DID} | {TRACE_MARK}"
    return send_message(msg)


def listen_messages(chat_id=None, duration=60):
    """监听群消息（轮询方式）"""
    target = chat_id or DEFAULT_CHAT_ID
    print(f"[IM-SYNC] 开始监听 {target}，时长 {duration} 秒")

    start = datetime.now()
    last_msg_id = None

    while (datetime.now() - start).seconds < duration:
        result = run_lark_cli([
            "im", "+chat-history",
            "--chat-id", target,
            "--page-size", "10"
        ])

        if result.get("ok"):
            messages = result.get("data", {}).get("items", [])
            for msg in reversed(messages):
                msg_id = msg.get("message_id")
                if msg_id and msg_id != last_msg_id:
                    sender = msg.get("sender", {}).get("id", "unknown")
                    body = msg.get("body", {}).get("content", "")
                    print(f"  [新消息] {sender}: {body[:100]}")
                    # 解析指令
                    if body.startswith("[指令]"):
                        print(f"    → 检测到指令，待处理")
                    last_msg_id = msg_id

        import time
        time.sleep(5)

    print(f"[IM-SYNC] 监听结束")


def main():
    parser = argparse.ArgumentParser(description='飞书IM消息同步通道')
    parser.add_argument('--send', type=str, help='发送消息内容')
    parser.add_argument('--chat-id', type=str, help='目标群聊ID')
    parser.add_argument('--heartbeat', action='store_true', help='发送心跳')
    parser.add_argument('--notify', action='store_true', help='发送通知')
    parser.add_argument('--level', type=str, default='info', choices=['info', 'warning', 'error', 'success', 'critical'], help='通知级别')
    parser.add_argument('--title', type=str, help='通知标题')
    parser.add_argument('--content', type=str, help='通知内容')
    parser.add_argument('--listen', action='store_true', help='监听消息')
    parser.add_argument('--duration', type=int, default=60, help='监听时长(秒)')

    args = parser.parse_args()

    print("=" * 60)
    print("  飞书IM消息同步通道")
    print(f"  DID: {DID} | {TRACE_MARK}")
    print("=" * 60)

    if args.send:
        send_message(args.send, args.chat_id)
    elif args.heartbeat:
        send_heartbeat()
    elif args.notify:
        if not args.title or not args.content:
            print("  ✗ 通知模式需要 --title 和 --content")
            return
        send_notification(args.level, args.title, args.content)
    elif args.listen:
        listen_messages(args.chat_id, args.duration)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
