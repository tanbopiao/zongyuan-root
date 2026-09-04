"""版本向量 - 多写入者并发冲突检测"""
import json, os
from datetime import datetime

VECTOR_FILE = "/opt/ZONGYUAN-ROOT/multi_writer/version_vectors.json"
AUDIT_FILE = "/opt/ZONGYUAN-ROOT/multi_writer/write_audit.log"

def load_vectors():
    if os.path.exists(VECTOR_FILE):
        with open(VECTOR_FILE) as f:
            return json.load(f)
    return {}

def save_vectors(vectors):
    with open(VECTOR_FILE, "w") as f:
        json.dump(vectors, f, indent=2)

def get_version_vector(truth_id: str) -> dict:
    vectors = load_vectors()
    return vectors.get(truth_id, {})

def increment_vector(truth_id: str, writer_id: str) -> dict:
    """写入者写入时递增版本向量"""
    vectors = load_vectors()
    if truth_id not in vectors:
        vectors[truth_id] = {}
    vectors[truth_id][writer_id] = vectors[truth_id].get(writer_id, 0) + 1
    vectors[truth_id]["_last_writer"] = writer_id
    vectors[truth_id]["_last_update"] = datetime.now().isoformat()
    save_vectors(vectors)
    return vectors[truth_id]

def detect_conflict(truth_id: str, writer_id: str, incoming_vector: dict) -> dict:
    """检测并发冲突
    Returns: {"has_conflict": bool, "type": str, "resolution": str}
    """
    current = get_version_vector(truth_id)
    if not current:
        return {"has_conflict": False, "type": "new", "resolution": "accept"}
    
    # 检查是否有其他写入者在当前写入者最后一次之后修改过
    current_writer_version = current.get(writer_id, 0)
    other_writers = {k: v for k, v in current.items() 
                     if k not in (writer_id, "_last_writer", "_last_update") and v > 0}
    
    if other_writers:
        # 有其他写入者修改过
        max_other = max(other_writers.values())
        if max_other > current_writer_version:
            return {
                "has_conflict": True,
                "type": "concurrent_modification",
                "conflicting_writers": list(other_writers.keys()),
                "resolution": "require_merge"
            }
    
    return {"has_conflict": False, "type": "sequential", "resolution": "accept"}

def audit_write(truth_id: str, writer_id: str, action: str, detail: str):
    """记录写入审计"""
    with open(AUDIT_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {writer_id} | {action} | {truth_id} | {detail}\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        vectors = load_vectors()
        print(f"已追踪真值: {len(vectors)} 条")
        print(f"审计日志: {AUDIT_FILE}")
    else:
        print("版本向量冲突检测 V1.0")
        print(f"已追踪: {len(load_vectors())} 条真值")
