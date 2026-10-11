#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""昆仑洞天 · 创作资产归档确权
扫描关键帧 + 成片 -> 算 SHA256 -> 登记本地台账 -> 写入 ZR 溯源链（POST /truth 自动进 Merkle-DAG）
独立运行，不触碰运行中的 wrapper(18080)/ZR(8920) 服务。
"""
import json, os, hashlib, urllib.request, urllib.error, sys, time

ZR_BASE = "https://www.huodouai.com/zr-api/api/v1"
ZR_KEY  = "zr-7962dc9e860d3f2cf63a9ca7"
FRAMES_DIR = "/www/wwwroot/huodouai.com/kunlun/frames"
VIDEOS_DIR = "/www/wwwroot/huodouai.com/kunlun/videos"
MANIFEST_PATH = "/www/wwwroot/huodouai.com/kunlun/regist/manifest.json"
OMEGA = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def post_truth(tid, content, source, conf=0.99, meta=None):
    body = {
        "truth_id": tid, "truth_type": "data", "content": content,
        "source": source, "confidence": conf, "meta": meta or {},
    }
    req = urllib.request.Request(
        ZR_BASE + "/truth", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": ZR_KEY},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode()[:200]}
    except Exception as e:
        return {"_err": str(e)}

def collect():
    """返回 frames/videos 资产清单 + sha256"""
    frames, videos = [], []
    if os.path.isdir(FRAMES_DIR):
        for f in sorted(os.listdir(FRAMES_DIR)):
            if f.lower().endswith((".jpg", ".png", ".jpeg")):
                fp = os.path.join(FRAMES_DIR, f)
                frames.append({"file": f, "size": os.path.getsize(fp),
                               "sha256": sha256_file(fp),
                               "url": "/kunlun/frames/" + f,
                               "mtime": int(os.path.getmtime(fp))})
    if os.path.isdir(VIDEOS_DIR):
        for f in sorted(os.listdir(VIDEOS_DIR)):
            if f.lower().endswith((".mp4", ".mov", ".webm")):
                fp = os.path.join(VIDEOS_DIR, f)
                sz = os.path.getsize(fp)
                # 过滤低质测试样片：<700KB 视为测试产物，不进入作品库
                if sz < 700 * 1024:
                    print("  跳过低质测试样片:", f, sz // 1024, "KB")
                    continue
                videos.append({"file": f, "size": sz,
                               "sha256": sha256_file(fp),
                               "url": "/kunlun/videos/" + f,
                               "mtime": int(os.path.getmtime(fp))})
    return frames, videos

def main():
    frames, videos = collect()
    print(f"扫描到 关键帧 {len(frames)} / 成片 {len(videos)}")
    # 1) 写聚合归档真值（自动进溯源链）
    agg = post_truth(
        "TRUTH-KUNLUN-ARCHIVE-" + time.strftime("%Y%m%d"),
        {"omega": OMEGA, "did": DID, "source": "huodouai.com/kunlun",
         "frames": len(frames), "videos": len(videos),
         "note": "昆仑洞天创作资产归档确权"},
        source="huodouai.com/kunlun", conf=0.99,
        meta={"series": "kunlun", "kind": "archive"})
    print("聚合归档:", {k: agg.get(k) for k in ("truth_id", "dag_index", "dag_sha256", "gateway_sync", "_err")})
    # 2) 逐条写关键帧哈希
    n_ok = n_fail = 0
    for i, fr in enumerate(frames):
        tid = f"TRUTH-KUNLUN-FRAME-{i+1:03d}-{fr['file'].replace('frame_','').replace('.jpg','')}"
        r = post_truth(tid, fr, source="huodouai.com/kunlun/frames", meta={"series": "kunlun", "kind": "frame"})
        if "dag_index" in r: n_ok += 1
        else:
            n_fail += 1
            print("  FAIL", tid, r)
        time.sleep(0.1)
    print(f"关键帧确权写入 成功 {n_ok} / 失败 {n_fail}")
    # 3) 逐条写成片哈希
    for i, v in enumerate(videos):
        tid = f"TRUTH-KUNLUN-VIDEO-{i+1:03d}-{v['file'].replace('.mp4','')}"
        r = post_truth(tid, v, source="huodouai.com/kunlun/videos", meta={"series": "kunlun", "kind": "video"})
        if "dag_index" in r: n_ok += 1
        else:
            n_fail += 1
            print("  FAIL", tid, r)
        time.sleep(0.1)
    print(f"合计确权写入 成功 {n_ok} / 失败 {n_fail}")
    # 4) 写本地台账
    manifest = {
        "omega": OMEGA, "did": DID,
        "archived_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "frames": frames, "videos": videos,
    }
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("台账已写入", MANIFEST_PATH)
    return 0

if __name__ == "__main__":
    sys.exit(main())
