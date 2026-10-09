"""
自建RAG算子 - 基于本地向量库的剧本增强
完全自主可控，不依赖第三方收费服务
复用vector_server (chromadb + sentence-transformers)
"""
import requests, json

VECTOR_API = "http://127.0.0.1:8003/api/v1"
AI_PROXY = "http://127.0.0.1:8021"

class LocalRAGOperators:
    """本地RAG算子组 - 知识库检索+剧本增强"""
    
    def __init__(self, config):
        self.config = config
        self.enabled = True  # 本地RAG默认启用
    
    def knowledge_search(self, query, top_k=5, category=None):
        """算子L1：知识库检索 - 从本地向量库检索相关内容"""
        try:
            payload = {"query": query, "n_results": top_k}
            r = requests.post(VECTOR_API + "/query", json=payload, timeout=30)
            data = r.json()
            results = []
            for item in data.get("results", []):
                results.append({
                    "text": item.get("text", ""),
                    "distance": item.get("distance", 1.0),
                    "metadata": item.get("metadata", {})
                })
            return {"success": True, "results": results, "count": len(results), "operator": "L1_search"}
        except Exception as e:
            return {"success": False, "error": str(e), "operator": "L1_search"}
    
    def enhance_script(self, template_name, base_script, knowledge_context=""):
        """算子L2：剧本增强 - 基于本地RAG检索结果增强剧本质量"""
        try:
            # 1. 检索知识库
            search_result = self.knowledge_search(template_name + " 剧本 角色 神话", top_k=5)
            context = knowledge_context
            if search_result.get("success"):
                for item in search_result.get("results", []):
                    if item.get("distance", 1.0) < 0.7:  # 只取相似度高的
                        context += item["text"][:300] + "\n"
            
            # 2. 基于检索结果增强剧本
            if context:
                prompt = "你是专业短剧编剧。请基于以下参考资料优化剧本，增强东方神话元素、人物塑造和冲突张力。\n\n参考资料：\n%s\n\n原剧本：\n%s\n\n优化后的剧本：" % (context[:1500], base_script[:800])
            else:
                prompt = "你是专业短剧编剧。请优化以下剧本，增强东方神话元素、人物塑造和冲突张力。\n\n原剧本：\n%s\n\n优化后的剧本：" % base_script[:800]
            
            r = requests.post(AI_PROXY + "/chat", json={"message": prompt, "model": "auto", "temperature": 0.7}, timeout=60)
            data = r.json()
            enhanced = data.get("result", base_script)
            
            return {
                "success": True,
                "script": enhanced,
                "enhanced_by": "local_rag",
                "knowledge_used": len(context) > 0,
                "operator": "L2_enhance"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "script": base_script, "operator": "L2_enhance"}
    
    def add_knowledge(self, text, category="general", source="manual"):
        """算子L3：添加知识 - 手动添加知识条目到向量库"""
        try:
            import hashlib, time
            doc_id = hashlib.md5(text.encode()).hexdigest()[:16]
            r = requests.post(VECTOR_API + "/add", json={"id": doc_id, "text": text, "metadata": {"category": category, "source": source, "timestamp": time.time()}}, timeout=30)
            return {"success": r.status_code == 200, "doc_id": doc_id, "operator": "L3_add"}
        except Exception as e:
            return {"success": False, "error": str(e), "operator": "L3_add"}
    
    def get_status(self):
        """算子L4：RAG状态检查"""
        try:
            r = requests.get(VECTOR_API + "/stats", timeout=5)
            stats = r.json()
            return {"success": True, "enabled": True, "vector_stats": stats, "operator": "L4_status"}
        except Exception as e:
            return {"success": True, "enabled": True, "error": str(e), "operator": "L4_status"}
