#!/usr/bin/env python3
"""
零成本额度监控自动锁死引擎
META-LAW-ZERO-COST-001 V2.0
核心逻辑：免费额度内可用 → 额度用完自动锁死 → 付费必须人工审批
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, os, time, hashlib, urllib.request

KERNEL_PATH = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
LOCK_LOG = os.path.expanduser("~/.zongyuan_root/zero_cost_lock_log.json")

FREE_BACKENDS = [
    {"name": "智谱GLM", "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "test_model": "glm-4-flash"},
    {"name": "硅基流动", "url": "https://api.siliconflow.cn/v1/chat/completions", "test_model": "Qwen/Qwen2.5-7B-Instruct"},
    {"name": "KIMI", "url": "https://api.moonshot.cn/v1/chat/completions", "test_model": "moonshot-v1-8k"},
]

def load_kernel():
    with open(KERNEL_PATH) as f:
        return json.load(f)

def check_quota(url, model, api_key=None):
    """检测服务是否可用（免费额度是否用完）"""
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        data = json.dumps({"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if "error" in result:
                err = result["error"]
                if "quota" in str(err).lower() or "429" in str(err) or "insufficient" in str(err).lower():
                    return "QUOTA_EXHAUSTED"
                return "ERROR"
            return "AVAILABLE"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return "QUOTA_EXHAUSTED"
        if e.code == 401 or e.code == 403:
            return "AUTH_FAILED"
        return f"HTTP_{e.code}"
    except Exception as e:
        return f"ERROR: {str(e)[:50]}"

def auto_lock_service(service_name, reason):
    """自动锁死服务"""
    kernel = load_kernel()
    if "zero_cost_policy" in kernel:
        if "locked_apis" in kernel["zero_cost_policy"]:
            if service_name in kernel["zero_cost_policy"]["locked_apis"]:
                kernel["zero_cost_policy"]["locked_apis"][service_name]["status"] = "AUTO_LOCKED_QUOTA_EXHAUSTED"
                kernel["zero_cost_policy"]["locked_apis"][service_name]["lock_reason"] = reason
                kernel["zero_cost_policy"]["locked_apis"][service_name]["locked_at"] = int(time.time())
    with open(KERNEL_PATH, 'w') as f:
        json.dump(kernel, f, ensure_ascii=False, indent=2)
    
    # 记录锁档日志
    log = []
    if os.path.exists(LOCK_LOG):
        with open(LOCK_LOG) as f:
            log = json.load(f)
    log.append({"service": service_name, "reason": reason, "locked_at": int(time.time()), "action": "AUTO_LOCKED"})
    with open(LOCK_LOG, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    print(f"  🔒 自动锁死: {service_name} - {reason}")

def run_monitor():
    print("=" * 60)
    print("零成本额度监控自动锁死引擎")
    print("META-LAW-ZERO-COST-001 V2.0")
    print("=" * 60)
    
    results = {}
    for backend in FREE_BACKENDS[:3]:  # 测试前3个
        status = check_quota(backend["url"], backend["test_model"])
        results[backend["name"]] = status
        icon = "✅" if status == "AVAILABLE" else "🔒" if "QUOTA" in status else "⚠️"
        print(f"  {icon} {backend['name']}: {status}")
        if status == "QUOTA_EXHAUSTED":
            auto_lock_service(backend["name"], "免费额度已用完，自动锁死")
    
    # 火山方舟始终锁定（付费模型）
    print(f"  🔒 火山方舟: LOCKED_ZERO_COST（付费模型默认禁用）")
    
    print("\n" + "=" * 60)
    print("监控完成。免费额度可用的服务继续使用，额度用完的已自动锁死。")
    print("需要付费调用？请发起人工审批。")
    print("=" * 60)
    return results

if __name__ == "__main__":
    run_monitor()
