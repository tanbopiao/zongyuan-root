#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 历史真值批量灌入向量库
DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | V1.0
"""
import json, time, urllib.request

VECTOR_URL = "http://127.0.0.1:8003/api/v1/add"
INDEX_PATH = "/home/user/ZONGYUAN-ROOT/memory_index.json"

def add_doc(doc_id, text, metadata):
    body = json.dumps({"id": doc_id, "text": text, "metadata": metadata}).encode()
    req = urllib.request.Request(VECTOR_URL, data=body, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

def main():
    idx = json.load(open(INDEX_PATH))
    entries = idx.get("asset_entries", [])
    print(f"待灌入: {len(entries)} 条")

    # 先查当前已有
    try:
        import urllib.request as u
        req = u.Request("http://127.0.0.1:8003/api/v1/stats", method="GET")
        with u.urlopen(req, timeout=10) as r:
            stats = json.load(r)
        existing = stats.get("doc_count", 0)
    except Exception as e:
        existing = 0
        print("⚠️ stats获取失败:", e)
    print(f"当前向量库已有: {existing} 条")

    ok = 0; fail = 0; skip = 0
    for i, e in enumerate(entries):
        doc_id = f"kd-{str(e.get('asset_id', 'misc')).lower()}-{i}"
        text = e.get("summary", "")[:500]
        metadata = {
            "asset_id": str(e.get("asset_id","misc")),
            "priority": e.get("priority","D"),
            "meta_class": e.get("meta_class",""),
            "sha256": e.get("sha256",""),
            "lock_level": e.get("lock_level",""),
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω"
        }
        if not text.strip():
            skip += 1; continue
        try:
            r = add_doc(doc_id, text, metadata)
            if r.get("status") == "added": ok += 1
            else: fail += 1
        except Exception as ex:
            fail += 1
        if (i+1) % 100 == 0:
            print(f"  进度 {i+1}/{len(entries)} | ok={ok} fail={fail}")
            time.sleep(1)  # 限流保护
    print(f"✅ 灌入完成: ok={ok} fail={fail} skip={skip}")

if __name__ == "__main__":
    main()
