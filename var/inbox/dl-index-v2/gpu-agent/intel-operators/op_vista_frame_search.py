#!/usr/bin/env python3
"""
OP-VISTA-FRAME-001 视觉帧快照检索算子
=========================================
来源: VISTA(MIT何恺明)情报转化 → META-RULE-017
零成本标记: memory_retrieval=True（不消耗模型额度，只做本地文件检索）

输入 JSON:
{
  "asset_id": "KUNLUN-ASSET-0002",   // 可选
  "character": "真武大帝",             // 可选，按角色过滤
  "scene": "昆仑绝壁",                  // 可选，按场景过滤
  "version": "V1.6",                   // 可选，按版本过滤
  "frame_range": [0, 10],              // 可选，帧范围
  "query_type": "search|compare|detail" // search=检索 / compare=多帧对比 / detail=单帧详情
}

输出 JSON:
{
  "operator_id": "OP-VISTA-FRAME-001",
  "memory_retrieval": true,
  "status": "ok|empty|error",
  "frames": [...],
  "comparison": {...},
  "cost": {"token": 0, "quota": "free"}
}
"""
import os, sys, json, hashlib, time, argparse, glob

# 帧快照根目录（本地持久层 + 魔搭数据湖双备份）
FRAME_ROOT_CANDIDATES = [
    os.path.expanduser("~/ZONGYUAN-ROOT/03_文档资产/帧快照"),
    "/mnt/workspace/ZONGYUAN-SHARED-DATALAKE/frame-snapshots",
    os.path.expanduser("~/Doubao/chats/38438491307070978/frame-snapshots"),
]

def find_frame_root():
    for p in FRAME_ROOT_CANDIDATES:
        if os.path.isdir(p):
            return p
    # 自动创建第一个候选目录
    os.makedirs(FRAME_ROOT_CANDIDATES[0], exist_ok=True)
    return FRAME_ROOT_CANDIDATES[0]

def scan_frames(root):
    """扫描帧快照目录，返回所有帧文件及其元数据"""
    frames = []
    for ext in ("*.webp", "*.png", "*.jpg", "*.json"):
        for f in glob.glob(os.path.join(root, "**", ext), recursive=True):
            try:
                st = os.stat(f)
                meta_file = f.rsplit(".", 1)[0] + ".json"
                meta = {}
                if os.path.exists(meta_file):
                    with open(meta_file, "r", encoding="utf-8") as fp:
                        meta = json.load(fp)
                frames.append({
                    "path": f,
                    "filename": os.path.basename(f),
                    "size_bytes": st.st_size,
                    "mtime": st.st_mtime,
                    "metadata": meta,
                })
            except Exception:
                continue
    return frames

def match_filter(frame, q):
    """按查询条件过滤帧"""
    m = frame.get("metadata", {})
    if q.get("asset_id") and q["asset_id"] not in str(frame.get("path", "")):
        return False
    if q.get("character") and q["character"] not in m.get("character", ""):
        return False
    if q.get("scene") and q["scene"] not in m.get("scene", ""):
        return False
    if q.get("version") and q["version"] not in m.get("version", ""):
        return False
    return True

def compare_frames(frames):
    """多帧对比：计算文件大小变化、哈希差异率"""
    if len(frames) < 2:
        return {"comparable": False, "reason": "帧数不足"}
    hashes = []
    for f in frames:
        try:
            with open(f["path"], "rb") as fp:
                hashes.append(hashlib.sha256(fp.read()).hexdigest()[:16])
        except Exception:
            hashes.append("error")
    unique = len(set(hashes))
    return {
        "comparable": True,
        "frame_count": len(frames),
        "unique_frames": unique,
        "hash_list": hashes,
        "note": "哈希差异率用于角色风格一致性粗检（零成本，不调模型）"
    }

def run(query):
    root = find_frame_root()
    all_frames = scan_frames(root)
    filtered = [f for f in all_frames if match_filter(f, query)]

    # 帧范围过滤
    fr = query.get("frame_range")
    if fr and len(fr) == 2:
        filtered = filtered[fr[0]:fr[1]]

    qtype = query.get("query_type", "search")
    result = {
        "operator_id": "OP-VISTA-FRAME-001",
        "memory_retrieval": True,
        "status": "ok" if filtered else "empty",
        "frame_root": root,
        "total_scanned": len(all_frames),
        "matched": len(filtered),
        "frames": [
            {
                "filename": f["filename"],
                "size_kb": round(f["size_bytes"] / 1024, 1),
                "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(f["mtime"])),
                "metadata": f["metadata"],
            }
            for f in filtered[:50]  # 单轮最多返回50帧，避免过载
        ],
        "cost": {"token": 0, "quota": "free", "model_call": False},
    }

    if qtype == "compare" and len(filtered) >= 2:
        result["comparison"] = compare_frames(filtered)

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="视觉帧快照检索算子 V1.0")
    parser.add_argument("query_json", nargs="?", default="{}", help="查询JSON字符串")
    args = parser.parse_args()
    try:
        q = json.loads(args.query_json) if args.query_json else {}
    except Exception:
        q = {}
    out = run(q)
    print(json.dumps(out, ensure_ascii=False, indent=2))
