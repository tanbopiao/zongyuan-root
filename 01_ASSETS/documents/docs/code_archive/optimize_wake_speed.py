#!/usr/bin/env python3
"""唤醒速度优化：echarts本地化 + ai_proxy快速路径"""
import subprocess, time, os

print("=" * 60)
print("唤醒速度优化")
print("=" * 60)

# 1. 下载echarts到本地
print("\n【1】下载echarts到本地")
for root in ["/www/wwwroot/www.huodouai.com", "/www/wwwroot/huodouai.com"]:
    os.makedirs(f"{root}/assets", exist_ok=True)
    dst = f"{root}/assets/echarts.min.js"
    if not os.path.exists(dst) or os.path.getsize(dst) < 100000:
        subprocess.run(["curl", "-sL", "-o", dst, "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"], timeout=30)
    size = os.path.getsize(dst) if os.path.exists(dst) else 0
    print(f"  {root}: {size//1024}KB")

# 2. ai_proxy快速路径
print("\n【2】ai_proxy快速路径（force_model跳过smart_route）")
proxy_path = "/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py"
with open(proxy_path, encoding="utf-8") as f:
    content = f.read()

old = """    attempt_models, estimated_tokens = smart_route(messages, mode=mode)
    # 如果指定了model_key且存在，将其移到最优先位置
    if model_key and model_key in MODELS and model_key in attempt_models:
        attempt_models.remove(model_key)
        attempt_models.insert(0, model_key)"""

new = """    # 快速路径：指定force_model时跳过智能路由，直接调用
    if model_key and model_key in MODELS:
        attempt_models = [model_key]
        estimated_tokens = sum(len(m.get("content","")) for m in messages if isinstance(m,dict)) // 4
    else:
        attempt_models, estimated_tokens = smart_route(messages, mode=mode)"""

if old in content:
    content = content.replace(old, new)
    with open(proxy_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("  ✅ 快速路径已添加")
else:
    print("  ⚠️ 已存在或不匹配")

# 3. 重启ai_proxy
print("\n【3】重启ai_proxy")
subprocess.run(["systemctl", "restart", "zongyuan-ai-proxy"])
time.sleep(2)
print("  ✅ 已重启")

# 4. 验证快速路径效果
print("\n【4】验证API响应速度")
for i in range(2):
    start = time.time()
    r = subprocess.run(["curl", "-s", "-X", "POST", "http://127.0.0.1:8021/chat",
                        "-H", "Content-Type: application/json",
                        "-d", '{"message":"hi","force_model":"zhipu","max_tokens":50}'],
                       capture_output=True, text=True, timeout=30)
    elapsed = time.time() - start
    print(f"  第{i+1}次: {elapsed:.2f}s")

print("\n" + "=" * 60)
print("优化完成")
print("=" * 60)
