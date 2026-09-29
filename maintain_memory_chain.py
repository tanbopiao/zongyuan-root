"""记忆链自动维护 - 每次锁档后自动生成下一个种子
OPS-02 记忆连续性公理工程化落地
"""
import json, hashlib, os
from datetime import datetime

MEMCHAIN_DIR = "/opt/ZONGYUAN-ROOT/memory_chain"

def get_seed_count():
    if not os.path.exists(MEMCHAIN_DIR):
        return 0
    return len([f for f in os.listdir(MEMCHAIN_DIR) if f.startswith("seed-") and f.endswith(".json")])

def get_last_seed_hash():
    count = get_seed_count()
    if count == 0:
        return "0" * 64
    last_file = f"{MEMCHAIN_DIR}/seed-{count:03d}.json"
    if os.path.exists(last_file):
        with open(last_file) as f:
            return json.load(f).get("hash", "0"*64)
    return "0" * 64

def generate_next_seed(trigger: str = "auto_lock", metadata: dict = None):
    """生成下一个记忆种子"""
    count = get_seed_count()
    next_num = count + 1
    last_hash = get_last_seed_hash()
    
    seed_content = {
        "seed_id": f"seed-{next_num:03d}",
        "sequence": next_num,
        "timestamp": datetime.now().isoformat(),
        "previous_hash": last_hash,
        "trigger": trigger,
        "kernel_version": "v9.10-META-ORDER",
        "metadata": metadata or {}
    }
    
    # 计算种子哈希（链式继承）
    hash_input = json.dumps(seed_content, sort_keys=True).encode()
    seed_content["hash"] = hashlib.sha256(hash_input).hexdigest()
    
    # 写入种子文件
    os.makedirs(MEMCHAIN_DIR, exist_ok=True)
    seed_file = f"{MEMCHAIN_DIR}/seed-{next_num:03d}.json"
    with open(seed_file, "w") as f:
        json.dump(seed_content, f, indent=2)
    
    return seed_content

def verify_chain() -> dict:
    """验证记忆链完整性"""
    count = get_seed_count()
    if count == 0:
        return {"valid": True, "count": 0, "message": "空链"}
    
    broken = []
    for i in range(2, count + 1):
        curr_file = f"{MEMCHAIN_DIR}/seed-{i:03d}.json"
        prev_file = f"{MEMCHAIN_DIR}/seed-{i-1:03d}.json"
        if not os.path.exists(curr_file) or not os.path.exists(prev_file):
            broken.append(f"seed-{i:03d}: 文件缺失")
            continue
        with open(curr_file) as f:
            curr = json.load(f)
        with open(prev_file) as f:
            prev = json.load(f)
        if curr.get("previous_hash") != prev.get("hash"):
            broken.append(f"seed-{i:03d}: 哈希链断裂")
    
    return {
        "valid": len(broken) == 0,
        "count": count,
        "broken": broken,
        "last_seed": f"seed-{count:03d}",
        "integrity": "INTACT" if not broken else "BROKEN"
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        print(json.dumps(verify_chain(), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "generate":
        trigger = sys.argv[2] if len(sys.argv) > 2 else "auto"
        result = generate_next_seed(trigger)
        print(f"✅ 生成 {result['seed_id']}, hash={result['hash'][:16]}...")
    else:
        status = verify_chain()
        print(f"记忆链: {status['count']}个种子, 完整性={status['integrity']}")
