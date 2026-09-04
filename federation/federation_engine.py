"""多实例进化合并引擎 - 云内核+本地内核+客户内核进化增量自动合并"""
import json, hashlib, time, os
from datetime import datetime

FEDERATION_DIR = "/opt/ZONGYUAN-ROOT/federation"
MERGE_LOG = f"{FEDERATION_DIR}/merge_log.json"
TRUTH_FILE = "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json"

def generate_truth_hash(truth):
    return hashlib.sha256(json.dumps(truth, sort_keys=True).encode()).hexdigest()[:16]

def merge_instance_truths(instance_id: str, instance_truths: list) -> dict:
    """合并来自其他实例的真值增量"""
    with open(TRUTH_FILE) as f:
        local = json.load(f)
    
    local_truths = {t["id"]: t for t in local.get("truths", []}
    local_hashes = {generate_truth_hash(t) for t in local_truths.values()}
    
    added = []
    conflicts = []
    skipped = 0
    
    for t in instance_truths:
        tid = t.get("id", "")
        thash = generate_truth_hash(t)
        
        if thash in local_hashes:
            skipped += 1
            continue
        
        if tid in local_truths:
            # 冲突检测：同ID不同内容
            if t.get("level", "").startswith("L0"):
                conflicts.append({"id": tid, "reason": "L0公理冲突，拒绝覆盖"})
                continue
            # L1+ 生成增量补丁
            t["status"] = "PENDING"
            t["source_instance"] = instance_id
            t["merged_at"] = datetime.now().isoformat()
            local_truths[tid] = t
            added.append(tid)
        else:
            t["source_instance"] = instance_id
            t["merged_at"] = datetime.now().isoformat()
            local_truths[tid] = t
            added.append(tid)
    
    local["truths"] = list(local_truths.values())
    local["truth_count"] = len(local_truths)
    
    with open(TRUTH_FILE, "w") as f:
        json.dump(local, f, ensure_ascii=False, indent=2)
    
    # 记录合并日志
    log = {"instance_id": instance_id, "added": len(added), "skipped": skipped,
           "conflicts": len(conflicts), "timestamp": datetime.now().isoformat()}
    logs = []
    if os.path.exists(MERGE_LOG):
        with open(MERGE_LOG) as f: logs = json.load(f)
    logs.append(log)
    with open(MERGE_LOG, "w") as f:
        json.dump(logs[-100:], f, indent=2)
    
    return {"added": len(added), "skipped": skipped, "conflicts": conflicts, "total": len(local_truths)}

def get_federation_status():
    """获取联邦进化状态"""
    logs = []
    if os.path.exists(MERGE_LOG):
        with open(MERGE_LOG) as f: logs = json.load(f)
    return {
        "total_merges": len(logs),
        "recent_merges": logs[-5:],
        "instances": list(set(l["instance_id"] for l in logs))
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(get_federation_status(), indent=2, ensure_ascii=False))
    else:
        print("用法: python3 federation_engine.py status")
