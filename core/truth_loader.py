#!/usr/bin/env python3
"""ZONGYUAN-ROOT 统一真值加载器"""
import json, os, glob, hashlib, threading
from typing import Any, Dict, List, Optional

TRUTH_DIRS = ["/opt/ZONGYUAN-ROOT/truth_architecture", "/opt/ZONGYUAN-ROOT/Ω-Brainμ", "/opt/ZONGYUAN-ROOT/autonomous_kernel_protocol"]
KERNEL_FILE = "/opt/ZONGYUAN-ROOT/kernel.json"

class TruthLoader:
    _instance = None
    _lock = threading.Lock()
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._loaded = False
        return cls._instance
    def __init__(self):
        if not self._loaded:
            self.truths = {}
            self.categories = {}
            self.index = []
            self.kernel = {}
            self._load_all()
            self._loaded = True
    def _load_all(self):
        count = 0
        for tdir in TRUTH_DIRS:
            if not os.path.isdir(tdir): continue
            for f in glob.glob(os.path.join(tdir, "**/*.json"), recursive=True):
                try:
                    with open(f) as fp: data = json.load(fp)
                    tid = "TRUTH-" + hashlib.md5(f.encode()).hexdigest()[:12]
                    self.truths[tid] = data
                    cat = self._detect_category(f, data)
                    self.categories.setdefault(cat, []).append(tid)
                    self.index.append({"id": tid, "file": f, "category": cat, "preview": json.dumps(data, ensure_ascii=False)[:100]})
                    count += 1
                except: pass
        try:
            with open(KERNEL_FILE) as f: self.kernel = json.load(f)
        except: pass
        self.total = count
    def _detect_category(self, filepath, data):
        name = os.path.basename(filepath).lower()
        if "axiom" in name: return "axiom"
        if "truth" in name: return "truth"
        if "snapshot" in name: return "snapshot"
        if "protocol" in name: return "protocol"
        if "config" in name: return "config"
        return "other"
    def get(self, truth_id): return self.truths.get(truth_id)
    def get_by_category(self, category): return [self.truths[tid] for tid in self.categories.get(category, [])]
    def search(self, query, limit=5):
        q = query.lower()
        results = []
        for item in self.index:
            score = 0
            if q in item["preview"].lower(): score += 2
            if q in item["file"].lower(): score += 1
            if score > 0: results.append({**item, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    def get_kernel(self): return self.kernel
    def get_snapshots(self): return self.kernel.get("snapshots", [])
    def get_stats(self):
        return {"total_truths": self.total, "categories": {k: len(v) for k,v in self.categories.items()}, "kernel_snapshots": len(self.kernel.get("snapshots",[])), "loaded": True}
    def reload(self):
        with self._lock:
            self.truths.clear(); self.categories.clear(); self.index.clear(); self._load_all()

truth_loader = TruthLoader()
if __name__ == "__main__":
    s = truth_loader.get_stats()
    print(f"真值加载器: {s['total_truths']}条, 分类={s['categories']}, 快照={s['kernel_snapshots']}")
    print(f"搜索'axiom': {len(truth_loader.search('axiom'))}条")
