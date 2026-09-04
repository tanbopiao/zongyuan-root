#!/usr/bin/env python3
"""
M3-3: 豆包知识库RAG接入模块
支持知识库创建、文档上传、语义检索，与Ω-Brainμ真值基座联动
配置API Key后可直接使用，未配置时使用本地向量库降级
"""
import json
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
CONFIG_FILE = ROOT / "config" / "rag_config.json"
RAG_CACHE = ROOT / "cache" / "rag_cache"
RAG_CACHE.mkdir(parents=True, exist_ok=True)

class RAGEngine:
    """豆包知识库RAG引擎"""

    def __init__(self):
        self.config = self._load_config()
        self.api_key = self.config.get("doubao_api_key", "")
        self.base_url = self.config.get("base_url", "https://ark.cn-beijing.volces.com/api/v3")
        self.knowledge_base_id = self.config.get("knowledge_base_id", "")
        self.mode = "api" if self.api_key and self.knowledge_base_id else "local"
        self.local_store = self._init_local_store()

    def _load_config(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                return json.load(f)
        return {
            "doubao_api_key": "",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "knowledge_base_id": "",
            "embedding_model": "doubao-embedding-text-240715",
            "embedding_dim": 2560,
            "chunk_size": 500,
            "chunk_overlap": 50,
            "top_k": 5,
            "score_threshold": 0.3
        }

    def _save_config(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def _init_local_store(self):
        """初始化本地向量存储（降级方案）"""
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            from vector_search import LightVectorStore
            store = LightVectorStore("rag_knowledge_base")
            # 自动索引真值基座
            truth_dir = ROOT / "truth_base"
            if truth_dir.exists():
                for fp in truth_dir.glob("*.json"):
                    with open(fp) as f:
                        data = json.load(f)
                    text = json.dumps(data, ensure_ascii=False)
                    store.add(fp.stem, text, {"source": "truth_base", "file": fp.name})
            return store
        except Exception as e:
            print(f"本地向量存储初始化失败: {e}")
            return None

    def configure(self, api_key: str, knowledge_base_id: str, base_url: str = None):
        """配置豆包知识库API"""
        self.config["doubao_api_key"] = api_key
        self.config["knowledge_base_id"] = knowledge_base_id
        if base_url:
            self.config["base_url"] = base_url
        self.api_key = api_key
        self.knowledge_base_id = knowledge_base_id
        self.mode = "api"
        self._save_config()
        return {"status": "configured", "mode": "api", "knowledge_base_id": knowledge_base_id}

    def upload_document(self, file_path: str, metadata: dict = None) -> dict:
        """上传文档到知识库"""
        if self.mode == "api":
            # 调用豆包知识库API上传
            import requests
            url = f"{self.base_url}/knowledge_bases/{self.knowledge_base_id}/documents"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            files = {"file": open(file_path, "rb")}
            data = {"metadata": json.dumps(metadata or {})}
            resp = requests.post(url, headers=headers, files=files, data=data)
            return resp.json()
        else:
            # 本地模式：加入本地向量库
            fp = Path(file_path)
            if fp.exists():
                text = fp.read_text(errors="ignore")
                doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
                if self.local_store:
                    self.local_store.add(doc_id, text, metadata or {"source": "local_upload", "file": fp.name})
                return {"status": "uploaded_local", "doc_id": doc_id, "mode": "local"}
            return {"status": "error", "message": "file not found"}

    def search(self, query: str, top_k: int = None, score_threshold: float = None) -> dict:
        """语义检索"""
        top_k = top_k or self.config.get("top_k", 5)
        score_threshold = score_threshold or self.config.get("score_threshold", 0.3)

        if self.mode == "api":
            return self._api_search(query, top_k)
        else:
            return self._local_search(query, top_k)

    def _api_search(self, query: str, top_k: int) -> dict:
        """API模式检索"""
        import requests
        url = f"{self.base_url}/knowledge_bases/{self.knowledge_base_id}/search"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"query": query, "top_k": top_k}
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        return {"mode": "api", "query": query, "results": data.get("results", []), "total": data.get("total", 0)}

    def _local_search(self, query: str, top_k: int) -> dict:
        """本地模式检索"""
        if not self.local_store:
            return {"mode": "local", "query": query, "results": [], "error": "local_store_not_initialized"}
        results = self.local_store.search(query, top_k=top_k)
        return {
            "mode": "local",
            "query": query,
            "results": results,
            "total": len(results),
            "note": "使用本地hash embedding降级方案，配置API Key后升级为真实向量检索"
        }

    def index_truth_base(self):
        """将真值基座全量索引到RAG"""
        count = 0
        truth_dir = ROOT / "truth_base"
        if truth_dir.exists():
            for fp in truth_dir.glob("*.json"):
                with open(fp) as f:
                    data = json.load(f)
                # 分块索引
                formulas = data.get("formulas", []) + data.get("truth_formulas", [])
                for i, formula in enumerate(formulas):
                    if isinstance(formula, dict):
                        text = formula.get("name", "") + " " + formula.get("expression", "") + " " + formula.get("description", "")
                    else:
                        text = str(formula)
                    if self.local_store:
                        self.local_store.add(f"{fp.stem}_f{i}", text, {"source": "truth_base", "type": "formula"})
                    count += 1
        return {"indexed": count, "mode": self.mode}

    def get_status(self) -> dict:
        """获取RAG引擎状态"""
        return {
            "mode": self.mode,
            "api_configured": bool(self.api_key),
            "knowledge_base_id": self.knowledge_base_id or "not_configured",
            "local_store_ready": self.local_store is not None,
            "local_indexed_count": self.local_store.count() if self.local_store else 0,
            "config": {k: v for k, v in self.config.items() if k != "doubao_api_key"}
        }

if __name__ == "__main__":
    import sys
    rag = RAGEngine()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(rag.get_status(), ensure_ascii=False, indent=2))
        elif cmd == "search" and len(sys.argv) > 2:
            result = rag.search(sys.argv[2])
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif cmd == "index":
            result = rag.index_truth_base()
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif cmd == "configure" and len(sys.argv) > 3:
            result = rag.configure(sys.argv[2], sys.argv[3])
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(rag.get_status(), ensure_ascii=False, indent=2))
