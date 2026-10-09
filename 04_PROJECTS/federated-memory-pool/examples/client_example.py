#!/usr/bin/env python3
"""
联邦记忆池 · 客户端调用示例（开源版）
演示: HMAC签名 + 健康检查 + 锚点拉取记忆
"""
import hashlib, hmac, json, urllib.request

GATEWAY_URL = "http://127.0.0.1:8077"
SECRET = "YOUR_MEMORY_GATEWAY_SECRET"  # 与环境变量保持一致

def sign(payload: str) -> str:
    """HMAC-SHA256 签名"""
    return hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

def health():
    """健康检查"""
    with urllib.request.urlopen(f"{GATEWAY_URL}/memory/health") as resp:
        return json.loads(resp.read())

def anchor(anchor_type: str, anchor_value: str = "", extract_mode: str = "truth_only"):
    """锚点拉取记忆"""
    body = json.dumps({
        "anchor_type": anchor_type,
        "anchor_value": anchor_value,
        "extract_mode": extract_mode
    }).encode()
    req = urllib.request.Request(
        f"{GATEWAY_URL}/memory/anchor",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Memory-Sig": sign(body.decode())
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

if __name__ == "__main__":
    # 1. 健康检查
    print("=== 健康检查 ===")
    print(json.dumps(health(), ensure_ascii=False, indent=2))

    # 2. 锚点拉取：最新记忆
    print("\n=== 拉取最新记忆 ===")
    result = anchor("latest")
    print(f"命中 {result['matched_count']} 条 / 索引共 {result['total_index']} 条")
    for m in result["memories"][:3]:
        print(f"  {m}")

    # 3. 按标签拉取
    print("\n=== 按标签拉取: 架构 ===")
    result = anchor("tag", "架构")
    print(f"命中 {result['matched_count']} 条")
    for m in result["memories"][:3]:
        print(f"  {m}")
