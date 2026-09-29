#!/usr/bin/env python3
"""
向量库操作日志 Merkle 锁档
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
记录8014向量库操作，计算Merkle根，生成锁档凭证
"""
import hashlib, json, time, os, urllib.request

VECTOR_API = "http://127.0.0.1:8014"
LOG_DIR = "/opt/storage/archive/vector_merkle_logs"
LOCK_FILE = "/opt/storage/archive/vector_merkle_lock.json"

def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_stats():
    try:
        with urllib.request.urlopen(VECTOR_API + "/stats", timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except:
        return {}

def get_collections():
    try:
        with urllib.request.urlopen(VECTOR_API + "/api/v1/collections", timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except:
        return {}

def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    
    stats = get_stats()
    collections = get_collections()
    
    timestamp = time.time()
    ts_str = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(timestamp))
    
    # 构建操作日志条目
    log_entry = {
        "timestamp": ts_str,
        "unix_ts": timestamp,
        "vector_count": stats.get("count", 0),
        "collection": stats.get("collection", "unknown"),
        "dim": stats.get("dim", 0),
        "embedder": stats.get("embedder", "unknown"),
        "model": stats.get("model", "unknown"),
        "runtime": stats.get("runtime", "unknown"),
        "storage_path": stats.get("storage_path", ""),
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω"
    }
    
    # 计算条目哈希
    entry_hash = sha256(json.dumps(log_entry, sort_keys=True, ensure_ascii=False))
    log_entry["entry_hash"] = entry_hash
    
    # 读取历史链
    chain = []
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            chain = data.get("chain", [])
    
    # 计算Merkle根（链式哈希）
    if len(chain) > 0:
        prev_root = chain[-1].get("merkle_root", sha256("genesis"))
    else:
        prev_root = sha256("genesis")
    
    merkle_root = sha256(prev_root + entry_hash)
    log_entry["merkle_root"] = merkle_root
    log_entry["prev_root"] = prev_root
    log_entry["block_height"] = len(chain) + 1
    
    chain.append(log_entry)
    
    # 写入锁档文件
    lock_data = {
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω",
        "protocol": "ZONGYUAN-ROOT",
        "current_root": merkle_root,
        "block_height": len(chain),
        "last_update": ts_str,
        "chain": chain[-100:]  # 保留最近100个块
    }
    
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, ensure_ascii=False, indent=2)
    
    # 写入单条日志
    log_file = os.path.join(LOG_DIR, "vector_log_" + ts_str + ".json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
    
    print("[完成] 向量库Merkle锁档")
    print("  块高度: " + str(len(chain)))
    print("  向量数: " + str(stats.get("count", 0)))
    print("  Merkle根: " + merkle_root[:32] + "...")
    print("  锁档文件: " + LOCK_FILE)
    print("  日志文件: " + log_file)
    print("  DID: DID-BR-000002")

if __name__ == "__main__":
    main()
