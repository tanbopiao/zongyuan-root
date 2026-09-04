#!/usr/bin/env python3
"""Ω-Brainμ 真值记忆中枢 V2.1 - 从truth_loader加载完整真值"""
import json, os, sys, hashlib, time, math, re
from collections import Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
from core.truth_loader import truth_loader

class VectorStoreV3:
    """Ω-Brainμ 向量存储 V3 - 1024维增强哈希+实体识别+语义位置编码"""
    # IP核心实体（高权重语义锚点）
    IP_ENTITIES = ["太阴月神","九天玄女","赤霞司命","绯灵汐","赤凰伺主","凰绾",
                   "玄鸟","凤凰","朱雀","昆仑洞天","天元法则","阴阳分立",
                   "雌雄纯一","纯乌黑长发","九头身","青黑长裙","赤金长裙",
                   "玄鸟图腾","桂月华光","天书","司命之力","霞光万道",
                   "ZONGYUAN-ROOT","Ω-Brainμ","火斗云智","短剧智能体"]
    
    def __init__(self, dim=1024):
        self.dim = dim
        self.docs = []
        self.idf = {}
        self.entity_weights = {}
        self._load_from_truth_loader()
        self._build_idf()
        self._build_entity_weights()
        self._precompute()
    
    def _tokenize(self, text):
        text = text.lower()
        en_words = re.findall(r'[a-z0-9]+', text)
        cn_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        cn_grams = []
        for seg in cn_chars:
            for i in range(len(seg)-1):
                cn_grams.append(seg[i:i+2])
            for i in range(len(seg)-2):
                cn_grams.append(seg[i:i+3])  # 新增三元组
        return en_words + cn_grams
    
    def _extract_entities(self, text):
        """提取IP核心实体，返回(实体列表, 实体权重和)"""
        found = []
        for ent in self.IP_ENTITIES:
            if ent in text:
                found.append(ent)
        return found
    
    def _build_entity_weights(self):
        """实体IDF权重：稀有实体权重更高"""
        N = len(self.docs) or 1
        df = Counter()
        for doc in self.docs:
            for ent in self.IP_ENTITIES:
                if ent in doc["text"]:
                    df[ent] += 1
        self.entity_weights = {ent: math.log((N+1)/(c+1))+1 for ent,c in df.items()}
    
    def _load_from_truth_loader(self):
        for item in truth_loader.index:
            text = item.get("preview", "")
            if len(text) < 10: continue
            self.docs.append({"id": item["id"], "text": text,
                "category": item["category"], "file": item["file"], "vec": None})
        ti_path = "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json"
        if os.path.exists(ti_path):
            with open(ti_path) as f:
                data = json.load(f)
            for t in data.get("truths", []):
                content = t.get("content", "")
                if content and len(content) > 10:
                    self.docs.append({"id": t.get("id",""), "text": content,
                        "category": t.get("category",t.get("type","news")),
                        "file": "truth_index.json", "vec": None})
    
    def _build_idf(self):
        N = len(self.docs) or 1
        df = Counter()
        for doc in self.docs:
            for t in set(self._tokenize(doc["text"])):
                df[t] += 1
        self.idf = {t: math.log((N+1)/(c+1))+1 for t,c in df.items()}
    
    def _embed(self, text):
        """1024维增强哈希：MD5+SHA1双哈希+实体加权+位置编码"""
        vec = [0.0] * self.dim
        tokens = self._tokenize(text)
        if not tokens: return vec
        tf = Counter(tokens)
        max_tf = max(tf.values())
        
        # 1. TF-IDF哈希向量（双哈希减少碰撞）
        for token, count in tf.items():
            h1 = hashlib.md5(token.encode()).hexdigest()
            h2 = hashlib.sha1(token.encode()).hexdigest()
            idx1 = int(h1[:8], 16) % self.dim
            idx2 = int(h2[:8], 16) % self.dim
            tf_val = 0.5 + 0.5 * count / max_tf
            idf_val = self.idf.get(token, 1.0)
            weight = tf_val * idf_val
            sign1 = 1 if int(h1[8:9], 16) % 2 == 0 else -1
            sign2 = 1 if int(h2[8:9], 16) % 2 == 0 else -1
            vec[idx1] += sign1 * weight
            vec[idx2] += sign2 * weight * 0.5  # 第二哈希半权重
        
        # 2. IP实体语义位置编码（实体映射到固定维度区间）
        entities = self._extract_entities(text)
        for i, ent in enumerate(entities):
            ent_hash = int(hashlib.md5(ent.encode()).hexdigest()[:8], 16)
            base_idx = (ent_hash % (self.dim // 4)) * 4  # 每个实体占4维
            ent_w = self.entity_weights.get(ent, 2.0)
            for j in range(4):
                vec[base_idx + j] += ent_w * (1.0 - j * 0.2)
        
        # 3. L2归一化
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
        return [v / norm for v in vec]
    
    def _precompute(self):
        for doc in self.docs:
            doc["vec"] = self._embed(doc["text"])
    
    def _cosine(self, a, b):
        return sum(x*y for x,y in zip(a,b))
    
    def _keyword_score(self, query, text):
        q = set(self._tokenize(query))
        d = set(self._tokenize(text))
        return len(q & d) / len(q) if q else 0.0
    
    def _entity_overlap(self, query, text):
        """实体重叠得分：IP实体匹配权重高"""
        q_ents = set(self._extract_entities(query))
        t_ents = set(self._extract_entities(text))
        if not q_ents: return 0.0
        return len(q_ents & t_ents) / len(q_ents)
    
    def recall(self, query, top_k=8):
        q_vec = self._embed(query)
        scored = []
        for doc in self.docs:
            sem = self._cosine(q_vec, doc["vec"])
            kw = self._keyword_score(query, doc["text"])
            ent = self._entity_overlap(query, doc["text"])
            # 混合权重：语义55% + 关键词25% + 实体20%
            hybrid = 0.55 * sem + 0.25 * kw + 0.20 * ent
            scored.append((hybrid, sem, kw, ent, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"id": d["id"], "category": d["category"],
                 "preview": d["text"][:150],
                 "hybrid_score": round(h,4), "semantic": round(s,4),
                 "keyword": round(k,4), "entity_match": round(e,4)}
                for h,s,k,e,d in scored[:top_k]]
    
    def stats(self):
        return {"total_docs": len(self.docs), "dim": self.dim,
                "categories": list(set(d["category"] for d in self.docs)),
                "engine": "enhanced_hash_1024_v3.0",
                "ip_entities": len(self.IP_ENTITIES),
                "hybrid_weights": "sem55/kw25/entity20"}

vector_store = VectorStoreV3()

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
            self._json({"status":"healthy","service":"Ω-Brainμ","version":"3.0-V3","truths":truth_loader.total,"vector_docs":len(vector_store.docs)})
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
            self._json({"service":"Ω-Brainμ V3.0","endpoints":["/health","/status","/recall?q=","/truth/search?q=","/truth/stats","/kernel/snapshots"]})
        else:
            self._json({"error":"not_found","path":path},404)
    def log_message(self,format,*args): pass

if __name__=="__main__":
    start_time=time.time()
    port=int(sys.argv[sys.argv.index("--port")+1]) if "--port" in sys.argv else 8000
    host=sys.argv[sys.argv.index("--host")+1] if "--host" in sys.argv else "0.0.0.0"
    server=HTTPServer((host,port),OmegaHandler)
    print(f"Ω-Brainμ V3.0 on {host}:{port} | truths={truth_loader.total} vector_docs={len(vector_store.docs)}")
    server.serve_forever()
