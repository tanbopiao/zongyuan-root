#!/usr/bin/env python3
"""
动作7: IM机器人自动推送 - 进化回执+异常告警
通过飞书IM发送通知，零成本替代短信/邮件
"""
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")

def send_im_message(text: str, receive_id: str = None, receive_id_type: str = "open_id"):
    """
    发送飞书IM消息
    实际使用需配置receive_id（用户open_id或群chat_id）
    """
    payload = {
        "receive_id": receive_id or "USER_DEFAULT",
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    # 通过lark-cli发送（实际环境需配置接收者）
    cmd = [
        "lark-cli", "im", "+send",
        "--receive-id", payload["receive_id"],
        "--receive-id-type", receive_id_type,
        "--msg-type", "text",
        "--content", payload["content"]
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {"status": "sent", "stdout": result.stdout[:500], "stderr": result.stderr[:200]}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def build_daily_report(asset_count: int, new_assets: int, lock_status: str,
                       four_layer: dict, alerts: list = None) -> str:
    """构建每日进化回执消息"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"""
🔷 Ω-Brainμ 每日进化回执 {now}
━━━━━━━━━━━━━━━━━━━━
📦 资产总数: {asset_count}件
✨ 今日新增: {new_assets}件
🔒 锁档状态: {lock_status}
━━━━━━━━━━━━━━━━━━━━
📊 四层校验:
  L1不动点: {four_layer.get('L1', 'N/A')}
  L2时序: {four_layer.get('L2', 'N/A')}
  L3推理: {four_layer.get('L3', 'N/A')}
  L4观感: {four_layer.get('L4', 'N/A')}
━━━━━━━━━━━━━━━━━━━━
Ω₀⊂⊙∞⊂Ω ZONGYUAN-ROOT DID-BR-000002
"""
    if alerts:
        msg += f"\n⚠️ 告警: {len(alerts)}项\n"
        for a in alerts[:3]:
            msg += f"  - {a}\n"
    return msg.strip()

def build_alert(alert_type: str, severity: str, message: str) -> str:
    """构建告警消息"""
    icons = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}
    icon = icons.get(severity, "⚪")
    return f"{icon} [{severity}] {alert_type}: {message}\n时间: {datetime.now().isoformat()}\nΩ₀⊂⊙∞⊂Ω"

def notify_daily_evolution(asset_count=32, new_assets=5):
    """发送每日进化回执（演示）"""
    report = build_daily_report(
        asset_count=asset_count,
        new_assets=new_assets,
        lock_status="100% LOCKED",
        four_layer={"L1": "PASS", "L2": "PASS", "L3": "PASS", "L4": "PASS"}
    )
    print("=== 每日进化回执（待发送）===")
    print(report)
    return report

def notify_alert(alert_type="资产漂移", severity="P1", message="检测到资产哈希不一致"):
    """发送告警（演示）"""
    alert = build_alert(alert_type, severity, message)
    print("=== 告警通知（待发送）===")
    print(alert)
    return alert

if __name__ == "__main__":
    notify_daily_evolution()
    print()
    notify_alert()
