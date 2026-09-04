#!/usr/bin/env python3
"""
P1-6: IM通知配置器
配置飞书消息接收者（用户open_id或群chat_id）
"""
import json
from pathlib import Path

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
CONFIG_FILE = ROOT / "config" / "im_config.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "default_receive_id": "USER_DEFAULT",
    "default_receive_type": "open_id",
    "alert_receive_id": "USER_DEFAULT",
    "alert_receive_type": "open_id",
    "daily_report_receive_id": "USER_DEFAULT",
    "daily_report_receive_type": "open_id",
    "channels": {
        "critical": {"receive_id": "USER_DEFAULT", "receive_type": "open_id"},
        "warning": {"receive_id": "USER_DEFAULT", "receive_type": "open_id"},
        "info": {"receive_id": "USER_DEFAULT", "receive_type": "open_id"}
    },
    "message_templates": {
        "alert": "【ZONGYUAN-ROOT告警】{level}: {message}",
        "daily": "【每日进化报告】{date}: {summary}",
        "lock": "【锁档完成】{asset} SHA256={hash}"
    }
}

def get_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG

def set_receive_id(channel: str, receive_id: str, receive_type: str = "open_id"):
    config = get_config()
    if channel in config["channels"]:
        config["channels"][channel] = {"receive_id": receive_id, "receive_type": receive_type}
    else:
        config["default_receive_id"] = receive_id
        config["default_receive_type"] = receive_type
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return config

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"IM配置已初始化: {CONFIG_FILE}")
    else:
        print(json.dumps(get_config(), ensure_ascii=False, indent=2))
