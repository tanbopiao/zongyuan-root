#!/usr/bin/env python3
"""ZONGYUAN-ROOT 内核授权守护模块
- 启动时验证授权码
- 验证失败降级为免费版
- 机器指纹绑定
- 到期前告警
- 运行时定期续约验证
"""
import hashlib, json, os, platform, socket, time, uuid
from datetime import datetime
import urllib.request

LICENSE_FILE = "/opt/ZONGYUAN-ROOT/.license"
LICENSE_SERVER = "http://127.0.0.1:8007"
LICENSE_REMOTE = "https://www.huodouai.com/license"

def get_machine_fingerprint() -> str:
    """生成机器指纹（CPU+主板+MAC+主机名哈希）"""
    raw = ""
    try:
        # CPU信息
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line or "serial" in line:
                    raw += line.strip()
                    break
    except: pass
    try:
        # 主板信息
        with open("/sys/class/dmi/id/product_uuid") as f:
            raw += f.read().strip()
    except: pass
    try:
        # MAC地址
        raw += hex(uuid.getnode())
    except: pass
    raw += platform.node() + platform.machine()
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

def verify_license(license_key: str = None) -> dict:
    """验证授权码，返回授权状态"""
    if not license_key:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE) as f:
                data = json.load(f)
                license_key = data.get("license_key", "")
        if not license_key:
            return {"valid": False, "plan": "free", "reason": "未配置授权码",
                    "limits": {"max_truths": 10, "max_instances": 1, "features": ["basic"]}}
    
    machine_id = get_machine_fingerprint()
    payload = json.dumps({"license_key": license_key, "machine_id": machine_id}).encode()
    
    # 先尝试本地，再尝试远程
    for server in [LICENSE_SERVER, LICENSE_REMOTE]:
        try:
            req = urllib.request.Request(f"{server}/api/v1/license/verify",
                                         data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                if result.get("valid"):
                    result["machine_id"] = machine_id
                    result["limits"] = get_plan_limits(result.get("plan", "free"))
                    # 缓存授权状态
                    with open(LICENSE_FILE, "w") as f:
                        json.dump({"license_key": license_key, "machine_id": machine_id,
                                   "plan": result.get("plan"), "verified_at": int(time.time()),
                                   "expires_at": result.get("expires_at")}, f, indent=2)
                    return result
        except Exception as e:
            continue
    
    # 网络不可用时使用缓存
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE) as f:
            cached = json.load(f)
            if cached.get("license_key") == license_key:
                expires = cached.get("expires_at", "")
                if expires:
                    try:
                        exp_ts = datetime.fromisoformat(expires).timestamp()
                        if exp_ts > time.time():
                            return {"valid": True, "plan": cached.get("plan", "free"),
                                    "reason": "离线缓存验证", "machine_id": machine_id,
                                    "limits": get_plan_limits(cached.get("plan", "free"))}
                    except: pass
    
    return {"valid": False, "plan": "free", "reason": "授权验证失败",
            "limits": get_plan_limits("free")}

def get_plan_limits(plan: str) -> dict:
    """各版本功能限制"""
    plans = {
        "free": {"max_truths": 10, "max_instances": 1, "features": ["basic", "truth_view"],
                 "api_rate_limit": "10/min", "support": "community"},
        "trial": {"max_truths": 164, "max_instances": 1, "features": ["all_basic", "truth_edit"],
                  "api_rate_limit": "60/min", "support": "email", "expires_days": 30},
        "personal": {"max_truths": 164, "max_instances": 1, "features": ["all", "memory_chain"],
                     "api_rate_limit": "120/min", "support": "email"},
        "professional": {"max_truths": 9999, "max_instances": 3, "features": ["all", "plugins", "bidirectional"],
                         "api_rate_limit": "300/min", "support": "priority"},
        "enterprise": {"max_truths": 99999, "max_instances": 999, "features": ["all", "multi_tenant", "sla"],
                       "api_rate_limit": "unlimited", "support": "7x24", "sla": "99.9%"},
    }
    return plans.get(plan, plans["free"])

def activate_license(license_key: str) -> dict:
    """激活授权码（首次使用）"""
    result = verify_license(license_key)
    return result

def check_expiry_warning() -> dict:
    """检查到期警告（7/3/1天前）"""
    if not os.path.exists(LICENSE_FILE):
        return {"warning": False}
    with open(LICENSE_FILE) as f:
        data = json.load(f)
    expires = data.get("expires_at", "")
    if not expires:
        return {"warning": False}
    try:
        exp_ts = datetime.fromisoformat(expires).timestamp()
        days_left = (exp_ts - time.time()) / 86400
        if days_left <= 1:
            return {"warning": True, "level": "P0", "days_left": int(days_left),
                    "message": "授权码将在24小时内到期，请立即续费"}
        elif days_left <= 3:
            return {"warning": True, "level": "P1", "days_left": int(days_left),
                    "message": f"授权码将在{int(days_left)}天后到期"}
        elif days_left <= 7:
            return {"warning": True, "level": "P2", "days_left": int(days_left),
                    "message": f"授权码将在{int(days_left)}天后到期"}
    except: pass
    return {"warning": False}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "activate":
        key = sys.argv[2] if len(sys.argv) > 2 else input("请输入授权码: ").strip()
        result = activate_license(key)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        result = verify_license()
        warning = check_expiry_warning()
        print(json.dumps({"license": result, "expiry_warning": warning}, indent=2, ensure_ascii=False))
    else:
        print("用法: python3 license_guard.py [activate <key>|status]")
