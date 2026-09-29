#!/usr/bin/env python3
import sqlite3, json, time, urllib.request

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
VECTOR_API = "http://127.0.0.1:8014"
BATCH_SIZE = 20

def load_truths():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT truth_key, truth_value, category, node_id, created_at FROM truths WHERE truth_value IS NOT NULL AND truth_value != ''")
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

def get_stats():
    try:
        with urllib.request.urlopen(VECTOR_API + "/stats", timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except:
        return {}

def main():
    print("[启动] 9120真值批量向量化导入")
    truths = load_truths()
    total = len(truths)
    print("[信息] 读取到 " + str(total) + " 条有效真值")
    truths = [t for t in truths if t[0] and t[0].strip()]
    print("[信息] 过滤空key后: " + str(len(truths)) + " 条")
    stats_before = get_stats()
    cnt_before = stats_before.get("count", "?")
    print("[信息] 导入前向量库: " + str(cnt_before) + " 条")
    success = 0
    failed = 0
    batches = (len(truths) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(truths), BATCH_SIZE):
        batch = truths[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print("[进度] 批次 " + str(batch_num) + "/" + str(batches) + ": " + str(len(batch)) + " 条")
        result = batch_add(batch)
        if "error" in result:
            print("  [失败] " + result["error"])
            failed += len(batch)
        else:
            print("  [成功] " + str(result.get("count", "?")) + " 条, 总计 " + str(result.get("total", "?")) + " 条")
            success += len(batch)
        time.sleep(1.0)
    stats_after = get_stats()
    cnt_after = stats_after.get("count", "?")
    print("")
    print("[完成] 导入结果汇总")
    print("  成功: " + str(success) + " 条")
    print("  失败: " + str(failed) + " 条")
    print("  导入后向量库: " + str(cnt_after) + " 条")
    print("  DID: DID-BR-000002")

if __name__ == "__main__":
    main()
