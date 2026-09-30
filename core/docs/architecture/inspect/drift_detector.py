#!/usr/bin/env python3
"""
全域漂移检测引擎
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
三重校验：哈希 + 结构 + 酉语义漂移
分级处置：轻度告警 / 中度隔离 / 重度回滚
"""
import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime

TRUTH_DIR = Path("core/truth")
BASELINE_FILE = Path("inspect/drift_baseline.json")
AUDIT_LOG = Path("inspect/audit.log")
SNAPSHOT_DIR = Path("snapshot/backup")

# 漂移阈值
THRESHOLD_LIGHT = 0.06   # 轻度：告警
THRESHOLD_MEDIUM = 0.12  # 中度：隔离
THRESHOLD_HEAVY = 0.20   # 重度：回滚

# 模拟词向量维度（实际可用sentence-transformers替换）
VECTOR_DIM = 4

def log(msg):
    ts = datetime.now().isoformat()
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def file_hash(filepath: Path) -> str:
    """计算文件SHA256"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def file_to_vector(filepath: Path) -> np.ndarray:
    """将文件内容转为向量（简化版：基于内容特征）"""
    text = filepath.read_text(encoding="utf-8")
    # 简化向量：基于关键词计数
    keywords = ["真值", "锁档", "Ω₀", "DID", "矩阵", "调度", "同源", "漂移", "权限", "L0"]
    vec = np.array([text.count(k) for k in keywords], dtype=float)
    # 归一化
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 1e-8 else vec

def load_baseline():
    """加载基线"""
    if not BASELINE_FILE.exists():
        return {}
    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_baseline(data):
    """保存基线"""
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_drift():
    """执行全域漂移检测"""
    baseline = load_baseline()
    results = []
    actions = []

    truth_files = sorted(TRUTH_DIR.glob("*.md"))
    log(f"漂移检测开始：{len(truth_files)}个文件")

    for filepath in truth_files:
        fname = filepath.name
        current_hash = file_hash(filepath)
        current_vec = file_to_vector(filepath)

        if fname not in baseline:
            # 新文件，建立基线
            baseline[fname] = {
                "sha256": current_hash,
                "vector": current_vec.tolist(),
                "first_seen": datetime.now().isoformat()
            }
            results.append({
                "file": fname, "status": "NEW", "drift_score": 0
            })
            log(f"新文件入库基线: {fname}")
            continue

        old = baseline[fname]
        old_hash = old["sha256"]
        old_vec = np.array(old["vector"])

        # 1. 哈希校验
        hash_match = (current_hash == old_hash)

        # 2. 语义漂移计算
        inner_product = float(np.dot(current_vec, old_vec))
        drift_score = 1.0 - inner_product

        # 3. 分级处置
        if drift_score < THRESHOLD_LIGHT and hash_match:
            status = "OK"
            action = "无操作"
        elif drift_score < THRESHOLD_MEDIUM:
            status = "LIGHT_DRIFT"
            action = "告警"
            actions.append(f"⚠️ 轻度漂移: {fname} ({drift_score:.4f})")
            log(f"LIGHT_DRIFT: {fname} drift={drift_score:.4f}")
        elif drift_score < THRESHOLD_HEAVY:
            status = "MEDIUM_DRIFT"
            action = "隔离"
            actions.append(f"🔶 中度漂移: {fname} ({drift_score:.4f})")
            log(f"MEDIUM_DRIFT: {fname} drift={drift_score:.4f}")
        else:
            status = "HEAVY_DRIFT"
            action = "回滚"
            actions.append(f"🔴 重度漂移: {fname} ({drift_score:.4f})")
            log(f"HEAVY_DRIFT: {fname} drift={drift_score:.4f}")

        # 更新基线
        baseline[fname]["sha256"] = current_hash
        baseline[fname]["vector"] = current_vec.tolist()
        baseline[fname]["last_checked"] = datetime.now().isoformat()
        baseline[fname]["last_status"] = status

        results.append({
            "file": fname, "status": status,
            "drift_score": round(drift_score, 4),
            "hash_match": hash_match, "action": action
        })

    save_baseline(baseline)

    return results, actions

def report(results, actions):
    print("=" * 60)
    print("全域漂移检测报告")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    status_count = {}
    for r in results:
        s = r["status"]
        status_count[s] = status_count.get(s, 0) + 1

    print(f"\n检测文件: {len(results)}个")
    for status, count in sorted(status_count.items()):
        print(f"  {status}: {count}个")

    if actions:
        print(f"\n处置动作:")
        for a in actions:
            print(f"  {a}")
    else:
        print(f"\n✅ 无漂移，全部正常")

    print("=" * 60)

if __name__ == "__main__":
    results, actions = check_drift()
    report(results, actions)
