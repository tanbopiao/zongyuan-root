import os
import json
import hashlib
from pathlib import Path
import requests
from datetime import datetime

# IMA API 配置（从环境变量读取）
IMA_API_KEY = os.environ.get("IMA_API_KEY", "")
IMA_CLIENT_ID = os.environ.get("IMA_CLIENT_ID", "")
IMA_API_URL = "https://ima.qq.com/api/v1/"

# 入库源目录
INGEST_SOURCES = [
    "/.octop/workspaces/main/logs/",
    "/zongyuan-yuanji/persist/seed_truth/",
    "/.octop/workspaces/main/*.md"
]

# 去重哈希表
INGESTED_HASHES = Path("/zongyuan-yuanji/data/.ingested_hashes.json")

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def load_ingested() -> set:
    if INGESTED_HASHES.exists():
        return set(json.loads(INGESTED_HASHES.read_text()))
    return set()

def save_ingested(hashes: set):
    INGESTED_HASHES.write_text(json.dumps(list(hashes), indent=2))

def scan_new_documents() -> list:
    ingested = load_ingested()
    new_docs = []
    for source_pattern in INGEST_SOURCES:
        for f in Path("/").glob(source_pattern.lstrip("/")):
            if f.is_file() and f.suffix in (".md", ".json", ".yaml"):
                content = f.read_text()
                h = compute_hash(content)
                if h not in ingested:
                    new_docs.append({
                        "path": str(f),
                        "hash": h,
                        "content": content,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    })
    return new_docs

def ingest_to_ima(doc: dict, target_kb: str = "个人库"):
    payload = {
        "kb_name": target_kb,
        "title": Path(doc["path"]).name,
        "content": doc["content"][:10000],  # 截断超长内容
        "source": doc["path"],
        "timestamp": doc["modified"],
        "client_id": IMA_CLIENT_ID,
        "api_key": IMA_API_KEY
    }
    response = requests.post(IMA_API_URL + "add_knowledge", data=payload)
    if response.status_code == 200:
        print(f"[INGEST] {payload['title']} → {target_kb}")
    else:
        print(f"[ERROR] {payload['title']} → {target_kb} (Failed to ingest)")

def run():
    new_docs = scan_new_documents()
    if not new_docs:
        print("[SCAN] 无新增文档")
        return
    print(f"[SCAN] 发现 {len(new_docs)} 个新文档")
    ingested = load_ingested()
    for doc in new_docs:
        target_kb = "个人库"
        ingest_to_ima(doc, target_kb)
        ingested.add(doc["hash"])
    save_ingested(ingested)
    print(f"[DONE] 入库完成，累计 {len(ingested)} 条")

if __name__ == "__main__":
    run()