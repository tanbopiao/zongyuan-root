#!/usr/bin/env python3
"""Ω-Brainμ 真值记忆中枢 V2.1 - 从truth_loader加载完整真值"""
import json, os, sys, hashlib, time, math, re
from collections import Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
from core.truth_loader import truth_loader

class VectorStoreV2:
    def __init__(self, dim=256):
        self.dim = dim
        self.docs = []
        self.idf = {}
        self._load_from_truth_loader()
        self._build_idf()
        self._precompute()
    
    def _tokenize(self, text):
        text = text.lower()
        en_words = re.findall(r'[a-z0-9]+', text)
        cn_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        cn_grams = []
        for seg in cn_chars:
            for i in range(len(seg)-1):
                cn_grams.append(seg[i:i+2])
        return en_words + cn_grams
    
    def _load_from_truth_loader(self):
        """从truth_loader加载有实际内容的真值"""
        for item in truth_loader.index:
            text = item.get("preview", "")
            if len(text) < 10: continue
            self.docs.append({
                "id": item["id"],
                "text": text,
                "category": item["category"],
                "file": item["file"],
                "vec": None
            })
        # 也加载Ω-Brainμ truth_index中有content的
        ti_path = "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json"
        if os.path.exists(ti_path):
            with open(ti_path) as f:
                data = json.load(f)
            for t in data.get("truths", []):
                content = t.get("content", "")
                if content and len(content) > 10:
                    self.docs.append({
                        "id": t.get("id", ""),
                        "text": content,
                        "category": t.get("category", t.get("type", "news")),
                        "file": "truth_index.json",
                        "vec": None
                    })
    
    def _build_idf(self):
        N = len(self.docs) or 1
        df = Counter()
        for doc in self.docs:
            tokens = set(self._tokenize(doc["text"]))
            for t in tokens: df[t] += 1
        self.idf = {t: math.log((N+1)/(c+1))+1 for t,c in df.items()}
    
    def _embed(self, text):
        vec = [0.0]*self.dim
        tokens = self._tokenize(text)
        if not tokens: return vec
        tf = Counter(tokens)
        max_tf = max(tf.values())
        for token, count in tf.items():
            h = hashlib.md5(token.encode()).hexdigest()
            idx = int(h[:8],16) % self.dim
            tf_val = 0.5 + 0.5*count/max_tf
            idf_val = self.idf.get(token, 1.0)
            sign = 1 if int(h[8:9],16)%2==0 else -1
            vec[idx] += sign * tf_val * idf_val
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
        return [v/norm for v in vec]
    
    def _precompute(self):
        for doc in self.docs:
            doc["vec"] = self._embed(doc["text"])
    
    def _cosine(self,a,b): return sum(x*y for x,y in zip(a,b))
    
    def _keyword_score(self, query, text):
        q = set(self._tokenize(query))
        d = set(self._tokenize(text))
        return len(q&d)/len(q) if q else 0.0
    
    def recall(self, query, top_k=8):
        q_vec = self._embed(query)
        scored = []
        for doc in self.docs:
            sem = self._cosine(q_vec, doc["vec"])
            kw = self._keyword_score(query, doc["text"])
            hybrid = 0.5*sem + 0.5*kw
            scored.append((hybrid, sem, kw, doc))
        scored.sort(key=lambda x:x[0], reverse=True)
        return [{"id":d["id"],"category":d["category"],"preview":d["text"][:150],
                 "hybrid_score":round(h,4),"semantic":round(s,4),"keyword":round(k,4)} 
                for h,s,k,d in scored[:top_k]]
    
    def stats(self):
        return {"total_docs":len(self.docs),"dim":self.dim,
                "categories":list(set(d["category"] for d in self.docs)),
                "engine":"tfidf_hash_hybrid_v2.1"}

vector_store = VectorStoreV2()

class OmegaHandler(BaseHTTPRequestHandler):
    def _json(self,data,code=200):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        path=self.path.split("?")[0]
        q=self.path.split("q=")[-1] if "q=" in self.path else ""
        if path=="/health":
            self._json({"status":"healthy","service":"Ω-Brainμ","version":"2.1-V2","truths":truth_loader.total,"vector_docs":len(vector_store.docs)})
        elif path=="/status":
            self._json({"truth_stats":truth_loader.get_stats(),"vector":vector_store.stats(),"uptime":int(time.time()-start_time)})
        elif path=="/truth/stats":
            self._json(truth_loader.get_stats())
        elif path.startswith("/truth/search"):
            self._json({"query":q,"results":truth_loader.search(q,10)})
        elif path.startswith("/recall"):
            self._json({"query":q,"results":vector_store.recall(q,8),"engine":vector_store.stats()["engine"]})
        elif path=="/kernel/snapshots":
            self._json({"snapshots":truth_loader.get_snapshots()})
        elif path=="/":
            self._json({"service":"Ω-Brainμ V2.1","endpoints":["/health","/status","/recall?q=","/truth/search?q=","/truth/stats","/kernel/snapshots"]})
        else:
            self._json({"error":"not_found","path":path},404)
    def log_message(self,format,*args): pass

if __name__=="__main__":
    start_time=time.time()
    port=int(sys.argv[sys.argv.index("--port")+1]) if "--port" in sys.argv else 8000
    host=sys.argv[sys.argv.index("--host")+1] if "--host" in sys.argv else "0.0.0.0"
    server=HTTPServer((host,port),OmegaHandler)
    print(f"Ω-Brainμ V2.1 on {host}:{port} | truths={truth_loader.total} vector_docs={len(vector_store.docs)}")
    server.serve_forever()
