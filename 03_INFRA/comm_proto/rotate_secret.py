#!/usr/bin/env python3
"""
ANCE 无SSH通讯协议 密钥轮换脚本
90天轮换计划：到期自动轮换 + 人工触发轮换。
- 生成新密钥，保留历史（旧密钥在宽限期仍可验签，实现无感轮换）
- 更新密钥配置文件
- 提示重启网关生效

溯源标识：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import json
import os
import secrets
import hashlib
import sys
import time
from datetime import datetime, timedelta

SECRET_FILE = os.path.expanduser("~/.zongyuan_root/kernel/comm_gateway_secret.json")
ROTATION_DAYS = 90  # 轮换周期
GRACE_DAYS = 7      # 旧密钥宽限期（无感轮换）


def load_cfg():
    with open(SECRET_FILE) as f:
        return json.load(f)


def save_cfg(cfg):
    os.chmod(SECRET_FILE, 0o600) if os.path.exists(SECRET_FILE) else None
    with open(SECRET_FILE, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.chmod(SECRET_FILE, 0o600)


def fingerprint(secret):
    return hashlib.sha256(secret.encode()).hexdigest()[:16].upper()


def rotate(force: bool = False) -> dict:
    """轮换密钥，返回结果"""
    cfg = load_cfg()
    now = datetime.now()
    created = datetime.fromisoformat(cfg.get("created_at", now.isoformat()))

    # 判断是否需要轮换
    if not force and (now - created).days < ROTATION_DAYS:
        remaining = ROTATION_DAYS - (now - created).days
        return {"rotated": False, "reason": f"距上次轮换{(now-created).days}天，未到{ROTATION_DAYS}天",
                "remaining_days": remaining}

    # 保留旧密钥进历史（宽限期）
    old_secret = cfg.get("secret")
    history = cfg.get("secret_history", [])
    if old_secret and old_secret not in [h["secret"] for h in history]:
        history.append({
            "secret": old_secret,
            "fingerprint": cfg.get("secret_fingerprint", ""),
            "rotated_at": now.isoformat(),
            "expires_at": (now + timedelta(days=GRACE_DAYS)).isoformat(),
        })
        # 只保留最近3代
        history = history[-3:]

    # 新密钥
    new_secret = "zy-" + secrets.token_urlsafe(48)
    cfg["secret"] = new_secret
    cfg["secret_fingerprint"] = fingerprint(new_secret)
    cfg["created_at"] = now.isoformat()
    cfg["last_rotated_at"] = now.isoformat()
    cfg["next_rotation_at"] = (now + timedelta(days=ROTATION_DAYS)).isoformat()
    cfg["rotation_days"] = ROTATION_DAYS
    cfg["grace_days"] = GRACE_DAYS
    cfg["secret_history"] = history
    cfg["did"] = "DID-BR-000002"
    cfg["trace"] = "Ω₀⊂⊙∞⊂Ω"
    cfg["node"] = "Ω-TAN-7-001"
    save_cfg(cfg)

    return {
        "rotated": True,
        "new_fingerprint": cfg["secret_fingerprint"],
        "next_rotation_at": cfg["next_rotation_at"],
        "history_kept": len(history),
        "action_required": "重启网关服务以生效",
    }


def get_rotation_status() -> dict:
    """查看轮换状态"""
    cfg = load_cfg()
    created = datetime.fromisoformat(cfg.get("created_at", datetime.now().isoformat()))
    now = datetime.now()
    days = (now - created).days
    return {
        "current_fingerprint": cfg.get("secret_fingerprint"),
        "age_days": days,
        "rotation_days": ROTATION_DAYS,
        "due_in_days": max(0, ROTATION_DAYS - days),
        "next_rotation_at": cfg.get("next_rotation_at"),
        "history_count": len(cfg.get("secret_history", [])),
        "due": days >= ROTATION_DAYS,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="9120网关密钥轮换")
    p.add_argument("--rotate", action="store_true", help="执行轮换")
    p.add_argument("--force", action="store_true", help="强制轮换（忽略周期）")
    p.add_argument("--status", action="store_true", help="查看轮换状态")
    p.add_argument("--due-check", action="store_true", help="检查是否到期（供cron调用）")
    args = p.parse_args()

    if args.status or not args.rotate:
        st = get_rotation_status()
        print(json.dumps(st, ensure_ascii=False, indent=2))
        if st["due"] and not args.status:
            print("[提醒] 密钥已到期，请执行 --rotate")
    elif args.rotate:
        r = rotate(force=args.force)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    if args.due_check:
        st = get_rotation_status()
        sys.exit(1 if st["due"] else 0)
