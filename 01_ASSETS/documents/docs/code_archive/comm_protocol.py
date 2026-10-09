#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜中枢通信协议
定义主中枢↔次中枢之间的消息格式、握手、指令下发、回执、心跳
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""
import json
import time
import hashlib
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
MSG_QUEUE_DIR = BASE_DIR / "comm" / "msgqueue"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

# 消息类型
MSG_TYPE_HANDSHAKE = "HANDSHAKE"
MSG_TYPE_HEARTBEAT = "HEARTBEAT"
MSG_TYPE_COMMAND = "COMMAND"
MSG_TYPE_RESULT = "RESULT"
MSG_TYPE_BROADCAST = "BROADCAST"
MSG_TYPE_APPROVAL = "APPROVAL"

# 指令动作
ACTION_SCAN_ASSET = "SCAN_ASSET"
ACTION_RUN_PIPELINE = "RUN_PIPELINE"
ACTION_CROSS_VERIFY = "CROSS_VERIFY"
ACTION_SYNC_LEDGER = "SYNC_LEDGER"
ACTION_RELOAD_RULE = "RELOAD_RULE"
ACTION_STOP = "STOP"


def ensure_queue_dirs():
    """确保消息队列目录存在"""
    for d in ["master_out", "slave_in", "slave_out", "master_in", "broadcast"]:
        (MSG_QUEUE_DIR / d).mkdir(parents=True, exist_ok=True)


def gen_msg_id():
    return f"MSG-{int(time.time())}-{uuid.uuid4().hex[:8]}"


def sha256_str(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def build_message(msg_type, source, target, payload, priority=5):
    """构建标准消息包"""
    msg = {
        "msg_id": gen_msg_id(),
        "msg_type": msg_type,
        "source": source,
        "target": target,
        "timestamp": time.time(),
        "priority": priority,
        "did": DID,
        "trace": TRACE,
        "payload": payload
    }
    msg["signature"] = sha256_str(json.dumps({k: v for k, v in msg.items() if k != "signature"}, ensure_ascii=False, sort_keys=True))
    return msg


def verify_message(msg):
    """验证消息签名"""
    sig = msg.get("signature", "")
    calc = sha256_str(json.dumps({k: v for k, v in msg.items() if k != "signature"}, ensure_ascii=False, sort_keys=True))
    return sig == calc


def write_message(queue_subdir, msg):
    """写入消息到队列目录"""
    ensure_queue_dirs()
    qdir = MSG_QUEUE_DIR / queue_subdir
    fname = f"{msg['msg_id']}.json"
    fpath = qdir / fname
    fpath.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")
    return fpath


def read_messages(queue_subdir, consume=True):
    """读取并消费消息队列中的消息"""
    qdir = MSG_QUEUE_DIR / queue_subdir
    if not qdir.exists():
        return []
    msgs = []
    for f in sorted(qdir.glob("*.json")):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            if verify_message(msg):
                msgs.append(msg)
            if consume:
                f.unlink()
        except Exception:
            pass
    return msgs


def write_broadcast(msg):
    """写入全域广播消息"""
    return write_message("broadcast", msg)


def read_broadcast(consume=True):
    """读取全域广播消息"""
    return read_messages("broadcast", consume)
