#!/usr/bin/env python3
"""
9120 -> 8014 增量同步适配器
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
只同步9120新增/修改的真值到8014向量库，避免全量重复导入
同步状态记录在 sync_state.json
"""
import sqlite3, json, time, os, urllib.request

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
VECTOR_API = "http://127.0.0.1:8014"
STATE_FILE = "/opt/ZONGYUAN-ROOT/ai-native-ops/sync_state.json"
BATCH_SIZE = 20

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_sync_ts": 0, "synced_keys": [], "total_synced": 0}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_new_truths(last_ts):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT truth_key, truth_value, category, node_id, created_at, updated_at "
        "FROM truths WHERE truth_value IS NOT NULL AND truth_value != '' "
        "AND (created_at > ? OR updated_at > ?) "
        "ORDER BY created_at ASC",
        (last_ts, last_ts)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def batch_add(truths_batch):
    ids = [t[0] for t in truths_batch]
    documents = [t[0] + ": " + t[1][:500] for t in truths_batch]
    metadatas = [{"key": t[0], "category": t[2] or "uncategorized", "node_id": t[3], "created_at": t[4]} for t in truths_batch]
    payload = json.dumps({"ids": ids, "documents": documents, "metadatas": metadatas}).encode("utf-8")
    req = urllib.request.Request(VECTOR_API + "/api/v1/add", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

def get_vector_count():
    try:
        with urllib.request.urlopen(VECTOR_API + "/stats", timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("count", 0)
    except:
        return -1

def main():
    print("[启动] 9120->8014 增量同步")
    state = load_state()
    last_ts = state.get("last_sync_ts", 0)
    print("[信息] 上次同步时间戳: " + str(last_ts))
    
    new_truths = get_new_truths(last_ts)
    print("[信息] 待同步新增/修改真值: " + str(len(new_truths)) + " 条")
    
    if len(new_truths) == 0:
        print("[完成] 无新增真值，无需同步")
        return
    
    success = 0
    failed = 0
    max_ts = last_ts
    
    for i in range(0, len(new_truths), BATCH_SIZE):
        batch = new_truths[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(new_truths) + BATCH_SIZE - 1) // BATCH_SIZE
        print("[进度] 批次 " + str(batch_num) + "/" + str(total_batches) + ": " + str(len(batch)) + " 条")
        
        result = batch_add(batch)
        if "error" in result:
            print("  [失败] " + result["error"])
            failed += len(batch)
        else:
            print("  [成功] " + str(result.get("count", "?")) + " 条, 向量库总计 " + str(result.get("total", "?")))
            success += len(batch)
            for t in batch:
                if t[5] > max_ts:  # updated_at
                    max_ts = t[5]
                if t[4] > max_ts:  # created_at
                    max_ts = t[4]
        
        time.sleep(1.0)
    
    state["last_sync_ts"] = max_ts
    state["total_synced"] = state.get("total_synced", 0) + success
    save_state(state)
    
    vec_count = get_vector_count()
    print("")
    print("[完成] 增量同步结果")
    print("  成功: " + str(success) + " 条")
    print("  失败: " + str(failed) + " 条")
    print("  向量库当前: " + str(vec_count) + " 条")
    print("  累计同步: " + str(state["total_synced"]) + " 条")
    print("  同步时间戳: " + str(max_ts))
    print("  DID: DID-BR-000002")

if __name__ == "__main__":
    main()
